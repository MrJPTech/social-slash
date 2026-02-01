# /social:multi-post - Multi-Platform Posting Command

Post content to multiple social media platforms simultaneously with optional AI enhancement.

## Usage
```
/social:multi-post <content> [options]
```

## Arguments
$ARGUMENTS

## Options
- `--enhance` - Enable AI content enhancement (Gemini)
- `--ai-provider <gemini|anthropic>` - Choose AI provider (default: gemini)
- `--media <urls>` - Attach media URLs (comma-separated)
- `--schedule <datetime>` - Schedule post for later (ISO 8601 format)
- `--dry-run` - Simulate without posting
- `--stop-on-error` - Stop posting if any platform fails

## Default Platforms
Posts to all connected accounts:
- LinkedIn, Twitter/X, Instagram, TikTok, Facebook, YouTube, Threads, Reddit, Google Business

## Examples
```bash
# Post to all platforms
/social:multi-post "Exciting news coming soon!"

# With AI enhancement
/social:multi-post "Check out our latest update!" --enhance

# Scheduled multi-platform post
/social:multi-post "Product launch tomorrow!" --schedule "2026-02-02T09:00:00Z"

# Dry run to test
/social:multi-post "Test content" --dry-run
```

## Execution
Run the Python backend:
```powershell
cd J:\PRSMTECH\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\posting\poster.py --content "<content>" --platforms all [options]
```

## Connected Accounts
- Twitter/X: @mrjptech
- LinkedIn: PRSM TECH INCORPORATED
- Instagram: @mrjptech_
- TikTok: @mrjptech
- Facebook: Prsm Tech Inc.
- YouTube: @mrjptechy
- Threads: @mrjptech_
- Reddit: MrJPTech
- Google Business: PRSM Tech Incorporated
