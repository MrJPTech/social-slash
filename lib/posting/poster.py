#!/usr/bin/env python3
"""
Social Slash - Content Poster

Orchestrates AI enhancement and Late API distribution for social media posting.
This is the main backend that powers the /social:post slash command.

Usage:
    python poster.py --content "Hello world" --platforms linkedin
    python poster.py --content "Hello" --platforms linkedin,twitter --enhance
    python poster.py --content "Test" --platforms linkedin --dry-run
"""

import argparse
import json
import os
import sys
from typing import Any

# Add lib to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_clients.late_client import LateDistributionClient
from models.platform_options import (
    InstagramOptions,
    LinkedInOptions,
    PlatformOptions,
    RedditOptions,
    ThreadsOptions,
    TwitterOptions,
)


class Poster:
    """
    Main posting orchestrator for Social Slash.

    Coordinates:
    - AI content enhancement (optional)
    - Late SDK distribution
    - Multi-platform posting
    - Scheduling
    """

    def __init__(self, skip_late_init: bool = False):
        """Initialize the poster with Late client and optional AI clients.

        Args:
            skip_late_init: If True, skip Late client initialization (for dry-run mode)
        """
        self._late_client = None
        self._skip_late_init = skip_late_init
        self.ai_client = None
        self._ai_provider = None

    @property
    def late_client(self) -> LateDistributionClient:
        """Lazy-initialize Late client on first access."""
        if self._late_client is None:
            if self._skip_late_init:
                raise RuntimeError("Late client not initialized (dry-run mode)")
            self._late_client = LateDistributionClient()
        return self._late_client

    def _init_ai_client(self, provider: str = "gemini"):
        """
        Initialize AI client on demand.

        Args:
            provider: AI provider ('gemini' or 'anthropic')
        """
        if self._ai_provider == provider and self.ai_client:
            return

        try:
            if provider == "gemini":
                from ai.gemini_client import GeminiClient

                self.ai_client = GeminiClient()
                self._ai_provider = "gemini"
                print("[INFO] AI enhancement enabled (Gemini)")

            elif provider == "anthropic":
                from ai.anthropic_client import AnthropicClient

                self.ai_client = AnthropicClient()
                self._ai_provider = "anthropic"
                print("[INFO] AI enhancement enabled (Anthropic)")

            else:
                raise ValueError(f"Unknown AI provider: {provider}")

        except ImportError as e:
            print(f"[WARNING] AI client not available: {e}")
            self.ai_client = None
        except ValueError as e:
            print(f"[WARNING] AI client not configured: {e}")
            self.ai_client = None

    def enhance_content(self, content: str, platform: str, provider: str = "gemini") -> str:
        """
        Enhance content using AI.

        Args:
            content: Original content
            platform: Target platform for optimization
            provider: AI provider to use

        Returns:
            Enhanced content string
        """
        self._init_ai_client(provider)

        if not self.ai_client:
            print("[WARNING] AI enhancement skipped - client not available")
            return content

        try:
            result = self.ai_client.enhance_content(content, platform)
            enhanced = result.get("enhanced_content", content)

            if enhanced != content:
                print(f"[INFO] Content enhanced for {platform}")
                changes = result.get("changes_made", [])
                for change in changes[:3]:
                    print(f"  - {change}")

            return enhanced

        except Exception as e:
            print(f"[WARNING] Enhancement failed, using original: {e}")
            return content

    def post(
        self,
        content: str,
        platforms: list[str],
        enhance: bool = False,
        ai_provider: str = "gemini",
        media_urls: list[str] | None = None,
        schedule: str | None = None,
        dry_run: bool = False,
        platform_options: PlatformOptions | None = None,
    ) -> dict[str, Any]:
        """
        Post content to specified platforms.

        Args:
            content: Post content
            platforms: List of target platforms
            enhance: Whether to AI-enhance the content
            ai_provider: Which AI provider to use ('gemini' or 'anthropic')
            media_urls: Optional list of media URLs to attach
            schedule: Optional ISO datetime for scheduling
            dry_run: If True, simulate without actually posting
            platform_options: Optional platform-specific options (Instagram story,
                LinkedIn first comment, Reddit title, etc.)

        Returns:
            Dictionary with results and summary
        """
        original_content = content

        # Validate platform options if provided
        if platform_options:
            warnings = platform_options.validate_for_platforms(platforms)
            for warning in warnings:
                print(f"[WARNING] {warning}")

        # Enhance content if requested
        if enhance:
            # Use first platform for enhancement context
            content = self.enhance_content(content, platforms[0], ai_provider)

        # Build platform-specific data for dry-run display
        platform_data_summary = {}
        if platform_options:
            for platform in platforms:
                data = platform_options.get_platform_data(platform)
                if data:
                    platform_data_summary[platform] = data

            # Get Reddit title if posting to Reddit
            if "reddit" in [p.lower() for p in platforms]:
                reddit_title = platform_options.get_reddit_title(content)
                platform_data_summary["reddit_title"] = reddit_title

        # Dry run mode
        if dry_run:
            return {
                "status": "dry-run",
                "original_content": original_content,
                "enhanced_content": content if enhance else None,
                "platforms": platforms,
                "media": media_urls,
                "schedule": schedule,
                "platform_options": platform_data_summary,
                "would_post": True,
            }

        # Single platform posting
        if len(platforms) == 1:
            platform = platforms[0]
            try:
                # Build platform-specific parameters
                post_kwargs = self._build_post_kwargs(platform, content, platform_options)

                result = self.late_client.post_to_platform(
                    content=content,
                    platform=platform,
                    media_urls=media_urls,
                    scheduled_for=schedule,
                    **post_kwargs,
                )
                return {
                    "status": "success",
                    "platform": platform,
                    "post_id": result.get("id"),
                    "url": result.get("url"),
                    "content": content,
                    "enhanced": enhance,
                    "scheduled": schedule is not None,
                    "platform_options": platform_data_summary.get(platform),
                }
            except Exception as e:
                return {
                    "status": "error",
                    "platform": platform,
                    "error": str(e),
                    "content": content,
                }

        # Multi-platform distribution with platform-specific options
        result = self._distribute_with_options(
            content=content,
            platforms=platforms,
            media_urls=media_urls,
            scheduled_for=schedule,
            platform_options=platform_options,
        )

        return {
            "status": "success" if result["summary"]["failed"] == 0 else "partial",
            "results": result["results"],
            "summary": result["summary"],
            "content": content,
            "enhanced": enhance,
            "scheduled": schedule is not None,
            "platform_options": platform_data_summary,
        }

    def _build_post_kwargs(
        self, platform: str, content: str, options: PlatformOptions | None
    ) -> dict[str, Any]:
        """
        Build platform-specific kwargs for late_client.post_to_platform().

        Args:
            platform: Target platform name
            content: Post content (for Reddit title extraction)
            options: Platform options container

        Returns:
            Dictionary of kwargs to pass to post_to_platform
        """
        kwargs = {}

        if not options:
            return kwargs

        platform = platform.lower()

        # Get platform-specific data
        platform_data = options.get_platform_data(platform)
        if platform_data:
            kwargs["platform_specific_data"] = platform_data

        # Handle Reddit title (passed as top-level param, not platformSpecificData)
        if platform == "reddit":
            kwargs["title"] = options.get_reddit_title(content)

        return kwargs

    def _distribute_with_options(
        self,
        content: str,
        platforms: list[str],
        media_urls: list[str] | None,
        scheduled_for: str | None,
        platform_options: PlatformOptions | None,
    ) -> dict[str, Any]:
        """
        Distribute to multiple platforms with individual platform options.

        Unlike distribute_multi_platform, this posts to each platform
        individually to support different platform-specific options.

        Args:
            content: Post content
            platforms: List of target platforms
            media_urls: Optional media URLs
            scheduled_for: Optional schedule datetime
            platform_options: Platform-specific options

        Returns:
            Dictionary with results and summary
        """
        results = {}
        successful = 0
        failed = 0

        print(f"[INFO] Distributing to {len(platforms)} platforms...")

        for platform in platforms:
            try:
                post_kwargs = self._build_post_kwargs(platform, content, platform_options)

                result = self.late_client.post_to_platform(
                    content=content,
                    platform=platform,
                    media_urls=media_urls,
                    scheduled_for=scheduled_for,
                    **post_kwargs,
                )
                results[platform] = {"success": True, "data": result}
                successful += 1

            except Exception as e:
                results[platform] = {"success": False, "error": str(e)}
                failed += 1

        summary = {"total": len(platforms), "successful": successful, "failed": failed}

        print("\n[SUMMARY] Distribution complete")
        print(f"  Successful: {successful}/{len(platforms)}")
        print(f"  Failed: {failed}/{len(platforms)}")

        return {"results": results, "summary": summary}


