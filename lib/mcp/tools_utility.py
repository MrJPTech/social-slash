"""Utility tools — account listing, post browsing, status overview."""

from __future__ import annotations

import os
from typing import Any

from ._shared import mcp
from ._client_helpers import get_late_client, suppress_stdout


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
