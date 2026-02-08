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

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from ._client_helpers import get_late_client, suppress_stdout, build_agent_config

# Initialize MCP server
mcp = FastMCP(
    "social-slash",
    instructions="""
Social Slash - Social media automation tools for PRSMTECH.

Available tools are prefixed by group:
- accounts_*   : List and manage connected social media accounts
- posts_*      : View recent posts and post details
- status_*     : Project status overview
- writing_*    : Generate posts/captions/threads in SWIZZ voice
- research_*   : Hashtag research, content ideas, trending analysis
- media_*      : Reel/story/carousel captions, alt text, format suggestions
- post_*       : Publish or dry-run posts to platforms
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
        db = EngagementDatabase()
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


@mcp.tool()
def writing_generate_post(
    topic: str,
    platform: str = "instagram",
    post_type: str = "casual",
    persona_mode: str = "professional",
) -> str:
    """Generate a social media post in the SWIZZ voice.

    Args:
        topic: What the post should be about
        platform: Target platform (instagram, twitter, linkedin, tiktok, etc.)
        post_type: Style - casual, announcement, resource_share, business, promo, hype
        persona_mode: professional (swizzimatic) or personal (bigswizzi)
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            result = agent.generate_post(
                topic=topic,
                platform=platform,
                post_type=post_type,
                persona_mode=persona_mode,
            )
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error generating post: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def writing_generate_caption(
    media_description: str,
    platform: str = "instagram",
    persona_mode: str = "professional",
) -> str:
    """Generate a caption for media content in SWIZZ voice.

    Args:
        media_description: What the photo/video shows
        platform: Target platform
        persona_mode: professional or personal
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            caption = agent.generate_caption(
                media_description=media_description,
                platform=platform,
                persona_mode=persona_mode,
            )
        return caption
    except Exception as e:
        return f"Error generating caption: {e}\nEnsure GOOGLE_API_KEY or ANTHROPIC_API_KEY is set."


@mcp.tool()
def writing_generate_thread(
    topic: str,
    platform: str = "twitter",
    num_posts: int = 3,
    persona_mode: str = "professional",
) -> str:
    """Generate a multi-post thread in SWIZZ voice.

    Args:
        topic: Thread topic
        platform: Target platform (twitter recommended)
        num_posts: Number of posts in thread (2-10)
        persona_mode: professional or personal
    """
    try:
        with suppress_stdout():
            agent = _get_writing_agent(persona_mode, platform)
            posts = agent.generate_thread(
                topic=topic,
                platform=platform,
                num_posts=num_posts,
                persona_mode=persona_mode,
            )
        return json.dumps(posts, indent=2)
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
# GROUP 5: POSTING TOOLS (Late API key required)
# ============================================================================


@mcp.tool()
def post_to_platform(
    content: str,
    platform: str,
    enhance: bool = False,
    media_urls: str = "",
    dry_run: bool = False,
) -> str:
    """Post content to a single social media platform.

    Args:
        content: The post text content
        platform: Target platform (twitter, linkedin, instagram, tiktok, etc.)
        enhance: Whether to AI-enhance the content before posting
        media_urls: Comma-separated media URLs to attach
        dry_run: If True, validate without actually posting
    """
    try:
        url_list = [u.strip() for u in media_urls.split(",") if u.strip()] if media_urls else None

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
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error posting to {platform}: {e}"


@mcp.tool()
def post_to_multiple(
    content: str,
    platforms: str,
    enhance: bool = False,
    media_urls: str = "",
) -> str:
    """Post content to multiple platforms at once.

    Args:
        content: The post text content
        platforms: Comma-separated platform names (e.g. "twitter,linkedin,instagram")
        enhance: Whether to AI-enhance the content before posting
        media_urls: Comma-separated media URLs to attach
    """
    try:
        platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]
        url_list = [u.strip() for u in media_urls.split(",") if u.strip()] if media_urls else None

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
        return json.dumps(result, indent=2, default=str)
    except Exception as e:
        return f"Error posting to {platforms}: {e}"


# ============================================================================
# HEALTH CHECK (Railway deployment)
# ============================================================================

from starlette.requests import Request
from starlette.responses import JSONResponse


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Railway."""
    return JSONResponse({"status": "healthy", "service": "social-slash-mcp", "tools": 19})


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    """Root endpoint with service info."""
    return JSONResponse({
        "service": "Social Slash MCP Server",
        "endpoints": {"mcp": "/mcp", "health": "/health"},
    })


# ============================================================================
# MAIN
# ============================================================================


def main() -> None:
    """Entry point - auto-detects transport from PORT env var."""
    port = os.environ.get("PORT")
    if port:
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = int(port)
        mcp.settings.stateless_http = True
        # Disable DNS rebinding protection for cloud deployment
        # (Railway domain isn't in the default localhost allowlist)
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )
        print(f"[MCP] Starting streamable-http transport on 0.0.0.0:{port}")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
