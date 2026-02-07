# /social:dm-agent - DM Reply Agent

Automated DM/conversation monitoring and AI-powered reply generation for social media platforms.

## Usage
```
/social:dm-agent [action] [options]
```

## Arguments
$ARGUMENTS

## Actions
- `start` - Start monitoring DMs on specified platforms
- `stop` - Stop the DM monitoring agent
- `status` - Show current agent status (default)
- `review` - List pending DM replies for human review
- `approve` - Approve and send a pending reply
- `reject` - Reject a pending reply

## Options
- `--platforms <list>` - Target platforms: instagram, telegram, reddit, facebook, bluesky, all (default: instagram, telegram, reddit)
- `--auto-reply` - Auto-send replies without human review
- `--poll-interval <seconds>` - Check interval (default: 30)
- `--response-delay <seconds>` - Delay before sending reply (default: 30)
- `--dry-run` - Simulate without sending replies
- `--review-id <id>` - Review ID for approve/reject actions
- `--json` - Output as JSON

## Examples

```bash
# Start monitoring Instagram and Telegram DMs
/social:dm-agent start -Platforms instagram,telegram

# Start with auto-reply (no human review)
/social:dm-agent start -Platforms instagram -AutoReply

# Dry run test
/social:dm-agent start -Platforms instagram -DryRun

# Custom polling and response delay
/social:dm-agent start -Platforms reddit -PollInterval 60 -ResponseDelay 45

# Review pending replies
/social:dm-agent review

# Approve a specific reply
/social:dm-agent approve -ReviewId 123

# Check agent status
/social:dm-agent status
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\agents\dm_agent.py --action start --platforms instagram,telegram
```
