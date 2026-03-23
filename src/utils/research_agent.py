"""Research agent — launch Opus subprocess to research workbench tools.

Spawns `claude -p` as a subprocess to run a COSTAR research prompt against
a workbench tool. The agent writes `research.md` to the output directory;
its stream-json output goes to `agent.log`.

Public API:
    launch_research_agent(tool, output_dir) -> subprocess.Popen
    is_agent_running(pid) -> bool
    tail_log(log_file, n=30) -> str
    parse_research_output(research_md) -> dict
    render_research_html(research_md, output_dir, tool_name) -> Path
"""

import html as html_module
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import markdown

logger = logging.getLogger(__name__)

_OPUS_MODEL = "claude-opus-4-6"
_SONNET_MODEL = "claude-sonnet-4-6"
_MODEL_FALLBACK_CHAIN = [_OPUS_MODEL, _SONNET_MODEL]
_MAX_RETRIES = 2
_WORKBENCH_ROOT = Path.home() / "research-workbench"

# Tools the research agent is allowed to use without interactive permission prompts.
# Covers: web search, docs lookup, file I/O for writing research.md.
_ALLOWED_TOOLS = [
    "WebSearch",
    "WebFetch",
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "mcp__exa-web-search__web_search_exa",
    "mcp__exa-web-search__get_code_context_exa",
    "mcp__context7__resolve-library-id",
    "mcp__context7__query-docs",
    "mcp__fetch__fetch",
]

# ---------------------------------------------------------------------------
# COSTAR research prompt template
# ---------------------------------------------------------------------------

_COSTAR_PROMPT_TEMPLATE = """\
<context>
Tool name: {name}
Category: {category}
Source: {source}
Description: {description}
{project_context}{transcript_context}</context>

<objective>
Research this tool thoroughly. Use Exa to search for documentation, GitHub \
repositories, and real-world usage examples. Use context7 to pull official \
API documentation where available. Assess whether the tool can be evaluated \
programmatically (headless, via code) or requires manual hands-on evaluation. \
Design a minimal, focused experiment that could be run within a sandbox \
environment.{project_objective}
</objective>

<style>
Structured markdown. Required sections (use exactly these headings):
## Overview
## How to Install
## Key APIs / Concepts
## Programmatic Assessment
## Experiment Design
## Safety Notes

The ## Programmatic Assessment section MUST start with YES or NO as the \
first word, followed by your reasoning.
</style>

<tone>
Terse, technically precise. No marketing language. Written for a developer \
deciding whether to invest time building a sandbox experiment.
</tone>

<audience>
Senior developer who wants to quickly assess whether to invest time \
integrating this tool into a project. Assume strong Python/CLI background.
</audience>

<response>
Write the full research report to {output_path}. \
Do not print the report content to stdout. \
Only write the file. Confirm the file was written.

SECURITY NOTE: Verify all package names match official PyPI or npm registry \
pages exactly. Flag any name that resembles a well-known package with slight \
typos — treat as potentially malicious.
</response>
"""


# ---------------------------------------------------------------------------
# Instagram topic-centric COSTAR prompt template
# ---------------------------------------------------------------------------

_INSTAGRAM_COSTAR_PROMPT_TEMPLATE = """\
<context>
Topic: {name}
Account: {account}
Date: {date}
Source URL: {source_url}
Key points: {key_points}
Keywords: {keywords}
Caption: {caption}
{project_context}{transcript_context}</context>

<objective>
Identify what this post is about. Research the underlying tool, pattern, or \
concept discussed. Use Exa to search for documentation, GitHub repositories, \
and real-world usage examples. Use context7 to pull official API documentation \
where available. Judge whether the topic is actionable (can be implemented \
now), experimental (needs evaluation), or informational (awareness only). \
Design a minimal evaluation path.{project_objective}{low_signal_note}
</objective>

<style>
Structured markdown. Required sections (use exactly these headings):
## Overview
## Getting Started
## Key APIs / Concepts
## Programmatic Assessment
## Experiment Design
## Safety Notes

The ## Programmatic Assessment section MUST start with YES or NO as the \
first word, followed by your reasoning.
</style>

<tone>
Terse, technically precise. No marketing language. Written for a developer \
deciding whether to invest time exploring this topic.
</tone>

<audience>
Senior developer who wants to quickly assess whether to invest time \
integrating this tool into a project. Assume strong Python/CLI background.
</audience>

<response>
Write the full research report to {output_path}. \
Do not print the report content to stdout. \
Only write the file. Confirm the file was written.

SECURITY NOTE: Verify all package names match official PyPI or npm registry \
pages exactly. Flag any name that resembles a well-known package with slight \
typos — treat as potentially malicious.
</response>
"""


