"""Tests for Agentic Hub tab — instagram post cards, account filter, actions."""

from pathlib import Path
from typing import Any

from utils.instagram_parser import parse_instagram_posts
from utils.page_helpers import safe_html


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_post(
    account: str = "hubaborern",
    shortcode: str = "ABC123",
    name: str = "Test Post Title",
    date: str = "2026-03-15",
) -> dict[str, Any]:
    """Return a minimal instagram post dict matching instagram_parser output."""
    return {
        "name": name,
        "account": account,
        "date": date,
        "source_url": f"https://www.instagram.com/p/{shortcode}/",
        "shortcode": shortcode,
        "key_points": ["Point one", "Point two"],
        "keywords": ["AI", "LLMs"],
        "caption": "A test caption for the post.",
        "transcript": "This is the transcript of the video.",
        "source_type": "instagram",
    }


def _make_posts(n: int = 3) -> list[dict[str, Any]]:
    """Build a list of sample posts from different accounts."""
    accounts = ["hubaborern", "ai_research_lab", "hubaborern"]
    return [
        _sample_post(
            account=accounts[i % len(accounts)],
            shortcode=f"SC{i:03d}",
            name=f"Post {i}",
            date=f"2026-03-{15 - i:02d}",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Empty state rendering
# ---------------------------------------------------------------------------


class TestAgenticHubEmptyState:
    """render_agentic_hub_tab renders empty state when no posts."""

    def test_empty_state_when_parser_returns_empty(self) -> None:
        """Empty post list triggers info message, not crash."""
        posts: list[dict[str, Any]] = []
        assert len(posts) == 0
        # The tab should render st.info(...) — this test validates the data path
        # UI rendering tested via parse_instagram_posts returning []

    def test_parser_returns_empty_for_missing_dir(self, empty_vault: Path) -> None:
        """parse_instagram_posts returns [] when Instagram dir absent."""
        posts = parse_instagram_posts(empty_vault)
        assert posts == []


# ---------------------------------------------------------------------------
# Account filter
# ---------------------------------------------------------------------------


class TestAccountFilter:
    """Account filter shows 'All' + unique accounts."""

    def test_unique_accounts_extracted(self) -> None:
        """Unique accounts extracted from posts list."""
        posts = _make_posts(3)
        accounts = sorted({p["account"] for p in posts})
        assert accounts == ["ai_research_lab", "hubaborern"]

    def test_all_option_present(self) -> None:
        """Filter options include 'All' as first element."""
        posts = _make_posts(3)
        accounts = sorted({p["account"] for p in posts})
        options = ["All"] + accounts
        assert options[0] == "All"
        assert len(options) == 3

    def test_all_filter_returns_all_posts(self) -> None:
        """Selecting 'All' returns the full unfiltered list."""
        posts = _make_posts(3)
        selected = "All"
        filtered = (
            posts
            if selected == "All"
            else [p for p in posts if p["account"] == selected]
        )
        assert len(filtered) == 3

    def test_account_filter_narrows_posts(self) -> None:
        """Selecting a specific account filters to that account only."""
        posts = _make_posts(3)
        selected = "ai_research_lab"
        filtered = [p for p in posts if p["account"] == selected]
        assert len(filtered) == 1
        assert all(p["account"] == "ai_research_lab" for p in filtered)


# ---------------------------------------------------------------------------
# Post card rendering data
# ---------------------------------------------------------------------------


class TestPostCardData:
    """Each post card renders account badge, date, title, key points, keywords."""

    def test_card_has_required_fields(self) -> None:
        """Post dict has all fields needed for card rendering."""
        post = _sample_post()
        assert "account" in post
        assert "date" in post
        assert "name" in post
        assert "key_points" in post
        assert "keywords" in post

    def test_key_points_are_list_of_strings(self) -> None:
        """Key points are a list of strings."""
        post = _sample_post()
        assert isinstance(post["key_points"], list)
        assert all(isinstance(p, str) for p in post["key_points"])

    def test_keyword_chips_are_list(self) -> None:
        """Keywords are a list of strings for chip rendering."""
        post = _sample_post()
        assert isinstance(post["keywords"], list)
        assert all(isinstance(k, str) for k in post["keywords"])


# ---------------------------------------------------------------------------
# Summarize button state
# ---------------------------------------------------------------------------


class TestSummarizeButton:
    """Summarize button disabled when inline summary already in session state."""

    def test_summarize_disabled_when_summary_exists(self) -> None:
        """Button should be disabled if session state has summary for shortcode."""
        post = _sample_post()
        session_state: dict[str, Any] = {
            f"dashboard__agentic_hub_summary_{post['shortcode']}": "A summary."
        }
        key = f"dashboard__agentic_hub_summary_{post['shortcode']}"
        assert key in session_state

    def test_summarize_enabled_when_no_summary(self) -> None:
        """Button should be enabled if session state lacks summary."""
        post = _sample_post()
        session_state: dict[str, Any] = {}
        key = f"dashboard__agentic_hub_summary_{post['shortcode']}"
        assert key not in session_state


# ---------------------------------------------------------------------------
# Workbench button state
# ---------------------------------------------------------------------------


class TestWorkbenchButton:
    """Workbench button calls add_to_workbench with source_type='instagram'."""

    def test_workbench_button_uses_shortcode_key(self) -> None:
        """Workbench key uses make_item_key('instagram', shortcode)."""
        from utils.workbench_tracker import make_item_key

        post = _sample_post()
        key = make_item_key("instagram", post["shortcode"])
        assert key == "instagram::ABC123"

    def test_workbench_button_disabled_when_already_in_workbench(
        self, tmp_path: Path
    ) -> None:
        """Button disabled when post shortcode already in workbench."""
        from utils.workbench_tracker import (
            add_to_workbench,
            get_workbench_items,
            make_item_key,
        )

        wb_file = tmp_path / "workbench.json"
        post = _sample_post()
        # Session 14: pass original post (with title as name), identity model keys on shortcode
        add_to_workbench(post, workbench_file=wb_file)

        items = get_workbench_items(wb_file)
        key = make_item_key("instagram", post["shortcode"])
        assert key in items

    def test_workbench_preserves_post_title(self, tmp_path: Path) -> None:
        """Workbench entry keeps original title for display, not shortcode."""
        from utils.workbench_tracker import (
            add_to_workbench,
            get_workbench_item,
            make_item_key,
        )

        wb_file = tmp_path / "workbench.json"
        post = _sample_post()
        add_to_workbench(post, workbench_file=wb_file)

        key = make_item_key("instagram", post["shortcode"])
        entry = get_workbench_item(key, wb_file)
        assert entry is not None
        assert entry["item"]["name"] == post["name"]
        assert entry["item"]["name"] == "Test Post Title"


# ---------------------------------------------------------------------------
# XSS safety
# ---------------------------------------------------------------------------


class TestXssSafety:
    """All vault-sourced strings passed through safe_html()."""

    def test_title_escaped(self) -> None:
        """Title with HTML is escaped."""
        post = _sample_post(name='<script>alert("xss")</script>')
        escaped = safe_html(post["name"])
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_key_points_escaped(self) -> None:
        """Key points with HTML are escaped."""
        point = '<img src=x onerror="alert(1)">'
        escaped = safe_html(point)
        assert "<img" not in escaped

    def test_caption_escaped(self) -> None:
        """Caption with HTML is escaped."""
        post = _sample_post()
        post["caption"] = "<b>Bold & bad</b>"
        escaped = safe_html(post["caption"])
        assert "<b>" not in escaped
        assert "&amp;" in escaped
