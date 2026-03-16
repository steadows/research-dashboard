"""Tests for smart_matcher — hybrid explicit + inferred item-to-project matching."""

from pathlib import Path
from typing import Any


class TestExplicitMatches:
    """Explicit wiki-link matches are preserved as Tier 1."""

    def test_explicit_matches_have_correct_match_type(
        self, tmp_vault: Path,
    ) -> None:
        """Items with wiki-links should have match_type='explicit'."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_vault))

        assert "Axon" in index
        explicit_items = [
            i for i in index["Axon"] if i["match_type"] == "explicit"
        ]
        assert len(explicit_items) >= 1
        names = [i["name"] for i in explicit_items]
        assert "Graph RAG for Code Search" in names

    def test_explicit_matches_have_confidence_1(
        self, tmp_vault: Path,
    ) -> None:
        """Explicit matches should always have confidence 1.0."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_vault))

        for items in index.values():
            for item in items:
                if item["match_type"] == "explicit":
                    assert item["confidence"] == 1.0

    def test_explicit_matches_preserve_all_fields(
        self, tmp_vault: Path,
    ) -> None:
        """Explicit items should retain all original fields plus match_type/confidence."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_vault))

        axon_items = index.get("Axon", [])
        graph_rag = next(
            (i for i in axon_items if i["name"] == "Graph RAG for Code Search"),
            None,
        )
        assert graph_rag is not None
        assert graph_rag["source_type"] == "method"
        assert "match_type" in graph_rag
        assert "confidence" in graph_rag


class TestInferredMatches:
    """Inferred matches via tech/keyword overlap (Tier 2)."""

    def test_tech_stack_keyword_match(self, tmp_path: Path) -> None:
        """An item mentioning a project's tech should produce an inferred match."""
        _build_vault_with_tech_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        # "PyTorch Profiler" tool mentions PyTorch; MLProject has PyTorch in tech
        ml_items = index.get("MLProject", [])
        inferred = [i for i in ml_items if i["match_type"] == "inferred"]
        inferred_names = [i["name"] for i in inferred]
        assert "PyTorch Profiler" in inferred_names

    def test_inferred_match_has_confidence_range(self, tmp_path: Path) -> None:
        """Inferred matches should have confidence between threshold and 0.9."""
        _build_vault_with_tech_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        ml_items = index.get("MLProject", [])
        inferred = [i for i in ml_items if i["match_type"] == "inferred"]
        for item in inferred:
            assert 0.3 <= item["confidence"] <= 0.9

    def test_inferred_match_type_is_inferred(self, tmp_path: Path) -> None:
        """Inferred items should have match_type='inferred'."""
        _build_vault_with_tech_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        ml_items = index.get("MLProject", [])
        inferred = [i for i in ml_items if i["match_type"] == "inferred"]
        assert len(inferred) > 0
        for item in inferred:
            assert item["match_type"] == "inferred"


class TestNoDuplicates:
    """Items should not appear twice for the same project (explicit + inferred)."""

    def test_no_duplicate_items_for_same_project(self, tmp_path: Path) -> None:
        """If an item is explicitly linked, it should not also appear as inferred."""
        _build_vault_with_explicit_and_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        ml_items = index.get("MLProject", [])
        # "TensorBoard Helper" is explicitly linked AND has keyword overlap
        tb_items = [i for i in ml_items if i["name"] == "TensorBoard Helper"]
        assert len(tb_items) == 1
        assert tb_items[0]["match_type"] == "explicit"


class TestConfidenceThresholding:
    """Low-confidence matches should be excluded."""

    def test_low_confidence_items_excluded(self, tmp_path: Path) -> None:
        """Items with minimal keyword overlap should not appear."""
        _build_vault_with_no_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        # "Cooking Recipe Parser" has nothing in common with "MLProject"
        ml_items = index.get("MLProject", [])
        item_names = [i["name"] for i in ml_items]
        assert "Cooking Recipe Parser" not in item_names


class TestEmptyVault:
    """Edge case: empty vault returns empty index."""

    def test_empty_vault_returns_empty_index(self, empty_vault: Path) -> None:
        """An empty vault should produce an empty smart index."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(empty_vault))
        assert index == {}


class TestNoMatchItems:
    """Items with no matches (explicit or inferred) should not appear."""

    def test_unmatched_items_absent(self, tmp_path: Path) -> None:
        """Items that don't match any project should not create index entries."""
        _build_vault_with_no_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        # No project should contain "Cooking Recipe Parser"
        for project_name, items in index.items():
            item_names = [i["name"] for i in items]
            assert "Cooking Recipe Parser" not in item_names


class TestSortOrder:
    """Items should be sorted: explicit first, then inferred by confidence desc."""

    def test_explicit_before_inferred(self, tmp_path: Path) -> None:
        """Explicit matches should appear before inferred ones."""
        _build_vault_with_explicit_and_overlap(tmp_path)
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_path))

        ml_items = index.get("MLProject", [])
        if len(ml_items) >= 2:
            # Find first inferred item index
            first_inferred_idx = next(
                (i for i, item in enumerate(ml_items)
                 if item["match_type"] == "inferred"),
                len(ml_items),
            )
            # All explicit items should come before first inferred
            for i in range(first_inferred_idx):
                assert ml_items[i]["match_type"] == "explicit"


