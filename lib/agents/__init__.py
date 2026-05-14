#!/usr/bin/env python3
"""
Engagement Automation Agents

Provides automated response agents for:
- Comment monitoring and replies
- DM monitoring and replies
- Bot account management
- Content writing in SWIZZ voice
- Content research and strategy
- Media captioning and formatting
- Content curation intelligence layer
"""

from lib.agents.base_agent import AgentState, BaseAgent
from lib.agents.bot_manager import BotManager
from lib.agents.comment_agent import CommentAgent
from lib.agents.dm_agent import DMAgent
from lib.agents.image_agent import ImageAgent
from lib.agents.media_agent import MediaAgent
from lib.agents.research_agent import ResearchAgent
from lib.agents.writing_agent import WritingAgent

try:
    from lib.agents.content_curator import ContentCurator
except ImportError:
    ContentCurator = None  # SwizzPersona dependency not available

__all__ = [
    "BaseAgent",
    "AgentState",
    "CommentAgent",
    "DMAgent",
    "BotManager",
    "WritingAgent",
    "ResearchAgent",
    "MediaAgent",
    "ImageAgent",
    "ContentCurator",
]
