"""Allow running MCP server with: python -m lib.mcp

Transport auto-detection:
  - PORT env var set (Railway/cloud): streamable-http on 0.0.0.0:$PORT
  - No PORT (local/Claude Desktop): stdio
"""

from lib.mcp.server import main

if __name__ == "__main__":
    main()
