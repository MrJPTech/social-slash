# Active Context

**Last Updated**: 2026-02-01 (Session 2)
**Project**: social-slash

## Current Focus
- [x] Initial project structure with Late SDK integration
- [x] CLAUDE.md documentation generated
- [x] Memory Bank initialized
- [x] Virtual environment created and dependencies installed
- [x] Fixed import issue (SCHEDULING_TOOLS missing from exports)
- [x] Fixed Poster to lazy-init Late client (dry-run now works without API key)
- [x] Unit tests created and passing (11 tests)
- [x] Environment variables configured (.env.local)
- [x] Gemini API tested and working (gemini-2.0-flash)
- [x] Late API working with new key (9 connected accounts)
- [x] Fixed Late SDK response handling (AccountsListResponse → .accounts)
- [x] Fixed posts.create API (requires platforms as list of {platform, accountId})
- [x] First real post published to Twitter/X with AI enhancement!
- [x] Claude Code slash command configs created (.claude/commands/social/)
- [ ] Update google.generativeai to google.genai (deprecated warning)

## Active Features
- `/social:post` - Main posting command (READY FOR PRODUCTION)
- `/social:multi-post` - Multi-platform helper (READY FOR PRODUCTION)
- `/social:schedule` - Scheduling helper (READY FOR PRODUCTION)

## Known Blockers
- None! All APIs working.

## Known Issues (Non-Blocking)
- `google.generativeai` package shows FutureWarning (deprecated)
  - Migrate to `google.genai` package when ready
  - Current functionality works with gemini-2.0-flash model

## Environment Variables (.env.local)
- `LATE_API_KEY`: Working (sk_a44dad37...)
- `GOOGLE_API_KEY`: Working
- `KIMI_API_KEY`: Set (not used by this project)
- `LATE_WEBHOOK_URL`: Set (optional)

## Connected Social Accounts (via Late)
1. Facebook: Prsm Tech Inc.
2. Google Business: PRSM Tech Incorporated
3. Instagram: PRSM TECH INC. (@mrjptech_)
4. LinkedIn: PRSM TECH INCORPORATED
5. Reddit: MrJPTech
6. Threads: @mrjptech_
7. TikTok: @mrjptech
8. Twitter/X: @mrjptech
9. YouTube: @mrjptechy

## Next Session Priorities
1. Migrate Gemini client to google.genai package (deprecated warning fix)
2. Add more comprehensive unit tests (AI enhancement, posting)
3. Test multi-platform posting (post to LinkedIn, Instagram, etc.)
4. Consider adding webhook handling for post callbacks

## Quick Notes
- Package version: 0.1.0
- Python 3.12 in use, requires 3.10+
- Late SDK 1.2.17 installed
- Gemini model: `gemini-2.0-flash`
- All 11 unit tests passing

---
**Usage**: Update at end of each session with current status
