# /social:status - Project Status Dashboard

Aggregated view of connected accounts, bot accounts, and API health for the social-slash project.

## Usage
```
/social:status [section] [options]
```

## Arguments
$ARGUMENTS

## Sections
- `all` - Full status dashboard (default)
- `accounts` - Connected Late SDK accounts only
- `bots` - Bot account configuration only
- `api` - API health check only

## Options
- `--json` - Output as JSON

## Examples

```bash
# Full status dashboard
/social:status

# Check API health only
/social:status api

# Get accounts as JSON
/social:status accounts --json
```

## Execution
```powershell
cd J:\PRSMTECH\PRSM-PROPRIETARY\INTERNAL-PROJECTS\social-slash
.\.venv\Scripts\python.exe -m lib.utility.status --section all
```
