"""
Social Slash Models

Data models for platform-specific posting options.
"""

from .platform_options import (
    InstagramOptions,
    LinkedInOptions,
    PlatformOptions,
    RedditOptions,
    ThreadsOptions,
)

__all__ = [
    "PlatformOptions",
    "InstagramOptions",
    "LinkedInOptions",
    "ThreadsOptions",
    "RedditOptions",
]
