# /social:schedule - Schedule Social Media Posts

Schedule content for future publishing to social media platforms.

## Usage
```
/social:schedule <content> --time <datetime> [options]
```

## Arguments
$ARGUMENTS

## Options
- `--time <datetime>` - **Required** - Schedule time (ISO 8601 format)
- `--platforms <list>` - Target platforms (comma-separated, default: all)
- `--enhance` - Enable AI content enhancement (Gemini)
- `--ai-provider <gemini|anthropic>` - Choose AI provider (default: gemini)
- `--media <urls>` - Attach media URLs (comma-separated)
- `--timezone <tz>` - Timezone for schedule (default: UTC)

## Time Formats
```bash
# ISO 8601 (recommended)
--time "2026-02-02T10:00:00Z"        # UTC
--time "2026-02-02T10:00:00-05:00"   # EST

# Relative times (parsed)
--time "tomorrow 9am"
--time "next monday 2pm"
```

## Examples
```bash
# Schedule for specific time
/social:schedule "Product launch!" --time "2026-02-02T10:00:00Z" --platforms linkedin,twitter

# Schedule with AI enhancement
/social:schedule "Big announcement coming!" --time "2026-02-03T14:00:00Z" --enhance

# Schedule to all platforms
/social:schedule "Weekly update" --time "2026-02-07T09:00:00-05:00"
```

## Execution
Run the Python backend:
```powershell
cd J:\PRSMTECH\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\posting\poster.py --content "<content>" --platforms <platforms> --schedule "<datetime>" [options]
```

## Best Posting Times (Reference)
| Platform | Best Times (EST) |
|----------|------------------|
| LinkedIn | Tue-Thu 9am-12pm |
| Twitter/X | Mon-Fri 8am-10am |
| Instagram | Mon-Fri 11am-1pm |
| TikTok | Tue-Thu 7pm-9pm |
| Facebook | Wed-Fri 1pm-4pm |

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