def _build_platform_options(args) -> PlatformOptions | None:
    """
    Build PlatformOptions from CLI arguments.

    Args:
        args: Parsed argparse namespace

    Returns:
        PlatformOptions object or None if no options specified
    """
    has_options = False

    # Build Instagram options
    instagram = None
    if any([args.ig_type, args.ig_first_comment, args.ig_collaborators, args.ig_no_feed]):
        collaborators = None
        if args.ig_collaborators:
            collaborators = [c.strip() for c in args.ig_collaborators.split(",")]

        instagram = InstagramOptions(
            content_type=args.ig_type,
            first_comment=args.ig_first_comment,
            share_to_feed=not args.ig_no_feed,
            collaborators=collaborators,
        )
        has_options = True

    # Build LinkedIn options
    linkedin = None
    if any([args.li_first_comment, args.li_no_link_preview]):
        linkedin = LinkedInOptions(
            first_comment=args.li_first_comment, disable_link_preview=args.li_no_link_preview
        )
        has_options = True

    # Build Threads options
    threads = None
    if any([args.threads_auto_thread, args.threads_number]):
        threads = ThreadsOptions(
            auto_thread=args.threads_auto_thread, thread_number=args.threads_number
        )
        has_options = True

    # Build Twitter options
    twitter = None
    if args.twitter_thread:
        twitter = TwitterOptions(auto_thread=True)
        has_options = True

    # Build Reddit options
    reddit = None
    if args.reddit_title:
        reddit = RedditOptions(title=args.reddit_title)
        has_options = True

    # Parse raw JSON platform options
    raw_platform_data = None
    if args.platform_options:
        try:
            raw_platform_data = json.loads(args.platform_options)
            has_options = True
        except json.JSONDecodeError as e:
            print(f"[WARNING] Invalid --platform-options JSON: {e}")

    if not has_options:
        return None

    return PlatformOptions(
        instagram=instagram,
        linkedin=linkedin,
        threads=threads,
        twitter=twitter,
        reddit=reddit,
        raw_platform_data=raw_platform_data,
    )


