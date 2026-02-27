"""Content curation tools — Jordan Ward angle analysis and format suggestions."""

from __future__ import annotations

from typing import Any

from ._shared import mcp


@mcp.tool()
def content_curate(
    description: str,
    context: str = "",
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Full content curation pipeline.

    Takes something Jordan found valuable (screenshot description, article,
    observation, idea) and returns:
    - The Jordan Ward angle (WHY this matters through his lens)
    - Best content formats (bridge_builder, real_talk, ask_the_audience, etc.)
    - Story connections (which life experiences connect)
    - Draft angles per platform (hook + framing guidance)

    Args:
        description: What you found — describe the screenshot, article, or idea
        context: Why it caught your eye (optional)
        platforms: Target platforms (default: linkedin, twitter, instagram)
    """
    from lib.agents import content_curator as _cc

    curator = _cc.ContentCurator(persona_mode="ceo")
    return curator.curate(description, context, platforms)


@mcp.tool()
def content_analyze_angle(
    description: str,
    context: str = "",
) -> dict[str, Any]:
    """Analyze the Jordan Ward angle on content.

    Determines WHY this matters through Jordan's lens — his background
    (Novi MI, Swizzimatic videography, reinvention, faith, mission)
    makes him uniquely positioned to talk about it.

    Returns themes, jordan_connection, audience_value, and tone suggestion.

    Args:
        description: What was found
        context: Why it caught his eye (optional)
    """
    from lib.agents import content_curator as _cc

    curator = _cc.ContentCurator(persona_mode="ceo")
    return curator.analyze_angle(description, context)


@mcp.tool()
def content_suggest_formats(
    description: str,
) -> list[dict[str, Any]]:
    """Rank which CEO content formats best fit this content.

    Scores each format (bridge_builder, real_talk, ask_the_audience,
    problem_solution, myth_busting, quick_tips, industry_commentary,
    vibe_coder, case_study, day_in_life) based on signal matching.

    Returns ranked list with scores, descriptions, and when-to-use guidance.

    Args:
        description: Content description to analyze
    """
    from lib.agents import content_curator as _cc

    curator = _cc.ContentCurator(persona_mode="ceo")
    return curator.suggest_formats(description)
