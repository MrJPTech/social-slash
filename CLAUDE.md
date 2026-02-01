# CLAUDE.md - Social Slash

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Social Slash is a standalone package of social media automation slash commands for Claude Code. It enables posting to 13 platforms with optional AI enhancement.

## Technology Stack

- **Language**: Python 3.10+, PowerShell (commands)
- **SDK**: Late SDK (`late-sdk>=1.2.17`)
- **AI**: Google Gemini, Anthropic Claude (optional)
- **Platforms**: LinkedIn, TikTok, Instagram, YouTube, Twitter, Facebook, Pinterest, Threads, Bluesky, Reddit, Snapchat, Telegram, Google Business

## Architecture

```
Claude Code Slash Command → PowerShell Wrapper → Python Backend → Late SDK → Platform
                                    ↓
                            AI Enhancement (optional)
```

## Key Files

| File | Purpose |
|------|---------|
| `.claude/commands/posting/post.ps1` | Main `/social:post` command |
| `lib/posting/poster.py` | Core posting orchestration |
| `lib/api_clients/late_client.py` | Late SDK wrapper |
| `lib/ai/gemini_client.py` | Gemini AI integration |
| `lib/ai/anthropic_client.py` | Claude AI integration |
| `data/platform_templates.json` | Platform configurations |

## Commands

### /social:post
Main posting command with full options.

```powershell
/social:post -Content "text" -Platforms linkedin
/social:post -Content "text" -Platforms linkedin,twitter -Enhance
/social:post -Content "text" -Platforms linkedin -DryRun
```

### /social:multi-post
Convenience for multi-platform posting.

```powershell
/social:multi-post -Content "text"  # Defaults to linkedin,twitter,threads
```

### /social:schedule
Schedule posts for future.

```powershell
/social:schedule -Content "text" -Platforms linkedin -At "tomorrow 9am"
```

## Environment Variables

```env
LATE_API_KEY=required
GOOGLE_API_KEY=optional (for Gemini)
ANTHROPIC_API_KEY=optional (for Claude)
```

## Testing

### Dry Run Mode
Always test with `-DryRun` first:
```powershell
/social:post -Content "Test" -Platforms linkedin -DryRun
```

### Python Direct
```bash
python lib/posting/poster.py --content "Test" --platforms linkedin --dry-run
```

## Common Tasks

### Add a new platform
1. Add platform config to `data/platform_templates.json`
2. Add to `SUPPORTED_PLATFORMS` in `lib/api_clients/late_client.py`
3. Add to `ValidateSet` in `.claude/commands/posting/post.ps1`

### Modify AI enhancement
1. Edit prompts in `lib/ai/gemini_client.py` or `anthropic_client.py`
2. Adjust `enhance_content()` method parameters

### Add new command
1. Create `.claude/commands/<category>/<name>.ps1`
2. Add Python backend in `lib/<category>/` if needed
3. Document in README.md

## Development Patterns

### Error Handling
Use bracketed log levels:
```python
print("[SUCCESS] Operation completed")
print("[INFO] Processing...")
print("[ERROR] Something failed")
```

### API Client Pattern
```python
class Client:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('API_KEY_NAME')
        if not self.api_key:
            raise ValueError("API key required")
```

### PowerShell Command Pattern
```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Content,
    [switch]$DryRun
)
# Build args, call Python, handle exit code
```

## Deployment

This is a standalone package. To use in another project:

1. Clone or copy to project
2. Install requirements: `pip install -r requirements.txt`
3. Set environment variables
4. Add `.claude/commands/` to Claude Code path