def _fmt_safe(value: str) -> str:
    """Escape curly braces so ``str.format()`` treats them as literals.

    Vault-sourced free-text (captions, transcripts, project names) may
    contain ``{`` or ``}`` which ``str.format()`` interprets as placeholders.

    Args:
        value: Raw string from vault or parser.

    Returns:
        String with ``{`` → ``{{`` and ``}`` → ``}}``.
    """
    return value.replace("{", "{{").replace("}", "}}")


def _build_project_context(
    item: dict[str, Any],
) -> tuple[str, str]:
    """Build project context and objective strings from item fields.

    Args:
        item: Item dict (tool, method, or instagram post).

    Returns:
        Tuple of (project_context, project_objective) strings.
    """
    project_dir = item.get("project_dir", "")
    project_name = item.get("project_name", "")
    if project_dir:
        return (
            f"\nTarget project: {_fmt_safe(project_name)}\nProject directory: {_fmt_safe(project_dir)}\n",
            " Also explore the project directory to understand the existing "
            "codebase — look at its structure, dependencies, and patterns. "
            "Add a ## Integration Notes section after Experiment Design with "
            "concrete suggestions for how this tool fits into the project.",
        )
    return "", ""


def _build_transcript_context(item: dict[str, Any]) -> str:
    """Build transcript context block, truncated to 4000 chars.

    Args:
        item: Item dict with optional ``transcript`` field.

    Returns:
        Transcript XML block, or empty string if no transcript.
    """
    transcript = item.get("transcript", "")
    if not transcript:
        return ""
    truncated = transcript[:4000]
    logger.debug("Injecting transcript context: %d chars", len(truncated))
    return f"\n<transcript>\n{_fmt_safe(truncated)}\n</transcript>\n"


def _is_low_signal(item: dict[str, Any]) -> bool:
    """Detect low-signal Instagram posts.

    Low-signal: no transcript, no key_points, and caption < 20 chars.

    Args:
        item: Instagram post dict.

    Returns:
        True if the post has very little actionable content.
    """
    has_transcript = bool(item.get("transcript", "").strip())
    has_key_points = bool(item.get("key_points"))
    caption_length = len(item.get("caption", "").strip())
    return not has_transcript and not has_key_points and caption_length < 20


def _build_instagram_prompt(item: dict[str, Any], output_dir: Path) -> str:
    """Build topic-centric COSTAR prompt for Instagram posts.

    Args:
        item: Instagram post dict from instagram_parser.
        output_dir: Directory where research.md will be written.

    Returns:
        Fully interpolated prompt string.
    """
    project_context, project_objective = _build_project_context(item)
    transcript_context = _build_transcript_context(item)

    low_signal_note = ""
    if _is_low_signal(item):
        low_signal_note = (
            " NOTE: This post has thin source material (no transcript, no key "
            "points, short caption). In ## Overview, note the limited source. "
            "In ## Programmatic Assessment, start with NO unless external "
            "research finds actionable content. In ## Experiment Design, "
            "recommend what evidence is needed before proceeding."
        )

    key_points = item.get("key_points", [])
    key_points_str = "; ".join(key_points) if key_points else "None"
    keywords = item.get("keywords", [])
    keywords_str = ", ".join(keywords) if keywords else "None"

    return _INSTAGRAM_COSTAR_PROMPT_TEMPLATE.format(
        name=_fmt_safe(item.get("name", "Unknown")),
        account=_fmt_safe(item.get("account", "Unknown")),
        date=item.get("date", "Unknown"),
        source_url=item.get("source_url", ""),
        key_points=_fmt_safe(key_points_str),
        keywords=_fmt_safe(keywords_str),
        caption=_fmt_safe(item.get("caption", "")),
        project_context=project_context,
        transcript_context=transcript_context,
        project_objective=project_objective,
        low_signal_note=low_signal_note,
        output_path=str(output_dir / "research.md"),
    )


