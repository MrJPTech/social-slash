"""
Platform-Specific Options for Social Slash

Data models for platform-specific posting parameters that map to
Late SDK's platformSpecificData field.

Usage:
    from models.platform_options import PlatformOptions, InstagramOptions

    options = PlatformOptions(
        instagram=InstagramOptions(content_type='story', first_comment='Links in bio!')
    )
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class InstagramOptions:
    """
    Instagram-specific posting options.

    Maps to Late SDK's InstagramPlatformData:
    - contentType: 'story' | 'post' | 'reel' (auto-detected from media if not set)
    - firstComment: Text to post as first comment after publishing
    - shareToFeed: For reels, whether to show on main feed (default True)
    - collaborators: List of usernames to invite as collaborators (max 3)

    Note: 'reel' is deprecated - Instagram auto-detects from video media.
    """

    content_type: str | None = None  # 'story' | 'post' | 'reel'
    first_comment: str | None = None
    share_to_feed: bool = True  # For reels
    collaborators: list[str] | None = None  # Max 3 usernames

    def to_platform_data(self) -> dict[str, Any] | None:
        """Convert to Late SDK platformSpecificData format."""
        data = {}

        if self.content_type:
            data["contentType"] = self.content_type

        if self.first_comment:
            data["firstComment"] = self.first_comment

        if not self.share_to_feed:
            data["shareToFeed"] = False

        if self.collaborators:
            data["collaborators"] = self.collaborators[:3]  # Max 3

        return data if data else None


@dataclass
class LinkedInOptions:
    """
    LinkedIn-specific posting options.

    Maps to Late SDK's LinkedInPlatformData:
    - firstComment: Text to post as first comment after publishing
    - disableLinkPreview: If True, disable the link preview card
    - organizationUrn: For company page posting (requires w_organization_social scope)

    Note: Company pages require different OAuth scope than personal profiles:
    - Personal: w_member_social
    - Company: w_organization_social + organization URN
    """

    first_comment: str | None = None
    disable_link_preview: bool = False
    organization_urn: str | None = None  # For company pages

    def to_platform_data(self) -> dict[str, Any] | None:
        """Convert to Late SDK platformSpecificData format."""
        data = {}

        if self.first_comment:
            data["firstComment"] = self.first_comment

        if self.disable_link_preview:
            data["disableLinkPreview"] = True

        if self.organization_urn:
            data["organizationUrn"] = self.organization_urn

        return data if data else None


@dataclass
class ThreadsOptions:
    """
    Threads-specific posting options.

    Maps to Late SDK's ThreadsPlatformData:
    - thread: If True, auto-break content into threaded format
    - threadNumber: If True, add numbering (1/n, 2/n...)

    Threads uses a two-step publishing workflow internally:
    1. Create container
    2. Publish container
    """

    auto_thread: bool = False  # Auto-break long content into thread
    thread_number: bool = False  # Add numbering to thread posts

    def to_platform_data(self) -> dict[str, Any] | None:
        """Convert to Late SDK platformSpecificData format."""
        data = {}

        if self.auto_thread:
            data["thread"] = True

        if self.thread_number:
            data["threadNumber"] = True

        return data if data else None


@dataclass
class TwitterOptions:
    """
    Twitter/X-specific posting options.

    Maps to Late SDK's TwitterPlatformData:
    - threadItems: Array for tweet threads (auto-generated if auto_thread=True)

    Note: Twitter threads require content to be split into individual tweets,
    each respecting the 280 character limit.
    """

    auto_thread: bool = False  # Auto-break long content into thread

    def to_platform_data(self) -> dict[str, Any] | None:
        """Convert to Late SDK platformSpecificData format."""
        # Thread items are generated separately by splitting content
        # This method returns None as threading is handled at a higher level
        return None


@dataclass
class RedditOptions:
    """
    Reddit-specific posting options.

    IMPORTANT LIMITATION: Reddit subreddit is configured at the account
    connection level in Late, NOT per-post via API. This cannot be changed
    dynamically per post.

    Available options:
    - title: Post title (required for Reddit, auto-generated from content if not provided)

    Post type (text, link, image) is auto-detected based on content and media.
    """

    title: str | None = None  # Auto-generated from first line if not provided

    def to_platform_data(self) -> dict[str, Any] | None:
        """Convert to Late SDK platformSpecificData format.

        Note: Reddit doesn't have a platformSpecificData model in Late SDK.
        Title is passed as a top-level parameter to posts.create().
        """
        # Reddit uses top-level 'title' param, not platformSpecificData
        return None


@dataclass
class PlatformOptions:
    """
    Container for all platform-specific options.

    Usage:
        # Instagram story with first comment
        options = PlatformOptions(
            instagram=InstagramOptions(content_type='story', first_comment='Link in bio!')
        )

        # Reddit post with explicit title
        options = PlatformOptions(
            reddit=RedditOptions(title='My Custom Title')
        )

        # Multi-platform with mixed options
        options = PlatformOptions(
            instagram=InstagramOptions(content_type='story'),
            linkedin=LinkedInOptions(first_comment='DM for details')
        )
    """

    instagram: InstagramOptions | None = None
    linkedin: LinkedInOptions | None = None
    threads: ThreadsOptions | None = None
    twitter: TwitterOptions | None = None
    reddit: RedditOptions | None = None

    # Raw JSON override for advanced users
    raw_platform_data: dict[str, dict[str, Any]] | None = None

    def get_platform_data(self, platform: str) -> dict[str, Any] | None:
        """
        Get platform-specific data for a given platform.

        Args:
            platform: Platform name (lowercase)

        Returns:
            Dictionary of platform-specific data or None
        """
        # Check raw override first
        if self.raw_platform_data and platform in self.raw_platform_data:
            base_data = self._get_typed_platform_data(platform) or {}
            return {**base_data, **self.raw_platform_data[platform]}

        return self._get_typed_platform_data(platform)

    def _get_typed_platform_data(self, platform: str) -> dict[str, Any] | None:
        """Get platform data from typed option classes."""
        platform = platform.lower()

        if platform == "instagram" and self.instagram:
            return self.instagram.to_platform_data()
        elif platform == "linkedin" and self.linkedin:
            return self.linkedin.to_platform_data()
        elif platform == "threads" and self.threads:
            return self.threads.to_platform_data()
        elif platform == "twitter" and self.twitter:
            return self.twitter.to_platform_data()
        # Reddit doesn't use platformSpecificData

        return None

    def get_reddit_title(self, content: str) -> str | None:
        """
        Get Reddit title, auto-generating from content if not explicitly set.

        Args:
            content: Post content to extract title from

        Returns:
            Title string (explicit or auto-generated)
        """
        if self.reddit and self.reddit.title:
            return self.reddit.title

        # Auto-generate from first line of content
        return self._extract_title_from_content(content)

    @staticmethod
    def _extract_title_from_content(content: str) -> str:
        """
        Extract title from first line of content.

        Removes hashtags and truncates to Reddit's 300 char limit.

        Args:
            content: Full post content

        Returns:
            Extracted title string
        """
        first_line = content.split("\n")[0].strip()

        # Remove hashtags from title
        words = first_line.split()
        title = " ".join(w for w in words if not w.startswith("#"))

        # Truncate to Reddit title limit (300 chars)
        if len(title) > 300:
            title = title[:297] + "..."

        return title or "New Post"

    def validate_for_platforms(self, platforms: list[str]) -> list[str]:
        """
        Validate that platform options match target platforms.

        Returns list of warnings for mismatched options.

        Args:
            platforms: List of target platforms

        Returns:
            List of warning messages
        """
        warnings = []
        platforms_lower = [p.lower() for p in platforms]

        if self.instagram and "instagram" not in platforms_lower:
            warnings.append("Instagram options provided but Instagram not in target platforms")

        if self.linkedin and "linkedin" not in platforms_lower:
            warnings.append("LinkedIn options provided but LinkedIn not in target platforms")

        if self.threads and "threads" not in platforms_lower:
            warnings.append("Threads options provided but Threads not in target platforms")

        if self.twitter and "twitter" not in platforms_lower:
            warnings.append("Twitter options provided but Twitter not in target platforms")

        if self.reddit and "reddit" not in platforms_lower:
            warnings.append("Reddit options provided but Reddit not in target platforms")

        return warnings
