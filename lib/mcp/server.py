"""
Social Slash MCP Server.

Exposes social media tools via Model Context Protocol for Claude Desktop
and Claude mobile/web (via SSE transport on Railway).

Transport auto-detection:
  - PORT env var set (Railway/cloud): streamable-http on 0.0.0.0:$PORT
  - No PORT (local/Claude Desktop): stdio

Usage:
    # Local development (stdio)
    PYTHONPATH=. python -m lib.mcp

    # Local SSE testing
    PORT=8000 PYTHONPATH=. python -m lib.mcp

    # Docker
    docker run -i --rm --env-file .env.local social-slash-mcp

    # Claude Desktop config (stdio):
    {
        "mcpServers": {
            "social-slash": {
                "command": "python",
                "args": ["-m", "lib.mcp"],
                "cwd": "J:\\\\PRSMTECH\\\\PRSM-PROPRIETARY\\\\INTERNAL-PROJECTS\\\\social-slash",
                "env": {"PYTHONPATH": "."}
            }
        }
    }

    # Claude mobile: Add as remote MCP server in Claude iOS/Android app
    #   URL: https://<railway-domain>/mcp
    #   Auth: Bearer token (MCP_AUTH_TOKEN env var)
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

from mcp.server.fastmcp import FastMCP

from ._client_helpers import get_late_client, suppress_stdout, build_agent_config

# Platforms that require media to post (text-only rejected by their APIs)
MEDIA_REQUIRED_PLATFORMS: frozenset[str] = frozenset({"instagram", "tiktok"})

# Initialize MCP server
mcp = FastMCP(
    "social-slash",
    instructions="""
Social Slash - Social media automation tools for PRSMTECH.

Available tools are prefixed by group:
- accounts_*   : List and manage connected social media accounts
- posts_*      : View recent posts and post details
- status_*     : Project status overview
- writing_*    : Generate posts/captions/threads in SWIZZ voice or Jordan Ward CEO voice
- research_*   : Hashtag research, content ideas, trending analysis
- media_*      : Reel/story/carousel captions, alt text, format suggestions
- image_*      : AI image generation (Imagen 4) with platform-optimized aspect ratios
- post_*       : Publish or dry-run posts to platforms

Voice personas:
- professional : @swizzimatic casual-professional voice
- personal     : @BigSwizzi ultra-concise AAVE voice
- ceo          : Jordan Ward evidence-based CEO thought leadership

Tone options (all writing tools):
  authentic, motivational, humorous, reflective, educational,
  hype, emotional, direct, raw, inspiring

Energy levels (all writing tools):
  low (calm/measured), medium (balanced), high (bold/loud)

CEO content formats (use with persona_mode="ceo"):
  problem_solution, myth_busting, quick_tips, day_in_life,
  case_study, industry_commentary, quick_wins, vibe_coder

Platform character limits:
  twitter=280, threads=500, instagram=2200, linkedin=3000,
  tiktok=150, bluesky=300, youtube=5000, facebook=8000,
  reddit=40000, telegram=4096, google_business=1500
