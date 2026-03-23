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
        assert "--allowedTools" in cmd
        assert "--fallback-model" in cmd

        # shell=True must NOT be used
        assert call_args[1].get("shell") is not True

        proc, model_used = result
        assert proc is mock_proc
        assert model_used == "claude-opus-4-6"

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
        """tail_log returns empty tuple with empty string when log file does not exist."""
        from utils.research_agent import tail_log

        missing = tmp_path / "nonexistent.log"
        text, offset = tail_log(missing)
        assert text == ""
        assert offset == 0

    def test_returns_last_n_lines(self, tmp_path: Path) -> None:
        """tail_log returns the last N parsed lines of a JSON-stream log file."""
        from utils.research_agent import tail_log

        log_file = tmp_path / "agent.log"
        # tail_log now parses JSON stream format; plain text lines are skipped
        # Write valid JSON stream entries
        import json

        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": f"line {i}"}]},
                }
            )
            for i in range(1, 51)
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        text, offset = tail_log(log_file, n=10)
        result_lines = text.strip().splitlines()
        assert len(result_lines) == 10
        assert offset > 0

    def test_returns_all_lines_when_fewer_than_n(self, tmp_path: Path) -> None:
        """tail_log returns all lines when file has fewer than N lines."""
        from utils.research_agent import tail_log

        import json

        log_file = tmp_path / "agent.log"
        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": f"line {i}"}]},
                }
            )
            for i in range(1, 4)
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        text, offset = tail_log(log_file, n=30)
        result_lines = text.strip().splitlines()
        assert len(result_lines) == 3

    def test_default_n_is_30(self, tmp_path: Path) -> None:
        """tail_log uses n=30 as default."""
        from utils.research_agent import tail_log

        import json

        log_file = tmp_path / "agent.log"
        entries = [
            json.dumps(
                {
                    "type": "assistant",
                    "message": {"content": [{"type": "text", "text": f"line {i}"}]},
                }
            )
            for i in range(1, 101)
        ]
        log_file.write_text("\n".join(entries), encoding="utf-8")

        text, _ = tail_log(log_file)
        assert len(text.strip().splitlines()) == 30


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


# ---------------------------------------------------------------------------
# get_fallback_model
# ---------------------------------------------------------------------------


class TestGetFallbackModel:
    """Tests for get_fallback_model."""

    def test_opus_falls_back_to_sonnet(self) -> None:
        """Opus returns Sonnet as fallback."""
        from utils.research_agent import get_fallback_model

        assert get_fallback_model("claude-opus-4-6") == "claude-sonnet-4-6"

    def test_sonnet_has_no_fallback(self) -> None:
        """Sonnet is the end of the chain — returns None."""
        from utils.research_agent import get_fallback_model

        assert get_fallback_model("claude-sonnet-4-6") is None

    def test_unknown_model_returns_none(self) -> None:
        """Unknown model ID returns None."""
        from utils.research_agent import get_fallback_model

        assert get_fallback_model("unknown-model") is None

    def test_none_defaults_to_opus_fallback(self) -> None:
        """None input treated as Opus — falls back to Sonnet."""
        from utils.research_agent import get_fallback_model

        assert get_fallback_model(None) == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# is_overload_failure
# ---------------------------------------------------------------------------


class TestIsOverloadFailure:
    """Tests for is_overload_failure."""

    def test_detects_529_in_log(self, tmp_path: Path) -> None:
        """Returns True when log contains 529 status code."""
        from utils.research_agent import is_overload_failure

        log = tmp_path / "agent.log"
        log.write_text("starting...\nAPI Error: Repeated 529 Overloaded errors\n")
        assert is_overload_failure(log) is True

    def test_detects_overloaded_keyword(self, tmp_path: Path) -> None:
        """Returns True when log contains 'Overloaded' keyword."""
        from utils.research_agent import is_overload_failure

        log = tmp_path / "agent.log"
        log.write_text("Error: Overloaded\n")
        assert is_overload_failure(log) is True

    def test_returns_false_for_other_errors(self, tmp_path: Path) -> None:
        """Returns False for non-overload errors."""
        from utils.research_agent import is_overload_failure

        log = tmp_path / "agent.log"
        log.write_text("Error: 401 Unauthorized\n")
        assert is_overload_failure(log) is False

    def test_returns_false_for_missing_log(self, tmp_path: Path) -> None:
        """Returns False when log file doesn't exist."""
        from utils.research_agent import is_overload_failure

        assert is_overload_failure(tmp_path / "nonexistent.log") is False


# ---------------------------------------------------------------------------
# launch_research_agent with model parameter
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# parse_log_status
# ---------------------------------------------------------------------------


class TestParseLogStatus:
    """Tests for parse_log_status."""

    def test_extracts_result_from_stream_json(self, tmp_path: Path) -> None:
        """Extracts the result field from a stream-json result line."""
        from utils.research_agent import parse_log_status

        log = tmp_path / "agent.log"
        log.write_text(
            '{"type":"system","subtype":"init","cwd":"/tmp"}\n'
            '{"type":"result","subtype":"success","result":"API Error: Repeated 529 Overloaded errors"}\n'
        )
        assert parse_log_status(log) == "API Error: Repeated 529 Overloaded errors"

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Returns empty string when log file doesn't exist."""
        from utils.research_agent import parse_log_status

        assert parse_log_status(tmp_path / "missing.log") == ""

    def test_returns_empty_for_empty_file(self, tmp_path: Path) -> None:
        """Returns empty string for empty log file."""
        from utils.research_agent import parse_log_status

        log = tmp_path / "agent.log"
        log.write_text("")
        assert parse_log_status(log) == ""

    def test_fallback_to_last_line_when_no_result(self, tmp_path: Path) -> None:
        """Falls back to last non-empty line when no result JSON found."""
        from utils.research_agent import parse_log_status

        log = tmp_path / "agent.log"
        log.write_text("some plain text log\nfinal line\n")
        assert parse_log_status(log) == "final line"


# ---------------------------------------------------------------------------
# launch_research_agent with model parameter
# ---------------------------------------------------------------------------


class TestLaunchWithModelFallback:
    """Tests for launch_research_agent model parameter."""

    def test_uses_custom_model_when_specified(self, tmp_path: Path) -> None:
        """launch_research_agent passes custom model to CLI args."""
        from utils.research_agent import launch_research_agent

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345

        with (
            patch("utils.research_agent.shutil.which", return_value="/usr/bin/claude"),
            patch(
                "utils.research_agent.subprocess.Popen", return_value=mock_proc
            ) as mock_popen,
            patch("builtins.open", MagicMock()),
        ):
            proc, model_used = launch_research_agent(
                _sample_tool(), tmp_path, model="claude-sonnet-4-6"
            )

        cmd = mock_popen.call_args[0][0]
        assert "claude-sonnet-4-6" in cmd
        assert model_used == "claude-sonnet-4-6"

    def test_defaults_to_opus_when_no_model(self, tmp_path: Path) -> None:
        """launch_research_agent defaults to Opus when model is None."""
        from utils.research_agent import launch_research_agent

        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345

        with (
            patch("utils.research_agent.shutil.which", return_value="/usr/bin/claude"),
            patch(
                "utils.research_agent.subprocess.Popen", return_value=mock_proc
            ) as mock_popen,
            patch("builtins.open", MagicMock()),
        ):
            proc, model_used = launch_research_agent(_sample_tool(), tmp_path)

        cmd = mock_popen.call_args[0][0]
        assert "claude-opus-4-6" in cmd
        assert model_used == "claude-opus-4-6"
