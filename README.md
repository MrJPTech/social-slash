<div align="center">

# Social Slash

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=22&pause=1000&color=FF3D00&center=true&vCenter=true&multiline=true&repeat=true&width=600&height=80&lines=19+MCP+Tools+%7C+13+Platforms+%7C+SWIZZ+Voice;AI+Content+Agents+%7C+Railway+SSE+%7C+Claude+Mobile" alt="Typing SVG" />

[![PRSMTECH](https://img.shields.io/badge/PRSMTECH-INTERNAL-FF3D00?style=for-the-badge&labelColor=0C0C0C)](https://github.com/MrJPTech)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-19_Tools-8B5CF6?style=for-the-badge)](https://modelcontextprotocol.io)
[![Late SDK](https://img.shields.io/badge/Late_SDK-13_Platforms-10B981?style=for-the-badge)](https://getlate.dev)
[![Railway](https://img.shields.io/badge/Railway-Deployed-06B6D4?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" alt="rainbow line" width="100%"/>

**Social media automation for Claude Code, Claude Desktop, and Claude Mobile.**
**Post to 13 platforms with AI-powered SWIZZ voice content generation.**

</div>

## Overview

Social Slash is a social media automation package that works across the entire Claude ecosystem:

| Mode | Transport | Use Case |
|:-----|:----------|:---------|
| **Slash Commands** | PowerShell + Python | Claude Code CLI |
| **MCP Server** | stdio | Claude Desktop |
| **MCP Server** | SSE (Railway) | Claude Mobile/Web |

19 tools across 5 groups: utility, writing, research, media, and posting. Optional AI content generation in the **SWIZZ** dual-mode voice persona (professional/personal).

## Architecture

```
Claude Code ──► PowerShell ──► Python Backend ──► Late SDK ──► Platform API
                                    │
Claude Desktop ──► MCP (stdio) ─────┘
                                    │
Claude Mobile ──► MCP (SSE/Railway) ┘
                                    │
                         Optional AI Enhancement
                        (Gemini 2.0 / Anthropic)
```

<details>
<summary><b>MCP Server Detail</b></summary>

```
Client (Desktop/Mobile) ──► MCP JSON-RPC
       │
lib/mcp/server.py (FastMCP, 19 @mcp.tool())
       │
  suppress_stdout()  ◄── prevents print() from corrupting stdio
       │
  Late SDK / Agents / Poster
       │
  Platform API ──► Result JSON ──► Client
```

Transport auto-detection: `PORT` env var triggers SSE for Railway; no `PORT` defaults to stdio for Claude Desktop.

</details>

## Features

| Category | Features |
|:---------|:---------|
| **Posting** | 13 platforms, multi-platform, scheduling, dry run, media upload |
| **AI Writing** | SWIZZ voice posts, captions, threads (professional/personal mode) |
| **Research** | Hashtag research, trending analysis, content calendars, idea generation |
| **Media** | Reel captions, story text, carousel captions, alt text, format suggestions |
| **Engagement** | Comment monitoring, DM auto-reply, bot management |
| **MCP Server** | 19 tools for Claude Desktop + Claude Mobile via Railway SSE |

## MCP Tools

| Group | Tools | Requires |
|:------|:------|:---------|
| **Utility** (5) | `accounts_list`, `accounts_refresh_cache`, `posts_recent`, `post_details`, `status_overview` | `LATE_API_KEY` |
| **Writing** (3) | `writing_generate_post`, `writing_generate_caption`, `writing_generate_thread` | AI key |
| **Research** (4) | `research_hashtags`, `research_content_ideas`, `research_trending`, `research_content_calendar` | AI key |
| **Media** (5) | `media_generate_caption`, `media_generate_story_text`, `media_generate_carousel`, `media_generate_alt_text`, `media_suggest_format` | AI key |
| **Posting** (2) | `post_to_platform`, `post_to_multiple` | `LATE_API_KEY` |

## Slash Commands

| Command | Description |
|:--------|:------------|
| `/social:post` | Post to single or multiple platforms |
| `/social:multi-post` | Quick multi-platform distribution |
| `/social:schedule` | Schedule future posts |
| `/social:write` | SWIZZ voice post/thread/caption generation |
| `/social:research` | Hashtag, trend, and content research |
| `/social:media` | Reel/story/carousel caption generation |
| `/social:comment-agent` | Comment monitoring and auto-reply |
| `/social:dm-agent` | DM monitoring and auto-reply |
| `/social:bot-manage` | Bot account management |
| `/social:accounts` | List and manage connected accounts |
| `/social:analytics` | Post activity and engagement metrics |
| `/social:status` | Project status dashboard |

## Quick Start

### Installation

```bash
git clone git@github.com:MrJPTech/social-slash.git
cd social-slash
pip install -r requirements.txt
cp .env.example .env.local
# Add your API keys to .env.local
```

### Post to LinkedIn

```powershell
/social:post -Content "Lock in developers" -Platforms linkedin
```

### Multi-platform with AI

```powershell
/social:post -Content "New content!" -Platforms linkedin,tiktok -Enhance
```

### Dry run

```powershell
/social:post -Content "Test" -Platforms linkedin -DryRun
```

### Generate SWIZZ voice content

```powershell
/social:write -Topic "AI automation" -Platform instagram -PersonaMode professional
```

## Configuration

### Environment Variables

```env
# Required
LATE_API_KEY=your_late_api_key

# Optional (for AI agent tools)
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### API Keys

| Service | Get At | Purpose |
|:--------|:-------|:--------|
| Late API | [getlate.dev](https://getlate.dev) | Core posting backend |
| Gemini | [aistudio.google.com](https://aistudio.google.com) | AI content generation |
| Anthropic | [console.anthropic.com](https://console.anthropic.com) | Alternative AI provider |

## Deployment

### Claude Desktop (stdio)

Add to `claude_desktop_config.json`:

```json
{
    "mcpServers": {
        "social-slash": {
            "command": "python",
            "args": ["-m", "lib.mcp"],
            "cwd": "/path/to/social-slash",
            "env": {
                "PYTHONPATH": ".",
                "LATE_API_KEY": "your_key",
                "GOOGLE_API_KEY": "your_key"
            }
        }
    }
}
```

### Claude Mobile/Web (Railway SSE)

Deployed at `web-production-c9cb9.up.railway.app`. Auto-deploys from `master` branch.

```bash
# Verify deployment
curl https://web-production-c9cb9.up.railway.app/health
```

Add as **Custom Connector** in claude.ai > Settings > Connectors to sync tools to Claude iOS/Android.

### Docker

```bash
docker build -t social-slash-mcp .
docker run -i --rm --env-file .env.local social-slash-mcp
```

## Supported Platforms

| Platform | Char Limit | Media Types |
|:---------|:-----------|:------------|
| LinkedIn | 3,000 | text, image, video, document |
| TikTok | 2,200 | video |
| Instagram | 2,200 | image, video, carousel, reel |
| YouTube | 5,000 | video, short, live |
| Twitter/X | 280 | text, image, video, poll |
| Facebook | 63,206 | text, image, video, link |
| Pinterest | 500 | image, video, idea pin |
| Threads | 500 | text, image, video |
| Bluesky | 300 | text, image |
| Reddit | 40,000 | text, image, video, link |
| Snapchat | 60s | image, video, story |
| Telegram | 4,096 | text, image, video, document |
| Google Business | 1,500 | text, image, offer, event |

## Project Structure

<details>
<summary><b>Full directory tree</b></summary>

```
social-slash/
├── .claude/commands/
│   ├── posting/              # post, multi-post, schedule
│   ├── engagement/           # comment-agent, dm-agent, bot-manage
│   ├── agents/               # write, research, media
│   ├── utility/              # accounts, analytics, status
│   └── social/               # Command documentation (.md)
├── lib/
│   ├── mcp/                  # MCP server (FastMCP, 19 tools)
│   │   ├── server.py         # Tool definitions + health routes
│   │   ├── _client_helpers.py # suppress_stdout, client factory
│   │   └── __main__.py       # Entry point with transport detection
│   ├── posting/poster.py     # Core posting orchestrator
│   ├── api_clients/          # Late SDK wrapper
│   ├── ai/                   # Gemini + Anthropic clients
│   ├── agents/               # Writing, Research, Media, Comment, DM agents
│   ├── persona/              # SWIZZ dual-mode voice persona
│   ├── engagement/           # Engagement client + response generator
│   ├── utility/              # Account, analytics, status backends
│   ├── storage/              # SQLite database + models
│   ├── tools/                # Social media tools reference DB
│   └── webhooks/             # Late webhook server (FastAPI)
├── data/                     # JSON configs (platform templates, queue, engagement)
├── tests/                    # 151 tests
├── Dockerfile                # Python 3.12-slim, auto-detect transport
├── railway.json              # Railway deployment config
├── requirements.txt          # Full dependencies
└── requirements-mcp.txt      # Slim MCP server dependencies
```

</details>

## Development

```bash
# Install all dependencies
pip install -r requirements.txt

# Run tests (151 passing)
pytest tests/

# Local MCP server (stdio)
PYTHONPATH=. python -m lib.mcp

# Local SSE testing
PORT=8000 PYTHONPATH=. python -m lib.mcp
```

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Runtime | Python 3.12 |
| Distribution | Late SDK (13 platforms) |
| AI | Google Gemini 2.0 Flash, Anthropic Claude |
| MCP | FastMCP 1.26 (stdio + SSE) |
| Server | uvicorn (SSE transport) |
| Deploy | Railway (auto-deploy from master) |
| Container | Docker (python:3.12-slim) |
| Data | Pydantic, SQLite, JSON configs |

<img src="https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png" alt="rainbow line" width="100%"/>

<div align="center">

**Built with precision by PRSMTECH**

[![Back to top](https://img.shields.io/badge/Back%20to%20Top-↑-FF3D00?style=for-the-badge)](#)

![Footer](https://capsule-render.vercel.app/api?type=waving&color=FF3D00&height=100&section=footer)

</div>
