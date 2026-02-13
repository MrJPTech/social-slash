# System Patterns & Conventions

**Project**: social-slash
**Last Updated**: 2026-02-12 (Session 18)

## Code Organization

### Directory Structure
```
social-slash/
├── .claude/commands/
│   ├── posting/                # Posting slash commands (post, multi-post, schedule)
│   ├── engagement/             # Engagement slash commands (comment-agent, dm-agent, bot-manage)
│   ├── agents/                 # Agent slash commands (write, research, media)
│   └── utility/                # Utility slash commands (accounts, analytics, status)
├── lib/                        # Python package source
│   ├── posting/                # Core posting logic
│   ├── api_clients/            # External API wrappers (late_client)
│   ├── ai/                     # AI clients (gemini, anthropic, imagen)
│   ├── tools/                  # Tools database
│   ├── agents/                 # Content + engagement automation agents
│   │   ├── base_agent.py       # Abstract base with state machine
│   │   ├── writing_agent.py    # SWIZZ/CEO voice post generation
│   │   ├── research_agent.py   # Content research and hashtags
│   │   ├── media_agent.py      # Media captioning agent
│   │   ├── image_agent.py      # AI image generation agent (Imagen 3)
│   │   ├── comment_agent.py    # Comment monitoring/reply agent
│   │   ├── dm_agent.py         # DM monitoring/reply agent
│   │   └── bot_manager.py      # Bot account management
│   ├── persona/                # Multi-mode voice persona system
│   │   ├── swizz_persona.py    # BasePersona, Swizzimatic, BigSwizzi, JordanWard, SwizzPersona router
│   │   └── instagram_parser.py # Instagram export data extractor
│   ├── engagement/             # Engagement client and response generator
│   │   ├── late_engagement_client.py  # Unified inbox client
│   │   └── response_generator.py      # AI response generation
│   ├── mcp/                    # MCP server for Claude Desktop/Claude.ai
│   │   ├── server.py           # FastMCP server with 24 tools + OAuth
│   │   ├── _client_helpers.py  # Late client factory, stdout suppressor
│   │   └── __main__.py         # Entry point: python -m lib.mcp
│   ├── storage/                # Database and models
│   │   ├── database.py         # SQLite wrapper
│   │   └── models.py           # Data models
│   └── webhooks/               # Webhook handler
│       └── late_webhook.py     # FastAPI webhook server
├── data/                       # JSON configuration
│   ├── platform_templates.json # Platform-specific settings
│   ├── engagement_config.json  # Agent configuration
│   └── response_templates.json # Response templates
├── tests/                      # Unit tests (239 passing)
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

## Gemini SDK Pattern (google-genai v1.63.0)

Migrated from deprecated `google-generativeai` to `google-genai`:

```python
# New pattern (google-genai)
from google import genai
client = genai.Client(api_key=api_key)
response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
text = response.text

# Old pattern (deprecated google-generativeai)
# import google.generativeai as genai
# genai.configure(api_key=api_key)
# model = genai.GenerativeModel('gemini-2.0-flash')
# response = model.generate_content(prompt)
```

**Key differences:**
- Client-based init vs module-level `configure()`
- Explicit `model=` and `contents=` params in generate call
- `response.text` unchanged between SDKs

## Imagen SDK Pattern (google-genai v1.63.0)

Image generation via same `google-genai` SDK as text, different API:

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=api_key)
response = client.models.generate_images(
    model="imagen-3.0-generate-002",
    prompt=prompt,
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="1:1",
        safety_filter_level="BLOCK_LOW_AND_ABOVE",
        person_generation="ALLOW_ADULT",
    )
)
for img in response.generated_images:
    image_bytes = img.image.image_bytes  # raw bytes
    # or img.image.save('output.png')   # PIL save
```

**Key differences from text generation:**
- `generate_images()` vs `generate_content()`
- Returns `generated_images` list with `.image.image_bytes`
- Requires `types.GenerateImagesConfig` for options
- Aspect ratios: 1:1, 3:4, 4:3, 9:16, 16:9
- Requires `Pillow` for image handling

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

## Persona Pattern

Voice/speech style system for content generation agents:

```python
from abc import ABC, abstractmethod
import re, random

class BasePersona(ABC):
    SHARED_VOCAB = {"going to": "gonna", "want to": "wanna", "got to": "gotta"}

    def apply_vocab_transform(self, text: str) -> str:
        """Post-process AI output with persona-specific vocabulary."""
        all_vocab = {**self.SHARED_VOCAB, **self.VOCAB_MAP}
        for original, replacement in all_vocab.items():
            text = re.sub(re.escape(original), replacement, text, flags=re.IGNORECASE)
        return text

    @abstractmethod
    def get_system_prompt(self, context_type: str) -> str: pass

    @abstractmethod
    def get_response_length_guide(self, context_type: str) -> tuple: pass

class SwizzPersona:
    """Router/factory that switches between professional and personal modes."""
    def __init__(self, mode="professional"):
        self._professional = SwizzimaticPersona()
        self._personal = BigSwizziPersona()
        self.set_mode(mode)

    def set_mode(self, mode): ...
    def get_active_persona(self) -> BasePersona: ...
    def get_platform_config(self, platform) -> dict: ...
```

**Key patterns:**
- Voice is a STYLE LAYER — captures how to speak, not what to talk about
- Content topics come from the caller/user, persona shapes the delivery
- Dual approach: system prompts guide AI + vocab post-processing ensures consistency
- Few-shot examples for voice consistency (Instagram data for SWIZZ, content strategy doc for CEO)
- Platform configs enforce character limits (tiktok: 150, twitter: 280, instagram: 2200)
- Three modes: professional (SwizzimaticPersona), personal (BigSwizziPersona), ceo (JordanWardPersona)
- CEO mode has 7 structured content formats with `get_content_format_prompt()` for structured prompts
- CEO vocab transforms are polished/formal (no SHARED_VOCAB slang contractions)
- `SwizzPersona` router delegates to the active persona via `_resolve_persona()` helper
- `determine_response_type()` routes CEO keywords (myth, tips, case study, etc.) to content formats

## Content Agent Pattern

Agents that generate content using persona voice:

```python
class WritingAgent(BaseAgent):
    def __init__(self, config, persona=None, db=None, ai_provider="gemini"):
        super().__init__(config, ai_provider, name="WritingAgent")
        self.persona = persona or SwizzPersona(mode=config.get('persona_mode', 'professional'))

    def generate_post(self, topic, platform, post_type, persona_mode="professional"):
        active = self.persona.get_active_persona()
        system_prompt = active.get_system_prompt(post_type)
        length_guide = active.get_response_length_guide(post_type)
        # Build prompt with system_prompt + few_shot_examples + topic
        raw = self.response_generator._generate(prompt, max_length=max_chars)
        content = active.apply_vocab_transform(raw)  # Post-process vocabulary
        return {"content": content, "platform": platform, ...}
```

**Key patterns:**
- All content agents extend BaseAgent with SwizzPersona integration
- Persona mode switchable via `--persona professional|personal|ceo` CLI flag
- AI generation → vocab post-processing → platform char limit enforcement
- CEO format integration: checks `get_content_format_prompt()` before using generic prompt
- CLI entry points via argparse with action/topic/platform/persona args

---
**Usage**: Update when establishing new patterns or conventions