def _build_prompt(tool: dict[str, Any], output_dir: Path) -> str:
    """Build the COSTAR research prompt interpolated with item fields.

    Branches on ``source_type``: Instagram posts get a topic-centric prompt;
    tools and methods get the standard tool-centric prompt.

    Args:
        tool: Item dict from parser (tool, method, or instagram post).
        output_dir: Directory where research.md will be written.

    Returns:
        Fully interpolated prompt string.
    """
    source_type = tool.get("source_type", "tool")
    if source_type == "instagram":
        return _build_instagram_prompt(tool, output_dir)

    description = (
        tool.get("what it does")
        or tool.get("description")
        or tool.get("why it matters")
        or ""
    )

    project_context, project_objective = _build_project_context(tool)
    transcript_context = _build_transcript_context(tool)

    return _COSTAR_PROMPT_TEMPLATE.format(
        name=_fmt_safe(tool.get("name", "Unknown")),
        category=_fmt_safe(tool.get("category", "Unknown")),
        source=_fmt_safe(tool.get("source", "Unknown")),
        description=_fmt_safe(description),
        project_context=project_context,
        transcript_context=transcript_context,
        project_objective=project_objective,
        output_path=str(output_dir / "research.md"),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def launch_research_agent(
    tool: dict[str, Any],
    output_dir: Path,
    model: str | None = None,
) -> tuple[subprocess.Popen, str]:
    """Launch research agent as a subprocess.

    The agent writes ``research.md`` to ``output_dir``. Stream-JSON output
    and stderr are redirected to ``{output_dir}/agent.log`` via a file handle.

    Args:
        tool: Tool dict (from tools_parser) to research.
        output_dir: Directory to write research.md and agent.log.
        model: Model ID to use. Defaults to Opus.

    Returns:
        Tuple of (subprocess.Popen handle, model ID used).
        Caller should save .pid and model to workbench entry.

    Raises:
        FileNotFoundError: If the ``claude`` CLI is not found in PATH.
    """
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise FileNotFoundError("claude CLI not found in PATH")

    resolved_model = model or _OPUS_MODEL
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt = _build_prompt(tool, output_dir)
    log_path = output_dir / "agent.log"

    cmd = [
        claude_bin,
        "-p",
        prompt,
        "--model",
        resolved_model,
        "--fallback-model",
        _SONNET_MODEL,
        "--allowedTools",
        ",".join(_ALLOWED_TOOLS),
        "--output-format",
        "stream-json",
        "--verbose",
    ]

    # Set cwd to project directory if available, so the agent can explore it
    project_dir = tool.get("project_dir", "")
    cwd = Path(project_dir) if project_dir else None
    if cwd and not cwd.is_dir():
        logger.warning("project_dir '%s' not found, ignoring", cwd)
        cwd = None

    log_fh = open(log_path, "w", encoding="utf-8")  # noqa: WPS515
    try:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=log_fh,
            stderr=log_fh,
            cwd=cwd,
            shell=False,
        )
    finally:
        # Parent closes its copy — child inherited its own fd via Popen
        log_fh.close()

    logger.info(
        "Launched research agent for '%s' (pid=%d, model=%s), log=%s",
        tool.get("name"),
        proc.pid,
        resolved_model,
        log_path,
    )
    return proc, resolved_model


