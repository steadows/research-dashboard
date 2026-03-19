"""Prompt builder — constructs prompts for Claude API analysis.

Provides quick (Haiku) and deep (Sonnet) prompt variants with shared
formatting helpers to avoid duplication.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Direction arrows for graph neighbors
_DIRECTION_ARROWS: dict[str, str] = {"in": "<-", "out": "->", "both": "<->"}


def _sanitize_note_name(name: str) -> str:
    """Escape XML control characters and normalize a vault note name.

    Prevents prompt injection via adversarial note names.

    Args:
        name: Raw note name from the vault graph.

    Returns:
        Sanitized string safe for prompt insertion.
    """
    sanitized = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    sanitized = sanitized.replace("\n", " ").replace("\r", " ")
    return sanitized[:200]


def _format_graph_context(graph_ctx: dict[str, Any] | None) -> str:
    """Format graph context data into a prompt section.

    Args:
        graph_ctx: Graph context dict with community_members, neighbors,
            suggested_connections, centrality_rank, node_count. Or None.

    Returns:
        Formatted string for prompt injection, or empty string.
    """
    if not graph_ctx:
        return ""

    lines: list[str] = []

    # Community peers
    community = graph_ctx.get("community_members")
    if community:
        peers = sorted(_sanitize_note_name(m) for m in community)
        lines.append(f"Community peers: {', '.join(peers)}")

    # Top neighbors
    neighbors = graph_ctx.get("neighbors", [])[:5]
    if neighbors:
        nb_lines = []
        for nb in neighbors:
            arrow = _DIRECTION_ARROWS.get(nb.get("direction", ""), "")
            name = _sanitize_note_name(nb.get("name", ""))
            score = nb.get("pagerank", 0.0)
            nb_lines.append(f"  {arrow} {name} (PageRank: {score:.4f})")
        lines.append("Top neighbors:\n" + "\n".join(nb_lines))

    # Suggested connections
    suggested = graph_ctx.get("suggested_connections", [])[:5]
    if suggested:
        sg_lines = []
        for name, score in suggested:
            sg_lines.append(f"  {_sanitize_note_name(name)} (Adamic-Adar: {score:.2f})")
        lines.append("Suggested connections:\n" + "\n".join(sg_lines))

    # Centrality rank
    rank = graph_ctx.get("centrality_rank")
    node_count = graph_ctx.get("node_count")
    if rank is not None and node_count is not None:
        lines.append(f"Centrality: #{rank} of {node_count}")

    return "\n".join(lines)


def _format_item_context(item: dict) -> str:
    """Format item details into a prompt section.

    Args:
        item: Item dict with at least 'name', optionally 'source',
              'status', 'why_it_matters', 'what_it_does'.

    Returns:
        Formatted string describing the item.
    """
    lines = [f"Item: {item.get('name', 'Unknown')}"]

    if source := item.get("source"):
        lines.append(f"Source: {source}")
    if status := item.get("status"):
        lines.append(f"Status: {status}")
    if why := item.get("why_it_matters"):
        lines.append(f"Why it matters: {why}")
    if what := item.get("what_it_does"):
        lines.append(f"What it does: {what}")
    if description := item.get("description"):
        lines.append(f"Description: {description}")

    return "\n".join(lines)


def _format_project_context(project: dict, *, include_full: bool = False) -> str:
    """Format project details into a prompt section.

    Args:
        project: Project dict with at least 'name', optionally 'status',
                 'domain', 'tech_stack', 'overview', 'gsd_plan'.
        include_full: If True, include overview and GSD plan for deep analysis.

    Returns:
        Formatted string describing the project.
    """
    lines = [f"Project: {project.get('name', 'Unknown')}"]

    if status := project.get("status"):
        lines.append(f"Status: {status}")
    if domain := project.get("domain"):
        lines.append(f"Domain: {domain}")

    tech_stack = project.get("tech", project.get("tech_stack", []))
    if tech_stack:
        lines.append(f"Tech Stack: {', '.join(tech_stack)}")

    if include_full:
        if overview := project.get("overview"):
            lines.append(f"\nProject Overview:\n{overview}")
        if gsd_plan := project.get("gsd_plan"):
            lines.append(f"\nCurrent GSD Plan:\n{gsd_plan}")

    return "\n".join(lines)


def build_quick_prompt(
    item: dict,
    project: dict,
    *,
    graph_context: dict[str, Any] | None = None,
) -> str:
    """Build a concise prompt for quick relevance analysis (Haiku).

    Args:
        item: Item dict (method, tool, or blog idea).
        project: Project dict with context.
        graph_context: Optional graph context for vault network intelligence.

    Returns:
        Prompt string for quick analysis.
    """
    item_context = _format_item_context(item)
    project_context = _format_project_context(project, include_full=True)
    graph_block = _format_graph_context(graph_context)

    graph_section = ""
    if graph_block:
        graph_section = f"""

