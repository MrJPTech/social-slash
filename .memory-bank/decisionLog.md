# Technical Decision Log

**Project**: social-slash

---

## 2026-02-12 - Separate ImagenClient from GeminiClient

**Context**: Adding image generation capability. The `google-genai` SDK supports both text (`generate_content`) and image (`generate_images`) generation, so could extend GeminiClient or create a new class.

**Decision**: Create separate `ImagenClient` class in `lib/ai/imagen_client.py`.

**Rationale**:
- Different API surface: `generate_images()` vs `generate_content()`, different return types
- Different config types: `GenerateImagesConfig` vs text-based prompts
- Different concerns: aspect ratios, platform presets, temp file management, Late SDK upload
- Follows Single Responsibility Principle

**Alternatives Considered**:
- Extend GeminiClient with image methods — violates SRP, muddies text vs image concerns
- Generic AI client wrapper — over-engineering for two distinct use cases

**Impact**:
- Clean separation of text and image generation
- ImagenClient can evolve independently (new models, features)
- Both use same `google-genai` SDK and `GOOGLE_API_KEY`

---

## 2026-02-12 - Two-Model Prompt Enhancement Pipeline

**Context**: User prompts like "tech startup workspace" need enhancement for best Imagen 3 results.

**Decision**: Use Gemini Flash (text) to refine prompts before passing to Imagen 3 (image).

**Rationale**:
- Imagen 3 generates better images with detailed, descriptive prompts
- Gemini Flash is fast and cheap for text refinement
- Persona context (professional/personal/ceo) can influence visual style through prompt wording
- Fallback: if enhancement fails, raw prompt is still usable

**Alternatives Considered**:
- Direct user prompts to Imagen — lower quality results
- Hardcoded style templates — inflexible, no persona awareness
- Client-side prompt building — more complex, less AI-aware

**Impact**:
- Higher quality generated images from better prompts
- Persona-aware visual styles (corporate blue, vibrant bold, executive dark tones)
- Small additional latency (~1s for Gemini Flash call)

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

## 2026-02-06 - Late SDK Media Upload for Local Files

**Context**: User wants to attach local screenshots to multi-platform posts. Late SDK's `posts.create()` only accepts media URLs, not local file paths.

**Decision**: Use `client.media.upload(file_path)` to upload local files first, then reference returned URLs in `posts.create()`.

**Rationale**:
- Late SDK has built-in media upload: `client.media.upload()` for files < 4MB
- `client.media.upload_large()` available for files 4MB-5GB (requires Vercel token)
- Returns cloud URLs at `media.getlate.dev/temp/`
- `media_items` format: `[{"type": "image", "url": "https://media.getlate.dev/..."}]`

**Alternatives Considered**:
- Hosting images externally (Imgur, Cloudflare) - unnecessary complexity
- Base64 encoding - not supported by Late API
- Modifying social-slash to auto-detect local vs URL - future improvement

**Impact**:
- Local file → Late media upload → URL → posts.create() pipeline works
- social-slash CLI currently only accepts URLs (could be enhanced)
- Instagram has aspect ratio limits: 0.75:1 to 1.91:1 (wide screenshots fail)
- YouTube requires video content, image-only posts rejected

---

## 2026-02-06 - Gemini API Key Rotation Needed

**Context**: Gemini API key returned 403 "reported as leaked" during AI enhancement attempt.

**Decision**: Need to rotate Google API key in Google Cloud Console and update `.env.local`.

**Rationale**:
- Key was likely flagged due to accidental exposure (committed to repo or logged)
- Both AI providers currently unavailable (Gemini leaked, Anthropic not configured)
- Manual content enhancement used as workaround this session

**Impact**:
- AI enhancement temporarily unavailable
- Need new key from https://aistudio.google.com/apikey
- Also need to set ANTHROPIC_API_KEY as backup

---

## 2026-02-06 - Dual-Mode Persona System (Voice as Style Layer)

**Context**: Need to generate social media content in the authentic voice of Jay Ward (@swizzimatic / @BigSwizzi) across two distinct communication modes.

**Decision**: Build a dual-mode persona system that captures ONLY speech patterns and voice personality — vocabulary, emoji usage, response length, tone, directness. Content topics come from the caller; the persona is just a style layer applied on top.

**Rationale**:
- Same person has two distinct modes: professional (@swizzimatic) and personal (@BigSwizzi)
- Voice is about HOW you speak, not WHAT you speak about
- Vocabulary post-processing (`apply_vocab_transform()`) ensures consistent voice after AI generation
- Few-shot examples from Instagram data provide voice consistency
- Platform configs enforce character limits per platform

