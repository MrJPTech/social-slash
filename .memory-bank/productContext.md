# Product Context

**Project**: social-slash
**Last Updated**: 2026-02-01
**Status**: In Development

## Overview
Social Slash is a standalone Claude Code slash command package for social media automation. It enables posting to 13 platforms via Late SDK with optional AI content enhancement using Gemini or Anthropic. Includes engagement automation (comment/DM agents, bot management) and persona-powered content generation in the SWIZZ voice.

## Tech Stack

### Frontend
- PowerShell slash commands (`.claude/commands/`)
- Claude Code CLI integration

### Backend
- Python 3.10+
- Late SDK for multi-platform distribution
- Pydantic for data validation
- httpx/requests for HTTP

### AI Integration
- Google Gemini 2.0 Flash (primary)
- Anthropic Claude (alternative)

### Infrastructure
- Standalone package (pip installable)
- No database required
- Stateless operation

## Architecture

```
Claude Code → PowerShell Command → Python Backend → Late SDK → Platform API
                                        ↓
                               Optional AI Enhancement
```

**Key Flow:**
1. User invokes `/social:post` with content and platform(s)
2. PowerShell wrapper builds CLI args and calls Python
3. `poster.py` orchestrates enhancement and distribution
4. `late_client.py` handles Late SDK interaction
5. Results returned to user

## Key Features
1. **13 Platform Support**: LinkedIn, TikTok, Instagram, YouTube, Twitter, Facebook, Pinterest, Threads, Bluesky, Reddit, Snapchat, Telegram, Google Business
2. **AI Enhancement**: Optional content optimization via Gemini or Claude
3. **Multi-Platform**: Post to multiple platforms simultaneously
4. **Scheduling**: Schedule posts for future publishing
5. **Dry Run**: Test posts without publishing

## External Integrations
- **Late API** (getlate.dev) - Core distribution backend
- **Google Gemini API** - AI content enhancement
- **Anthropic API** - Alternative AI enhancement

## Environment Variables
```env
# Required
LATE_API_KEY=your_late_api_key

# Optional (for AI enhancement)
GOOGLE_API_KEY=your_google_api_key
ANTHROPIC_API_KEY=your_anthropic_key
```

---
**Usage**: Update when architecture or major features change
