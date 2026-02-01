# /social:post - Social Media Posting Command

Post content to social media platforms via Late API with optional AI enhancement.

## Usage
```
/social:post <content> [options]
```

## Arguments
$ARGUMENTS

## Options
- `--platforms <list>` - Target platforms (comma-separated): linkedin, twitter, instagram, tiktok, facebook, youtube, threads, reddit, bluesky, pinterest, snapchat, telegram, googlebusiness
- `--enhance` - Enable AI content enhancement (Gemini)
- `--ai-provider <gemini|anthropic>` - Choose AI provider (default: gemini)
- `--media <urls>` - Attach media URLs (comma-separated)
- `--schedule <datetime>` - Schedule post for later (ISO 8601 format)
- `--dry-run` - Simulate without posting

## Examples
```bash
# Simple post to Twitter
/social:post "Hello world!" --platforms twitter

# Multi-platform with AI enhancement
/social:post "Check out our new feature!" --platforms linkedin,twitter,instagram --enhance

# Scheduled post
/social:post "Coming soon!" --platforms linkedin --schedule "2026-02-02T10:00:00Z"

# Dry run test
/social:post "Test post" --platforms twitter --dry-run
```

## Execution
Run the Python backend:
```powershell
cd J:\PRSMTECH\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\posting\poster.py --content "<content>" --platforms <platforms> [options]
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
