# /social:imagine - AI Image Generation Agent

Generate images for social media using Google Imagen 3 with persona-aware prompt enhancement.

## Usage
```
/social:imagine <action> [options]
```

## Arguments
$ARGUMENTS

## Actions
- `graphic` - Generate a social post graphic (platform-optimized aspect ratio)
- `thumbnail` - Generate a video/blog thumbnail (16:9)
- `carousel` - Generate images for each carousel slide
- `story` - Generate a story/reel cover image (9:16)
- `overlay` - Generate a background for text overlay / quote card
- `art` - Generate freeform AI art (custom aspect ratio)
- `presets` - List available platform aspect ratio presets
- `status` - Show agent status

## Options
- `--prompt <text>` - Image description (required for most actions)
- `--platform <name>` - Target platform (default: instagram)
- `--style <style>` - Visual style: modern, minimal, bold, artistic, photorealistic, flat, gradient, neon
- `--persona <mode>` - Persona: professional, personal, ceo (default: professional)
- `--aspect-ratio <ratio>` - Override auto-detect: 1:1, 3:4, 4:3, 9:16, 16:9
- `--num-images <n>` - Number of variants, 1-4 (default: 1)
- `--slides <texts>` - Slide descriptions for carousel (space-separated)
- `--upload` - Upload to Late SDK and return cloud URLs
- `--dry-run` - Show enhanced prompt without generating

## Examples

```bash
# Generate a LinkedIn post graphic
/social:imagine graphic -Prompt "Modern tech startup workspace" -Platform linkedin

# Generate a YouTube thumbnail
/social:imagine thumbnail -Prompt "10 Python Tips You Need" -Platform youtube

# Generate carousel images (3 slides)
/social:imagine carousel -Slides "Intro to AI" "Key Benefits" "Get Started" -Platform instagram

# Story cover in personal voice
/social:imagine story -Prompt "Behind the scenes at PRSMTECH" -Persona personal

# CEO-styled graphic
/social:imagine graphic -Prompt "Data-driven leadership" -Persona ceo -Platform linkedin

# Freeform AI art
/social:imagine art -Prompt "Abstract neural network visualization" -Style neon -AspectRatio 16:9

# Preview prompt without generating
/social:imagine graphic -Prompt "Team collaboration" -DryRun

# Generate and upload to Late SDK
/social:imagine graphic -Prompt "Product launch" -Platform twitter -Upload

# List all platform presets
/social:imagine presets
```

## Persona Visual Styles
- **professional** - Clean, corporate, modern color palette, polished
- **personal** - Vibrant, bold, energetic, street style, dynamic colors
- **ceo** - Authoritative, executive, premium, sophisticated, dark tones

## Platform Aspect Ratios (Auto-detected)
| Platform | Post | Story/Reel | Thumbnail |
|----------|------|------------|-----------|
| Instagram | 1:1 | 9:16 | - |
| Twitter | 16:9 | - | - |
| LinkedIn | 4:3 | - | 16:9 |
| YouTube | - | - | 16:9 |
| TikTok | 9:16 | 9:16 | - |
| Facebook | 4:3 | 9:16 | 16:9 |
| Pinterest | 3:4 | - | - |

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.agents.image_agent --action graphic --prompt "description" --platform instagram
```
