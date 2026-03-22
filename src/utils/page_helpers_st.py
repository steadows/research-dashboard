"""Streamlit-dependent page helpers — UI rendering functions that require streamlit."""

from typing import TYPE_CHECKING

from utils.page_helpers import safe_html

if TYPE_CHECKING:
    from utils.paper_fetcher import PaperContext


# ---------------------------------------------------------------------------
# Fetch state badge colors
# ---------------------------------------------------------------------------

_FETCH_STATE_BADGES: dict[str, tuple[str, str]] = {
    "not_fetched": ("#6B7280", "Not fetched"),
    "not_found": ("#9CA3AF", "Not found"),
    "failed": ("#EF4444", "Failed"),
    "abstract_only": ("#F59E0B", "Abstract only"),
    "pdf": ("#10B981", "PDF full text"),
    "arxiv_html": ("#10B981", "arXiv HTML"),
}


def render_context_sources(
    paper_context: "PaperContext | None",
    connected_projects: list[str],
) -> None:
    """Render a context sources expander showing what data the LLM has access to.

    Uses the paper_context's explicit fetch_state field for status display.

    Args:
        paper_context: PaperContext dict or None if not yet fetched.
        connected_projects: List of connected project names.
    """
    import streamlit as st

    with st.expander("📊 Context Sources"):
        # Paper context status
        if paper_context is None:
            fetch_state = "not_fetched"
            abstract_len = 0
            full_text_len = 0
            error_msg = ""
        else:
            fetch_state = paper_context.get("fetch_state", "not_fetched")
            abstract_len = len(paper_context.get("abstract", ""))
            full_text_len = len(paper_context.get("full_text", ""))
            error_msg = paper_context.get("error", "")

        color, label = _FETCH_STATE_BADGES.get(fetch_state, ("#6B7280", fetch_state))

        st.markdown(
            f'**Paper Context:** <span style="color:{color};font-weight:600">'
            f"{safe_html(label)}</span>",
            unsafe_allow_html=True,
        )

        if abstract_len:
            tokens_est = abstract_len // 4
            st.caption(f"Abstract: {abstract_len:,} chars (~{tokens_est:,} tokens)")

        if full_text_len:
            tokens_est = full_text_len // 4
            st.caption(f"Full text: {full_text_len:,} chars (~{tokens_est:,} tokens)")

        if error_msg:
            st.caption(f"Error: {safe_html(error_msg)}")

        # Connected projects
        if connected_projects:
            project_list = ", ".join(safe_html(p) for p in connected_projects)
            st.markdown(
                f"**Connected Projects:** {project_list}",
                unsafe_allow_html=True,
            )
        else:
            st.caption("No connected projects")
