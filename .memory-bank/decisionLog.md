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

**Usage**: Add entry whenever making significant technical decisions
