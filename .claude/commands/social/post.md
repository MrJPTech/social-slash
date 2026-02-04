# /social:post - Social Media Posting Command

Post content to social media platforms via Late API with optional AI enhancement and platform-specific options.

## Usage
```
/social:post <content> [options]
```

## Arguments
$ARGUMENTS

## Core Options
- `--platforms <list>` - Target platforms (comma-separated): linkedin, twitter, instagram, tiktok, facebook, youtube, threads, reddit, bluesky, pinterest, snapchat, telegram, googlebusiness
- `--enhance` - Enable AI content enhancement (Gemini)
- `--ai-provider <gemini|anthropic>` - Choose AI provider (default: gemini)
- `--media <urls>` - Attach media URLs (comma-separated)
- `--schedule <datetime>` - Schedule post for later (ISO 8601 format)
- `--dry-run` - Simulate without posting
- `--json` - Output results as JSON

## Platform-Specific Options

### Reddit
- `-RedditTitle <text>` - Post title (auto-generated from first line of content if not provided)
- **Note**: Subreddit is configured at account connection level, not per-post

### Instagram
- `-IgType <story|post|reel>` - Content type (default: auto-detect from media)
- `-IgFirstComment <text>` - First comment to post after publishing
- `-IgCollaborators <users>` - Collaborator usernames (comma-separated, max 3)
- `-IgNoFeed` - For reels, don't show on main feed (reels tab only)

### LinkedIn
- `-LiFirstComment <text>` - First comment to post after publishing
- `-LiNoLinkPreview` - Disable link preview card

### Threads
- `-ThreadsAutoThread` - Auto-break long content into threaded replies
- `-ThreadsNumber` - Add numbering to thread posts (1/n, 2/n...)

### Twitter/X
- `-TwitterThread` - Auto-break long content into tweet thread

### Advanced
- `-PlatformOptions <json>` - Raw JSON string with platform-specific options

## Examples

### Basic Posting
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

### Instagram Examples
```bash
# Instagram story
/social:post "Behind the scenes!" -Platforms instagram -IgType story

# Instagram reel with first comment
/social:post "New tutorial!" -Platforms instagram -IgFirstComment "Links in bio!"

# Instagram post with collaborators
/social:post "Collab time!" -Platforms instagram -IgCollaborators "user1,user2"
```

### LinkedIn Examples
```bash
# LinkedIn with first comment
/social:post "Big announcement!" -Platforms linkedin -LiFirstComment "DM for details"

# LinkedIn without link preview
/social:post "Check https://example.com" -Platforms linkedin -LiNoLinkPreview
```

### Reddit Examples
```bash
# Reddit post (title auto-generated from first line)
/social:post "My Awesome Title`n`nPost body content here..." -Platforms reddit

# Reddit post with explicit title
/social:post "Post body content..." -Platforms reddit -RedditTitle "My Custom Title"
```

### Threads Examples
```bash
# Threads auto-thread
/social:post "Long content that will be auto-split into multiple posts..." -Platforms threads -ThreadsAutoThread

# Threads with numbering
/social:post "Thread content..." -Platforms threads -ThreadsAutoThread -ThreadsNumber
```

### Multi-Platform with Mixed Options
```bash
# Cross-platform with platform-specific settings
/social:post "Cross-platform content!" -Platforms linkedin,instagram,twitter -LiFirstComment "More info..." -IgType story
```

## Execution
Run the Python backend directly:
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\posting\poster.py --content "<content>" --platforms <platforms> [options]
```

## Connected Accounts
- Twitter/X: @mrjptech
- LinkedIn: PRSM TECH INCORPORATED
- Instagram: @mrjptech_ (Business account)
- TikTok: @mrjptech
- Facebook: Prsm Tech Inc.
- YouTube: @mrjptechy
- Threads: @mrjptech_
- Reddit: MrJPTech
- Google Business: PRSM Tech Incorporated

## Platform Notes

### Reddit Limitations
- Subreddit cannot be changed per-post (configured at account connection level)
- Title is required (auto-generated from first line if not specified)
- Post type (text/link/image) auto-detected from content and media

### Instagram Requirements
- Requires Instagram Business account (not personal/creator)
- Reels are auto-detected from video media
- `story` content type for 24-hour ephemeral posts

### LinkedIn OAuth Scopes
- Personal profiles: `w_member_social`
- Company pages: `w_organization_social` + organization URN
