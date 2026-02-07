# /social:media - SWIZZ Voice Media Agent

Generate reel captions, story text, carousel captions, alt text, and media format suggestions in SWIZZ voice.

## Usage
```
/social:media <action> [options]
```

## Arguments
$ARGUMENTS

## Actions
- `caption` - Generate a reel/video caption
- `story` - Generate story overlay text
- `carousel` - Generate carousel slide captions
- `alt` - Generate accessible alt text
- `suggest` - Get media format recommendation
- `status` - Show agent status

## Options
- `--description <text>` - Media description or content idea (required for most actions)
- `--context <text>` - Additional context for caption generation
- `--platform <name>` - Target platform (default: instagram)
- `--persona <mode>` - Persona: professional or personal (default: professional)
- `--slides <texts>` - Slide descriptions for carousel (space-separated)

## Examples

```bash
# Generate a reel caption
/social:media caption -Description "Product flat lay photo" -Platform instagram

# Generate story text in BigSwizzi voice
/social:media story -Description "Behind the scenes at the studio" -Persona personal

# Generate carousel captions
/social:media carousel -Slides "Slide 1 intro" "Slide 2 details" "Slide 3 CTA"

# Generate alt text
/social:media alt -Description "Team photo at conference booth"

# Get format recommendation
/social:media suggest -Description "Tutorial on API integration" -Platform tiktok

# Check agent status
/social:media status
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.agents.media_agent --action caption --description "description" --platform instagram
```
