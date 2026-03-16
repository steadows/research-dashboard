"""Tests for research_agent — Opus subprocess, log tail, research output parsing."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_tool(name: str = "Cursor Tab") -> dict:
    """Return a minimal tool dict matching tools_parser output."""
    return {
        "name": name,
        "category": "IDE",
        "source": "TLDR 2026-03-07",
        "source_type": "tool",
        "what it does": "AI-powered tab completion with context awareness.",
        "projects": ["Research Intelligence Dashboard"],
    }


def _write_research_md(output_dir: Path, content: str) -> Path:
    """Write a research.md file to the output dir and return its path."""
    path = output_dir / "research.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# launch_research_agent
# ---------------------------------------------------------------------------


class TestLaunchResearchAgent:
    """Tests for launch_research_agent."""

    def test_spawns_subprocess_with_claude_p_args(self, tmp_path: Path) -> None:
        """launch_research_agent calls subprocess.Popen with claude -p args."""
        from utils.research_agent import launch_research_agent

        output_dir = tmp_path / "cursor-tab"
        output_dir.mkdir()

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999

        with (
            patch("utils.research_agent.shutil.which", return_value="/usr/bin/claude"),
            patch(
                "utils.research_agent.subprocess.Popen", return_value=mock_proc
            ) as mock_popen,
            patch("builtins.open", MagicMock()),
        ):
            result = launch_research_agent(_sample_tool(), output_dir)

        # Must be called
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args

        # First positional arg is the command list
        cmd = call_args[0][0]
        assert isinstance(cmd, list), "Command must be a list (not a string)"
        assert cmd[0].endswith("claude")
        assert "-p" in cmd
        assert "--model" in cmd
        assert "claude-opus-4-6" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd

        # shell=True must NOT be used
        assert call_args[1].get("shell") is not True

        assert result is mock_proc

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        """launch_research_agent creates output_dir when it doesn't exist."""
        from utils.research_agent import launch_research_agent

        output_dir = tmp_path / "new-dir" / "nested"
        assert not output_dir.exists()

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999

        with (
            patch("utils.research_agent.shutil.which", return_value="/usr/bin/claude"),
            patch("utils.research_agent.subprocess.Popen", return_value=mock_proc),
            patch("builtins.open", MagicMock()),
        ):
            launch_research_agent(_sample_tool(), output_dir)

        assert output_dir.exists()

    def test_raises_when_claude_not_found(self, tmp_path: Path) -> None:
        """launch_research_agent raises FileNotFoundError when claude CLI is missing."""
        from utils.research_agent import launch_research_agent

        output_dir = tmp_path / "tool-dir"
        output_dir.mkdir()

        with patch("utils.research_agent.shutil.which", return_value=None):
            with pytest.raises(FileNotFoundError, match="claude CLI not found"):
                launch_research_agent(_sample_tool(), output_dir)


# ---------------------------------------------------------------------------
# is_agent_running
# ---------------------------------------------------------------------------


class TestIsAgentRunning:
    """Tests for is_agent_running."""

    def test_returns_true_when_process_alive(self) -> None:
        """is_agent_running returns True when os.kill(pid, 0) does not raise."""
        from utils.research_agent import is_agent_running

        with patch("utils.research_agent.os.kill", return_value=None):
            assert is_agent_running(12345) is True

    def test_returns_false_when_process_gone(self) -> None:
        """is_agent_running returns False when os.kill raises ProcessLookupError."""
        from utils.research_agent import is_agent_running

        with patch("utils.research_agent.os.kill", side_effect=ProcessLookupError):
            assert is_agent_running(12345) is False

    def test_returns_true_on_permission_error(self) -> None:
        """is_agent_running returns True when os.kill raises PermissionError.

        PermissionError means the process EXISTS but is owned by a different
        user. We conservatively treat it as still running.
        """
        from utils.research_agent import is_agent_running

        with patch("utils.research_agent.os.kill", side_effect=PermissionError):
            assert is_agent_running(12345) is True


# ---------------------------------------------------------------------------
# tail_log
# ---------------------------------------------------------------------------


class TestTailLog:
    """Tests for tail_log."""

    def test_returns_empty_string_when_file_missing(self, tmp_path: Path) -> None:
        """tail_log returns empty string when log file does not exist."""
        from utils.research_agent import tail_log

        missing = tmp_path / "nonexistent.log"
        assert tail_log(missing) == ""

    def test_returns_last_n_lines(self, tmp_path: Path) -> None:
        """tail_log returns the last N lines of a file."""
        from utils.research_agent import tail_log

        log_file = tmp_path / "agent.log"
        lines = [f"line {i}" for i in range(1, 51)]  # 50 lines
        log_file.write_text("\n".join(lines), encoding="utf-8")

        result = tail_log(log_file, n=10)
        result_lines = result.strip().splitlines()
        assert len(result_lines) == 10
        assert result_lines[-1] == "line 50"
        assert result_lines[0] == "line 41"

    def test_returns_all_lines_when_fewer_than_n(self, tmp_path: Path) -> None:
        """tail_log returns all lines when file has fewer than N lines."""
        from utils.research_agent import tail_log

        log_file = tmp_path / "agent.log"
        log_file.write_text("line 1\nline 2\nline 3", encoding="utf-8")

        result = tail_log(log_file, n=30)
        result_lines = result.strip().splitlines()
        assert len(result_lines) == 3

    def test_default_n_is_30(self, tmp_path: Path) -> None:
        """tail_log uses n=30 as default."""
        from utils.research_agent import tail_log

        log_file = tmp_path / "agent.log"
        lines = [f"line {i}" for i in range(1, 101)]  # 100 lines
        log_file.write_text("\n".join(lines), encoding="utf-8")

        result = tail_log(log_file)
        assert len(result.strip().splitlines()) == 30


