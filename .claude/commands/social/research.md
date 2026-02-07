# /social:research - SWIZZ Voice Research Agent

Research hashtags, suggest content ideas, analyze trends, and build content calendars for social media strategy.

## Usage
```
/social:research <action> [options]
```

## Arguments
$ARGUMENTS

## Actions
- `hashtags` - Research relevant hashtags for a topic
- `suggest` - Generate content ideas for a theme
- `trending` - Analyze current trends on a platform
- `calendar` - Build a multi-day content calendar
- `status` - Show agent status

## Options
- `--topic <text>` - Research topic (required for hashtags)
- `--theme <text>` - Content theme (required for suggest)
- `--platform <name>` - Target platform (default: instagram)
- `--count <n>` - Number of results (default: 5)
- `--days <n>` - Calendar days (default: 7)
- `--persona <mode>` - Persona: professional or personal (default: professional)

## Examples

```bash
# Research hashtags
/social:research hashtags -Topic "web development" -Platform instagram

# Generate content ideas
/social:research suggest -Theme "spring marketing" -Count 10

# Analyze TikTok trends
/social:research trending -Platform tiktok

# Build a 2-week content calendar
/social:research calendar -Days 14 -Platform instagram

# Check agent status
/social:research status
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.agents.research_agent --action hashtags --topic "topic" --platform instagram
```