**Alternatives Considered**:
- RAG over Instagram data - overkill, not about content topics
- Single persona mode - loses the dual-mode communication style
- Topical content agents (video/music) - user explicitly rejected, agents are voice-only

**Impact**:
- 6 new files in lib/persona/ and lib/agents/
- 3 modified files for integration
- CLI + programmatic API for all 3 new agents
- Persona can be used by existing CommentAgent/DMAgent via 'swizz'/'bigswizzi' brand voices

---

## 2026-02-06 - BaseAgent Pattern for New Agents (Not ElizaOS)

**Context**: PRSMTECH-SMCA uses ElizaOS Service/Action/Provider pattern. social-slash uses its own BaseAgent(ABC) pattern.

**Decision**: Follow social-slash's existing BaseAgent pattern for all 3 new agents. Use SMCA's voice/persona concepts as inspiration only.

**Rationale**:
- Consistency within social-slash codebase
- BaseAgent provides state machine, rate limiting, stats, logging, ResponseGenerator integration
- No dependency on ElizaOS runtime
- Adapting SMCA patterns would require architectural changes

**Impact**:
- All 3 new agents extend BaseAgent with SwizzPersona integration
- Reuse existing ResponseGenerator._generate() for AI calls
- Consistent CLI pattern with argparse across all agents

---

## 2026-02-06 - Vocabulary Post-Processing Over Prompt-Only Approach

**Context**: Need AI-generated content to use SWIZZ-specific vocabulary ("ya" instead of "your", "gonna" instead of "going to", etc.)

**Decision**: Use dual approach: persona system prompts guide the AI, then `apply_vocab_transform()` applies regex-based vocabulary mapping as post-processing.

**Rationale**:
- AI models don't reliably maintain consistent vocabulary in output
- Post-processing ensures 100% vocabulary consistency
- Regex with `re.IGNORECASE` handles all casing variations
- Shared vocab (contractions) + mode-specific vocab (AAVE for BigSwizzi)

**Alternatives Considered**:
- Prompt engineering only - inconsistent results
- Fine-tuned model - too expensive for this use case
- Template-based (no AI) - loses natural language generation

**Impact**:
- `BasePersona.apply_vocab_transform()` applied to all AI output
- SHARED_VOCAB for common contractions both modes use
- Mode-specific VOCAB_MAP for unique vocabulary per persona
- BigSwizziPersona has 12+ vocab entries including AAVE terms

---

## 2026-02-08 - Streamable-HTTP Transport for Claude Mobile

**Context**: Claude mobile app needs HTTP-based MCP transport, not stdio.

**Decision**: Switch from SSE to `streamable-http` transport with `stateless_http=True`.

**Rationale**:
- Claude mobile app doesn't support SSE transport
- `streamable-http` uses single `/mcp` POST endpoint
- `stateless_http=True` avoids session persistence on Railway (stateless deployment)
- Simpler than managing SSE connections

**Impact**:
- Single `/mcp` endpoint replaces `/sse` + `/messages/`
- Railway auto-deploys from GitHub master push
- Works for both Claude Desktop (remote URL) and Claude.ai web

---

## 2026-02-08 - OAuth 2.0 for Claude.ai Custom Connectors

**Context**: Claude.ai custom connectors require OAuth 2.0 authentication, not simple bearer tokens.

**Decision**: Implement full OAuth 2.0 flow (RFC 8414, RFC 9728, RFC 7591) with auto-approve for single-user server.

**Rationale**:
- Claude.ai mandates OAuth 2.0 for custom MCP connectors
- Single-user personal server → auto-approve on `/authorize` is acceptable
- PKCE (S256) verification adds security without user friction
- In-memory stores sufficient for single Railway instance