""",
)


# ============================================================================
# GROUP 1: UTILITY TOOLS (Late API key only)
# ============================================================================


@mcp.tool()
def accounts_list(platform: str = "") -> str:
    """List all connected social media accounts. Optionally filter by platform name."""
    with suppress_stdout():
        client = get_late_client()
        response = client.accounts.list()
    accounts = response.accounts or []

    if platform:
        accounts = [
            a for a in accounts if a.platform and a.platform.lower() == platform.lower()
        ]

    if not accounts:
        return f"No accounts found{f' for {platform}' if platform else ''}. Connect at https://getlate.dev"

    lines = [f"Found {len(accounts)} connected account(s):\n"]
    for acc in accounts:
        username = acc.username or acc.displayName or acc.field_id
        lines.append(f"- {acc.platform}: {username} (ID: {acc.field_id})")
    return "\n".join(lines)


@mcp.tool()
def accounts_refresh_cache() -> str:
    """Clear and refresh the account cache by re-fetching from Late API."""
    with suppress_stdout():
        client = get_late_client()
        response = client.accounts.list()
    accounts = response.accounts or []
    return f"Cache refreshed. Found {len(accounts)} connected account(s)."


@mcp.tool()
def posts_recent(platform: str = "", limit: int = 10) -> str:
    """List recent posts. Optionally filter by platform. Returns up to `limit` posts."""
    with suppress_stdout():
        client = get_late_client()
        params: dict[str, Any] = {"limit": limit}
        response = client.posts.list(**params)
    posts = response.posts or []

    if platform:
        posts = [
            p for p in posts
            if any(
                t.platform and t.platform.lower() == platform.lower()
                for t in (p.platforms or [])
            )
        ]

    if not posts:
        return f"No posts found{f' for {platform}' if platform else ''}."

    lines = [f"Found {len(posts)} post(s):\n"]
    for post in posts:
        content = post.content or ""
        preview = content[:60] + "..." if len(content) > 60 else content
        platforms = ", ".join(t.platform or "?" for t in (post.platforms or []))
        status = post.status.value if post.status else "unknown"
        lines.append(f"- [{status}] {preview}")
        lines.append(f"  Platforms: {platforms} | ID: {post.field_id}")
    return "\n".join(lines)


@mcp.tool()
def post_details(post_id: str) -> str:
    """Get detailed information about a specific post by its ID."""
    with suppress_stdout():
        client = get_late_client()
        response = client.posts.get(post_id)
    post = response.post
    if not post:
        return f"Post {post_id} not found."

    content = post.content or ""
    preview = content[:200] + "..." if len(content) > 200 else content
    platforms = ", ".join(t.platform or "?" for t in (post.platforms or []))
    status = post.status.value if post.status else "unknown"

    lines = [
        f"Post ID: {post.field_id}",
        f"Status: {status}",
        f"Platforms: {platforms}",
        f"Content: {preview}",
    ]
    if post.scheduledFor:
        lines.append(f"Scheduled for: {post.scheduledFor}")
    return "\n".join(lines)


@mcp.tool()
def status_overview() -> str:
    """Get a project status overview: connected accounts, API health, and bot status."""
    results = []

    # Accounts
    try:
        with suppress_stdout():
            client = get_late_client()
            response = client.accounts.list()
        accounts = response.accounts or []
        platform_names = [a.platform for a in accounts if a.platform]
        results.append(f"Connected accounts: {len(accounts)}")
        results.append(f"Platforms: {', '.join(platform_names)}")
    except Exception as e:
        results.append(f"Late API: ERROR - {e}")

    # AI provider status
    gemini_key = os.getenv("GOOGLE_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    results.append(f"Gemini API key: {'SET' if gemini_key else 'NOT SET'}")
    results.append(f"Anthropic API key: {'SET' if anthropic_key else 'NOT SET'}")

    # Bot database (graceful if not available)
    try:
        from lib.storage.database import EngagementDatabase
        EngagementDatabase()
        results.append("Engagement DB: Available")
    except Exception:
        results.append("Engagement DB: Not available (mount data/engagement.db)")

    return "\n".join(results)


# ============================================================================
# GROUP 2: WRITING AGENT TOOLS (requires AI provider key)
# ============================================================================


def _get_writing_agent(persona_mode: str = "professional", platform: str = "instagram"):
    """Create a WritingAgent with stdout suppression."""
    with suppress_stdout():
        from lib.agents.writing_agent import WritingAgent
        config = build_agent_config(persona_mode, platform)
        return WritingAgent(config)


def _persona_label(persona_mode: str) -> str:
    """Return the display handle for a persona mode."""
    return {"professional": "@swizzimatic", "personal": "@BigSwizzi", "ceo": "Jordan Ward"}.get(
        persona_mode, persona_mode
    )


def _format_post_result(result: dict) -> str:
    """Format a generate_post result dict as clean readable markdown."""
    platform = result.get("platform", "unknown").title()
    persona = _persona_label(result.get("persona_mode", "professional"))
    post_type = result.get("post_type", "casual").replace("_", " ").title()
    tone = result.get("tone", "authentic").title()
    energy = result.get("energy", "medium").title()
    char_count = result.get("char_count", 0)
    char_limit = result.get("char_limit", 2200)
    headroom = char_limit - char_count
    content = result.get("content", "")
    hashtags = result.get("hashtags", [])
    emojis = result.get("emojis", [])

    lines = [
        f"**Platform**: {platform} | **Persona**: {persona} | **Type**: {post_type}",
        f"**Tone**: {tone} | **Energy**: {energy} | **Length**: {char_count}/{char_limit} ({headroom} chars left)",
        "",
        "---",
        "",
        content,
        "",
        "---",
    ]
    if hashtags:
        lines.append(f"**Hashtags**: {' '.join(hashtags)}")
    if emojis:
        lines.append(f"**Emojis**: {' '.join(emojis)}")
    return "\n".join(lines)


@mcp.tool()
def writing_generate_post(
    topic: str,
    platform: str = "instagram",
    post_type: str = "casual",
    persona_mode: str = "professional",
    tone: str = "authentic",
    energy: str = "medium",
) -> str:
    """Generate a social media post in the SWIZZ or CEO voice.

    Args:
        topic: What the post should be about
        platform: Target platform (instagram, twitter, linkedin, tiktok, youtube, reddit, etc.)
        post_type: Style - casual, announcement, resource_share, business, promo, hype,
                   or CEO formats: problem_solution, myth_busting, quick_tips, day_in_life,
                   case_study, industry_commentary, quick_wins, vibe_coder
                   Use "auto" to detect best type from topic keywords.
        persona_mode: professional (swizzimatic), personal (bigswizzi), or ceo (jordan ward)
        tone: Emotional tone - authentic, motivational, humorous, reflective, educational,
              hype, emotional, direct, raw, inspiring
        energy: Energy level - low (calm/measured), medium (balanced), high (bold/loud)
    """
    try:
        # Auto-detect post_type from topic keywords when "auto" is passed
        resolved_post_type = post_type
        if post_type == "auto":
            with suppress_stdout():
                from lib.persona.swizz_persona import SwizzPersona
                router = SwizzPersona(mode=persona_mode)
                resolved_post_type = router.determine_response_type(topic)

        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            result = agent.generate_post(
                topic=topic,
                platform=platform,
                post_type=resolved_post_type,
                persona_mode=persona_mode,
                tone=tone,
                energy=energy,
            )
        return _format_post_result(result)
    except Exception as e:
        return f"Error generating post: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def writing_generate_caption(
    media_description: str,
    platform: str = "instagram",
    persona_mode: str = "professional",
    tone: str = "authentic",
    energy: str = "medium",
) -> str:
    """Generate a caption for media content in SWIZZ or CEO voice.

    Args:
        media_description: What the photo/video shows
        platform: Target platform
        persona_mode: professional, personal, or ceo
        tone: Emotional tone - authentic, motivational, humorous, hype, emotional, direct, raw
        energy: Energy level - low, medium, high
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            result = agent.generate_post(
                topic=f"Caption for this media: {media_description}",
                platform=platform,
                post_type="casual",
                persona_mode=persona_mode,
                tone=tone,
                energy=energy,
            )
        content = result.get("content", "")
        char_count = result.get("char_count", 0)
        char_limit = result.get("char_limit", 2200)
        persona = _persona_label(persona_mode)
        hashtags = result.get("hashtags", [])
        out = [
            f"**Caption** | {persona} | {platform.title()} | {char_count}/{char_limit} chars",
            "",
            content,
        ]
        if hashtags:
            out.append(f"\n**Hashtags**: {' '.join(hashtags)}")
        return "\n".join(out)
    except Exception as e:
        return f"Error generating caption: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def writing_generate_thread(
    topic: str,
    platform: str = "twitter",
    num_posts: int = 3,
    persona_mode: str = "professional",
    tone: str = "authentic",
    energy: str = "medium",
) -> str:
    """Generate a multi-post thread in SWIZZ or CEO voice.

    Args:
        topic: Thread topic
        platform: Target platform (twitter/threads recommended)
        num_posts: Number of posts in thread (2-10)
        persona_mode: professional, personal, or ceo
        tone: Emotional tone - authentic, motivational, humorous, educational, hype, direct
        energy: Energy level - low, medium, high
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            posts = agent.generate_thread(
                topic=topic,
                platform=platform,
                num_posts=num_posts,
                persona_mode=persona_mode,
                tone=tone,
                energy=energy,
            )
        if not posts:
            return "No posts generated. Try a different topic."

        persona = _persona_label(persona_mode)
        char_limit = posts[0].get("char_limit", 280) if posts else 280
        lines = [
            f"**Thread**: {len(posts)} posts | **Platform**: {platform.title()} | **Persona**: {persona}",
            f"**Tone**: {tone.title()} | **Energy**: {energy.title()} | **Limit**: {char_limit} chars/post",
            "",
        ]
        for i, post in enumerate(posts, 1):
            lines.append(f"**{i}/{len(posts)}** ({post['char_count']} chars)")
            lines.append(post["content"])
            if i < len(posts):
                lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error generating thread: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


# ============================================================================
# GROUP 3: RESEARCH AGENT TOOLS (requires AI provider key)
# ============================================================================


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
        return f"Error researching hashtags: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


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


# ============================================================================
# GROUP 4: MEDIA AGENT TOOLS (requires AI provider key)
# ============================================================================


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


# ============================================================================
# GROUP 6: IMAGE GENERATION TOOLS (requires GOOGLE_API_KEY)
# ============================================================================


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


# ============================================================================
# ============================================================================
# POSTING HELPERS
# ============================================================================


def _auto_generate_image(content: str, platform: str) -> Optional[str]:
    """Generate an AI image for a media-required platform and upload to Late.

    Derives a visual prompt from the post content, generates a platform-
    optimized image via Imagen 4, uploads to Late media hosting, and
    returns the cloud URL.

    Args:
        content: Post text content (used as visual theme)
        platform: Target platform (instagram → 1:1, tiktok → 9:16)

    Returns:
        Cloud media URL string, or None if generation fails.
    """
    try:
        from lib.ai.imagen_client import ImagenClient

        # Derive a visual prompt from the post content
        topic = content[:150].replace('\n', ' ').strip()
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

        # instagram → square post (1:1), tiktok → vertical cover (9:16)
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


# ============================================================================
# GROUP 5: POSTING TOOLS (Late API key required)
# ============================================================================


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
        auto_generated_url: Optional[str] = None

        # Auto-generate image for platforms that require media
        if auto_image and not url_list and platform_lower in MEDIA_REQUIRED_PLATFORMS and not dry_run:
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
        auto_generated_url: Optional[str] = None

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


# ============================================================================
# HEALTH CHECK (Railway deployment)
# ============================================================================

from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, RedirectResponse  # noqa: E402


# ============================================================================
# SCHEDULER (SLASHERBOT daily posting)
# ============================================================================

_scheduler: Optional[Any] = None  # DailyScheduler instance, None when disabled


def _get_scheduler():
    return _scheduler


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Railway."""
    sched = _get_scheduler()
    return JSONResponse({
        "status": "healthy",
        "service": "social-slash-mcp",
        "tools": 24,
        "scheduler": "running" if (sched and sched.scheduler.running) else "disabled",
        "env": {
            "LATE_API_KEY": "set" if os.getenv("LATE_API_KEY") else "MISSING",
            "GOOGLE_API_KEY": "set" if os.getenv("GOOGLE_API_KEY") else "MISSING",
            "ANTHROPIC_API_KEY": "set" if os.getenv("ANTHROPIC_API_KEY") else "MISSING",
            "MCP_AUTH_TOKEN": "set" if os.getenv("MCP_AUTH_TOKEN") else "MISSING",
            "OAUTH_CLIENT_ID": "set" if os.getenv("OAUTH_CLIENT_ID") else "MISSING",
            "GCHAT_WEBHOOK_SOCIAL_SLASH": "set" if os.getenv("GCHAT_WEBHOOK_SOCIAL_SLASH") else "MISSING",
            "APPROVAL_TOKEN_SECRET": "set" if os.getenv("APPROVAL_TOKEN_SECRET") else "MISSING",
        },
    })


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    """Root endpoint with service info."""
    return JSONResponse({
        "service": "Social Slash MCP Server",
        "endpoints": {
            "mcp": "/mcp",
            "health": "/health",
            "approval": "/approval",
            "scheduler_status": "/scheduler/status",
            "scheduler_trigger": "/scheduler/trigger",
        },
        "auth": "OAuth 2.0 (Authorization Code + PKCE)",
    })


