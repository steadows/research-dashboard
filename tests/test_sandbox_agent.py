"""Tests for sandbox agent — launch, prompt structure, cost detection."""

from unittest.mock import MagicMock, patch

import pytest

from utils.research_agent import (
    _detect_cost_flags,
    launch_sandbox_agent,
    parse_research_output,
)


# ---------------------------------------------------------------------------
# Cost detection tests
# ---------------------------------------------------------------------------


def test_detect_cost_flags_clean_text():
    assert _detect_cost_flags("This is a free open-source tool.") == (False, "")


def test_detect_cost_flags_subscription():
    text = "Requires a subscription to use the API."
    flagged, notes = _detect_cost_flags(text)
    assert flagged is True
    assert "subscription" in notes.lower()


def test_detect_cost_flags_pricing():
    text = "See their pricing page for current rates."
    flagged, notes = _detect_cost_flags(text)
    assert flagged is True


def test_detect_cost_flags_case_insensitive():
    text = "This tool has a PAID PLAN for enterprise users."
    flagged, _ = _detect_cost_flags(text)
    assert flagged is True


def test_detect_cost_flags_caps_at_three_sentences():
    text = (
        "Monthly subscription required. "
        "Billing is handled per seat. "
        "Enterprise plan available. "
        "Per year pricing also available."
    )
    _, notes = _detect_cost_flags(text)
    # Should have at most 3 pipe-separated entries
    assert notes.count("|") <= 2


def test_parse_research_output_includes_cost_fields(tmp_path):
    md = tmp_path / "research.md"
    md.write_text(
        "## Overview\nA tool for X.\n"
        "## Programmatic Assessment\nYES it can.\n"
        "## Experiment Design\nTest it.\n"
        "## Safety Notes\nRequires a subscription to API.\n"
    )
    result = parse_research_output(md)
    assert "cost_flagged" in result
    assert "cost_notes" in result
    assert result["cost_flagged"] is True


def test_parse_research_output_no_cost(tmp_path):
    md = tmp_path / "research.md"
    md.write_text("## Overview\nFree tool.\n## Programmatic Assessment\nYES.\n")
    result = parse_research_output(md)
    assert result["cost_flagged"] is False
    assert result["cost_notes"] == ""


# ---------------------------------------------------------------------------
# Sandbox agent launch tests
# ---------------------------------------------------------------------------


def test_launch_sandbox_agent_raises_if_research_md_missing(tmp_path):
    item = {"name": "TestTool", "category": "AI", "source_type": "tool"}
    with pytest.raises(FileNotFoundError, match="research.md not found"):
        launch_sandbox_agent(item, tmp_path / "research.md", tmp_path)


def test_launch_sandbox_agent_raises_if_claude_missing(tmp_path):
    md = tmp_path / "research.md"
    md.write_text("## Overview\nA tool.\n## Experiment Design\nTest it.\n")
    item = {"name": "TestTool", "category": "AI", "source_type": "tool"}
    with patch("shutil.which", return_value=None):
        with pytest.raises(FileNotFoundError, match="claude CLI"):
            launch_sandbox_agent(item, md, tmp_path)


def test_launch_sandbox_agent_spawns_subprocess(tmp_path):
    md = tmp_path / "research.md"
    md.write_text(
        "## Overview\nA tool for vector search.\n"
        "## Experiment Design\nIndex 100 items and measure latency.\n"
    )
    item = {"name": "VectorSearch", "category": "AI", "source_type": "tool"}
    mock_proc = MagicMock()
    mock_proc.pid = 12345

    with patch("shutil.which", return_value="/usr/local/bin/claude"):
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            proc = launch_sandbox_agent(item, md, tmp_path)

    assert proc.pid == 12345
    cmd = mock_popen.call_args[0][0]
    assert "claude" in cmd[0]
    assert "-p" in cmd


def test_sandbox_prompt_contains_experiment_design(tmp_path):
    """Sandbox prompt must inject the Experiment Design section from research."""
    md = tmp_path / "research.md"
    experiment_design = "Measure index latency for 1000 vectors."
    md.write_text(
        f"## Overview\nVectorDB tool.\n## Experiment Design\n{experiment_design}\n"
    )
    item = {"name": "VectorDB", "category": "Database", "source_type": "tool"}
    mock_proc = MagicMock()
    mock_proc.pid = 99

    with patch("shutil.which", return_value="/usr/bin/claude"):
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            launch_sandbox_agent(item, md, tmp_path)

    prompt = mock_popen.call_args[0][0][2]  # -p <prompt>
    assert "Measure index latency" in prompt


def test_sandbox_prompt_requires_experiment_results_json(tmp_path):
    md = tmp_path / "research.md"
    md.write_text("## Overview\nTool.\n## Experiment Design\nTest.\n")
    item = {"name": "Tool", "category": "X", "source_type": "tool"}
    mock_proc = MagicMock()
    mock_proc.pid = 1

    with patch("shutil.which", return_value="/usr/bin/claude"):
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            launch_sandbox_agent(item, md, tmp_path)

    prompt = mock_popen.call_args[0][0][2]
    assert "experiment_results.json" in prompt
    assert "experiment_findings.md" in prompt


def test_sandbox_prompt_contains_safety_clause(tmp_path):
    md = tmp_path / "research.md"
    md.write_text("## Overview\nTool.\n## Experiment Design\nTest.\n")
    item = {"name": "Tool", "category": "X", "source_type": "tool"}
    mock_proc = MagicMock()
    mock_proc.pid = 1

    with patch("shutil.which", return_value="/usr/bin/claude"):
        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            launch_sandbox_agent(item, md, tmp_path)

    prompt = mock_popen.call_args[0][0][2]
    assert "curl" in prompt.lower() or "SAFETY" in prompt
