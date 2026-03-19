"""Tests for graph-powered item discovery via project proximity (Tier 3)."""

from __future__ import annotations

from utils.smart_matcher import get_graph_linked_items


# ---------------------------------------------------------------------------
# Helpers — reusable item + index factories
# ---------------------------------------------------------------------------


def _make_item(
    name: str,
    source_type: str = "method",
    match_type: str = "explicit",
    confidence: float = 1.0,
    source: str = "JournalClub 2026-03-07",
) -> dict:
    """Create a minimal item dict for testing."""
    return {
        "name": name,
        "source_type": source_type,
        "source": source,
        "match_type": match_type,
        "confidence": confidence,
    }


def _graph_ctx(
    community_members: frozenset[str] | None = None,
    suggested_connections: list[tuple[str, float]] | None = None,
) -> dict:
    """Build a minimal graph_context dict."""
    ctx: dict = {}
    if community_members is not None:
        ctx["community_members"] = community_members
    if suggested_connections is not None:
        ctx["suggested_connections"] = suggested_connections
    return ctx


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLinkedItemsReturnedWithDiscoverySource:
    """Linked items are returned with discovery_source='linked'."""

    def test_linked_items_tagged_correctly(self) -> None:
        items = [_make_item("M1"), _make_item("T1", source_type="tool")]
        result = get_graph_linked_items("ProjectA", items, {}, graph_context=None)
        assert len(result) == 2
        assert all(r["discovery_source"] == "linked" for r in result)
        assert all(r["via_project"] is None for r in result)

    def test_existing_source_field_preserved(self) -> None:
        items = [_make_item("M1", source="JournalClub 2026-03-07")]
        result = get_graph_linked_items("ProjectA", items, {})
        assert result[0]["source"] == "JournalClub 2026-03-07"


