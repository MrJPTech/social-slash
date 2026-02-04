# Technical Decision Log

**Project**: social-slash

---

## 2026-01-31 - Late SDK as Primary Backend

**Context**: Need a reliable way to post to multiple social media platforms without managing individual API integrations.

**Decision**: Use Late SDK (late-sdk) as the primary distribution backend.

**Rationale**:
- Late handles OAuth and API complexity for 13+ platforms
- Single API key simplifies credential management
- Supports scheduling natively
- Active development and documentation at getlate.dev

**Alternatives Considered**:
- Individual platform SDKs (Tweepy, instagrapi, etc.) - too much complexity
- Buffer/Hootsuite APIs - commercial pricing
- Custom scraping - fragile and ToS issues

**Impact**:
- Single dependency for all platform posting
- Requires Late API subscription
- Simpler codebase to maintain

---

## 2026-01-31 - PowerShell for Slash Commands

**Context**: Claude Code slash commands can use PowerShell or shell scripts.

**Decision**: Use PowerShell (.ps1) for command wrappers.

**Rationale**:
- Windows-first environment at PRSMTECH
- Better parameter handling with `param()` blocks
- ValidateSet for platform validation
- Cross-platform with PowerShell Core

**Alternatives Considered**:
- Bash scripts - less Windows-friendly
- Direct Python invocation - less Claude Code integration

**Impact**:
- Clean command interface with proper parameter validation
- Exit code propagation for error handling

---

## 2026-01-31 - Gemini as Default AI Provider

**Context**: AI enhancement is optional but valuable for content optimization.

**Decision**: Use Google Gemini 2.0 Flash as the default AI provider, with Anthropic as alternative.

**Rationale**:
- Gemini 2.0 Flash is fast and cost-effective
- JSON output works well for structured enhancement
- Anthropic as fallback for users with existing Claude access

**Alternatives Considered**:
- Anthropic-only - limits user choice
- OpenAI - additional API to manage
- No AI - reduces value proposition

**Impact**:
- Optional dependency (google-generativeai)
- Lazy loading avoids import errors when not installed

---

## 2026-01-31 - Lazy Loading for AI Clients

**Context**: AI packages are optional dependencies that may not be installed.

**Decision**: Lazy-load AI clients in `Poster._init_ai_client()` rather than at module import.

**Rationale**:
- Avoids ImportError when AI packages not installed
- Users can run basic posting without AI dependencies
- Clean fallback with warning message

**Impact**:
- `[ai]` extras in setup.py for optional install
- Runtime check before AI usage

---

## 2026-02-01 - Late SDK Response Object Handling

**Context**: Late SDK returns Pydantic response objects, not plain Python dicts/lists.

**Decision**: Use `getattr()` and attribute access for all Late SDK responses.

**Rationale**:
- `accounts.list()` returns `AccountsListResponse` with `.accounts` attribute
- `SocialAccount` objects use `.field_id` for ID and `.platform` for platform name
- `posts.create()` requires `platforms` as list of dicts: `[{"platform": "twitter", "accountId": "..."}]`

**Impact**:
- More robust code that handles SDK object types
- Cache account IDs in `_account_cache` for performance
- Fixed production posting functionality

---

## 2026-02-01 - Claude Code Slash Command Format

**Context**: Need to create Claude Code slash command configurations.

**Decision**: Use markdown files in `.claude/commands/social/` directory.

**Rationale**:
- Claude Code supports markdown command definitions
- Cleaner than PowerShell for documentation-style commands
- Allows $ARGUMENTS placeholder for user input
- Better integration with Claude Code CLI

**Impact**:
- Three command configs: post.md, multi-post.md, schedule.md
- Commands available as `/social:post`, `/social:multi-post`, `/social:schedule`

---

## 2026-02-03 - Late API Unified Inbox for Engagement

**Context**: Need engagement automation (comment replies, DM replies) for social media accounts.

**Decision**: Use Late API's unified inbox (Comments + DMs Add-on) instead of platform-specific APIs.

**Rationale**:
- Single API handles all platforms (Instagram, Reddit, YouTube, Facebook, LinkedIn, Bluesky, TikTok, Telegram)
- No need to manage individual platform SDKs (instagrapi, praw, tweepy, etc.)
- Consistent interface for comments and DMs across platforms
- Webhook support for real-time event handling

**Alternatives Considered**:
- Platform-specific APIs (PRAW for Reddit, Instagrapi for Instagram) - too complex
- Buffer/Hootsuite engagement APIs - commercial pricing
- Web scraping - fragile and ToS issues

**Impact**:
- Single `LateEngagementClient` handles all platforms
- Requires Late Inbox Add-on subscription
- Simplified codebase with unified patterns

