"""
Social Media Hacker Tools Database

Curated collection of tools, SDKs, and services for social media automation.
Source: https://github.com/MobileFirstLLC/social-media-hacker-list

Usage:
    from lib.tools import (
        get_tools_by_platform,
        get_developer_sdks,
        LINKEDIN_TOOLS,
        PYTHON_SDKS
    )
"""

from dataclasses import dataclass
from enum import Enum


class Platform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    MASTODON = "mastodon"
    REDDIT = "reddit"
    SNAPCHAT = "snapchat"
    THREADS = "threads"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    MULTI = "multi"
    BLUESKY = "bluesky"
    PINTEREST = "pinterest"
    TELEGRAM = "telegram"


class Category(str, Enum):
    ALTERNATIVE_CLIENT = "alternative_client"
    ANALYTICS = "analytics"
    BOT = "bot"
    CONTENT_CREATION = "content_creation"
    DEVELOPER = "developer"
    IMAGE = "image"
    PRODUCTIVITY = "productivity"
    VIDEO = "video"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    GO = "go"
    KOTLIN = "kotlin"
    RUST = "rust"


@dataclass
class SocialTool:
    """Represents a social media tool/SDK/service."""

    name: str
    platform: Platform
    category: Category
    url: str
    description: str
    open_source: bool = False
    language: Language | None = None
    install_command: str | None = None
    github_url: str | None = None


# =============================================================================
# TOOL DATABASE - Focused on posting/scheduling tools for social-slash
# =============================================================================

TOOLS: list[SocialTool] = [
    # =========================================================================
    # SCHEDULING & AUTOMATION (Core for social-slash)
    # =========================================================================
    SocialTool(
        name="Buffer",
        platform=Platform.MULTI,
        category=Category.ANALYTICS,
        url="https://buffer.com/",
        description="Automation, scheduling, and analytics",
    ),
    SocialTool(
        name="Hootsuite",
        platform=Platform.MULTI,
        category=Category.PRODUCTIVITY,
        url="https://www.hootsuite.com/",
        description="Manage all your social media",
    ),
    SocialTool(
        name="HypeFury",
        platform=Platform.MULTI,
        category=Category.PRODUCTIVITY,
        url="https://hypefury.com/",
        description="Grow and monetize your social media",
    ),
    SocialTool(
        name="MeetEdgar",
        platform=Platform.MULTI,
        category=Category.PRODUCTIVITY,
        url="https://meetedgar.com/",
        description="Automation and scheduling",
    ),
    SocialTool(
        name="dlvr.it",
        platform=Platform.MULTI,
        category=Category.PRODUCTIVITY,
        url="https://dlvrit.com",
        description="Social media automation",
    ),
    SocialTool(
        name="Statuz",
        platform=Platform.MULTI,
        category=Category.PRODUCTIVITY,
        url="https://statuz.gg",
        description="Cross-post to X, BlueSky, Mastodon from menu bar",
    ),
    SocialTool(
        name="Later",
        platform=Platform.INSTAGRAM,
        category=Category.PRODUCTIVITY,
        url="https://later.com/auto-publish/",
        description="Auto publish for Instagram",
    ),
    SocialTool(
        name="Typefully",
        platform=Platform.TWITTER,
        category=Category.PRODUCTIVITY,
        url="https://typefully.app/",
        description="Distraction-free tweet and thread composer",
    ),
    # =========================================================================
    # DEVELOPER SDKs (For custom integrations)
    # =========================================================================
    SocialTool(
        name="Tweepy",
        platform=Platform.TWITTER,
        category=Category.DEVELOPER,
        url="https://www.tweepy.org/",
        description="Twitter API client for Python",
        open_source=True,
        language=Language.PYTHON,
        install_command="pip install tweepy",
        github_url="https://github.com/tweepy/tweepy",
    ),
    SocialTool(
        name="instagrapi",
        platform=Platform.INSTAGRAM,
        category=Category.DEVELOPER,
        url="https://github.com/adw0rd/instagrapi",
        description="Unofficial Instagram private API for Python",
        open_source=True,
        language=Language.PYTHON,
        install_command="pip install instagrapi",
        github_url="https://github.com/adw0rd/instagrapi",
    ),
    SocialTool(
        name="PRAW",
        platform=Platform.REDDIT,
        category=Category.DEVELOPER,
        url="https://praw.readthedocs.io/",
        description="Python Reddit API Wrapper",
        open_source=True,
        language=Language.PYTHON,
        install_command="pip install praw",
        github_url="https://github.com/praw-dev/praw",
    ),
    SocialTool(
        name="Mastodon.py",
        platform=Platform.MASTODON,
        category=Category.DEVELOPER,
        url="https://github.com/halcy/Mastodon.py",
        description="Python wrapper for Mastodon API",
        open_source=True,
        language=Language.PYTHON,
        install_command="pip install Mastodon.py",
        github_url="https://github.com/halcy/Mastodon.py",
    ),
    SocialTool(
        name="linkedin_scraper",
        platform=Platform.LINKEDIN,
        category=Category.DEVELOPER,
        url="https://github.com/joeyism/linkedin_scraper",
        description="Scrape LinkedIn for user data",
        open_source=True,
        language=Language.PYTHON,
        install_command="pip install linkedin-scraper",
        github_url="https://github.com/joeyism/linkedin_scraper",
    ),
    SocialTool(
        name="yt-dlp",
        platform=Platform.YOUTUBE,
        category=Category.DEVELOPER,
        url="https://github.com/yt-dlp/yt-dlp",
        description="Enhanced YouTube video downloader",
        open_source=True,
        language=Language.PYTHON,
        install_command="pip install yt-dlp",
        github_url="https://github.com/yt-dlp/yt-dlp",
    ),
    # =========================================================================
    # CONTENT CREATION
    # =========================================================================
    SocialTool(
        name="Canva",
        platform=Platform.MULTI,
        category=Category.IMAGE,
        url="https://www.canva.com/",
        description="Design social media graphics",
    ),
    SocialTool(
        name="Kapwing",
        platform=Platform.MULTI,
        category=Category.VIDEO,
        url="https://www.kapwing.com/",
        description="Create images, videos, and GIFs",
    ),
    SocialTool(
        name="Recast Studio",
        platform=Platform.MULTI,
        category=Category.VIDEO,
        url="https://recast.studio/",
        description="Turn long-form content into social clips",
    ),
    # =========================================================================
    # LEAD GENERATION
    # =========================================================================
    SocialTool(
        name="LinkedIn Lead Generator",
        platform=Platform.LINKEDIN,
        category=Category.PRODUCTIVITY,
        url="https://getleadfox.com/",
        description="Auto-reply and find emails from commenters",
    ),
    SocialTool(
        name="Heepsy",
        platform=Platform.INSTAGRAM,
        category=Category.ANALYTICS,
        url="https://www.heepsy.com/",
        description="Influencer discovery platform",
    ),
    # =========================================================================
    # ANALYTICS
    # =========================================================================
    SocialTool(
        name="SHIELD",
        platform=Platform.LINKEDIN,
        category=Category.ANALYTICS,
        url="https://www.shieldapp.ai/",
        description="LinkedIn analytics dashboard",
    ),
    SocialTool(
        name="Ilo",
        platform=Platform.TWITTER,
        category=Category.ANALYTICS,
        url="https://ilo.so/",
        description="Twitter analytics",
    ),
    # =========================================================================
    # BOTS
    # =========================================================================
    SocialTool(
        name="ManyChat",
        platform=Platform.MULTI,
        category=Category.BOT,
        url="https://manychat.com/",
        description="Automate conversations in Messenger and Instagram",
    ),
]