# ============================================================================
# SLASHERBOT APPROVAL ENDPOINT
# ============================================================================


from starlette.responses import HTMLResponse  # noqa: E402


@mcp.custom_route("/approval", methods=["GET"])
async def approval_handler(request: Request) -> HTMLResponse:
    """Handle approval button clicks from Google Chat cards.

    Query params: slot (slot_id), choice (A1/A2/B1/B2/SKIP/REGEN), token (HMAC)
    """
    params = request.query_params
    slot_id = params.get("slot", "")
    choice = params.get("choice", "")
    token = params.get("token", "")

    def _html(title: str, body: str, color: str = "#1a73e8") -> HTMLResponse:
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SLASHERBOT — {title}</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;
       display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
  .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;
         padding:2rem 3rem;max-width:500px;text-align:center}}
  h1{{color:{color};margin-bottom:0.5rem}}
  p{{color:#8b949e;margin-top:0.5rem}}
  code{{background:#21262d;padding:0.2em 0.5em;border-radius:4px;font-size:0.85em}}
</style></head>
<body><div class="card"><h1>{title}</h1>{body}</div></body></html>"""
        )

    # Validate inputs
    if not slot_id or not choice:
        return _html("❌ Invalid Link", "<p>Missing slot or choice parameter.</p>", "#da3633")

    # Verify HMAC token
    from lib.scheduler.gchat_cards import verify_token
    if not verify_token(slot_id, choice, token):
        return _html("❌ Invalid Token", "<p>This link has expired or been tampered with.</p>", "#da3633")

    # Handle SKIP
    if choice == "SKIP":
        from lib.scheduler.approval_store import ApprovalStore
        store = ApprovalStore()
        store.mark_posted(slot_id, "SKIP")
        return _html("⏭ Skipped", "<p>This post has been skipped.</p>", "#8b949e")

    # Handle REGEN (placeholder — full regen would re-trigger the pipeline)
    if choice == "REGEN":
        return _html(
            "🔄 Regenerate",
            "<p>Regeneration is not yet automated. Use the MCP trigger endpoint to create a new slot.</p>",
            "#e3b341",
        )

    # Load bundle
    from lib.scheduler.approval_store import ApprovalStore
    store = ApprovalStore()
    bundle = store.get(slot_id)
    if not bundle:
        return _html("❌ Not Found", f"<p>Slot <code>{slot_id[:8]}</code> not found. It may have expired.</p>", "#da3633")

    if bundle.posted:
        return _html(
            "✅ Already Posted",
            f"<p>Slot <code>{slot_id[:8]}</code> was already posted (choice: <code>{bundle.choice}</code>).</p>",
        )

    # Map choice to content + image
    if choice.startswith("A"):
        option = bundle.option_a
    elif choice.startswith("B"):
        option = bundle.option_b
    else:
        return _html("❌ Unknown Choice", f"<p>Unknown choice <code>{choice}</code>.</p>", "#da3633")

    image_url = bundle.image_1_url if choice.endswith("1") else bundle.image_2_url
    content = option.get("content", "")
    media_urls = [image_url] if image_url else None

    # Post
    try:
        with suppress_stdout():
            from lib.posting.poster import Poster
            poster = Poster()
            result = poster.post(
                content=content,
                platforms=[bundle.platform],
                media_urls=media_urls,
            )
        if not isinstance(result, dict):
            result = {}
    except Exception as exc:
        logger.error(f"[approval] Post failed for slot {slot_id[:8]}: {exc}")
        return _html("❌ Post Failed", f"<p>Error: <code>{str(exc)[:200]}</code></p>", "#da3633")

    # Mark posted
    store.mark_posted(slot_id, choice)

    # Send confirmation card to SLASHERBOT
    try:
        from lib.scheduler.gchat_cards import send_confirmation_card, SLASHERBOT_WEBHOOK
        send_confirmation_card(bundle, choice, result, SLASHERBOT_WEBHOOK)
    except Exception as exc:
        logger.warning(f"[approval] Confirmation card failed: {exc}")

    platform_label = bundle.platform.upper()
    preview = content[:100].replace("<", "&lt;").replace(">", "&gt;")
    return _html(
        f"✅ Posted to {platform_label}!",
        f"<p>Choice: <code>{choice}</code></p><p>{preview}…</p>",
        "#3fb950",
    )


# ============================================================================
# SCHEDULER STATUS & MANUAL TRIGGER
# ============================================================================


@mcp.custom_route("/scheduler/status", methods=["GET"])
async def scheduler_status_handler(request: Request) -> JSONResponse:
    """Return scheduler status and next run times for all platform jobs."""
    sched = _get_scheduler()
    if not sched:
        return JSONResponse({"enabled": False, "message": "Set SCHEDULER_ENABLED=true to activate"})
    return JSONResponse({"enabled": True, **sched.get_status()})


@mcp.custom_route("/scheduler/trigger", methods=["POST"])
async def scheduler_trigger_handler(request: Request) -> JSONResponse:
    """Manually trigger a content slot for testing. Body: {platform, time_label, persona}"""
    sched = _get_scheduler()
    if not sched:
        return JSONResponse({"error": "Scheduler not running"}, status_code=503)

    try:
        body_bytes = await request.body()
        if body_bytes:
            params = json.loads(body_bytes)
        else:
            params = {}
    except Exception:
        params = {}

    platform = params.get("platform", request.query_params.get("platform", "twitter"))
    time_label = params.get("time_label", "manual")
    persona = params.get("persona", "professional")

    slot_id = sched.trigger_slot(platform, time_label, persona)
    if slot_id:
        return JSONResponse({"status": "triggered", "slot_id": slot_id, "platform": platform})
    return JSONResponse({"error": "Trigger failed — check server logs"}, status_code=500)


# ============================================================================
# OAUTH 2.0 ENDPOINTS (Claude.ai custom connector)
# ============================================================================

# In-memory stores (single Railway instance, acceptable for personal server)
_auth_codes: dict[str, dict] = {}  # code -> {client_id, code_challenge, expires}

# Pre-shared OAuth credentials — only clients with matching values can authenticate.
# Set these in Railway env vars; leave empty for local dev (auth bypassed).
_OAUTH_CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "")
_OAUTH_CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET", "")


def _get_server_url(request: Request) -> str:
    """Derive the public server URL from the request."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}"


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_metadata(request: Request) -> JSONResponse:
    """RFC 8414 - OAuth 2.0 Authorization Server Metadata."""
    base = _get_server_url(request)
    return JSONResponse({
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "code_challenge_methods_supported": ["S256"],
    })


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def resource_metadata(request: Request) -> JSONResponse:
    """RFC 9728 - OAuth 2.0 Protected Resource Metadata."""
    base = _get_server_url(request)
    return JSONResponse({
        "resource": f"{base}/mcp",
        "authorization_servers": [base],
        "bearer_methods_supported": ["header"],
    })


@mcp.custom_route("/register", methods=["POST"])
async def register_client(request: Request) -> JSONResponse:
    """Dynamic client registration is disabled — use pre-shared credentials."""
    return JSONResponse({"error": "registration_not_supported"}, status_code=403)


@mcp.custom_route("/authorize", methods=["GET"])
async def authorize(request: Request) -> RedirectResponse:
    """Authorization endpoint - auto-approves (single-user personal server)."""
    params = request.query_params
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")
    code_challenge = params.get("code_challenge", "")
    client_id = params.get("client_id", "")
    response_type = params.get("response_type", "")

    if response_type != "code":
        return RedirectResponse(
            f"{redirect_uri}?error=unsupported_response_type&state={state}",
            status_code=302,
        )

    # Validate client_id against pre-shared credential
    if _OAUTH_CLIENT_ID and client_id != _OAUTH_CLIENT_ID:
        return RedirectResponse(
            f"{redirect_uri}?error=unauthorized_client&state={state}",
            status_code=302,
        )

    # Generate authorization code
    code = secrets.token_urlsafe(32)
    _auth_codes[code] = {
        "client_id": client_id,
        "code_challenge": code_challenge,
        "redirect_uri": redirect_uri,
        "expires": time.time() + 300,  # 5 minute expiry
    }

    return RedirectResponse(
        f"{redirect_uri}?code={code}&state={state}",
        status_code=302,
    )


@mcp.custom_route("/token", methods=["POST"])
async def token_exchange(request: Request) -> JSONResponse:
    """Token endpoint - exchanges authorization code for access token (with PKCE)."""
    try:
        body = await request.body()
        # Support both form-encoded and JSON
        content_type = request.headers.get("content-type", "")
        if "json" in content_type:
            params = json.loads(body)
        else:
            from urllib.parse import parse_qs
            raw = parse_qs(body.decode())
            params = {k: v[0] for k, v in raw.items()}
    except Exception:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    grant_type = params.get("grant_type", "")
    code = params.get("code", "")
    code_verifier = params.get("code_verifier", "")
    client_id = params.get("client_id", "")
    client_secret = params.get("client_secret", "")

    if grant_type != "authorization_code":
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

    # Validate client credentials against pre-shared values
    if _OAUTH_CLIENT_ID and client_id != _OAUTH_CLIENT_ID:
        return JSONResponse({"error": "invalid_client", "error_description": "Unknown client_id"}, status_code=401)
    if _OAUTH_CLIENT_SECRET and client_secret != _OAUTH_CLIENT_SECRET:
        return JSONResponse({"error": "invalid_client", "error_description": "Bad client_secret"}, status_code=401)

    # Look up and consume the auth code
    code_data = _auth_codes.pop(code, None)
    if not code_data:
        return JSONResponse({"error": "invalid_grant", "error_description": "Code not found or already used"}, status_code=400)

    if code_data["expires"] < time.time():
        return JSONResponse({"error": "invalid_grant", "error_description": "Code expired"}, status_code=400)

    # Verify client_id matches the one that requested the auth code
    if client_id and code_data.get("client_id") and client_id != code_data["client_id"]:
        return JSONResponse({"error": "invalid_grant", "error_description": "client_id mismatch"}, status_code=400)

    # PKCE verification (S256)
    if code_data["code_challenge"] and code_verifier:
        digest = hashlib.sha256(code_verifier.encode()).digest()
        computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        if computed != code_data["code_challenge"]:
            return JSONResponse({"error": "invalid_grant", "error_description": "PKCE verification failed"}, status_code=400)

    # Return the MCP_AUTH_TOKEN as the access token
    auth_token = os.environ.get("MCP_AUTH_TOKEN", "")
    if not auth_token:
        return JSONResponse({"error": "server_error", "error_description": "MCP_AUTH_TOKEN not configured"}, status_code=500)

    return JSONResponse({
        "access_token": auth_token,
        "token_type": "Bearer",
    })


# ============================================================================
# BEARER TOKEN AUTH MIDDLEWARE
# ============================================================================


class BearerAuthMiddleware:
    """ASGI middleware that requires a Bearer token on the /mcp endpoint.

    Public endpoints (/, /health) are not protected.
    If MCP_AUTH_TOKEN is not set, all requests are allowed.
    """

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/mcp":
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()
            expected = f"Bearer {self.token}"
            if auth_header != expected:
                # Derive base URL for resource_metadata link
                host = ""
                for k, v in scope.get("headers", []):
                    if k == b"x-forwarded-host":
                        host = v.decode()
                        break
                    elif k == b"host":
                        host = v.decode()
                scheme = "https" if any(k == b"x-forwarded-proto" and v == b"https" for k, v in scope.get("headers", [])) else "https"
                base = f"{scheme}://{host}" if host else ""
                res_uri = f"{base}/.well-known/oauth-protected-resource" if base else ""
                www_auth = f'Bearer resource_metadata="{res_uri}"' if res_uri else "Bearer"
                response = JSONResponse(
                    {"error": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": www_auth},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    """Entry point - auto-detects transport from PORT env var."""
    global _scheduler

    port = os.environ.get("PORT")

    # Start scheduler if enabled (Railway / cloud only)
    scheduler_enabled = os.environ.get("SCHEDULER_ENABLED", "false").lower() == "true"
    if scheduler_enabled:
        try:
            from lib.scheduler.daily_scheduler import DailyScheduler
            _scheduler = DailyScheduler()
            _scheduler.start()
            print("[SLASHERBOT] Daily scheduler started")
        except Exception as exc:
            print(f"[SLASHERBOT] Scheduler failed to start: {exc}")
            _scheduler = None

    if port:
        import anyio
        import uvicorn
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = int(port)
        mcp.settings.stateless_http = True
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )

        auth_token = os.environ.get("MCP_AUTH_TOKEN", "")

        async def _serve():
            app = mcp.streamable_http_app()
            if auth_token:
                app = BearerAuthMiddleware(app, auth_token)
                print("[MCP] Auth: Bearer token + OAuth 2.0 on /mcp")
            else:
                print("[MCP] Auth: DISABLED (set MCP_AUTH_TOKEN to enable)")
            oauth_status = "locked" if _OAUTH_CLIENT_ID else "open (set OAUTH_CLIENT_ID to lock)"
            print(f"[MCP] OAuth: {oauth_status}")
            print(f"[MCP] Starting streamable-http on 0.0.0.0:{port}")
            config = uvicorn.Config(app, host="0.0.0.0", port=int(port), log_level="info")
            server = uvicorn.Server(config)
            try:
                await server.serve()
            finally:
                if _scheduler:
                    _scheduler.stop()

        anyio.run(_serve)
    else:
        try:
            mcp.run(transport="stdio")
        finally:
            if _scheduler:
                _scheduler.stop()


if __name__ == "__main__":
    main()
