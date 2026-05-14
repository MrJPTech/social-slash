"""Shared MCP instance, constants, and scheduler accessor for all tool/route modules.

This module owns the FastMCP instance that every tools_*.py and routes_*.py
file decorates on.  Import graph is a clean DAG:

    _shared  <--  tools_*  /  routes_*  <--  server.py

No module in this package imports from server.py, preventing circular deps.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Platforms that require media to post (text-only rejected by their APIs)
MEDIA_REQUIRED_PLATFORMS: frozenset[str] = frozenset({"instagram", "tiktok"})

# Initialize MCP server
mcp = FastMCP(
    "social-slash",
    instructions="""
Social Slash - Social media automation tools for PRSMTECH.

Available tools are prefixed by group:
- accounts_*   : List and manage connected social media accounts
- posts_*      : View recent posts and post details
- status_*     : Project status overview
- writing_*    : Generate posts/captions/threads in SWIZZ voice or Jordan Ward CEO voice
- research_*   : Hashtag research, content ideas, trending analysis
- media_*      : Reel/story/carousel captions, alt text, format suggestions
- image_*      : AI image generation (Imagen 4) with platform-optimized aspect ratios
- post_*       : Publish or dry-run posts to platforms
- content_*    : Content curation intelligence (turn screenshots/ideas into content strategy)
- media_library_* : Manage screenshot/photo library (scan, search, sync local folders)

Voice personas:
- professional : @swizzimatic casual-professional voice
- personal     : @BigSwizzi ultra-concise AAVE voice
- ceo          : Jordan Ward evidence-based CEO thought leadership

Tone options (all writing tools):
  authentic, motivational, humorous, reflective, educational,
  hype, emotional, direct, raw, inspiring

Energy levels (all writing tools):
  low (calm/measured), medium (balanced), high (bold/loud)

CEO content formats (use with persona_mode="ceo"):
  problem_solution, myth_busting, quick_tips, day_in_life,
  case_study, industry_commentary, quick_wins, vibe_coder,
  bridge_builder, real_talk, ask_the_audience

Platform character limits:
  twitter=280, threads=500, instagram=2200, linkedin=3000,
  tiktok=150, bluesky=300, youtube=5000, facebook=8000,
  reddit=40000, telegram=4096, google_business=1500
""",
)


# ---------------------------------------------------------------------------
# Scheduler singleton — set by main(), read by route handlers
# ---------------------------------------------------------------------------

_scheduler: Any | None = None


def _get_scheduler():
    """Return the DailyScheduler instance, or None when disabled."""
    return _scheduler


def _set_scheduler(s):
    """Set the DailyScheduler instance (called once from main())."""
    global _scheduler
    _scheduler = s
