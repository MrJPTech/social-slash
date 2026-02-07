# /social:analytics - Post Analytics

View recent post activity, check post status, and see engagement metrics.

## Usage
```
/social:analytics [action] [options]
```

## Arguments
$ARGUMENTS

## Actions
- `recent` - Show recent posts with status (default)
- `post` - Show detailed status and analytics for a single post

## Options
- `--post-id <id>` - Post ID for detail view (required for `post` action)
- `--platform <name>` - Filter recent posts by platform
- `--limit <n>` - Number of recent posts (default: 10)
- `--json` - Output as JSON

## Examples

```bash
# Show recent posts
/social:analytics recent

# Show 5 most recent Twitter posts
/social:analytics recent -Platform twitter -Limit 5

# Get details for a specific post
/social:analytics post -PostId "abc123"

# JSON output
/social:analytics recent --json
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.utility.analytics --action recent --limit 10
```