def get_fallback_model(current_model: str | None) -> str | None:
    """Return the next model in the fallback chain, or None if exhausted.

    Args:
        current_model: The model that just failed.

    Returns:
        Next model ID to try, or None if no fallback available.
    """
    current = current_model or _OPUS_MODEL
    try:
        idx = _MODEL_FALLBACK_CHAIN.index(current)
    except ValueError:
        return None
    next_idx = idx + 1
    if next_idx < len(_MODEL_FALLBACK_CHAIN):
        return _MODEL_FALLBACK_CHAIN[next_idx]
    return None


def is_retryable_failure(log_file: Path) -> bool:
    """Check whether a research agent failed due to a transient API error.

    Scans the last 20 lines of the log for overload (529), internal
    server error (500), or other transient indicators.

    Args:
        log_file: Path to the agent.log file.

    Returns:
        True if the failure appears transient and worth retrying.
    """
    if not log_file.is_file():
        return False
    try:
        raw = log_file.read_text(encoding="utf-8", errors="replace")
        # Check the last ~4KB for transient error markers
        tail = raw[-4096:]
    except OSError:
        return False
    return any(
        marker in tail
        for marker in ("529", "Overloaded", "500", "Internal server error")
    )


# Keep old name as alias for backward compatibility in tests
is_overload_failure = is_retryable_failure


def parse_agent_activity(log_file: Path, max_items: int = 8) -> list[str]:
    """Extract recent tool-use activity from a stream-json agent log.

    Parses the log for ``tool_use`` content blocks in assistant messages
    and returns human-readable descriptions of the most recent tool calls.

    Args:
        log_file: Path to the agent.log file.
        max_items: Maximum number of activity items to return.

    Returns:
        List of human-readable activity strings (most recent last).
    """
    if not log_file.is_file():
        return []

    activities: list[str] = []

    for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        if obj.get("type") != "assistant":
            continue

        msg = obj.get("message", {})
        for block in msg.get("content", []):
            if block.get("type") != "tool_use":
                continue
            label = _describe_tool_call(block)
            if label:
                activities.append(label)

    return activities[-max_items:]


def _describe_tool_call(block: dict[str, Any]) -> str:
    """Convert a tool_use block into a short human-readable description.

    Args:
        block: A tool_use content block from stream-json.

    Returns:
        Short description string, or empty string if unrecognizable.
    """
    name = block.get("name", "")
    inp = block.get("input", {})

    if name == "Read":
        path = inp.get("file_path", "")
        return f"Reading {Path(path).name}" if path else "Reading file"
    if name == "Write":
        path = inp.get("file_path", "")
        return f"Writing {Path(path).name}" if path else "Writing file"
    if name == "Glob":
        return f"Searching files: {inp.get('pattern', '')}"
    if name == "Grep":
        return f"Searching code: {inp.get('pattern', '')[:40]}"
    if name == "Agent":
        return f"Agent: {inp.get('description', '')[:50]}"
    if "fetch" in name.lower():
        url = inp.get("url", "")
        if url:
            # Show domain + first path segment
            from urllib.parse import urlparse

            parsed = urlparse(url)
            short = parsed.netloc + parsed.path[:30]
            return f"Fetching {short}"
        return "Fetching URL"
    if "search" in name.lower():
        query = inp.get("query", "")
        return f"Searching: {query[:45]}" if query else "Web search"
    if "context7" in name:
        return f"Docs lookup: {inp.get('libraryName', inp.get('topic', ''))[:40]}"

    return name if name else ""


