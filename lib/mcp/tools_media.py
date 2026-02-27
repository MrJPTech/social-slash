"""Media agent tools — reel/story/carousel captions, alt text, format suggestions."""

from __future__ import annotations

import json

from ._shared import mcp
from ._client_helpers import suppress_stdout, build_agent_config


def _get_media_agent(persona_mode: str = "professional", platform: str = "instagram"):
    """Create a MediaAgent with stdout suppression."""
    with suppress_stdout():
        from lib.agents.media_agent import MediaAgent
        config = build_agent_config(persona_mode, platform)
        return MediaAgent(config)


@mcp.tool()
def media_generate_caption(
    description: str,
    context: str = "",
    persona_mode: str = "professional",
) -> str:
    """Generate a short, punchy reel/post caption.

    Args:
        description: What the media content shows
        context: Additional context or notes
        persona_mode: professional or personal
    """
    try:
        with suppress_stdout():
            agent = _get_media_agent(persona_mode)
            caption = agent.generate_reel_caption(description, context, persona_mode)
        return caption
    except Exception as e:
        return f"Error generating caption: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def media_generate_story_text(context: str, persona_mode: str = "professional") -> str:
    """Generate ultra-short story overlay text (1-5 words + emojis).

    Args:
        context: What the story is about
        persona_mode: professional or personal
    """
    try:
        with suppress_stdout():
            agent = _get_media_agent(persona_mode)
            text = agent.generate_story_text(context, persona_mode=persona_mode)
        return text
    except Exception as e:
        return f"Error generating story text: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def media_generate_carousel(
    slides: str,
    platform: str = "instagram",
    persona_mode: str = "professional",
) -> str:
    """Generate captions for a multi-slide carousel post.

    Args:
        slides: Comma-separated slide descriptions (e.g. "Intro slide,Feature 1,Feature 2,CTA")
        platform: Target platform
        persona_mode: professional or personal
    """
    try:
        slide_list = [s.strip() for s in slides.split(",") if s.strip()]
        with suppress_stdout():
            agent = _get_media_agent(persona_mode, platform)
            result = agent.generate_carousel_captions(slide_list, platform, persona_mode)
        return result.get("main_caption", json.dumps(result, indent=2))
    except Exception as e:
        return f"Error generating carousel captions: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def media_generate_alt_text(description: str) -> str:
    """Generate accessible alt text for an image or video. Professional tone, max 125 chars.

    Args:
        description: What the media visually shows
    """
    try:
        with suppress_stdout():
            agent = _get_media_agent()
            alt = agent.generate_alt_text(description)
        return alt
    except Exception as e:
        return f"Error generating alt text: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def media_suggest_format(content_idea: str, platform: str = "instagram") -> str:
    """Recommend the best media format (Reel, Post, Carousel, Story, Live) for a content idea.

    Args:
        content_idea: The content concept
        platform: Target platform
    """
    try:
        with suppress_stdout():
            agent = _get_media_agent(platform=platform)
            result = agent.suggest_media_format(content_idea, platform)
        return result.get("recommendation", json.dumps(result, indent=2))
    except Exception as e:
        return f"Error suggesting format: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."
