# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Social Slash is a standalone Claude Code slash command package for social media automation. It posts to 13 platforms via Late SDK with optional AI content enhancement using Gemini or Anthropic. Also available as an MCP server for Claude Desktop.

## Build Commands

```bash
pip install -r requirements.txt              # Install all dependencies
pip install -r requirements-mcp.txt          # Install MCP server dependencies
pip install -e .                             # Install package in development mode
pip install -e ".[ai]"                       # Install with AI enhancement support
pip install -e ".[all]"                      # Install all optional dependencies
```

## MCP Server (Claude Desktop)

```bash
# Development (direct Python)
PYTHONPATH=. python -m lib.mcp

# Docker build & run
docker build -t social-slash-mcp .
docker run -i --rm --env-file .env.local social-slash-mcp
```

19 tools across 5 groups: utility (5), writing (3), research (4), media (5), posting (2).

## Testing

```bash
pytest tests/                                # Run all tests
python lib/posting/poster.py --dry-run       # Test posting without publishing

# Dry run from slash command
/social:post -Content "Test" -Platforms linkedin -DryRun
```

151 tests passing, 1 skipped.

## Architecture

### Request Flow (Claude Code - Slash Commands)

```
/social:post (PowerShell)
       ↓
post.ps1 → Builds CLI args, finds Python
       ↓
poster.py (Poster class)
       ↓
    ┌──────────────────────┐
    │  Optional AI Step    │
    │  gemini_client.py OR │
    │  anthropic_client.py │
    └──────────────────────┘
       ↓
late_client.py → Late SDK
       ↓
Platform API → Posted content
```

### Request Flow (Claude Desktop - MCP Server)

```
Claude Desktop → MCP JSON-RPC (stdio)
       ↓
lib/mcp/server.py (FastMCP, 19 tools)
       ↓
    ┌──────────────────────────┐
    │  suppress_stdout()       │
    │  prevents print()        │
    │  from corrupting stdio   │
    └──────────────────────────┘
       ↓
Late SDK / Agents / Poster
       ↓
Platform API → Result JSON → Claude Desktop
```

### Core Components

**Posting Commands** (`.claude/commands/posting/`)
- `post.ps1` - Main `/social:post` command with all options
- `multi-post.ps1` - Convenience wrapper for multi-platform posting
- `schedule.ps1` - Future scheduling wrapper

**Engagement Commands** (`.claude/commands/engagement/`)
- `comment-agent.ps1` - `/social:comment-agent` comment monitoring and auto-reply
- `dm-agent.ps1` - `/social:dm-agent` DM monitoring and auto-reply
- `bot-manage.ps1` - `/social:bot-manage` bot account management

**Agent Commands** (`.claude/commands/agents/`)
- `write.ps1` - `/social:write` SWIZZ voice post/thread/caption generation
- `research.ps1` - `/social:research` hashtag/trend/content research
- `media.ps1` - `/social:media` reel/story/carousel caption generation

**Utility Commands** (`.claude/commands/utility/`)
- `accounts.ps1` - `/social:accounts` list and manage connected accounts
- `analytics.ps1` - `/social:analytics` post activity and engagement metrics
- `status.ps1` - `/social:status` project status dashboard

**MCP Server** (`lib/mcp/`)
- `server.py` - FastMCP server with 19 `@mcp.tool()` definitions
- `_client_helpers.py` - Late client factory, stdout suppressor, agent config builder
- `__main__.py` - Entry point: `python -m lib.mcp`

**Python Backend** (`lib/`)
- `posting/poster.py` - Main orchestrator, handles AI enhancement + distribution
- `api_clients/late_client.py` - Late SDK wrapper with account caching
- `ai/gemini_client.py` - Gemini 2.0 Flash content enhancement
- `ai/anthropic_client.py` - Claude AI content enhancement
- `agents/writing_agent.py` - SWIZZ voice post generation agent
- `agents/research_agent.py` - Content research and hashtag agent
- `agents/media_agent.py` - Media captioning agent
- `agents/comment_agent.py` - Comment monitoring agent
- `agents/dm_agent.py` - DM monitoring agent
- `agents/bot_manager.py` - Bot account management
- `persona/swizz_persona.py` - Dual-mode SWIZZ voice persona system
- `utility/accounts.py` - Account listing utility
- `utility/analytics.py` - Post analytics utility
- `utility/status.py` - Project status aggregation utility
- `tools/social_tools.py` - Social media tools database (SDKs, schedulers, etc.)

**Configuration** (`data/`)
- `platform_templates.json` - Per-platform settings (char limits, best times, content types)
- `queue_config.json` - Queue/scheduling settings
- `engagement_config.json` - Agent configuration
- `response_templates.json` - Response templates for comments and DMs

## Key Directories

- `.claude/commands/posting/` - Posting slash commands (post, multi-post, schedule)
- `.claude/commands/engagement/` - Engagement slash commands (comment-agent, dm-agent, bot-manage)
- `.claude/commands/agents/` - Agent slash commands (write, research, media)
- `.claude/commands/utility/` - Utility slash commands (accounts, analytics, status)
- `.claude/commands/social/` - Documentation (.md) for all slash commands
- `lib/mcp/` - MCP server for Claude Desktop (19 tools, FastMCP, Docker)
- `lib/posting/` - Core posting orchestration
- `lib/api_clients/` - External API wrappers
- `lib/ai/` - AI enhancement clients
- `lib/agents/` - Engagement and content generation agents
- `lib/persona/` - SWIZZ dual-mode voice persona system
- `lib/utility/` - Account, analytics, and status utilities
- `lib/engagement/` - Engagement client and response generator
- `lib/storage/` - SQLite database and models
- `lib/tools/` - Social media tools database
- `data/` - JSON configuration files

## File Locations

- **Platform Config**: `data/platform_templates.json`
- **Environment Template**: `.env.example`

## Notes

- PowerShell commands call Python backend via subprocess - exit codes propagate
- AI clients lazy-load (`_init_ai_client`) to avoid import errors when AI packages aren't installed
- Late SDK client caches account IDs in `_account_cache` to avoid repeated API calls
- Console output uses bracketed prefixes: `[SUCCESS]`, `[INFO]`, `[ERROR]`, `[WARNING]`
- Supported platforms are defined in `LateDistributionClient.SUPPORTED_PLATFORMS` (must match `ValidateSet` in post.ps1)
- Gemini uses `gemini-2.0-flash-exp` model for content enhancement
- Platform char limits and best practices in `data/platform_templates.json` inform AI enhancement prompts
- `lib/tools/social_tools.py` is a reference database - not used in core posting flow
