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
from typing import Dict, List, Optional, Any

# Add lib to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_clients.late_client import LateDistributionClient


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
                print(f"[INFO] AI enhancement enabled (Gemini)")

            elif provider == "anthropic":
                from ai.anthropic_client import AnthropicClient
                self.ai_client = AnthropicClient()
                self._ai_provider = "anthropic"
                print(f"[INFO] AI enhancement enabled (Anthropic)")

            else:
                raise ValueError(f"Unknown AI provider: {provider}")

        except ImportError as e:
            print(f"[WARNING] AI client not available: {e}")
            self.ai_client = None
        except ValueError as e:
            print(f"[WARNING] AI client not configured: {e}")
            self.ai_client = None

    def enhance_content(
        self,
        content: str,
        platform: str,
        provider: str = "gemini"
    ) -> str:
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
            enhanced = result.get('enhanced_content', content)

            if enhanced != content:
                print(f"[INFO] Content enhanced for {platform}")
                changes = result.get('changes_made', [])
                for change in changes[:3]:
                    print(f"  - {change}")

            return enhanced

        except Exception as e:
            print(f"[WARNING] Enhancement failed, using original: {e}")
            return content

    def post(
        self,
        content: str,
        platforms: List[str],
        enhance: bool = False,
        ai_provider: str = "gemini",
        media_urls: Optional[List[str]] = None,
        schedule: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
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

        Returns:
            Dictionary with results and summary
        """
        original_content = content

        # Enhance content if requested
        if enhance:
            # Use first platform for enhancement context
            content = self.enhance_content(content, platforms[0], ai_provider)

        # Dry run mode
        if dry_run:
            return {
                "status": "dry-run",
                "original_content": original_content,
                "enhanced_content": content if enhance else None,
                "platforms": platforms,
                "media": media_urls,
                "schedule": schedule,
                "would_post": True
            }

        # Single platform posting
        if len(platforms) == 1:
            try:
                result = self.late_client.post_to_platform(
                    content=content,
                    platform=platforms[0],
                    media_urls=media_urls,
                    scheduled_for=schedule
                )
                return {
                    "status": "success",
                    "platform": platforms[0],
                    "post_id": result.get('id'),
                    "url": result.get('url'),
                    "content": content,
                    "enhanced": enhance,
                    "scheduled": schedule is not None
                }
            except Exception as e:
                return {
                    "status": "error",
                    "platform": platforms[0],
                    "error": str(e),
                    "content": content
                }

        # Multi-platform distribution
        result = self.late_client.distribute_multi_platform(
            content=content,
            platforms=platforms,
            media_urls=media_urls,
            scheduled_for=schedule
        )

        return {
            "status": "success" if result['summary']['failed'] == 0 else "partial",
            "results": result['results'],
            "summary": result['summary'],
            "content": content,
            "enhanced": enhance,
            "scheduled": schedule is not None
        }


def main():
    """CLI entry point for the poster."""
    parser = argparse.ArgumentParser(
        description='Social Slash Content Poster',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python poster.py --content "Hello world" --platforms linkedin
  python poster.py --content "New video!" --platforms tiktok,instagram --enhance
  python poster.py --content "Test post" --platforms linkedin --dry-run
  python poster.py --content "Scheduled" --platforms twitter --schedule "2024-12-01T10:00:00Z"
        """
    )

    parser.add_argument(
        '--content', '-c',
        required=True,
        help='Content to post'
    )

    parser.add_argument(
        '--platforms', '-p',
        required=True,
        help='Comma-separated list of platforms (e.g., linkedin,twitter)'
    )

    parser.add_argument(
        '--enhance', '-e',
        action='store_true',
        help='Enable AI content enhancement'
    )

    parser.add_argument(
        '--ai-provider',
        choices=['gemini', 'anthropic'],
        default='gemini',
        help='AI provider for enhancement (default: gemini)'
    )

    parser.add_argument(
        '--media', '-m',
        help='Comma-separated list of media URLs'
    )

    parser.add_argument(
        '--schedule', '-s',
        help='ISO datetime for scheduling (e.g., 2024-12-01T10:00:00Z)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate posting without actually posting'
    )

    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )

    args = parser.parse_args()

    # Parse platforms
    platforms = [p.strip().lower() for p in args.platforms.split(',')]

    # Parse media URLs
    media_urls = None
    if args.media:
        media_urls = [u.strip() for u in args.media.split(',')]

    # Create poster and execute
    poster = Poster(skip_late_init=args.dry_run)

    result = poster.post(
        content=args.content,
        platforms=platforms,
        enhance=args.enhance,
        ai_provider=args.ai_provider,
        media_urls=media_urls,
        schedule=args.schedule,
        dry_run=args.dry_run
    )

    # Output results
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = result.get('status', 'unknown')

        if args.dry_run:
            print("\n[DRY-RUN] Would post:")
            print(f"  Content: {result.get('enhanced_content') or result.get('original_content', '')[:100]}...")
            print(f"  Platforms: {', '.join(result.get('platforms', []))}")
            if result.get('media'):
                print(f"  Media: {len(result['media'])} files")
            if result.get('schedule'):
                print(f"  Scheduled for: {result['schedule']}")
            print("\n  No actual post was made.")

        elif status == 'success':
            print(f"\n[SUCCESS] Posted to: {', '.join(platforms)}")

            if 'post_id' in result:
                print(f"  Post ID: {result['post_id']}")
            if 'url' in result:
                print(f"  URL: {result['url']}")

            if 'summary' in result:
                summary = result['summary']
                print(f"  Successful: {summary['successful']}/{summary['total']}")

        elif status == 'partial':
            print(f"\n[PARTIAL] Some posts failed:")
            summary = result.get('summary', {})
            print(f"  Successful: {summary.get('successful', 0)}/{summary.get('total', 0)}")
            print(f"  Failed: {summary.get('failed', 0)}")

        elif status == 'error':
            print(f"\n[ERROR] Failed to post to {result.get('platform', 'unknown')}")
            print(f"  Error: {result.get('error', 'Unknown error')}")

        if result.get('enhanced'):
            print(f"\n  AI Enhancement: Enabled ({args.ai_provider})")

        if result.get('scheduled'):
            print(f"  Scheduled: {args.schedule}")


if __name__ == "__main__":
    main()