class TestKeywordExtraction:
    """Unit tests for keyword extraction helpers."""

    def test_extract_keywords_filters_stop_words(self) -> None:
        """Stop words should be excluded from keyword sets."""
        from utils.smart_matcher import _extract_keywords

        keywords = _extract_keywords("the quick brown fox is a great system")
        assert "the" not in keywords
        assert "is" not in keywords
        assert "a" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords
        assert "fox" in keywords

    def test_extract_keywords_handles_multi_word_terms(self) -> None:
        """Multi-word tech terms should be recognized as single tokens."""
        from utils.smart_matcher import _extract_keywords

        keywords = _extract_keywords("Using Graph RAG for knowledge graph search")
        assert "graph rag" in keywords
        assert "knowledge graph" in keywords

    def test_extract_keywords_lowercases(self) -> None:
        """All keywords should be lowercase."""
        from utils.smart_matcher import _extract_keywords

        keywords = _extract_keywords("PyTorch FastAPI SwiftUI")
        assert "pytorch" in keywords
        assert "fastapi" in keywords
        assert "swiftui" in keywords

    def test_extract_item_keywords_method(self) -> None:
        """Method items should extract from name + why it matters."""
        from utils.smart_matcher import _extract_item_keywords

        item: dict[str, Any] = {
            "name": "Neural Architecture Search",
            "source_type": "method",
            "why it matters": "Automates PyTorch model design.",
        }
        kw = _extract_item_keywords(item)
        assert "neural" in kw
        assert "pytorch" in kw
        assert "automates" in kw

    def test_extract_item_keywords_tool(self) -> None:
        """Tool items should extract from name + what it does + category."""
        from utils.smart_matcher import _extract_item_keywords

        item: dict[str, Any] = {
            "name": "MLflow",
            "source_type": "tool",
            "what it does": "Experiment tracking for ML pipelines.",
            "category": "MLOps",
        }
        kw = _extract_item_keywords(item)
        assert "mlflow" in kw
        assert "experiment" in kw
        assert "mlops" in kw

    def test_extract_item_keywords_blog(self) -> None:
        """Blog items should extract from name + hook + tags."""
        from utils.smart_matcher import _extract_item_keywords

        item: dict[str, Any] = {
            "name": "Building with FastAPI",
            "source_type": "blog",
            "hook": "Production-ready APIs in Python.",
            "tags": "python, fastapi, backend",
        }
        kw = _extract_item_keywords(item)
        assert "fastapi" in kw
        assert "python" in kw
        assert "backend" in kw


