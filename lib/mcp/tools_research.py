"""Research agent tools — hashtags, content ideas, trending, and content calendar."""

from __future__ import annotations

import json

from ._client_helpers import build_agent_config, suppress_stdout
from ._shared import mcp


def _get_research_agent(persona_mode: str = "professional", platform: str = "instagram"):
    """Create a ResearchAgent with stdout suppression."""
    with suppress_stdout():
        from lib.agents.research_agent import ResearchAgent

        config = build_agent_config(persona_mode, platform)
        return ResearchAgent(config)


@mcp.tool()
def research_hashtags(topic: str, platform: str = "instagram") -> str:
    """Research relevant hashtags for a topic, organized by reach level.

    Args:
        topic: Content topic to research hashtags for
        platform: Target platform
    """
    try:
        with suppress_stdout():
            agent = _get_research_agent(platform=platform)
            result = agent.research_hashtags(topic, platform)
        return result.get("research", json.dumps(result, indent=2))
    except Exception as e:
        return (
            f"Error researching hashtags: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."
        )


@mcp.tool()
def research_content_ideas(theme: str, count: int = 5) -> str:
    """Generate content ideas for a theme with format and platform suggestions.

    Args:
        theme: Content theme or niche
        count: Number of ideas (1-20)
    """
    try:
        with suppress_stdout():
            agent = _get_research_agent()
            result = agent.suggest_content_ideas(theme, count)
        return result.get("ideas", json.dumps(result, indent=2))
    except Exception as e:
        return f"Error generating ideas: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def research_trending(platform: str = "instagram") -> str:
    """Analyze trending content formats and topics on a platform.

    Args:
        platform: Platform to analyze trends for
    """
    try:
        with suppress_stdout():
            agent = _get_research_agent(platform=platform)
            result = agent.analyze_trending(platform)
        return result.get("analysis", json.dumps(result, indent=2))
    except Exception as e:
        return f"Error analyzing trends: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def research_content_calendar(theme: str, days: int = 7, platform: str = "instagram") -> str:
    """Generate a multi-day content calendar with posting schedule.

    Args:
        theme: Content theme for the calendar
        days: Number of days to plan (1-30)
        platform: Primary platform
    """
    try:
        with suppress_stdout():
            agent = _get_research_agent(platform=platform)
            result = agent.build_content_calendar(days, [platform])
        return result.get("calendar", json.dumps(result, indent=2))
    except Exception as e:
        return f"Error building calendar: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."
