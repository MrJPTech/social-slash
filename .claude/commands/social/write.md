# /social:write - SWIZZ Voice Writing Agent

Generate social media posts, threads, and captions in the SWIZZ voice persona using AI-powered content generation.

## Usage
```
/social:write <action> [options]
```

## Arguments
$ARGUMENTS

## Actions
- `generate` - Generate a single post for a platform
- `thread` - Generate a multi-post thread
- `caption` - Generate a media caption
- `status` - Show agent status and configuration

## Options
- `--topic <text>` - Content topic (required for generate/thread/caption)
- `--platform <name>` - Target platform (default: instagram)
- `--post-type <type>` - Post type: announcement, resource_share, casual, business, promo, hype (default: casual)
- `--persona <mode>` - Persona: professional (Swizzimatic) or personal (BigSwizzi) (default: professional)
- `--num-posts <n>` - Thread post count (default: 3)
- `--dry-run` - Preview without posting

## Platforms
linkedin, tiktok, instagram, youtube, twitter, facebook, pinterest, threads, bluesky, reddit, snapchat, telegram, googlebusiness

## Examples

```bash
# Generate a casual Instagram post
/social:write generate -Topic "New product launch" -Platform instagram

# Generate a 5-post Twitter thread
/social:write thread -Topic "AI workflow tips" -Platform twitter -NumPosts 5

# Generate a promo post in BigSwizzi voice
/social:write generate -Topic "Flash sale" -PostType promo -Persona personal

# Generate a media caption
/social:write caption -Topic "Studio flat lay photo" -Platform instagram

# Check agent status
/social:write status
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.agents.writing_agent --action generate --topic "topic" --platform instagram
```
