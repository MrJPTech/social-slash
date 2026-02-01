# Social Slash

Social media automation slash commands for Claude Code.

## Features

- **13 Platform Support**: LinkedIn, TikTok, Instagram, YouTube, Twitter, Facebook, Pinterest, Threads, Bluesky, Reddit, Snapchat, Telegram, Google Business
- **AI Enhancement**: Optional content optimization via Gemini or Claude
- **Multi-Platform**: Post to multiple platforms simultaneously
- **Scheduling**: Schedule posts for future publishing
- **Dry Run**: Test posts without publishing

## Installation

1. Clone this repository:
   ```bash
   git clone git@github.com:MrJPTech/social-slash.git
   cd social-slash
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment template:
   ```bash
   cp .env.example .env.local
   ```

4. Add your API keys to `.env.local`

5. Add `.claude/commands/` to your Claude Code commands path

## Commands

| Command | Description |
|---------|-------------|
| `/social:post` | Post to single or multiple platforms |
| `/social:multi-post` | Quick multi-platform distribution |
| `/social:schedule` | Schedule future posts |

## Quick Start

### Post to LinkedIn
```powershell
/social:post -Content "Lock in developers" -Platforms linkedin
```

### Multi-platform with AI enhancement
```powershell
/social:post -Content "New content!" -Platforms linkedin,tiktok -Enhance
```

### Dry run (test without posting)
```powershell
/social:post -Content "Test" -Platforms linkedin -DryRun
```

### Schedule a post
```powershell
/social:schedule -Content "Morning post" -Platforms linkedin -At "tomorrow 9am"
```

### Use Anthropic instead of Gemini
```powershell
/social:post -Content "Quality content" -Platforms linkedin -Enhance -AIProvider anthropic
```

## Configuration

### Required Environment Variables

```env
# Late API (required)
LATE_API_KEY=your_late_api_key

# AI Enhancement (optional)
GOOGLE_API_KEY=your_google_api_key      # For Gemini
ANTHROPIC_API_KEY=your_anthropic_key    # For Claude
```

### Getting API Keys

- **Late API**: Sign up at [getlate.dev](https://getlate.dev)
- **Gemini API**: Get at [Google AI Studio](https://aistudio.google.com)
- **Anthropic API**: Get at [console.anthropic.com](https://console.anthropic.com)

## Supported Platforms

| Platform | Char Limit | Media Types |
|----------|------------|-------------|
| LinkedIn | 3000 | text, image, video, document |
| TikTok | 2200 | video |
| Instagram | 2200 | image, video, carousel, reel |
| YouTube | 5000 (desc) | video, short, live |
| Twitter/X | 280 | text, image, video, poll |
| Facebook | 63206 | text, image, video, link |
| Pinterest | 500 (desc) | image, video, idea_pin |
| Threads | 500 | text, image, video |
| Bluesky | 300 | text, image |
| Reddit | 40000 | text, image, video, link |
| Snapchat | 60s video | image, video, story |
| Telegram | 4096 | text, image, video, document |
| Google Business | 1500 | text, image, offer, event |

## Project Structure

```
social-slash/
├── .claude/commands/
│   └── posting/
│       ├── post.ps1           # Main post command
│       ├── multi-post.ps1     # Multi-platform helper
│       └── schedule.ps1       # Scheduling helper
├── lib/
│   ├── api_clients/
│   │   └── late_client.py     # Late SDK wrapper
│   ├── ai/
│   │   ├── gemini_client.py   # Gemini AI
│   │   └── anthropic_client.py # Claude AI
│   └── posting/
│       └── poster.py          # Core posting logic
├── data/
│   ├── platform_templates.json # Platform configs
│   └── queue_config.json      # Queue settings
├── .env.example
├── requirements.txt
└── README.md
```

## Python CLI Usage

You can also use the Python backend directly:

```bash
# Basic post
python lib/posting/poster.py --content "Hello world" --platforms linkedin

# Multi-platform with AI
python lib/posting/poster.py --content "Hello" --platforms linkedin,twitter --enhance

# Dry run with JSON output
python lib/posting/poster.py --content "Test" --platforms linkedin --dry-run --json
```

## Development

### Install dev dependencies
```bash
pip install -r requirements.txt
```

### Run tests
```bash
pytest tests/
```

### Code formatting
```bash
black lib/
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- Issues: [GitHub Issues](https://github.com/MrJPTech/social-slash/issues)
- Documentation: [docs/](./docs/)
