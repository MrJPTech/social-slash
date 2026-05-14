"""Image generation tools — AI graphics via Google Imagen 4."""

from __future__ import annotations

import json

from ._client_helpers import build_agent_config, suppress_stdout
from ._shared import mcp


def _get_image_agent(persona_mode: str = "professional", platform: str = "instagram"):
    """Create an ImageAgent with stdout suppression."""
    with suppress_stdout():
        from lib.agents.image_agent import ImageAgent

        config = build_agent_config(persona_mode, platform)
        return ImageAgent(config)


@mcp.tool()
def image_generate_graphic(
    prompt: str,
    platform: str = "instagram",
    style: str = "modern",
    persona_mode: str = "professional",
    num_images: int = 1,
) -> str:
    """Generate an AI image for a social media post using Google Imagen 3.

    The prompt is automatically enhanced for better results using the selected
    persona's visual style. Images are saved locally as PNG files.

    Args:
        prompt: What the image should depict (e.g. "Modern tech startup workspace")
        platform: Target platform - determines aspect ratio (instagram=1:1, twitter=16:9, etc.)
        style: Visual style (modern, minimal, bold, artistic, photorealistic, flat, gradient, neon)
        persona_mode: professional (clean/corporate), personal (vibrant/bold), ceo (authoritative/premium)
        num_images: Number of image variants to generate (1-4)
    """
    try:
        with suppress_stdout():
            agent = _get_image_agent(persona_mode, platform)
            result = agent.generate_post_graphic(
                topic=prompt,
                platform=platform,
                style=style,
                persona_mode=persona_mode,
                num_images=num_images,
                upload=False,
            )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error generating image: {e}\nEnsure GOOGLE_API_KEY is set."


@mcp.tool()
def image_generate_thumbnail(
    title: str,
    platform: str = "youtube",
    style: str = "bold",
    num_images: int = 1,
) -> str:
    """Generate a video/blog thumbnail image (16:9 aspect ratio).

    Args:
        title: Video or blog title to inspire the thumbnail
        platform: Target platform (youtube, linkedin, twitter)
        style: Visual style (bold, modern, minimal, photorealistic)
        num_images: Number of variants (1-4)
    """
    try:
        with suppress_stdout():
            agent = _get_image_agent("professional", platform)
            result = agent.generate_thumbnail(
                title=title,
                platform=platform,
                style=style,
                num_images=num_images,
                upload=False,
            )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error generating thumbnail: {e}\nEnsure GOOGLE_API_KEY is set."


@mcp.tool()
def image_generate_carousel(
    slides: str,
    platform: str = "instagram",
    style: str = "modern",
    persona_mode: str = "professional",
) -> str:
    """Generate images for a multi-slide carousel post (one image per slide).

    Args:
        slides: Comma-separated slide descriptions (e.g. "Intro graphic,Feature highlight,Call to action")
        platform: Target platform
        style: Visual style (consistent across all slides)
        persona_mode: professional, personal, or ceo
    """
    try:
        slide_list = [s.strip() for s in slides.split(",") if s.strip()]
        with suppress_stdout():
            agent = _get_image_agent(persona_mode, platform)
            result = agent.generate_carousel_images(
                slides=slide_list,
                platform=platform,
                style=style,
                persona_mode=persona_mode,
                upload=False,
            )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error generating carousel images: {e}\nEnsure GOOGLE_API_KEY is set."


@mcp.tool()
def image_generate_story(
    context: str,
    platform: str = "instagram",
    persona_mode: str = "professional",
) -> str:
    """Generate a story/reel cover image (9:16 vertical aspect ratio).

    Args:
        context: What the story is about
        platform: Target platform (instagram, facebook, tiktok)
        persona_mode: professional, personal, or ceo
    """
    try:
        with suppress_stdout():
            agent = _get_image_agent(persona_mode, platform)
            result = agent.generate_story_image(
                context=context,
                platform=platform,
                persona_mode=persona_mode,
                upload=False,
            )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error generating story image: {e}\nEnsure GOOGLE_API_KEY is set."


@mcp.tool()
def image_generate_art(
    description: str,
    style: str = "artistic",
    aspect_ratio: str = "1:1",
    num_images: int = 1,
) -> str:
    """Generate freeform AI art (not tied to a specific platform).

    Args:
        description: Detailed image description
        style: Visual style (artistic, photorealistic, flat, abstract, watercolor, neon, etc.)
        aspect_ratio: Image dimensions (1:1, 16:9, 9:16, 4:3, 3:4)
        num_images: Number of images (1-4)
    """
    try:
        with suppress_stdout():
            agent = _get_image_agent("professional")
            result = agent.generate_ai_art(
                description=description,
                style=style,
                aspect_ratio=aspect_ratio,
                num_images=num_images,
                upload=False,
            )
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error generating art: {e}\nEnsure GOOGLE_API_KEY is set."
