# /social:bot-manage - Bot Account Manager

Configure and manage dedicated bot accounts for automated social media engagement.

## Usage
```
/social:bot-manage [action] [options]
```

## Arguments
$ARGUMENTS

## Actions
- `list` - Show all configured bot accounts (default)
- `available` - List Late accounts available to use as bots
- `register` - Register a Late account as a bot
- `deactivate` - Deactivate a bot account
- `activate` - Reactivate a deactivated bot
- `set-primary` - Set an account as the primary bot for its platform
- `stats` - Show bot activity statistics

## Options
- `--platform <name>` - Platform filter or target
- `--account-id <id>` - Late account ID for register/update actions
- `--name <text>` - Bot display name
- `--primary` - Set as primary bot for platform (used with register)
- `--style <mode>` - Response style: professional, friendly, casual, enthusiastic, supportive (default: professional)
- `--max-replies <n>` - Maximum replies per hour (default: 60)
- `--cooldown <seconds>` - Cooldown between replies in seconds (default: 300)

## Examples

```bash
# List all configured bot accounts
/social:bot-manage list

# Show available Late accounts for bot registration
/social:bot-manage available

# Register an Instagram bot as primary
/social:bot-manage register -Platform instagram -AccountId abc123 -Primary

# Register with custom style and limits
/social:bot-manage register -Platform reddit -AccountId def456 -Name "PRSM Reddit" -Style friendly -MaxReplies 30

# Deactivate a bot
/social:bot-manage deactivate -Platform instagram -AccountId abc123

# Set a different bot as primary
/social:bot-manage set-primary -Platform instagram -AccountId xyz789

# View bot activity stats
/social:bot-manage stats
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe lib\agents\bot_manager.py --action list
```