def parse_log_status(log_file: Path) -> str:
    """Extract a human-readable status line from a stream-json agent log.

    Scans the log for the ``result`` JSON line and returns its ``result``
    field. Falls back to the last non-empty line if no result line is found.

    Args:
        log_file: Path to the agent.log file.

    Returns:
        Human-readable status string, or empty string if log is missing.
    """
    if not log_file.is_file():
        return ""

    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()

    # Walk backwards to find the result line
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if obj.get("type") == "result":
            return obj.get("result", "Unknown result")

    # Fallback: return last non-empty line (truncated)
    for line in reversed(lines):
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


def is_agent_running(pid: int) -> bool:
    """Check whether a process is still running.

    Uses ``os.waitpid`` with ``WNOHANG`` to reap zombie child processes
    (which ``os.kill(pid, 0)`` alone cannot distinguish from live processes).
    Falls back to signal-based check for non-child processes.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process exists and is running, False otherwise.
    """
    # Try to reap the child — handles zombie (defunct) processes
    try:
        waited_pid, status = os.waitpid(pid, os.WNOHANG)
        if waited_pid != 0:
            # Child was reaped — it has exited
            return False
        # waitpid returned 0 — child is still running
        return True
    except ChildProcessError:
        # Not our child — fall back to signal check
        pass

    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by a different user — treat as still running
        return True


def tail_log(log_file: Path, n: int = 30, *, offset: int = 0) -> tuple[str, int]:
    """Return human-readable lines from a Claude JSON-stream log file.

    Parses the JSON stream format and extracts meaningful events:
    - Assistant text responses
    - Tool use calls (name + truncated input)
    - Errors

    Args:
        log_file: Path to the log file.
        n: Max number of display lines to return.
        offset: Byte offset to start reading from (for incremental tailing).

    Returns:
        Tuple of (display text, new byte offset).
    """
    if not log_file.is_file():
        return "", 0

    content = log_file.read_text(encoding="utf-8", errors="replace")
    new_offset = len(content.encode("utf-8"))

    # Only process new content
    if offset > 0:
        content = content.encode("utf-8")[offset:].decode("utf-8", errors="replace")

    display_lines: list[str] = []
    for raw_line in content.splitlines():
        if not raw_line.strip():
            continue
        try:
            entry = json.loads(raw_line)
        except (json.JSONDecodeError, ValueError):
            continue

        msg_type = entry.get("type", "")

        if msg_type == "assistant":
            # Extract text from assistant message content
            message = entry.get("message", {})
            for block in message.get("content", []):
                if block.get("type") == "text":
                    text = block["text"].strip()
                    if text:
                        # Take first 200 chars to keep log readable
                        preview = text[:200] + ("..." if len(text) > 200 else "")
                        display_lines.append(preview)
                elif block.get("type") == "tool_use":
                    name = block.get("name", "unknown")
                    display_lines.append(f"[TOOL] {name}")

        elif msg_type == "tool_use":
            name = entry.get("name", "unknown")
            display_lines.append(f"[TOOL] {name}")

        elif msg_type == "result":
            # Final result
            result = entry.get("result", "")
            if result:
                preview = result[:200] + ("..." if len(result) > 200 else "")
                display_lines.append(f"[RESULT] {preview}")

    return "\n".join(display_lines[-n:]), new_offset


def parse_research_output(research_md: Path) -> dict[str, Any]:
    """Parse the generated research.md file.

    Extracts ``experiment_type`` from ``## Programmatic Assessment`` section
    (first word YES → "programmatic", NO → "manual", absent → None) and
    ``summary`` from the ``## Overview`` section.

    Args:
        research_md: Path to the research.md file.

    Returns:
        Dict with keys:
            - ``experiment_type``: ``"programmatic"``, ``"manual"``, or ``None``
            - ``summary``: Text of the ``## Overview`` section (may be empty).
    """
    result: dict[str, Any] = {"experiment_type": None, "summary": ""}

    if not research_md.is_file():
        return result

    content = research_md.read_text(encoding="utf-8", errors="replace")
    sections = _split_sections(content)

    # Extract experiment_type
    assessment = sections.get("Programmatic Assessment", "").strip()
    if assessment:
        first_word = (
            assessment.split()[0].upper().rstrip(".,—-") if assessment.split() else ""
        )
        if first_word == "YES":
            result["experiment_type"] = "programmatic"
        elif first_word == "NO":
            result["experiment_type"] = "manual"

    # Extract summary from Overview
    result["summary"] = sections.get("Overview", "").strip()

    return result


