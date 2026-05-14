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
                "cwd": "/path/to/social-slash",
                "env": {"PYTHONPATH": "."}
            }
        }
    }

    # Claude mobile: Add as remote MCP server in Claude iOS/Android app
    #   URL: https://<railway-domain>/mcp
    #   Auth: Bearer token (MCP_AUTH_TOKEN env var)
"""

from __future__ import annotations

import os

# Import every tool / route module so that their @mcp.tool() and
# @mcp.custom_route() decorators register on the shared `mcp` instance.
from . import (
    routes_infra,  # noqa: F401  — /health, /
    routes_oauth,  # noqa: F401  — OAuth 2.0 endpoints
    routes_scheduler,  # noqa: F401  — /approval, /gchat/events, /scheduler/*
    tools_content,  # noqa: F401  — 3 tools
    tools_image,  # noqa: F401  — 5 tools
    tools_media,  # noqa: F401  — 5 tools
    tools_media_library,  # noqa: F401  — 6 tools
    tools_posting,  # noqa: F401  — 2 tools
    tools_research,  # noqa: F401  — 4 tools
    tools_utility,  # noqa: F401  — 5 tools
    tools_writing,  # noqa: F401  — 3 tools
)

# Re-export the shared mcp instance for backward compatibility:
#   from lib.mcp.server import mcp
#   from lib.mcp.server import main
from ._shared import _set_scheduler, mcp  # noqa: F401
from .middleware import BearerAuthMiddleware
from .routes_oauth import OAUTH_CLIENT_ID


def main() -> None:
    """Entry point - auto-detects transport from PORT env var."""
    port = os.environ.get("PORT")

    # Start scheduler if enabled (Railway / cloud only)
    scheduler_enabled = os.environ.get("SCHEDULER_ENABLED", "false").lower() == "true"
    if scheduler_enabled:
        try:
            from lib.scheduler.daily_scheduler import DailyScheduler

            scheduler = DailyScheduler()
            scheduler.start()
            _set_scheduler(scheduler)
            print("[SLASHERBOT] Daily scheduler started")
        except Exception as exc:
            print(f"[SLASHERBOT] Scheduler failed to start: {exc}")

    from ._shared import _get_scheduler

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
            oauth_status = "locked" if OAUTH_CLIENT_ID else "open (set OAUTH_CLIENT_ID to lock)"
            print(f"[MCP] OAuth: {oauth_status}")
            print(f"[MCP] Starting streamable-http on 0.0.0.0:{port}")
            config = uvicorn.Config(
                app,
                host="0.0.0.0",
                port=int(port),
                log_level="info",
                # Give streaming MCP connections 5 s to close cleanly on Railway
                # rolling deploys, reducing "ASGI callable returned without
                # completing response" noise in logs.
                timeout_graceful_shutdown=5,
            )
            server = uvicorn.Server(config)
            try:
                await server.serve()
            finally:
                sched = _get_scheduler()
                if sched:
                    sched.stop()

        anyio.run(_serve)
    else:
        try:
            mcp.run(transport="stdio")
        finally:
            sched = _get_scheduler()
            if sched:
                sched.stop()


if __name__ == "__main__":
    main()
