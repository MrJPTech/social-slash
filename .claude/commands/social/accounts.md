# /social:accounts - Account Manager

List and manage connected social media accounts via Late SDK.

## Usage
```
/social:accounts [action] [options]
```

## Arguments
$ARGUMENTS

## Actions
- `list` - Show all connected accounts (default)
- `refresh` - Clear cache and re-fetch from Late API

## Options
- `--platform <name>` - Filter by platform name
- `--json` - Output as JSON

## Examples

```bash
# List all connected accounts
/social:accounts list

# Filter by platform
/social:accounts list -Platform instagram

# Refresh account cache
/social:accounts refresh

# JSON output for scripting
/social:accounts list --json
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.utility.accounts --action list
```