def render_research_html(
    research_md: Path,
    output_dir: Path,
    tool_name: str = "",
) -> Path:
    """Convert research.md to a styled HTML report.

    Reads ``research.md``, converts with ``markdown.markdown()``, wraps in a
    minimal dark HTML template. Writes ``research.html`` to ``output_dir``.

    Args:
        research_md: Path to the research.md file.
        output_dir: Directory to write research.html.
        tool_name: Tool name used in the HTML ``<title>`` tag.

    Returns:
        Path to the generated ``research.html`` file.
    """
    md_content = ""
    if research_md.is_file():
        md_content = research_md.read_text(encoding="utf-8", errors="replace")

    body_html = markdown.markdown(
        md_content,
        extensions=["fenced_code", "tables"],
    )

    safe_title = html_module.escape(
        f"Research: {tool_name}" if tool_name else "Research Report"
    )
    html = _build_html_template(safe_title, body_html)

    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "research.html"
    html_path.write_text(html, encoding="utf-8")

    logger.info("Rendered research HTML to %s", html_path)
    return html_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_sections(content: str) -> dict[str, str]:
    """Split a markdown document into sections keyed by heading text.

    Only parses ``##`` (h2) headings. The text between two adjacent headings
    (or from the last heading to end-of-file) becomes the section body.

    Args:
        content: Raw markdown string.

    Returns:
        Dict mapping heading text (without ``## ``) to body text.
    """
    sections: dict[str, str] = {}
    current_key: str | None = None
    body_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if current_key is not None:
                sections[current_key] = "\n".join(body_lines).strip()
            current_key = line[3:].strip()
            body_lines = []
        else:
            body_lines.append(line)

    if current_key is not None:
        sections[current_key] = "\n".join(body_lines).strip()

    return sections


def _build_html_template(title: str, body_html: str) -> str:
    """Wrap converted markdown HTML in a minimal dark-theme page.

    Args:
        title: Page title (used in ``<title>`` and ``<h1>``).
        body_html: HTML string produced by markdown conversion.

    Returns:
        Complete HTML document string.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{
    background: #0A0A0A;
    color: #D1D5DB;
    font-family: 'Roboto Mono', monospace, sans-serif;
    font-size: 15px;
    line-height: 1.7;
    max-width: 860px;
    margin: 40px auto;
    padding: 0 20px 60px;
  }}
  h1, h2, h3 {{
    color: #3B82F6;
    font-family: 'Exo', sans-serif;
    margin-top: 2rem;
  }}
  h1 {{ font-size: 1.6rem; border-bottom: 1px solid #1F2937; padding-bottom: 0.5rem; }}
  h2 {{ font-size: 1.25rem; }}
  h3 {{ font-size: 1.05rem; }}
  code {{
    background: #111827;
    color: #93C5FD;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }}
  pre {{
    background: #111827;
    border: 1px solid #1F2937;
    border-radius: 6px;
    padding: 16px;
    overflow-x: auto;
  }}
  pre code {{
    background: none;
    padding: 0;
  }}
  a {{ color: #3B82F6; }}
  table {{
    border-collapse: collapse;
    width: 100%;
    margin: 1rem 0;
  }}
  th, td {{
    border: 1px solid #1F2937;
    padding: 8px 12px;
    text-align: left;
  }}
  th {{ background: #111827; color: #9CA3AF; }}
  blockquote {{
    border-left: 4px solid #1E40AF;
    margin-left: 0;
    padding-left: 16px;
    color: #9CA3AF;
  }}
</style>
</head>
<body>
<h1>{title}</h1>
{body_html}
</body>
</html>
"""
