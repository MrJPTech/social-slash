#!/usr/bin/env python3
"""
Engagement Module - Response Generation and Late API Inbox Client

Provides:
- AI-powered response generation for comments and DMs
- Late API unified inbox client for cross-platform engagement
"""

from lib.engagement.response_generator import ResponseGenerator
from lib.engagement.late_engagement_client import LateEngagementClient

__all__ = [
    'ResponseGenerator',
    'LateEngagementClient'
]