**Impact**:
- OAuth endpoints: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource`, `/authorize`, `/token`, `/register`
- Token exchange returns `MCP_AUTH_TOKEN` as `access_token`
- BearerAuthMiddleware validates all `/mcp` requests

---

## 2026-02-08 - Pre-Shared OAuth Credentials (Lock Down)

**Context**: OAuth flow auto-approved everyone. Anyone finding the Railway URL could get full access to all 19 tools including posting to social accounts.

**Decision**: Require pre-shared `OAUTH_CLIENT_ID` + `OAUTH_CLIENT_SECRET` set as Railway env vars. Block dynamic client registration entirely.

**Rationale**:
- Open registration is a security risk for a personal automation server
- Pre-shared credentials mean only you can authenticate
- Claude.ai connector dialog has fields for OAuth Client ID/Secret
- `/register` returning 403 prevents unauthorized client creation
- Client ID validated on `/authorize`, both ID + secret validated on `/token`

**Alternatives Considered**:
- IP allowlisting - too restrictive for mobile/travel
- Rate limiting only - doesn't prevent unauthorized access
- Keep open registration - unacceptable security risk

**Impact**:
- `/register` returns 403 `registration_not_supported`
- `/authorize` redirects with `error=unauthorized_client` if client_id doesn't match
- `/token` returns 401 `invalid_client` if credentials don't match
- Claude.ai connector configured with matching ID/secret

---

## 2026-02-08 - Railway Shared Variables Must Be Linked to Service

**Context**: Mac and Claude.ai web getting "GOOGLE_API_KEY not found" despite Railway dashboard showing the variables.

**Decision**: Added `/health` env var diagnostics to expose which vars are actually reaching the process. Discovered Railway "Shared Variables" must be explicitly linked to the service.

**Rationale**:
- Railway Shared Variables exist at project level but DON'T automatically propagate to services
- Must click "Add All" or individually link them to the `web` service
- `/health` endpoint diagnostics (`set` vs `MISSING`) immediately revealed the issue
- This is a Railway platform behavior, not a code bug

**Impact**:
- `/health` now shows env var status for quick diagnostics
- All 6 env vars linked to web service and confirmed working
- Lesson: always verify env vars reach the process, not just the dashboard

---

## 2026-02-12 - Jordan Ward CEO Persona as Third Voice Mode

**Context**: PRSMTECH CEO content needs a distinct voice from the SWIZZ personas. Jordan Ward's CEO voice is evidence-based, contrarian, mentorship-oriented, and data-driven — fundamentally different from @swizzimatic (professional tech) and @BigSwizzi (personal/casual).

**Decision**: Add `JordanWardPersona(BasePersona)` as a third voice mode alongside the existing two SWIZZ modes. CEO voice has its own vocabulary map (polished, no slang), 7 structured content formats, and separate few-shot examples.

**Rationale**:
- CEO content strategy document (650 lines) defines distinct hooks, scripts, formats
- Evidence-based voice ("the data shows" vs "I think") is fundamentally different from SWIZZ casual tone
- 7 content formats (problem_solution, myth_busting, quick_tips, etc.) provide structured prompts
- Reuses existing BasePersona/SwizzPersona infrastructure — just a new mode, not a new system
- `get_content_format_prompt()` CEO-specific method enables structured content generation

**Alternatives Considered**:
- Separate persona system — unnecessary, SwizzPersona router handles multiple modes cleanly
- Prompt-only approach (no new class) — loses structure, vocabulary consistency, and format templates
- Fine-tuned model — too expensive for three distinct voices

**Impact**:
- 8 files modified/created, ~760 lines added
- SwizzPersona router now accepts "ceo" mode alongside "professional" and "personal"
- Writing agent CLI accepts `--persona ceo` and 7 CEO post types
- MCP tools accept `persona_mode="ceo"` and CEO post types
- 50 new unit tests covering all CEO persona functionality
- Module docstring updated from "Dual-mode" to "Multi-mode"

---

## 2026-02-12 - Migrate from google-generativeai to google-genai SDK

**Context**: The `google-generativeai` package (PyPI) is deprecated (EOL August 2025). Google replaced it with `google-genai` which uses a client-based API pattern instead of module-level configuration.

**Decision**: Migrate all Gemini usage to `google-genai` SDK v1.63.0 with the new `genai.Client()` pattern.

**Rationale**:
- Old package is deprecated and will stop receiving updates
- New SDK uses cleaner client-based pattern: `genai.Client(api_key=key)` instead of `genai.configure(api_key=key)` + `genai.GenerativeModel(model)`
- New generation call: `client.models.generate_content(model=MODEL, contents=prompt)` is more explicit
- `response.text` accessor unchanged — minimal migration effort
- Already had the new SDK in requirements (`google-genai>=1.0.0`) but code was still using old patterns

**Alternatives Considered**:
- Keep old package — would eventually break as Google drops support
- Use Anthropic as primary — loses cost advantage of Gemini Flash
- Use REST API directly — more work, less maintainable

**Impact**:
- 4 files modified: `gemini_client.py`, `response_generator.py`, `requirements.txt`, `requirements-mcp.txt`
- No breaking changes to external API (same tool signatures, same output format)
- Railway Docker rebuild required (new pip dependency)
- All 173 tests passing after migration

---

**Usage**: Add entry whenever making significant technical decisions