---

## 2026-02-03 - Agent State Machine Pattern

**Context**: Need structured agents for automated engagement that can be monitored and controlled.

**Decision**: Implement agents with explicit state machine: IDLE → MONITORING → PROCESSING → GENERATING → REVIEWING → RESPONDING → ERROR

**Rationale**:
- Clear state transitions for debugging
- Easy to implement human-in-the-loop review (REVIEWING state)
- Graceful error handling (ERROR state with recovery)
- Status reporting for CLI commands

**Alternatives Considered**:
- Simple polling loop without states - harder to monitor/control
- Event-driven only - loses visibility into agent state

**Impact**:
- All agents inherit from BaseAgent with state tracking
- CLI can report current agent state
- Human review queue integrates naturally

---

## 2026-02-03 - SQLite for Engagement Storage

**Context**: Need to persist tracked posts, comments, DMs, and bot configurations.

**Decision**: Use SQLite for local storage via `EngagementDatabase` class.

**Rationale**:
- No additional infrastructure required
- Single file database, easy backup
- Sufficient for single-instance engagement automation
- Python sqlite3 built-in, no extra dependencies

**Alternatives Considered**:
- PostgreSQL - overkill for local automation
- Redis - good for caching but not persistence
- JSON files - no query capability

**Impact**:
- Database file at `data/engagement.db`
- Simple schema for posts, comments, DMs, bots
- Easy migration path to PostgreSQL if needed

---

## 2026-02-03 - Human-in-the-Loop Default

**Context**: Auto-replying to comments/DMs carries reputation risk.

**Decision**: Default to human review queue (`auto_approve: false`, `auto_reply: false`).

**Rationale**:
- Prevents inappropriate automated responses
- Allows quality control before sending
- User can enable auto-mode when confident
- `PendingReview` model tracks suggested responses

**Alternatives Considered**:
- Auto-approve by default - too risky for brand reputation
- No auto mode at all - limits utility

**Impact**:
- CLI commands include review/approve/reject actions
- Review queue visible via `/social:comment-agent review`
- Auto modes available but explicitly disabled by default

---

## 2026-02-03 - Absolute Imports for Module Structure

**Context**: Relative imports (`from ..engagement`) caused "beyond top-level package" errors.

**Decision**: Use absolute imports (`from engagement.late_engagement_client`) in all modules.

**Rationale**:
- Works for both package imports and standalone script execution
- Consistent import style across codebase
- Avoids relative import complexity

**Impact**:
- All `__init__.py` files use absolute imports
- Agents, engagement, storage, webhooks modules all consistent
- Tests can import modules directly

---

## 2026-02-03 - Railway for Webhook Deployment

**Context**: Webhooks need public HTTPS endpoint for Late to send events.

**Decision**: Use Railway for webhook server deployment.

**Rationale**:
- Simple deployment from git
- Auto HTTPS with custom domain support
- Free tier sufficient for webhook handling
- Environment variable management
- Easy scaling if needed

**Alternatives Considered**:
- Vercel - serverless, potential cold start issues
- AWS Lambda - more complex setup
- Self-hosted - requires infrastructure management

**Impact**:
- `railway.json` and `Procfile` for deployment config
- Uvicorn serves FastAPI webhook handler
- Health check endpoint at `/health`

---

## 2026-02-03 - Skip Anthropic Test When API Key Missing

**Context**: Test `test_init_anthropic_provider` fails when `ANTHROPIC_API_KEY` environment variable is not set.

**Decision**: Add `@pytest.mark.skipif` decorator to skip the test when API key is not available.

**Rationale**:
- Tests should pass in CI/local environments without all API keys configured
- Anthropic provider test requires actual API key to validate initialization
- Skip is more appropriate than mock for provider initialization tests
- Other provider tests (Gemini) have similar skip patterns

**Impact**:
- Test suite passes in all environments
- Anthropic functionality still tested when API key is available
- Clear skip reason documented in test output

---

## 2026-02-03 - Explicit is_active Parameter for Bot Accounts

**Context**: `save_bot_account()` was missing `is_active` parameter, causing `deactivate_bot()` to not persist the deactivation state.

**Decision**: Add explicit `is_active` parameter to `save_bot_account()` and include it in both INSERT and UPDATE SQL.

**Rationale**:
- Bot activation/deactivation is a core feature
- ON CONFLICT DO UPDATE clause needs all fields to update
- Explicit parameter makes the API clearer than relying on defaults
- Consistent with other optional parameters like `is_primary`

**Impact**:
- `deactivate_bot()` and `activate_bot()` now work correctly
- Bot status persists across application restarts
- `update_bot()` can modify any bot field including active status

---

**Usage**: Add entry whenever making significant technical decisions
