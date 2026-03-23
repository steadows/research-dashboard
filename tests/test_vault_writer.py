"""Tests for vault_writer — write sandbox notes to Obsidian vault."""

import pytest

from utils.vault_writer import write_sandbox_note


@pytest.fixture()
def vault(tmp_path):
    """Create a minimal vault structure."""
    (tmp_path / "Projects").mkdir()
    return tmp_path


def _sample_tool():
    return {
        "name": "Graph RAG",
        "category": "AI",
        "source_type": "tool",
    }


def test_write_sandbox_note_creates_file(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox" / "tool-graph-rag"
    path = write_sandbox_note(_sample_tool(), "A great tool.", sandbox_dir, vault)
    assert path.exists()


def test_write_sandbox_note_creates_sandbox_dir(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox" / "tool-graph-rag"
    write_sandbox_note(_sample_tool(), "Summary.", sandbox_dir, vault)
    assert (vault / "Projects" / "Sandbox").is_dir()


def test_write_sandbox_note_correct_path(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox" / "tool-graph-rag"
    path = write_sandbox_note(_sample_tool(), "Summary.", sandbox_dir, vault)
    assert path.parent == vault / "Projects" / "Sandbox"
    assert "Graph RAG" in path.stem or "Graph_RAG" in path.stem


def test_write_sandbox_note_frontmatter(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox" / "tool-graph-rag"
    path = write_sandbox_note(_sample_tool(), "Summary.", sandbox_dir, vault)
    content = path.read_text()
    assert "status: sandbox_ready" in content
    assert "tool_name: Graph RAG" in content
    assert "category: AI" in content
    assert str(sandbox_dir) in content


def test_write_sandbox_note_contains_summary(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox"
    path = write_sandbox_note(_sample_tool(), "This is the overview.", sandbox_dir, vault)
    assert "This is the overview." in path.read_text()


def test_write_sandbox_note_includes_findings_text(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox"
    path = write_sandbox_note(
        _sample_tool(), "Summary.", sandbox_dir, vault,
        findings_text="INTEGRATE — significant improvement detected."
    )
    content = path.read_text()
    assert "INTEGRATE" in content


def test_write_sandbox_note_no_overwrite(vault, tmp_path):
    sandbox_dir = tmp_path / "sandbox"
    path1 = write_sandbox_note(_sample_tool(), "First.", sandbox_dir, vault)
    path2 = write_sandbox_note(_sample_tool(), "Second.", sandbox_dir, vault)
    assert path1 != path2
    assert path1.exists()
    assert "First." in path1.read_text()


def test_write_sandbox_note_path_traversal(tmp_path):
    """Vault path traversal should raise ValueError."""
    vault = tmp_path / "vault"
    vault.mkdir()
    # Craft a tool with a name containing path traversal chars (sanitized)
    tool = {"name": "../../etc/passwd", "category": "hack"}
    sandbox_dir = tmp_path / "sandbox"
    # Should not raise — the name gets sanitized, path stays inside vault
    path = write_sandbox_note(tool, "Summary.", sandbox_dir, vault)
    assert vault.resolve() in path.resolve().parents
