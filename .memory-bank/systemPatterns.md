# System Patterns & Conventions

**Project**: social-slash
**Last Updated**: 2026-02-03

## Code Organization

### Directory Structure
```
social-slash/
├── .claude/commands/
│   ├── posting/                # Posting slash commands (post, multi-post, schedule)
│   └── engagement/             # Engagement slash commands (comment-agent, dm-agent, bot-manage)
├── lib/                        # Python package source
│   ├── posting/                # Core posting logic
│   ├── api_clients/            # External API wrappers (late_client)
│   ├── ai/                     # AI enhancement clients (gemini, anthropic)
│   ├── tools/                  # Tools database
│   ├── agents/                 # Engagement automation agents
│   │   ├── base_agent.py       # Abstract base with state machine
│   │   ├── comment_agent.py    # Comment monitoring/reply agent
│   │   ├── dm_agent.py         # DM monitoring/reply agent
│   │   └── bot_manager.py      # Bot account management
│   ├── engagement/             # Engagement client and response generator
│   │   ├── late_engagement_client.py  # Unified inbox client
│   │   └── response_generator.py      # AI response generation
│   ├── storage/                # Database and models
│   │   ├── database.py         # SQLite wrapper
│   │   └── models.py           # Data models
│   └── webhooks/               # Webhook handler
│       └── late_webhook.py     # FastAPI webhook server
├── data/                       # JSON configuration
│   ├── platform_templates.json # Platform-specific settings
│   ├── engagement_config.json  # Agent configuration
│   └── response_templates.json # Response templates
├── tests/                      # Unit tests
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

Established patterns for unit testing:

```python
import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os

class TestModuleName:
    """Test suite for module_name."""

    @pytest.fixture
    def mock_client(self):
        """Create mock API client."""
        with patch('module.Client') as mock:
            yield mock

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database for testing."""
        db_path = tmp_path / "test.db"
        yield str(db_path)

    def test_method_success(self, mock_client):
        """Test successful operation."""
        mock_client.return_value.method.return_value = {"data": "test"}
        # ... assertions

    def test_method_error(self, mock_client):
        """Test error handling."""
        mock_client.return_value.method.side_effect = Exception("API error")
        # ... assertions
```

**Key patterns:**
- Use `pytest` as test runner
- Mock external APIs with `unittest.mock`
- Use `pytest.fixture` for setup/teardown
- Use `tmp_path` fixture for temporary files
- Test both success and error paths
- Name tests descriptively: `test_<method>_<scenario>`

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

## Agent Pattern

State machine pattern for automation agents:

```python
from enum import Enum
from abc import ABC, abstractmethod

class AgentState(Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    PROCESSING = "processing"
    GENERATING = "generating"
    REVIEWING = "reviewing"      # Human-in-the-loop
    RESPONDING = "responding"
    ERROR = "error"

class BaseAgent(ABC):
    def __init__(self, config: dict):
        self.state = AgentState.IDLE
        self.config = config

    def transition(self, new_state: AgentState):
        print(f"[{self.__class__.__name__}] {self.state.value} → {new_state.value}")
        self.state = new_state

    @abstractmethod
    async def start(self): pass

    @abstractmethod
    async def stop(self): pass

    @abstractmethod
    async def process_item(self, item): pass
```

**Key patterns:**
- Explicit state transitions for visibility
- REVIEWING state for human approval
- ERROR state with recovery path
- Async methods for non-blocking I/O

## Database Pattern

SQLite storage pattern:

```python
import sqlite3
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str = "data/app.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS ...''')
```

**Key patterns:**
- Context manager for connection handling
- Auto-commit on success
- Row factory for dict-like access
- Schema initialization in `_init_db()`

## Import Pattern

Use absolute imports throughout:

```python
# ✅ Correct (absolute imports)
from agents.base_agent import BaseAgent, AgentState
from storage.database import EngagementDatabase
from engagement.late_engagement_client import LateEngagementClient

# ❌ Avoid (relative imports)
from ..engagement.late_engagement_client import LateEngagementClient
from .base_agent import BaseAgent
```

**Rationale:**
- Works for both package imports and standalone execution
- Avoids "beyond top-level package" errors
- Consistent import style across codebase

## Webhook Pattern

FastAPI webhook handler pattern:

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post("/webhooks/service")
async def handle_webhook(request: Request):
    signature = request.headers.get("X-Signature")
    body = await request.body()

    if not verify_signature(body, signature or "", SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    # Process event...
    return {"status": "ok"}
```

**Key patterns:**
- HMAC-SHA256 signature verification
- Async request handling
- Return 401 for invalid signatures
- Return simple status response

---
**Usage**: Update when establishing new patterns or conventions