class TestCommunityItemsViaProjectProximity:
    """Community peers propagate their explicitly-linked items."""

    def test_community_items_surfaced(self) -> None:
        linked = [_make_item("M1")]
        index = {
            "ProjectA": [_make_item("M1")],
            "ProjectB": [_make_item("M2", match_type="explicit")],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "ProjectB"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        community_items = [r for r in result if r["discovery_source"] == "community"]
        assert len(community_items) == 1
        assert community_items[0]["name"] == "M2"
        assert community_items[0]["via_project"] == "ProjectB"

    def test_inferred_matches_not_propagated(self) -> None:
        linked = [_make_item("M1")]
        index = {
            "ProjectA": [_make_item("M1")],
            "ProjectB": [_make_item("M2", match_type="inferred", confidence=0.5)],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "ProjectB"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        community_items = [r for r in result if r["discovery_source"] == "community"]
        assert len(community_items) == 0


class TestSuggestedItemsViaProjectProximity:
    """Suggested connections propagate their explicitly-linked items."""

    def test_suggested_items_surfaced(self) -> None:
        linked = [_make_item("M1")]
        index = {
            "ProjectA": [_make_item("M1")],
            "ProjectC": [_make_item("M3", match_type="explicit")],
        }
        ctx = _graph_ctx(suggested_connections=[("ProjectC", 2.5)])
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        suggested = [r for r in result if r["discovery_source"] == "suggested"]
        assert len(suggested) == 1
        assert suggested[0]["name"] == "M3"
        assert suggested[0]["via_project"] == "ProjectC"


class TestCommunityPeersSortedAlphabetically:
    """Community peers sorted alphabetically — via_project is deterministic."""

    def test_via_project_is_alphabetically_first(self) -> None:
        linked: list[dict] = []
        index = {
            "Zebra": [_make_item("SharedMethod", match_type="explicit")],
            "Alpha": [_make_item("SharedMethod", match_type="explicit")],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "Alpha", "Zebra"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        community_items = [r for r in result if r["discovery_source"] == "community"]
        assert len(community_items) == 1
        assert community_items[0]["via_project"] == "Alpha"


class TestDeduplicationCompositeKey:
    """Dedup uses source_type::name composite key."""

    def test_linked_wins_over_community(self) -> None:
        linked = [_make_item("M1")]
        index = {
            "ProjectA": [_make_item("M1")],
            "ProjectB": [_make_item("M1", match_type="explicit")],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "ProjectB"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        m1_items = [r for r in result if r["name"] == "M1"]
        assert len(m1_items) == 1
        assert m1_items[0]["discovery_source"] == "linked"

    def test_community_wins_over_suggested(self) -> None:
        linked: list[dict] = []
        index = {
            "ProjectB": [_make_item("M1", match_type="explicit")],
            "ProjectC": [_make_item("M1", match_type="explicit")],
        }
        ctx = _graph_ctx(
            community_members=frozenset({"ProjectA", "ProjectB"}),
            suggested_connections=[("ProjectC", 2.0)],
        )
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        m1_items = [r for r in result if r["name"] == "M1"]
        assert len(m1_items) == 1
        assert m1_items[0]["discovery_source"] == "community"

    def test_different_source_types_not_collapsed(self) -> None:
        linked = [_make_item("Widget", source_type="method")]
        index = {
            "ProjectB": [
                _make_item("Widget", source_type="tool", match_type="explicit")
            ],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "ProjectB"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        assert len(result) == 2


class TestItemsFromMultiplePeersDeduped:
    """Items from multiple peer projects are deduplicated."""

    def test_first_alphabetical_peer_wins(self) -> None:
        linked: list[dict] = []
        index = {
            "PeerB": [_make_item("M1", match_type="explicit")],
            "PeerA": [_make_item("M1", match_type="explicit")],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectX", "PeerA", "PeerB"}))
        result = get_graph_linked_items("ProjectX", linked, index, graph_context=ctx)
        assert len(result) == 1
        assert result[0]["via_project"] == "PeerA"


class TestPropagatedItemsCarryOriginMetadata:
    """Propagated items have origin_match_type and origin_confidence."""

    def test_origin_fields_present(self) -> None:
        linked: list[dict] = []
        index = {
            "ProjectB": [_make_item("M1", match_type="explicit", confidence=1.0)],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "ProjectB"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        item = result[0]
        assert item["origin_match_type"] == "explicit"
        assert item["origin_confidence"] == 1.0
        assert "match_type" not in item
        assert "confidence" not in item

    def test_linked_items_keep_match_type(self) -> None:
        linked = [_make_item("M1", match_type="explicit", confidence=1.0)]
        result = get_graph_linked_items("ProjectA", linked, {})
        item = result[0]
        assert item.get("match_type") == "explicit"
        assert item.get("confidence") == 1.0
        assert "origin_match_type" not in item


class TestEmptyGraphContextReturnsLinkedOnly:
    """graph_context=None returns only linked items — backward compatible."""

    def test_none_graph_context(self) -> None:
        linked = [_make_item("M1"), _make_item("M2")]
        index = {"ProjectB": [_make_item("M3", match_type="explicit")]}
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=None)
        assert len(result) == 2
        assert all(r["discovery_source"] == "linked" for r in result)


class TestEmptyProjectIndexReturnsEmpty:
    """Empty project index and no linked items returns empty list."""

    def test_empty(self) -> None:
        result = get_graph_linked_items("ProjectA", [], {}, graph_context=None)
        assert result == []


class TestReturnTypeAndImmutability:
    """Return type is list[dict], original items never mutated."""

    def test_return_type(self) -> None:
        linked = [_make_item("M1")]
        result = get_graph_linked_items("ProjectA", linked, {})
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    def test_originals_not_mutated(self) -> None:
        original = _make_item("M1")
        original_keys = set(original.keys())
        get_graph_linked_items("ProjectA", [original], {})
        assert set(original.keys()) == original_keys


class TestSortOrder:
    """Items sorted: linked first, then community, then suggested."""

    def test_sort_order(self) -> None:
        linked = [_make_item("M1")]
        index = {
            "ProjectB": [_make_item("M2", match_type="explicit")],
            "ProjectC": [_make_item("M3", match_type="explicit")],
        }
        ctx = _graph_ctx(
            community_members=frozenset({"ProjectA", "ProjectB"}),
            suggested_connections=[("ProjectC", 2.0)],
        )
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        sources = [r["discovery_source"] for r in result]
        assert sources == ["linked", "community", "suggested"]


class TestPeerProjectEdgeCases:
    """Edge cases: non-existent peers, self-exclusion."""

    def test_nonexistent_peers_ignored(self) -> None:
        linked = [_make_item("M1")]
        ctx = _graph_ctx(community_members=frozenset({"ProjectA", "NonExistent"}))
        result = get_graph_linked_items("ProjectA", linked, {}, graph_context=ctx)
        assert len(result) == 1  # Only linked M1

    def test_self_excluded_from_peer_lookup(self) -> None:
        linked = [_make_item("M1")]
        index = {
            "ProjectA": [_make_item("M1"), _make_item("M2", match_type="explicit")],
        }
        ctx = _graph_ctx(community_members=frozenset({"ProjectA"}))
        result = get_graph_linked_items("ProjectA", linked, index, graph_context=ctx)
        # M2 should NOT appear — ProjectA is excluded from its own peer lookup
        assert len(result) == 1
        assert result[0]["name"] == "M1"
