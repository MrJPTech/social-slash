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

    def get_accounts(self) -> List[Any]:
        """
        Get all connected social media accounts.

        Returns:
            List of SocialAccount objects with id, platform, name, etc.
        """
        try:
            response = self.client.accounts.list()
            accounts = response.accounts if hasattr(response, 'accounts') else []
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

        # Normalize platform names
        platform_map = {
            'google_business': 'googlebusiness',
            'x': 'twitter',
        }
        platform = platform_map.get(platform, platform)

        # Check cache first
        if platform in self._account_cache:
            return self._account_cache[platform]

        # Fetch accounts and find matching platform
        accounts = self.get_accounts()

        for account in accounts:
            # Handle SocialAccount objects from Late SDK
            account_platform = getattr(account, 'platform', '').lower()
            account_id = getattr(account, 'field_id', None)

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
        publish_now: bool = True,
        title: Optional[str] = None,
        platform_specific_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Post content to a single platform.

        Args:
            content: Post text content
            platform: Target platform (e.g., 'linkedin')
            media_urls: Optional list of media URLs to attach
            scheduled_for: Optional ISO datetime for scheduling
            publish_now: If True, publish immediately (default True)
            title: Optional post title (required for Reddit, optional for YouTube/Pinterest)
            platform_specific_data: Optional dict with platform-specific options
                (maps to Late SDK's platformSpecificData field)
            **kwargs: Additional platform-specific parameters

        Returns:
            Post result dictionary with id, status, url, etc.
        """
        platform = platform.lower()

        # Normalize platform names for Late SDK
        platform_map = {
            'google_business': 'googlebusiness',
            'x': 'twitter',
        }
        late_platform = platform_map.get(platform, platform)

        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform: {platform}. "
                f"Supported: {', '.join(self.SUPPORTED_PLATFORMS)}"
            )

        # Verify account is connected
        account_id = self.get_account_id(platform)
        if not account_id:
            raise ValueError(
                f"No {platform} account connected. "
                f"Connect an account at https://app.getlate.dev"
            )

        try:
            print(f"[INFO] Posting to {platform}...")

            # Late SDK requires platforms as list of dicts with platform and accountId
            platforms_payload = [{
                "platform": late_platform,
                "accountId": account_id
            }]

            # Add platform-specific data if provided
            if platform_specific_data:
                platforms_payload[0]["platformSpecificData"] = platform_specific_data
                print(f"[INFO] Platform-specific options: {list(platform_specific_data.keys())}")

            # Format media_items as list of dicts (Late SDK requires type + url)
            formatted_media = None
            if media_urls:
                formatted_media = []
                for item in media_urls:
                    if isinstance(item, str):
                        # Determine type from URL extension
                        url_lower = item.lower().split('?')[0]
                        if any(url_lower.endswith(ext) for ext in ('.mp4', '.mov', '.avi', '.webm')):
                            media_type = "video"
                        else:
                            media_type = "image"
                        formatted_media.append({"type": media_type, "url": item})
                    elif isinstance(item, dict):
                        # Already in correct format
                        formatted_media.append(item)

            # Build create params
            create_params = {
                "content": content,
                "platforms": platforms_payload,
                "media_items": formatted_media,
                "scheduled_for": scheduled_for,
                "publish_now": publish_now if not scheduled_for else False,
            }

            # Add title if provided (for Reddit, YouTube, Pinterest)
            if title:
                create_params["title"] = title
                print(f"[INFO] Post title: {title[:50]}{'...' if len(title) > 50 else ''}")

            result = self.client.posts.create(**create_params, **kwargs)

            # Handle response object
            post_id = getattr(result, 'field_id', None) or getattr(result, 'id', 'unknown')
            status = getattr(result, 'status', 'unknown')

            print(f"[SUCCESS] Posted to {platform}")
            print(f"  Post ID: {post_id}")
            print(f"  Status: {status}")

            post_url = getattr(result, 'url', None)
            if post_url:
                print(f"  URL: {post_url}")

            # Convert response to dict for consistency
            if hasattr(result, 'model_dump'):
                return result.model_dump()
            elif hasattr(result, 'dict'):
                return result.dict()
            else:
                return {'id': post_id, 'status': status, 'url': post_url}

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
