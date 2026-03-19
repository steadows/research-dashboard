"""Shared test fixtures for the research-dashboard test suite."""

from pathlib import Path

import networkx as nx
import pytest


@pytest.fixture
def tmp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault with realistic project and research files."""
    # Projects
    projects_dir = tmp_path / "Projects"
    projects_dir.mkdir()

    (projects_dir / "Axon.md").write_text(
        "# Axon\n\n"
        "**Type:** Developer Tool\n"
        "**Status:** Active\n"
        "**Stack:** Python, KuzuDB\n\n"
        "## Overview\n\nCode intelligence graph.\n"
    )

    (projects_dir / "Wealth Manager.md").write_text(
        "---\n"
        "tags:\n  - project\n  - active\n"
        "status: active\n"
        "domain: Native Apps\n"
        "tech: [SwiftUI, FastAPI, Plaid]\n"
        "---\n\n"
        "# Wealth Manager\n\n"
        "AI personal CFO.\n\n"
        "## Tech Stack\n"
        "[[SwiftUI]] · [[FastAPI]] · [[Plaid]]\n\n"
        "## Plans\n"
        "- [[Wealth Manager GSD Plan]]\n"
    )

    # Research directory
    research_dir = tmp_path / "Research"
    research_dir.mkdir()

    (research_dir / "Methods to Try.md").write_text(
        "# Methods to Try\n\n"
        "## Graph RAG for Code Search\n"
        "**Source:** JournalClub 2026-03-07\n"
        "**Status:** New\n"
        "**Why it matters:** Combines graph structure with retrieval.\n"
        "**Projects:** [[Axon]], [[Autoresearch]]\n\n"
        "## Prompt Caching with Claude\n"
        "**Source:** JournalClub 2026-02-28\n"
        "**Status:** Reviewed\n"
        "**Why it matters:** Reduces API costs significantly.\n"
        "**Projects:** [[Wealth Manager]]\n"
    )

    (research_dir / "Tools Radar.md").write_text(
        "# Tools Radar\n\n"
        "## Cursor Tab\n"
        "**Category:** IDE\n"
        "**Source:** TLDR 2026-03-07\n"
        "**Status:** New\n"
        "**What it does:** AI-powered tab completion.\n"
        "**Projects:** [[Axon]]\n\n"
        "## Valkey\n"
        "**Category:** Database\n"
        "**Source:** TLDR 2026-02-28\n"
        "**Status:** New\n"
        "**What it does:** Redis fork.\n"
        "**Projects:** [[Wealth Manager]], [[DinnerBot]]\n"
    )

    # JournalClub reports
    jc_dir = research_dir / "JournalClub"
    jc_dir.mkdir()

    (jc_dir / "JournalClub 2026-03-07.md").write_text(
        "# JournalClub — 2026-03-07\n\n"
        "## Top Picks\n"
        "1. Graph RAG paper\n"
        "2. Mixture of Agents\n\n"
        "## Methods\n"
        "- Graph RAG for Code Search\n\n"
        "## Key Takeaways\n"
        "Graphs are the future of RAG.\n"
    )

    # TLDR reports
    tldr_dir = research_dir / "TLDR"
    tldr_dir.mkdir()

    (tldr_dir / "TLDR 2026-03-07.md").write_text(
        "# TLDR AI — 2026-03-07\n\n"
        "## Headlines\n"
        "- Claude 4 released\n\n"
        "## Tools\n"
        "- Cursor Tab\n\n"
        "## \U0001f4f0 AI Signal\n"
        "The industry is shifting toward agent-first.\n"
    )

    # Writing directory
    writing_dir = tmp_path / "Writing"
    writing_dir.mkdir()

    (writing_dir / "Blog Queue.md").write_text(
        "# Blog Queue\n\n"
        "## Building a Code Knowledge Graph\n"
        "**Status:** Draft\n"
        "**Hook:** Technical deep-dive on Axon architecture.\n"
        "**Tags:** research, graph, ml\n"
        "**Projects:** [[Axon]]\n"
        "**Added:** 2026-03-01\n\n"
        "## AI CFO: Building Wealth Manager\n"
        "**Status:** Idea\n"
        "**Hook:** Journey building a personal finance AI.\n"
        "**Projects:** [[Wealth Manager]]\n"
    )

    # Plans directory
    plans_dir = tmp_path / "Plans"
    plans_dir.mkdir()

    (plans_dir / "Wealth Manager GSD Plan.md").write_text(
        "# Wealth Manager GSD Plan\n\n## Phase 1\n- [x] Setup project\n"
    )

    return tmp_path


@pytest.fixture
def graph_fixture() -> nx.DiGraph:
    """Build a small DiGraph with known topology for graph engine tests.

    Topology:
        8 nodes: 3 projects (A, B, C), 3 methods (M1, M2, M3), 2 tools (T1, T2)
        Edges: A→M1, A→T1, B→M2, B→T1, B→T2, C→M3, M1→T1, M2→M3
        Hub: T1 (3 in-degree)
        Bridge: B (connects two clusters)
        Weak node: C (only 2 edges)
        Clusters: {A, M1, T1} and {B, M2, M3, T2, C}
    """
    G = nx.DiGraph()
    G.add_nodes_from(["A", "B", "C", "M1", "M2", "M3", "T1", "T2"])
    G.add_edges_from(
        [
            ("A", "M1"),
            ("A", "T1"),
            ("B", "M2"),
            ("B", "T1"),
            ("B", "T2"),
            ("C", "M3"),
            ("M1", "T1"),
            ("M2", "M3"),
        ]
    )
    return G


@pytest.fixture
def empty_vault(tmp_path: Path) -> Path:
    """Create a vault with required directories but no content files."""
    (tmp_path / "Projects").mkdir()
    (tmp_path / "Research").mkdir()
    (tmp_path / "Writing").mkdir()
    return tmp_path