class TestConfidenceScoring:
    """Unit tests for confidence computation."""

    def test_zero_overlap_gives_zero(self) -> None:
        """No keyword overlap should produce 0.0 confidence."""
        from utils.smart_matcher import _compute_confidence

        score = _compute_confidence(
            {"pytorch", "neural"},
            {"cooking", "recipes"},
            {"cooking"},
        )
        assert score == 0.0

    def test_tech_overlap_gives_high_confidence(self) -> None:
        """Multiple tech stack matches should give 0.5+."""
        from utils.smart_matcher import _compute_confidence

        score = _compute_confidence(
            {"pytorch", "fastapi", "python"},
            {"pytorch", "fastapi", "python", "ml", "agent"},
            {"pytorch", "fastapi", "python"},
        )
        assert score >= 0.7

    def test_general_overlap_gives_moderate_confidence(self) -> None:
        """General keyword overlap (no tech) should give moderate score."""
        from utils.smart_matcher import _compute_confidence

        score = _compute_confidence(
            {"agent", "autonomous", "ml"},
            {"agent", "autonomous", "ml", "research"},
            set(),  # no tech keywords
        )
        assert 0.2 <= score <= 0.6

    def test_confidence_capped_at_0_9(self) -> None:
        """Confidence should never exceed 0.9 for inferred matches."""
        from utils.smart_matcher import _compute_confidence

        score = _compute_confidence(
            {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"},
            {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"},
            {"a", "b", "c", "d", "e", "f", "g", "h", "i", "j"},
        )
        assert score <= 0.9


class TestIntegrationWithExistingFixture:
    """Integration tests using the shared tmp_vault fixture."""

    def test_blog_items_included_in_smart_index(self, tmp_vault: Path) -> None:
        """Blog queue items with wiki-links should appear in the smart index."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_vault))

        axon_items = index.get("Axon", [])
        blog_items = [i for i in axon_items if i["source_type"] == "blog"]
        blog_names = [i["name"] for i in blog_items]
        assert "Building a Code Knowledge Graph" in blog_names

    def test_all_items_have_match_metadata(self, tmp_vault: Path) -> None:
        """Every item in the index should have match_type and confidence."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_vault))

        for items in index.values():
            for item in items:
                assert "match_type" in item
                assert "confidence" in item
                assert item["match_type"] in ("explicit", "inferred")
                assert isinstance(item["confidence"], float)

    def test_backward_compatible_structure(self, tmp_vault: Path) -> None:
        """Index should still be dict[str, list[dict]] as before."""
        from utils.smart_matcher import build_smart_project_index

        index = build_smart_project_index(str(tmp_vault))

        assert isinstance(index, dict)
        for key, value in index.items():
            assert isinstance(key, str)
            assert isinstance(value, list)
            for item in value:
                assert isinstance(item, dict)
                assert "name" in item
                assert "source_type" in item

    def test_returns_deep_copies(self, tmp_vault: Path) -> None:
        """Modifying returned items should not affect future calls."""
        from utils.smart_matcher import build_smart_project_index

        index1 = build_smart_project_index(str(tmp_vault))
        if "Axon" in index1 and index1["Axon"]:
            index1["Axon"][0]["name"] = "MUTATED"

        # Clear streamlit cache for test isolation
        build_smart_project_index.clear()

        index2 = build_smart_project_index(str(tmp_vault))
        if "Axon" in index2 and index2["Axon"]:
            assert index2["Axon"][0]["name"] != "MUTATED"


# ---------------------------------------------------------------------------
# Test helpers — build focused vault fixtures
# ---------------------------------------------------------------------------


def _build_vault_with_tech_overlap(vault_path: Path) -> None:
    """Build a vault where items overlap with project tech stacks."""
    projects_dir = vault_path / "Projects"
    projects_dir.mkdir(exist_ok=True)
    (projects_dir / "MLProject.md").write_text(
        "---\n"
        "status: active\n"
        "domain: ML\n"
        "tech: [PyTorch, Python, Weights & Biases]\n"
        "---\n\n"
        "# MLProject\n\n"
        "Autonomous ML experimentation platform.\n"
    )

    research_dir = vault_path / "Research"
    research_dir.mkdir(exist_ok=True)
    (research_dir / "Methods to Try.md").write_text(
        "# Methods\n\n"
        "## Gradient Checkpointing\n"
        "**Source:** JournalClub\n"
        "**Status:** New\n"
        "**Why it matters:** Reduces PyTorch GPU memory.\n"
    )
    (research_dir / "Tools Radar.md").write_text(
        "# Tools\n\n"
        "## PyTorch Profiler\n"
        "**Category:** Profiling\n"
        "**Source:** TLDR\n"
        "**Status:** New\n"
        "**What it does:** Profile PyTorch models.\n"
    )

    writing_dir = vault_path / "Writing"
    writing_dir.mkdir(exist_ok=True)
    (writing_dir / "Blog Queue.md").write_text("# Blog Queue\n")


def _build_vault_with_explicit_and_overlap(vault_path: Path) -> None:
    """Build a vault where an item is both explicitly linked AND has keyword overlap."""
    projects_dir = vault_path / "Projects"
    projects_dir.mkdir(exist_ok=True)
    (projects_dir / "MLProject.md").write_text(
        "---\n"
        "status: active\n"
        "domain: ML\n"
        "tech: [PyTorch, TensorBoard, Python]\n"
        "---\n\n"
        "# MLProject\n\n"
        "Deep learning experimentation.\n"
    )

    research_dir = vault_path / "Research"
    research_dir.mkdir(exist_ok=True)
    (research_dir / "Methods to Try.md").write_text("# Methods\n")
    (research_dir / "Tools Radar.md").write_text(
        "# Tools\n\n"
        "## TensorBoard Helper\n"
        "**Category:** Visualization\n"
        "**Source:** TLDR\n"
        "**Status:** New\n"
        "**What it does:** Enhanced TensorBoard for PyTorch.\n"
        "**Apply to:** [[MLProject]]\n\n"
        "## PyTorch Lightning CLI\n"
        "**Category:** Framework\n"
        "**Source:** TLDR\n"
        "**Status:** New\n"
        "**What it does:** CLI for PyTorch Lightning training.\n"
    )

    writing_dir = vault_path / "Writing"
    writing_dir.mkdir(exist_ok=True)
    (writing_dir / "Blog Queue.md").write_text("# Blog Queue\n")


def _build_vault_with_no_overlap(vault_path: Path) -> None:
    """Build a vault where items have zero keyword overlap with projects."""
    projects_dir = vault_path / "Projects"
    projects_dir.mkdir(exist_ok=True)
    (projects_dir / "MLProject.md").write_text(
        "---\n"
        "status: active\n"
        "domain: ML\n"
        "tech: [PyTorch, Python]\n"
        "---\n\n"
        "# MLProject\n\n"
        "Deep learning research.\n"
    )

    research_dir = vault_path / "Research"
    research_dir.mkdir(exist_ok=True)
    (research_dir / "Methods to Try.md").write_text("# Methods\n")
    (research_dir / "Tools Radar.md").write_text(
        "# Tools\n\n"
        "## Cooking Recipe Parser\n"
        "**Category:** Food\n"
        "**Source:** TLDR\n"
        "**Status:** New\n"
        "**What it does:** Extracts ingredients from cooking blogs.\n"
    )

    writing_dir = vault_path / "Writing"
    writing_dir.mkdir(exist_ok=True)
    (writing_dir / "Blog Queue.md").write_text("# Blog Queue\n")
