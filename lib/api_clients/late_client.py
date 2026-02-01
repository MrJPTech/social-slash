#!/usr/bin/env python3
"""
Late SDK Distribution Client

Wrapper around the Late SDK for multi-platform social media distribution.
Provides account management, posting, scheduling, and analytics.

Documentation: https://docs.getlate.dev
"""

import os
from typing import Dict, List, Optional, Any
from late import Late


class LateDistributionClient:
    """
    High-level client for Late SDK distribution operations.

    Features:
    - Account caching for performance
    - Multi-platform distribution
    - Scheduled posting support
    - Analytics tracking

    Usage:
        client = LateDistributionClient()
        result = client.post_to_platform(
            content="Hello world!",
            platform="linkedin"
        )
    """

    # Supported platforms
    SUPPORTED_PLATFORMS = [
        'linkedin', 'tiktok', 'instagram', 'youtube', 'twitter',
        'facebook', 'pinterest', 'threads', 'bluesky', 'reddit',
        'snapchat', 'telegram', 'google_business'
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Late distribution client.

        Args:
            api_key: Late API key. Defaults to LATE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('LATE_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Late API key not found. Set LATE_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = Late(api_key=self.api_key)
        self._account_cache: Dict[str, str] = {}

    def get_accounts(self) -> List[Dict[str, Any]]:
        """
        Get all connected social media accounts.

        Returns:
            List of account dictionaries with id, platform, name, etc.
        """
        try:
            accounts = self.client.accounts.list()
            print(f"[INFO] Found {len(accounts)} connected accounts")
            return accounts
        except Exception as e:
            print(f"[ERROR] Failed to fetch accounts: {e}")
            raise

    def get_account_id(self, platform: str) -> Optional[str]:
        """
        Get account ID for a specific platform.
        Uses caching to avoid repeated API calls.

        Args:
            platform: Platform name (e.g., 'linkedin', 'twitter')

        Returns:
            Account ID string or None if not found
        """
        platform = platform.lower()

        # Check cache first
        if platform in self._account_cache:
            return self._account_cache[platform]

        # Fetch accounts and find matching platform
        accounts = self.get_accounts()

        for account in accounts:
            account_platform = account.get('platform', '').lower()
            account_id = account.get('id')

            # Cache all accounts while we're at it
            if account_platform and account_id:
                self._account_cache[account_platform] = account_id

        return self._account_cache.get(platform)

    def post_to_platform(
        self,
        content: str,
        platform: str,
        media_urls: Optional[List[str]] = None,
        scheduled_for: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Post content to a single platform.

        Args:
            content: Post text content
            platform: Target platform (e.g., 'linkedin')
            media_urls: Optional list of media URLs to attach
            scheduled_for: Optional ISO datetime for scheduling
            **kwargs: Additional platform-specific parameters

        Returns:
            Post result dictionary with id, status, url, etc.
        """
        platform = platform.lower()

        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported: {', '.join(self.SUPPORTED_PLATFORMS)}"
            )

        # Get account ID for platform
        account_id = self.get_account_id(platform)

        if not account_id:
            raise ValueError(
                f"No {platform} account connected. "
                f"Connect an account at https://app.getlate.dev"
            )

        # Build post payload
        payload = {
            'account_id': account_id,
            'content': content,
        }

        if media_urls:
            payload['media'] = media_urls

        if scheduled_for:
            payload['scheduled_for'] = scheduled_for

        # Add any additional kwargs
        payload.update(kwargs)

        try:
            print(f"[INFO] Posting to {platform}...")
            result = self.client.posts.create(**payload)

            post_id = result.get('id', 'unknown')
            status = result.get('status', 'unknown')

            print(f"[SUCCESS] Posted to {platform}")
            print(f"  Post ID: {post_id}")
            print(f"  Status: {status}")

            if result.get('url'):
                print(f"  URL: {result['url']}")

            return result

        except Exception as e:
            print(f"[ERROR] Failed to post to {platform}: {e}")
            raise

    def distribute_multi_platform(
        self,
        content: str,
        platforms: List[str],
        media_urls: Optional[List[str]] = None,
        scheduled_for: Optional[str] = None,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """
        Distribute content to multiple platforms.

        Args:
            content: Post text content
            platforms: List of target platforms
            media_urls: Optional list of media URLs
            scheduled_for: Optional ISO datetime for scheduling
            stop_on_error: If True, stop on first failure

        Returns:
            Dictionary with 'results' and 'summary' keys
        """
        results = {}
        successful = 0
        failed = 0

        print(f"[INFO] Distributing to {len(platforms)} platforms...")

        for platform in platforms:
            try:
                result = self.post_to_platform(
                    content=content,
                    platform=platform,
                    media_urls=media_urls,
                    scheduled_for=scheduled_for
                )
                results[platform] = {
                    'success': True,
                    'data': result
                }
                successful += 1

            except Exception as e:
                results[platform] = {
                    'success': False,
                    'error': str(e)
                }
                failed += 1

                if stop_on_error:
                    print(f"[ERROR] Stopping due to error on {platform}")
                    break

        summary = {
            'total': len(platforms),
            'successful': successful,
            'failed': failed
        }

        print(f"\n[SUMMARY] Distribution complete")
        print(f"  Successful: {successful}/{len(platforms)}")
        print(f"  Failed: {failed}/{len(platforms)}")

        return {
            'results': results,
            'summary': summary
        }

    def get_post_status(self, post_id: str) -> Dict[str, Any]:
        """
        Get the current status of a post.

        Args:
            post_id: The post ID to check

        Returns:
            Post status dictionary
        """
        try:
            return self.client.posts.get(post_id)
        except Exception as e:
            print(f"[ERROR] Failed to get post status: {e}")
            raise

    def get_analytics(self, post_id: str) -> Dict[str, Any]:
        """
        Get analytics for a post.

        Args:
            post_id: The post ID to get analytics for

        Returns:
            Analytics dictionary with engagement metrics
        """
        try:
            return self.client.posts.analytics(post_id)
        except Exception as e:
            print(f"[ERROR] Failed to get analytics: {e}")
            raise

    def clear_cache(self):
        """Clear the account cache."""
        self._account_cache.clear()
        print("[INFO] Account cache cleared")


# Convenience function for backward compatibility
def post_to_linkedin(content: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick function to post to LinkedIn.

    Args:
        content: Post text content
        api_key: Optional API key (defaults to env var)

    Returns:
        Post result dictionary
    """
    client = LateDistributionClient(api_key=api_key)
    return client.post_to_platform(content=content, platform='linkedin')


# Example usage
if __name__ == "__main__":
    # Demo usage
    client = LateDistributionClient()

    # List accounts
    accounts = client.get_accounts()
    print("\nConnected accounts:")
    for acc in accounts:
        print(f"  - {acc.get('platform')}: {acc.get('name', 'Unknown')}")

    # Example post (dry run - uncomment to actually post)
    # result = client.post_to_platform(
    #     content="Hello from Social Slash! 🚀",
    #     platform="linkedin"
    # )
