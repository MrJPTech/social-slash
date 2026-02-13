# Product Context

**Project**: social-slash
**Last Updated**: 2026-02-12
**Status**: In Development (Sprint 3)

## Overview
Social Slash is a social media automation platform with three access methods: Claude Code slash commands, MCP server (Claude Desktop + Claude.ai), and Python CLI. Posts to 13 platforms via Late SDK with AI content enhancement and AI image generation. Features engagement automation (comment/DM agents, bot management), multi-mode persona-powered content generation (3 voice modes), AI image creation (Google Imagen 3 with persona-aware prompts), and 24 MCP tools deployed to Railway with OAuth 2.0.

## Tech Stack

### Interfaces
- PowerShell slash commands (`.claude/commands/`) — 13 commands
- MCP server (FastMCP) — 24 tools, Claude Desktop + Claude.ai
- Python CLI — direct module execution

### Backend
- Python 3.10+
- Late SDK for multi-platform distribution
- FastMCP (mcp v1.26.0) for MCP server
- Starlette for HTTP/OAuth endpoints
- Pydantic for data validation
- SQLite for engagement storage

### AI Integration
- Google Gemini 2.0 Flash (primary text generation)
- Google Imagen 3 (image generation via google-genai SDK)
- Anthropic Claude (alternative text generation)
- Pillow (image processing for Imagen SDK)

### Infrastructure
- Railway (MCP server deployment, auto-deploy from master)
- Docker (python:3.12-slim image)
- OAuth 2.0 (pre-shared credentials for Claude.ai)
- Streamable-HTTP transport (`/mcp` endpoint)

## Architecture

### Slash Commands (Claude Code)
```
/social:post (PowerShell) → poster.py → Late SDK → Platform API
                                ↓
                       Optional AI Enhancement
```

### MCP Server (Claude Desktop / Claude.ai)
```
Claude Desktop/Claude.ai → MCP JSON-RPC → server.py (19 tools)
                                              ↓
                                    suppress_stdout()
                                              ↓
                              Late SDK / Agents / Poster → Platform API
```

### Three Access Methods
1. **Windows Claude Desktop** — local Python stdio
2. **Mac Claude Desktop** — remote Railway URL
3. **Claude.ai Web** — remote Railway URL + OAuth 2.0

## Key Features
1. **13 Platform Support**: LinkedIn, TikTok, Instagram, YouTube, Twitter, Facebook, Pinterest, Threads, Bluesky, Reddit, Snapchat, Telegram, Google Business
2. **AI Enhancement**: Content optimization via Gemini or Claude
3. **3 Voice Modes**: Professional (@swizzimatic), Personal (@BigSwizzi), CEO (Jordan Ward)
4. **7 CEO Content Formats**: problem_solution, myth_busting, quick_tips, day_in_life, case_study, industry_commentary, quick_wins
5. **24 MCP Tools**: 5 utility + 3 writing + 4 research + 5 media + 2 posting + 5 image
6. **Engagement Automation**: Comment/DM agents with human-in-the-loop review
7. **Multi-Platform Posting**: Post to multiple platforms simultaneously
8. **Scheduling**: Schedule posts for future publishing
9. **OAuth 2.0**: Pre-shared credentials for Claude.ai custom connectors
10. **AI Image Generation**: Google Imagen 3 with persona-aware prompt enhancement, 22 platform presets

## External Integrations
- **Late API** (getlate.dev) — Core distribution backend (9 connected accounts)
- **Google Gemini API** — AI content enhancement
- **Anthropic API** — Alternative AI enhancement
- **Railway** — MCP server deployment (`https://web-production-c9cb9.up.railway.app/mcp`)

## Environment Variables
```env
# Required
LATE_API_KEY=your_late_api_key

# Optional (for AI enhancement)
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_key

# Railway MCP server
MCP_AUTH_TOKEN=bearer_token_for_remote_access
OAUTH_CLIENT_ID=pre_shared_oauth_client_id
OAUTH_CLIENT_SECRET=pre_shared_oauth_client_secret
```

## Test Suite
- **239 tests passing**, 1 skipped
- 38 image generation tests (18 ImagenClient + 20 ImageAgent)
- 50 CEO persona tests across 11 test classes
- Gemini SDK migration validated (google-genai v1.63.0)

---
**Usage**: Update when architecture or major features change