# Convenience lists
PLATFORMS = list(Platform)
CATEGORIES = list(Category)
LANGUAGES = list(Language)


def get_tools_by_platform(platform: str) -> list[SocialTool]:
    """Get all tools for a specific platform."""
    platform_enum = Platform(platform.lower())
    return [t for t in TOOLS if t.platform == platform_enum]


def get_tools_by_category(category: str) -> list[SocialTool]:
    """Get all tools for a specific category."""
    category_enum = Category(category.lower())
    return [t for t in TOOLS if t.category == category_enum]


def get_developer_sdks(language: str | None = None) -> list[SocialTool]:
    """Get all developer SDKs, optionally filtered by language."""
    devtools = [t for t in TOOLS if t.category == Category.DEVELOPER]
    if language:
        lang_enum = Language(language.lower())
        devtools = [t for t in devtools if t.language == lang_enum]
    return devtools


def get_open_source_tools() -> list[SocialTool]:
    """Get all open source tools."""
    return [t for t in TOOLS if t.open_source]


def get_python_install_commands() -> dict[str, str]:
    """Get all Python pip install commands."""
    return {
        t.name: t.install_command
        for t in TOOLS
        if t.language == Language.PYTHON and t.install_command
    }


def search_tools(query: str) -> list[SocialTool]:
    """Search tools by name or description."""
    query = query.lower()
    return [t for t in TOOLS if query in t.name.lower() or query in t.description.lower()]


# Quick access convenience
TWITTER_TOOLS = get_tools_by_platform("twitter")
INSTAGRAM_TOOLS = get_tools_by_platform("instagram")
LINKEDIN_TOOLS = get_tools_by_platform("linkedin")
YOUTUBE_TOOLS = get_tools_by_platform("youtube")
REDDIT_TOOLS = get_tools_by_platform("reddit")
PYTHON_SDKS = get_developer_sdks("python")
SCHEDULING_TOOLS = get_tools_by_category("productivity")


if __name__ == "__main__":
    print(f"Total tools: {len(TOOLS)}")
    print(f"\nScheduling tools ({len(SCHEDULING_TOOLS)}):")
    for tool in SCHEDULING_TOOLS:
        print(f"  - {tool.name}: {tool.url}")
    print(f"\nPython SDKs ({len(PYTHON_SDKS)}):")
    for sdk in PYTHON_SDKS:
        print(f"  - {sdk.name}: {sdk.install_command}")
