"""Tests for prompt_builder — quick and deep prompt construction."""

from utils.prompt_builder import build_deep_prompt, build_quick_prompt


# --- Fixtures ---

SAMPLE_ITEM = {
    "name": "Graph RAG for Code Search",
    "source": "JournalClub 2026-03-07",
    "status": "New",
    "why_it_matters": "Combines graph structure with retrieval.",
}

SAMPLE_PROJECT = {
    "name": "Axon",
    "status": "Active",
    "domain": "Developer Tools",
    "tech_stack": ["Python", "KuzuDB"],
    "overview": "Code intelligence graph for static analysis.",
    "gsd_plan": "## Phase 1\n- [x] Setup project\n- [ ] Build parser",
}


class TestBuildQuickPrompt:
    """Tests for build_quick_prompt."""

    def test_contains_item_name(self) -> None:
        prompt = build_quick_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Graph RAG for Code Search" in prompt

    def test_contains_project_name(self) -> None:
        prompt = build_quick_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Axon" in prompt

    def test_contains_item_description(self) -> None:
        prompt = build_quick_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Combines graph structure with retrieval" in prompt

    def test_contains_project_context(self) -> None:
        prompt = build_quick_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Developer Tools" in prompt

    def test_returns_string(self) -> None:
        prompt = build_quick_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_minimal_item_no_crash(self) -> None:
        """Minimal item dict with only a name should still produce a prompt."""
        minimal_item = {"name": "Test Item"}
        minimal_project = {"name": "Test Project"}
        prompt = build_quick_prompt(minimal_item, minimal_project)
        assert "Test Item" in prompt
        assert "Test Project" in prompt


class TestBuildDeepPrompt:
    """Tests for build_deep_prompt."""

    def test_contains_item_name(self) -> None:
        prompt = build_deep_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Graph RAG for Code Search" in prompt

    def test_contains_full_project_context(self) -> None:
        prompt = build_deep_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Axon" in prompt
        assert "Developer Tools" in prompt
        assert "Code intelligence graph" in prompt

    def test_contains_tech_stack(self) -> None:
        prompt = build_deep_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Python" in prompt
        assert "KuzuDB" in prompt

    def test_contains_gsd_plan(self) -> None:
        prompt = build_deep_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert "Phase 1" in prompt

    def test_deep_longer_than_quick(self) -> None:
        quick = build_quick_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        deep = build_deep_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        assert len(deep) > len(quick)

    def test_no_duplicated_stack_formatting(self) -> None:
        """Tech stack should appear once in the prompt, not duplicated."""
        prompt = build_deep_prompt(SAMPLE_ITEM, SAMPLE_PROJECT)
        # Count occurrences of the tech stack items — they should appear
        # together in one section, not scattered/duplicated
        python_count = prompt.count("Python")
        kuzu_count = prompt.count("KuzuDB")
        # Each tech item should appear exactly once (or twice max if in
        # both item and project context — but not more)
        assert python_count <= 2
        assert kuzu_count <= 2

    def test_missing_gsd_plan_no_crash(self) -> None:
        """Project without a GSD plan should not crash."""
        project_no_plan = {
            "name": "Axon",
            "status": "Active",
            "domain": "Developer Tools",
            "tech_stack": ["Python"],
        }
        prompt = build_deep_prompt(SAMPLE_ITEM, project_no_plan)
        assert "Axon" in prompt
