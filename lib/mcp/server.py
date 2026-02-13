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
import os
import secrets
import time
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
- writing_*    : Generate posts/captions/threads in SWIZZ voice or Jordan Ward CEO voice
- research_*   : Hashtag research, content ideas, trending analysis
- media_*      : Reel/story/carousel captions, alt text, format suggestions
- image_*      : AI image generation (Imagen 3) with platform-optimized aspect ratios
- post_*       : Publish or dry-run posts to platforms

Voice personas:
- professional : @swizzimatic casual-professional voice
- personal     : @BigSwizzi ultra-concise AAVE voice
- ceo          : Jordan Ward evidence-based CEO thought leadership

CEO content formats (use with persona_mode="ceo"):
  problem_solution, myth_busting, quick_tips, day_in_life,
  case_study, industry_commentary, quick_wins
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


@mcp.tool()
def writing_generate_post(
    topic: str,
    platform: str = "instagram",
    post_type: str = "casual",
    persona_mode: str = "professional",
) -> str:
    """Generate a social media post in the SWIZZ or CEO voice.

    Args:
        topic: What the post should be about
        platform: Target platform (instagram, twitter, linkedin, tiktok, etc.)
        post_type: Style - casual, announcement, resource_share, business, promo, hype,
                   or CEO formats: problem_solution, myth_busting, quick_tips, day_in_life,
                   case_study, industry_commentary, quick_wins
        persona_mode: professional (swizzimatic), personal (bigswizzi), or ceo (jordan ward)
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
    """Generate a caption for media content in SWIZZ or CEO voice.

    Args:
        media_description: What the photo/video shows
        platform: Target platform
        persona_mode: professional, personal, or ceo
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
    """Generate a multi-post thread in SWIZZ or CEO voice.

    Args:
        topic: Thread topic
        platform: Target platform (twitter recommended)
        num_posts: Number of posts in thread (2-10)
        persona_mode: professional, personal, or ceo
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

from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, RedirectResponse  # noqa: E402


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Railway."""
    return JSONResponse({
        "status": "healthy",
        "service": "social-slash-mcp",
        "tools": 24,
        "env": {
            "LATE_API_KEY": "set" if os.getenv("LATE_API_KEY") else "MISSING",
            "GOOGLE_API_KEY": "set" if os.getenv("GOOGLE_API_KEY") else "MISSING",
            "ANTHROPIC_API_KEY": "set" if os.getenv("ANTHROPIC_API_KEY") else "MISSING",
            "MCP_AUTH_TOKEN": "set" if os.getenv("MCP_AUTH_TOKEN") else "MISSING",
            "OAUTH_CLIENT_ID": "set" if os.getenv("OAUTH_CLIENT_ID") else "MISSING",
        },
    })


@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    """Root endpoint with service info."""
    return JSONResponse({
        "service": "Social Slash MCP Server",
        "endpoints": {"mcp": "/mcp", "health": "/health"},
        "auth": "OAuth 2.0 (Authorization Code + PKCE)",
    })


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
    port = os.environ.get("PORT")
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
            await server.serve()

        anyio.run(_serve)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
