# /social:comment-agent - Comment Reply Agent

Automated comment monitoring and AI-powered reply generation for social media posts.

## Usage
```
/social:comment-agent [action] [options]
```

## Arguments
$ARGUMENTS

## Actions
- `start` - Start monitoring comments on specified platforms
- `stop` - Stop the comment monitoring agent
- `status` - Show current agent status (default)
- `review` - List pending comment replies for human review
- `approve` - Approve and send a pending reply
- `reject` - Reject a pending reply

## Options
- `--platforms <list>` - Target platforms: instagram, reddit, youtube, facebook, linkedin, bluesky, tiktok, all (default: instagram, reddit)
- `--auto-approve` - Auto-send replies without human review
- `--poll-interval <seconds>` - Check interval (default: 60)
- `--dry-run` - Simulate without sending replies
- `--review-id <id>` - Review ID for approve/reject actions
- `--json` - Output as JSON

## Examples

```bash
# Start monitoring Instagram and Reddit
/social:comment-agent start -Platforms instagram,reddit

# Start with auto-approve (no human review)
/social:comment-agent start -Platforms instagram -AutoApprove

# Dry run test
/social:comment-agent start -Platforms instagram -DryRun

# Review pending replies
/social:comment-agent review

# Approve a specific reply
/social:comment-agent approve -ReviewId 123

# Check agent status
/social:comment-agent status
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\agents\comment_agent.py --action start --platforms instagram,reddit
```
