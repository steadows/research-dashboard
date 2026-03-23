"""Round-trip workbench pipeline integration tests."""

import pytest

from utils.workbench_tracker import (
    add_to_workbench,
    get_workbench_item,
    get_workbench_items,
    make_item_key,
    update_workbench_item,
)
from utils.vault_writer import write_sandbox_note


@pytest.fixture()
def workbench_file(tmp_path):
    return tmp_path / "workbench.json"


@pytest.fixture()
def status_file(tmp_path):
    return tmp_path / "status.json"


def _sample_tool():
    return {
        "name": "VectorDB",
        "category": "Database",
        "source_type": "tool",
    }


class TestSandboxSchema:
    def test_add_creates_cost_fields(self, workbench_file, status_file):
        add_to_workbench(_sample_tool(), workbench_file=workbench_file)
        key = make_item_key("tool", "VectorDB")
        entry = get_workbench_item(key, workbench_file=workbench_file)
        assert "cost_flagged" in entry
        assert entry["cost_flagged"] is False
        assert "cost_notes" in entry
        assert entry["cost_notes"] == ""
        assert "cost_approved" in entry
        assert entry["cost_approved"] is False
        assert "findings_path" in entry
        assert entry["findings_path"] is None

    def test_update_cost_approved(self, workbench_file):
        add_to_workbench(_sample_tool(), workbench_file=workbench_file)
        key = make_item_key("tool", "VectorDB")
        update_workbench_item(key, {"cost_approved": True}, workbench_file=workbench_file)
        entry = get_workbench_item(key, workbench_file=workbench_file)
        assert entry["cost_approved"] is True

    def test_update_cost_flagged(self, workbench_file):
        add_to_workbench(_sample_tool(), workbench_file=workbench_file)
        key = make_item_key("tool", "VectorDB")
        update_workbench_item(
            key,
            {"cost_flagged": True, "cost_notes": "Subscription required."},
            workbench_file=workbench_file,
        )
        entry = get_workbench_item(key, workbench_file=workbench_file)
        assert entry["cost_flagged"] is True
        assert "Subscription" in entry["cost_notes"]

    def test_update_findings_path(self, workbench_file, tmp_path):
        add_to_workbench(_sample_tool(), workbench_file=workbench_file)
        key = make_item_key("tool", "VectorDB")
        findings = tmp_path / "experiment_findings.md"
        findings.write_text("# Findings\nINTEGRATE")
        update_workbench_item(
            key,
            {"findings_path": str(findings)},
            workbench_file=workbench_file,
        )
        entry = get_workbench_item(key, workbench_file=workbench_file)
        assert entry["findings_path"] == str(findings)

    def test_source_item_id_not_updatable(self, workbench_file):
        add_to_workbench(_sample_tool(), workbench_file=workbench_file)
        key = make_item_key("tool", "VectorDB")
        with pytest.raises(ValueError, match="Disallowed"):
            update_workbench_item(
                key,
                {"source_item_id": "hack"},
                workbench_file=workbench_file,
            )


class TestFullSandboxPipeline:
    def test_pipeline_add_research_sandbox_ready(self, workbench_file, tmp_path):
        """Full pipeline: add → research → sandbox_creating → sandbox_ready."""
        tool = _sample_tool()
        add_to_workbench(tool, workbench_file=workbench_file)
        key = make_item_key("tool", "VectorDB")

        # Simulate research completing
        update_workbench_item(
            key,
            {
                "status": "researched",
                "experiment_type": "programmatic",
                "cost_flagged": False,
                "reviewed": True,
            },
            workbench_file=workbench_file,
        )

        entry = get_workbench_item(key, workbench_file=workbench_file)
        assert entry["status"] == "researched"
        assert entry["reviewed"] is True

        # Simulate sandbox creating and ready
        findings = tmp_path / "experiment_findings.md"
        findings.write_text("## Results\nPASSED")
        update_workbench_item(
            key,
            {
                "status": "sandbox_ready",
                "sandbox_dir": str(tmp_path),
                "findings_path": str(findings),
            },
            workbench_file=workbench_file,
        )

        final = get_workbench_item(key, workbench_file=workbench_file)
        assert final["status"] == "sandbox_ready"
        assert final["findings_path"] is not None

    def test_vault_note_contains_findings(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / "Projects").mkdir(parents=True)
        sandbox_dir = tmp_path / "sandbox"

        path = write_sandbox_note(
            _sample_tool(),
            "VectorDB overview.",
            sandbox_dir,
            vault,
            findings_text="INTEGRATE — 20% latency improvement.",
        )
        content = path.read_text()
        assert "VectorDB overview." in content
        assert "INTEGRATE" in content

    def test_workbench_survives_concurrent_reads(self, workbench_file):
        add_to_workbench(_sample_tool(), workbench_file=workbench_file)
        items1 = get_workbench_items(workbench_file=workbench_file)
        items2 = get_workbench_items(workbench_file=workbench_file)
        assert items1 == items2
