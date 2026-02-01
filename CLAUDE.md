# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Social Slash is a standalone Claude Code slash command package for social media automation. It posts to 13 platforms via Late SDK with optional AI content enhancement using Gemini or Anthropic.

## Build Commands

```bash
pip install -r requirements.txt              # Install all dependencies
pip install -e .                             # Install package in development mode
pip install -e ".[ai]"                       # Install with AI enhancement support
pip install -e ".[all]"                      # Install all optional dependencies
```

## Testing

```bash
pytest tests/                                # Run all tests
python lib/posting/poster.py --dry-run       # Test posting without publishing

# Dry run from slash command
/social:post -Content "Test" -Platforms linkedin -DryRun
```

No test files exist yet - the `tests/` directory is empty.

## Architecture

### Request Flow

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

### Core Components

**Slash Commands** (`.claude/commands/posting/`)
- `post.ps1` - Main `/social:post` command with all options
- `multi-post.ps1` - Convenience wrapper for multi-platform posting
- `schedule.ps1` - Future scheduling wrapper

**Python Backend** (`lib/`)
- `posting/poster.py` - Main orchestrator, handles AI enhancement + distribution
- `api_clients/late_client.py` - Late SDK wrapper with account caching
- `ai/gemini_client.py` - Gemini 2.0 Flash content enhancement
- `ai/anthropic_client.py` - Claude AI content enhancement
- `tools/social_tools.py` - Social media tools database (SDKs, schedulers, etc.)

**Configuration** (`data/`)
- `platform_templates.json` - Per-platform settings (char limits, best times, content types)
- `queue_config.json` - Queue/scheduling settings

## Key Directories

- `.claude/commands/` - PowerShell slash command definitions
- `lib/posting/` - Core posting orchestration
- `lib/api_clients/` - External API wrappers
- `lib/ai/` - AI enhancement clients
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
