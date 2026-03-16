"""Prompt builder — constructs prompts for Claude API analysis.

Provides quick (Haiku) and deep (Sonnet) prompt variants with shared
formatting helpers to avoid duplication.
"""

import logging

logger = logging.getLogger(__name__)


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


def build_quick_prompt(item: dict, project: dict) -> str:
    """Build a concise prompt for quick relevance analysis (Haiku).

    Args:
        item: Item dict (method, tool, or blog idea).
        project: Project dict with context.

    Returns:
        Prompt string for quick analysis.
    """
    item_context = _format_item_context(item)
    project_context = _format_project_context(project, include_full=True)

    return f"""\
<context>
You are a research relevance analyst. A researcher is triaging items from their reading \
list against active projects to decide where to focus next.

--- ITEM ---
{item_context}

--- PROJECT ---
{project_context}
</context>

<objective>
Assess how relevant this item is to the given project.
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


def build_deep_prompt(item: dict, project: dict) -> str:
    """Build a detailed prompt for deep analysis (Sonnet).

    Includes full project context, GSD plan, and tech stack for
    comprehensive relevance and implementation analysis.

    Args:
        item: Item dict (method, tool, or blog idea).
        project: Project dict with full context.

    Returns:
        Prompt string for deep analysis.
    """
    item_context = _format_item_context(item)
    project_context = _format_project_context(project, include_full=True)

    return f"""\
<context>
You are a senior research engineer performing a deep analysis of how a research item \
applies to a specific project. You have full project context including the tech stack, \
current status, and active GSD plan.

--- ITEM ---
{item_context}

--- PROJECT (Full Context) ---
{project_context}
</context>

<objective>
Provide a comprehensive analysis of this item's applicability to the project, including \
integration path, risks, and concrete next steps.
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