# ---------------------------------------------------------------------------
# parse_research_output
# ---------------------------------------------------------------------------


_RESEARCH_MD_PROGRAMMATIC = """\
## Overview

Cursor Tab is an AI-powered tab completion tool for IDEs.

## How to Install

```bash
pip install cursor-tab
```

## Key APIs / Concepts

- `tab_complete()` — synchronous completion API

## Programmatic Assessment

YES — The tool exposes a clean Python API and can be integrated headlessly.
Testing via unit tests is straightforward.

## Experiment Design

Write a small harness that calls `tab_complete()` with a test prompt.

## Safety Notes

Package name confirmed on PyPI.
"""

_RESEARCH_MD_MANUAL = """\
## Overview

Valkey is a Redis-compatible in-memory datastore.

## Programmatic Assessment

NO — Valkey requires a running server. Integration testing needs a real
Valkey instance and is fundamentally manual/infra setup work.

## Experiment Design

Spin up a Valkey container via Docker.
"""

_RESEARCH_MD_NO_SECTION = """\
## Overview

Some tool without assessment.

## How to Install

```bash
pip install sometool
```
"""


class TestParseResearchOutput:
    """Tests for parse_research_output."""

    def test_returns_programmatic_when_yes(self, tmp_path: Path) -> None:
        """parse_research_output returns experiment_type='programmatic' for YES."""
        from utils.research_agent import parse_research_output

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_PROGRAMMATIC)
        result = parse_research_output(research_md)
        assert result["experiment_type"] == "programmatic"

    def test_returns_manual_when_no(self, tmp_path: Path) -> None:
        """parse_research_output returns experiment_type='manual' for NO."""
        from utils.research_agent import parse_research_output

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_MANUAL)
        result = parse_research_output(research_md)
        assert result["experiment_type"] == "manual"

    def test_returns_none_when_section_missing(self, tmp_path: Path) -> None:
        """parse_research_output returns experiment_type=None when section absent."""
        from utils.research_agent import parse_research_output

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_NO_SECTION)
        result = parse_research_output(research_md)
        assert result["experiment_type"] is None

    def test_returns_summary_from_overview_section(self, tmp_path: Path) -> None:
        """parse_research_output extracts summary from ## Overview section."""
        from utils.research_agent import parse_research_output

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_PROGRAMMATIC)
        result = parse_research_output(research_md)
        assert "summary" in result
        assert "Cursor Tab" in result["summary"]

    def test_returns_empty_summary_when_no_overview(self, tmp_path: Path) -> None:
        """parse_research_output returns empty summary when ## Overview is absent."""
        from utils.research_agent import parse_research_output

        content = "## Programmatic Assessment\n\nYES — Works programmatically.\n"
        research_md = _write_research_md(tmp_path, content)
        result = parse_research_output(research_md)
        assert result["summary"] == ""

    def test_returns_none_for_missing_file(self, tmp_path: Path) -> None:
        """parse_research_output returns None experiment_type when file missing."""
        from utils.research_agent import parse_research_output

        missing = tmp_path / "research.md"
        result = parse_research_output(missing)
        assert result["experiment_type"] is None
        assert result["summary"] == ""

    def test_returns_programmatic_for_yes_with_punctuation(
        self, tmp_path: Path
    ) -> None:
        """parse_research_output handles 'YES,' (with comma) as programmatic."""
        from utils.research_agent import parse_research_output

        content = "## Programmatic Assessment\n\nYES, the tool has a Python API.\n"
        research_md = _write_research_md(tmp_path, content)
        result = parse_research_output(research_md)
        assert result["experiment_type"] == "programmatic"


# ---------------------------------------------------------------------------
# render_research_html
# ---------------------------------------------------------------------------


class TestRenderResearchHtml:
    """Tests for render_research_html."""

    def test_creates_research_html_in_output_dir(self, tmp_path: Path) -> None:
        """render_research_html writes research.html to output_dir."""
        from utils.research_agent import render_research_html

        tool = _sample_tool("Cursor Tab")
        research_md = _write_research_md(tmp_path, _RESEARCH_MD_PROGRAMMATIC)

        output_dir = tmp_path
        render_research_html(research_md, output_dir, tool_name=tool["name"])

        assert (output_dir / "research.html").exists()

    def test_returns_path_to_generated_file(self, tmp_path: Path) -> None:
        """render_research_html returns Path pointing to research.html."""
        from utils.research_agent import render_research_html

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_PROGRAMMATIC)
        result = render_research_html(research_md, tmp_path, tool_name="Cursor Tab")

        assert isinstance(result, Path)
        assert result.name == "research.html"
        assert result.exists()

    def test_html_contains_tool_name_in_title(self, tmp_path: Path) -> None:
        """render_research_html includes tool name in <title> tag."""
        from utils.research_agent import render_research_html

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_PROGRAMMATIC)
        html_path = render_research_html(research_md, tmp_path, tool_name="Cursor Tab")

        html_content = html_path.read_text(encoding="utf-8")
        assert "Cursor Tab" in html_content
        assert "<title>" in html_content

    def test_html_has_dark_background(self, tmp_path: Path) -> None:
        """render_research_html uses dark theme (#0A0A0A background)."""
        from utils.research_agent import render_research_html

        research_md = _write_research_md(tmp_path, _RESEARCH_MD_PROGRAMMATIC)
        html_path = render_research_html(research_md, tmp_path, tool_name="Cursor Tab")

        html_content = html_path.read_text(encoding="utf-8")
        assert "#0A0A0A" in html_content or "0a0a0a" in html_content.lower()
