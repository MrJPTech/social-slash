"""Allow running MCP server with: python -m lib.mcp

Transport auto-detection:
  - PORT env var set (Railway/cloud): SSE on 0.0.0.0:$PORT
  - No PORT (local/Claude Desktop): stdio
"""
import os

from lib.mcp.server import mcp

if __name__ == "__main__":
    port = os.environ.get("PORT")
    if port:
        from mcp.server.transport_security import TransportSecuritySettings

        mcp.settings.host = "0.0.0.0"
        mcp.settings.port = int(port)
        mcp.settings.transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
        )
        print(f"[MCP] Starting SSE transport on 0.0.0.0:{port}")
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