def main():
    """CLI entry point for the poster."""
    parser = argparse.ArgumentParser(
        description="Social Slash Content Poster",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python poster.py --content "Hello world" --platforms linkedin
  python poster.py --content "New video!" --platforms tiktok,instagram --enhance
  python poster.py --content "Test post" --platforms linkedin --dry-run
  python poster.py --content "Scheduled" --platforms twitter --schedule "2024-12-01T10:00:00Z"

Platform-Specific Examples:
  # Reddit with explicit title
  python poster.py --content "Post body" --platforms reddit --reddit-title "My Title"

  # Instagram story with first comment
  python poster.py --content "Check this!" --platforms instagram --ig-type story --ig-first-comment "Links in bio!"

  # LinkedIn with first comment
  python poster.py --content "Announcement" --platforms linkedin --li-first-comment "DM for details"

  # Threads auto-threading
  python poster.py --content "Long content..." --platforms threads --threads-auto-thread
        """,
    )

    parser.add_argument("--content", "-c", required=True, help="Content to post")

    parser.add_argument(
        "--platforms",
        "-p",
        required=True,
        help="Comma-separated list of platforms (e.g., linkedin,twitter)",
    )

    parser.add_argument(
        "--enhance", "-e", action="store_true", help="Enable AI content enhancement"
    )

    parser.add_argument(
        "--ai-provider",
        choices=["gemini", "anthropic"],
        default="gemini",
        help="AI provider for enhancement (default: gemini)",
    )

    parser.add_argument("--media", "-m", help="Comma-separated list of media URLs")

    parser.add_argument(
        "--schedule", "-s", help="ISO datetime for scheduling (e.g., 2024-12-01T10:00:00Z)"
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate posting without actually posting"
    )

    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    # ==========================================================================
    # Platform-Specific Options
    # ==========================================================================

    # Reddit options
    reddit_group = parser.add_argument_group("Reddit Options")
    reddit_group.add_argument(
        "--reddit-title", help="Post title (auto-generated from first line if not provided)"
    )

    # Instagram options
    ig_group = parser.add_argument_group("Instagram Options")
    ig_group.add_argument(
        "--ig-type",
        choices=["story", "post", "reel"],
        help="Content type (default: auto-detect from media)",
    )
    ig_group.add_argument("--ig-first-comment", help="First comment to post after publishing")
    ig_group.add_argument(
        "--ig-collaborators", help="Collaborator usernames (comma-separated, max 3)"
    )
    ig_group.add_argument(
        "--ig-no-feed", action="store_true", help="For reels, do not show on main feed"
    )

    # LinkedIn options
    li_group = parser.add_argument_group("LinkedIn Options")
    li_group.add_argument("--li-first-comment", help="First comment to post after publishing")
    li_group.add_argument(
        "--li-no-link-preview", action="store_true", help="Disable link preview card"
    )

    # Threads options
    threads_group = parser.add_argument_group("Threads Options")
    threads_group.add_argument(
        "--threads-auto-thread",
        action="store_true",
        help="Auto-break long content into threaded replies",
    )
    threads_group.add_argument(
        "--threads-number", action="store_true", help="Add numbering to thread posts (1/n, 2/n...)"
    )

    # Twitter options
    twitter_group = parser.add_argument_group("Twitter/X Options")
    twitter_group.add_argument(
        "--twitter-thread", action="store_true", help="Auto-break long content into tweet thread"
    )

    # Advanced: Raw JSON platform options
    parser.add_argument(
        "--platform-options", help="JSON string with raw platform-specific options (advanced)"
    )

    args = parser.parse_args()

    # Parse platforms
    platforms = [p.strip().lower() for p in args.platforms.split(",")]

    # Parse media URLs
    media_urls = None
    if args.media:
        media_urls = [u.strip() for u in args.media.split(",")]

    # Build platform-specific options
    platform_options = _build_platform_options(args)

    # Create poster and execute
    poster = Poster(skip_late_init=args.dry_run)

    result = poster.post(
        content=args.content,
        platforms=platforms,
        enhance=args.enhance,
        ai_provider=args.ai_provider,
        media_urls=media_urls,
        schedule=args.schedule,
        dry_run=args.dry_run,
        platform_options=platform_options,
    )

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")

        if args.dry_run:
            print("\n[DRY-RUN] Would post:")
            print(
                f"  Content: {result.get('enhanced_content') or result.get('original_content', '')[:100]}..."
            )
            print(f"  Platforms: {', '.join(result.get('platforms', []))}")
            if result.get("media"):
                print(f"  Media: {len(result['media'])} files")
            if result.get("schedule"):
                print(f"  Scheduled for: {result['schedule']}")

            # Display platform-specific options
            platform_opts = result.get("platform_options", {})
            if platform_opts:
                print("\n  Platform Options:")
                for platform, opts in platform_opts.items():
                    if platform == "reddit_title":
                        print(f"    Reddit Title: {opts}")
                    elif isinstance(opts, dict):
                        print(f"    {platform.title()}:")
                        for key, val in opts.items():
                            print(f"      - {key}: {val}")

            print("\n  No actual post was made.")

        elif status == "success":
            print(f"\n[SUCCESS] Posted to: {', '.join(platforms)}")

            if "post_id" in result:
                print(f"  Post ID: {result['post_id']}")
            if "url" in result:
                print(f"  URL: {result['url']}")

            if "summary" in result:
                summary = result["summary"]
                print(f"  Successful: {summary['successful']}/{summary['total']}")

        elif status == "partial":
            print("\n[PARTIAL] Some posts failed:")
            summary = result.get("summary", {})
            print(f"  Successful: {summary.get('successful', 0)}/{summary.get('total', 0)}")
            print(f"  Failed: {summary.get('failed', 0)}")

        elif status == "error":
            print(f"\n[ERROR] Failed to post to {result.get('platform', 'unknown')}")
            print(f"  Error: {result.get('error', 'Unknown error')}")

        if result.get("enhanced"):
            print(f"\n  AI Enhancement: Enabled ({args.ai_provider})")

        if result.get("scheduled"):
            print(f"  Scheduled: {args.schedule}")


if __name__ == "__main__":
    main()
