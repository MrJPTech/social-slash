"""Posting tools — publish content to one or multiple platforms."""

from __future__ import annotations

import json

from ._client_helpers import suppress_stdout
from ._shared import MEDIA_REQUIRED_PLATFORMS, mcp

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _auto_generate_image(content: str, platform: str) -> str | None:
    """Generate an AI image for a media-required platform and upload to Late.

    Derives a visual prompt from the post content, generates a platform-
    optimized image via Imagen 4, uploads to Late media hosting, and
    returns the cloud URL.

    Args:
        content: Post text content (used as visual theme)
        platform: Target platform (instagram -> 1:1, tiktok -> 9:16)

    Returns:
        Cloud media URL string, or None if generation fails.
    """
    try:
        from lib.ai.imagen_client import ImagenClient

        # Derive a visual prompt from the post content
        topic = content[:150].replace("\n", " ").strip()
        if not topic:
            topic = f"Professional social media content for {platform}"

        prompt = (
            f"Professional social media visual for {platform}. "
            f"Theme: {topic}. "
            "Abstract, modern, high-quality digital art. "
            "No text or words in the image. "
            "Vibrant colors, sharp composition, cinematic quality."
        )

        imagen = ImagenClient()

        # instagram -> square post (1:1), tiktok -> vertical cover (9:16)
        image_type = "cover" if platform == "tiktok" else "post"

        urls = imagen.generate_and_upload(
            prompt=prompt,
            platform=platform,
            image_type=image_type,
            num_images=1,
        )

        return urls[0] if urls else None

    except Exception as e:
        # Non-fatal — return None and let the caller decide what to do
        print(f"[WARNING] Auto image generation failed for {platform}: {e}")
        return None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def post_to_platform(
    content: str,
    platform: str,
    enhance: bool = False,
    media_urls: str = "",
    dry_run: bool = False,
    auto_image: bool = True,
) -> str:
    """Post content to a single social media platform.

    Instagram and TikTok require media. When auto_image=True (default) and no
    media_urls are provided, an AI image is automatically generated via Imagen 4
    and attached before posting.

    Args:
        content: The post text content
        platform: Target platform (twitter, linkedin, instagram, tiktok, etc.)
        enhance: Whether to AI-enhance the content before posting
        media_urls: Comma-separated media URLs to attach
        dry_run: If True, validate without actually posting
        auto_image: Auto-generate an AI image for media-required platforms
                    (instagram, tiktok) when no media_urls provided. Default True.
    """
    try:
        url_list = [u.strip() for u in media_urls.split(",") if u.strip()] if media_urls else None
        platform_lower = platform.lower()
        auto_generated_url: str | None = None

        # Auto-generate image for platforms that require media
        if (
            auto_image
            and not url_list
            and platform_lower in MEDIA_REQUIRED_PLATFORMS
            and not dry_run
        ):
            with suppress_stdout():
                auto_generated_url = _auto_generate_image(content, platform_lower)
            if auto_generated_url:
                url_list = [auto_generated_url]

        with suppress_stdout():
            from lib.posting.poster import Poster

            poster = Poster(skip_late_init=dry_run)

            if enhance:
                enhanced = poster.enhance_content(content, platform)
                if enhanced:
                    content = enhanced

            result = poster.post(
                content=content,
                platforms=[platform],
                media_urls=url_list,
                dry_run=dry_run,
            )

        if auto_generated_url:
            result["auto_generated_image"] = auto_generated_url

        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error posting to {platform}: {e}"


@mcp.tool()
def post_to_multiple(
    content: str,
    platforms: str,
    enhance: bool = False,
    media_urls: str = "",
    auto_image: bool = True,
) -> str:
    """Post content to multiple platforms at once.

    When auto_image=True (default) and the platform list includes instagram or
    tiktok without media_urls, an AI image is auto-generated and shared across
    all platforms in the list.

    Args:
        content: The post text content
        platforms: Comma-separated platform names (e.g. "twitter,linkedin,instagram")
        enhance: Whether to AI-enhance the content before posting
        media_urls: Comma-separated media URLs to attach
        auto_image: Auto-generate an AI image when instagram/tiktok are in the
                    list and no media_urls are provided. Default True.
    """
    try:
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        url_list = [u.strip() for u in media_urls.split(",") if u.strip()] if media_urls else None
        auto_generated_url: str | None = None

        # Auto-generate image if any media-required platform is in the list
        needs_image = any(p in MEDIA_REQUIRED_PLATFORMS for p in platform_list)
        if auto_image and not url_list and needs_image:
            # Use instagram as the reference platform for aspect ratio (1:1 works everywhere)
            ref_platform = next(
                (p for p in platform_list if p in MEDIA_REQUIRED_PLATFORMS), "instagram"
            )
            with suppress_stdout():
                auto_generated_url = _auto_generate_image(content, ref_platform)
            if auto_generated_url:
                url_list = [auto_generated_url]

        with suppress_stdout():
            from lib.posting.poster import Poster

            poster = Poster()

            if enhance:
                enhanced = poster.enhance_content(content, platform_list[0])
                if enhanced:
                    content = enhanced

            result = poster.post(
                content=content,
                platforms=platform_list,
                media_urls=url_list,
            )

        if auto_generated_url:
            result["auto_generated_image"] = auto_generated_url

        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error posting to {platforms}: {e}"