<graph_context>
{graph_block}
</graph_context>"""

    graph_objective = ""
    if graph_block:
        graph_objective = (
            " Factor in the project's graph structure — community peers and "
            "suggested connections indicate related work that may increase relevance."
        )

    return f"""\
<context>
You are a research relevance analyst. A researcher is triaging items from their reading \
list against active projects to decide where to focus next.

--- ITEM ---
{item_context}

--- PROJECT ---
{project_context}
</context>{graph_section}

<objective>
Assess how relevant this item is to the given project.{graph_objective}
</objective>

<style>
Concise and structured. Three lines, nothing more.
</style>

<tone>
Analytical and direct.
</tone>

<audience>
The researcher themselves — this feeds a personal triage dashboard.
</audience>

<response>
Exactly 3 lines, plain text:
1. Relevance score (1–5, where 5 = directly applicable)
2. One-sentence explanation of why it is or isn't relevant
3. Suggested next action (try it / skip / bookmark / investigate)
</response>"""


def build_deep_prompt(
    item: dict,
    project: dict,
    *,
    graph_context: dict[str, Any] | None = None,
) -> str:
    """Build a detailed prompt for deep analysis (Sonnet).

    Includes full project context, GSD plan, and tech stack for
    comprehensive relevance and implementation analysis.

    Args:
        item: Item dict (method, tool, or blog idea).
        project: Project dict with full context.
        graph_context: Optional graph context for vault network intelligence.

    Returns:
        Prompt string for deep analysis.
    """
    item_context = _format_item_context(item)
    project_context = _format_project_context(project, include_full=True)
    graph_block = _format_graph_context(graph_context)

    graph_section = ""
    if graph_block:
        graph_section = f"""

<graph_context>
{graph_block}
</graph_context>"""

    graph_objective = ""
    if graph_block:
        graph_objective = (
            " Use the graph structure to assess cross-project relevance — "
            "community peers and suggested connections reveal related work."
        )

    return f"""\
<context>
You are a senior research engineer performing a deep analysis of how a research item \
applies to a specific project. You have full project context including the tech stack, \
current status, and active GSD plan.

--- ITEM ---
{item_context}

--- PROJECT (Full Context) ---
{project_context}
</context>{graph_section}

<objective>
Provide a comprehensive analysis of this item's applicability to the project, including \
integration path, risks, and concrete next steps.{graph_objective}
</objective>

<style>
Detailed and structured. Use numbered sections matching the response format exactly.
</style>

<tone>
Expert, technical, and pragmatic. Prioritise actionability over thoroughness.
</tone>

<audience>
The engineer who owns the project — they want actionable recommendations, not summaries \
of what they already know.
</audience>

<response>
Six numbered sections:
1. Relevance score (1–5, where 5 = directly applicable)
2. Detailed explanation of relevance to this specific project
3. How this could be integrated into the current tech stack
4. Potential risks or trade-offs
5. Concrete next steps for implementation
6. Estimated effort (hours/days) and complexity (low/medium/high)
</response>"""
