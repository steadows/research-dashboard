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
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import markdown

logger = logging.getLogger(__name__)

_OPUS_MODEL = "claude-opus-4-6"
_WORKBENCH_ROOT = Path.home() / "research-workbench"

# ---------------------------------------------------------------------------
# COSTAR research prompt template
# ---------------------------------------------------------------------------

_COSTAR_PROMPT_TEMPLATE = """\
<context>
Tool name: {name}
Category: {category}
Source: {source}
Description: {description}
</context>

<objective>
Research this tool thoroughly. Use Exa to search for documentation, GitHub \
repositories, and real-world usage examples. Use context7 to pull official \
API documentation where available. Assess whether the tool can be evaluated \
programmatically (headless, via code) or requires manual hands-on evaluation. \
Design a minimal, focused experiment that could be run within a sandbox \
environment.
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


def _build_prompt(tool: dict[str, Any], output_dir: Path) -> str:
    """Build the COSTAR research prompt interpolated with tool fields.

    Args:
        tool: Tool dict from tools_parser.
        output_dir: Directory where research.md will be written.

    Returns:
        Fully interpolated prompt string.
    """
    description = (
        tool.get("what it does")
        or tool.get("description")
        or tool.get("why it matters")
        or ""
    )
    return _COSTAR_PROMPT_TEMPLATE.format(
        name=tool.get("name", "Unknown"),
        category=tool.get("category", "Unknown"),
        source=tool.get("source", "Unknown"),
        description=description,
        output_path=str(output_dir / "research.md"),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def launch_research_agent(tool: dict[str, Any], output_dir: Path) -> subprocess.Popen:
    """Launch Opus research agent as a subprocess.

    The agent writes ``research.md`` to ``output_dir``. Stream-JSON output
    and stderr are redirected to ``{output_dir}/agent.log`` via a file handle.

    Args:
        tool: Tool dict (from tools_parser) to research.
        output_dir: Directory to write research.md and agent.log.

    Returns:
        subprocess.Popen handle. Caller should save .pid to workbench entry.

    Raises:
        FileNotFoundError: If the ``claude`` CLI is not found in PATH.
    """
    claude_bin = shutil.which("claude")
    if claude_bin is None:
        raise FileNotFoundError("claude CLI not found in PATH")

    output_dir.mkdir(parents=True, exist_ok=True)

    prompt = _build_prompt(tool, output_dir)
    log_path = output_dir / "agent.log"

    cmd = [
        claude_bin,
        "-p",
        prompt,
        "--model",
        _OPUS_MODEL,
        "--output-format",
        "stream-json",
    ]

    log_fh = open(log_path, "w", encoding="utf-8")  # noqa: WPS515
    try:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=log_fh,
            stderr=log_fh,
            shell=False,
        )
    finally:
        # Parent closes its copy — child inherited its own fd via Popen
        log_fh.close()

    logger.info(
        "Launched research agent for '%s' (pid=%d), log=%s",
        tool.get("name"),
        proc.pid,
        log_path,
    )
    return proc


def is_agent_running(pid: int) -> bool:
    """Check whether a process is still running.

    Args:
        pid: Process ID to check.

    Returns:
        True if the process exists and is running, False otherwise.
    """
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by a different user — treat as still running
        return True


def tail_log(log_file: Path, n: int = 30) -> str:
    """Return the last N lines from a log file.

    Args:
        log_file: Path to the log file.
        n: Number of lines to return (default 30).

    Returns:
        Last N lines joined as a string, or empty string if file missing.
    """
    if not log_file.is_file():
        return ""

    lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


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
