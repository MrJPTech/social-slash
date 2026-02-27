"""Infrastructure routes — health check and root endpoint."""

from __future__ import annotations

import os

from starlette.requests import Request
from starlette.responses import JSONResponse

from ._shared import mcp, _get_scheduler


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Railway."""
    sched = _get_scheduler()
    return JSONResponse({
        "status": "healthy",
        "service": "social-slash-mcp",
        "tools": 33,
        "scheduler": "running" if (sched and sched.scheduler.running) else "disabled",
        "env": {
            "LATE_API_KEY": "set" if os.getenv("LATE_API_KEY") else "MISSING",
            "GOOGLE_API_KEY": "set" if os.getenv("GOOGLE_API_KEY") else "MISSING",
            "ANTHROPIC_API_KEY": "set" if os.getenv("ANTHROPIC_API_KEY") else "MISSING",
            "MCP_AUTH_TOKEN": "set" if os.getenv("MCP_AUTH_TOKEN") else "MISSING",
            "OAUTH_CLIENT_ID": "set" if os.getenv("OAUTH_CLIENT_ID") else "MISSING",
            "GCHAT_WEBHOOK_SOCIAL_SLASH": "set" if os.getenv("GCHAT_WEBHOOK_SOCIAL_SLASH") else "MISSING",
            "APPROVAL_TOKEN_SECRET": "set" if os.getenv("APPROVAL_TOKEN_SECRET") else "MISSING",
            "GCHAT_BOT_SECRET": "set" if os.getenv("GCHAT_BOT_SECRET") else "unset (open)",
            "SUPABASE_URL": "set" if os.getenv("SUPABASE_URL") else "unset (Late fallback)",
            "SUPABASE_SERVICE_KEY": "set" if os.getenv("SUPABASE_SERVICE_KEY") else "unset (Late fallback)",
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
            "gchat_bot": "/gchat/events",
        },
        "auth": "OAuth 2.0 (Authorization Code + PKCE)",
    })
