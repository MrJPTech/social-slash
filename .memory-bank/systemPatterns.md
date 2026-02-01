# System Patterns & Conventions

**Project**: social-slash
**Last Updated**: 2026-02-01

## Code Organization

### Directory Structure
```
social-slash/
├── .claude/commands/posting/   # PowerShell slash commands
├── lib/                        # Python package source
│   ├── posting/                # Core posting logic
│   ├── api_clients/            # External API wrappers
│   ├── ai/                     # AI enhancement clients
│   └── tools/                  # Tools database
├── data/                       # JSON configuration
├── tests/                      # Test files (TBD)
└── .memory-bank/               # This directory
```

## Naming Conventions

### Files
- Python: snake_case (`late_client.py`, `gemini_client.py`)
- PowerShell: kebab-case (`multi-post.ps1`)
- JSON: snake_case (`platform_templates.json`)

### Python
- Classes: PascalCase (`LateDistributionClient`, `Poster`)
- Functions/Methods: snake_case (`post_to_platform`, `enhance_content`)
- Constants: UPPER_SNAKE_CASE (`SUPPORTED_PLATFORMS`, `MODEL`)
- Private methods: underscore prefix (`_init_ai_client`, `_account_cache`)

## API Client Pattern

Standard structure for all API clients:

```python
class ClientName:
    """Docstring with purpose and usage."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('API_KEY_NAME')
        if not self.api_key:
            raise ValueError("API key required...")

        # Initialize SDK/client
        self.client = SomeSDK(api_key=self.api_key)
```

**Key patterns:**
- Accept API key as parameter OR from environment
- Raise ValueError early if key missing
- Cache where beneficial (`_account_cache`)

## Console Output Pattern

Use bracketed prefixes for all console output:

```python
print("[SUCCESS] Operation completed")
print("[INFO] Processing...")
print("[WARNING] Non-critical issue")
print("[ERROR] Something failed")
```

## PowerShell Command Pattern

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$Content,

    [ValidateSet("linkedin", "twitter", ...)]
    [string[]]$Platforms,

    [switch]$DryRun
)

# Build args, call Python, handle exit code
& $pythonExe @args
exit $LASTEXITCODE
```

**Key patterns:**
- Use `ValidateSet` for platform validation
- Propagate exit codes from Python
- Find Python in project venv first, then system

## Error Handling

- Raise exceptions early for validation errors
- Try/except around API calls with meaningful error messages
- Return dictionaries with `status` key for result handling

```python
try:
    result = api.operation()
    return {"status": "success", "data": result}
except Exception as e:
    print(f"[ERROR] Operation failed: {e}")
    return {"status": "error", "error": str(e)}
```

## Configuration Pattern

JSON files in `data/` for configuration:

```json
{
  "platforms": {
    "linkedin": {
      "char_limit": 3000,
      "optimal_length": 1300,
      "best_times": ["08:00", "12:00"],
      ...
    }
  }
}
```

## Testing Patterns

(To be established)
- pytest for test runner
- Mock external APIs
- Test dry-run mode for integration tests

## Type Hints

Use type hints throughout:

```python
from typing import Dict, List, Optional, Any

def method(
    content: str,
    platforms: List[str],
    enhance: bool = False
) -> Dict[str, Any]:
```

---
**Usage**: Update when establishing new patterns or conventions
