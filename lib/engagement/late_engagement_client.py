#!/usr/bin/env python3
"""
Late SDK Engagement Client - Unified Inbox for Comments and DMs

Wraps Late API inbox endpoints for cross-platform engagement automation.
Handles comments and direct messages across all supported platforms.

Requires Late Inbox Add-on subscription.
Documentation: https://docs.getlate.dev/core/comments, /core/messages
"""

import os
from typing import Any

import httpx


class LateEngagementClient:
    """
    Unified client for Late API inbox operations.

    Handles comments and DMs across all platforms with a single API.
    Provides methods for:
    - Listing and replying to comments
    - Managing DM conversations
    - Comment moderation (hide, like, delete)
    """

    BASE_URL = "https://getlate.dev/api/v1"

    # Comment-supported platforms
    COMMENT_PLATFORMS = [
        "facebook",
        "instagram",
        "youtube",
        "linkedin",
        "reddit",
        "bluesky",
        "tiktok",
    ]

    # DM-supported platforms
    DM_PLATFORMS = ["facebook", "instagram", "bluesky", "reddit", "telegram"]

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Late engagement client.

        Args:
            api_key: Late API key. Defaults to LATE_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("LATE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Late API key not found. Set LATE_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        self.client = httpx.Client(base_url=self.BASE_URL, headers=self.headers, timeout=30.0)

        print("[INFO] Late engagement client initialized")

    # ─────────────────────────────────────────────────────────────
    # COMMENTS API
    # ─────────────────────────────────────────────────────────────

    def list_posts_with_comments(
        self,
        platform: str | None = None,
        min_comments: int = 1,
        limit: int = 50,
        cursor: str | None = None,
        sort_by: str = "date",
        sort_order: str = "desc",
    ) -> dict[str, Any]:
        """
        List posts that have comments.

        Args:
            platform: Filter by platform (optional)
            min_comments: Minimum comment count (default: 1)
            limit: Max results per page (default: 50)
            cursor: Pagination cursor
            sort_by: Sort field (date, comments)
            sort_order: Sort direction (asc, desc)

        Returns:
            Dictionary with 'data' (posts) and 'cursor' for pagination
        """
        params = {
            "minComments": min_comments,
            "limit": limit,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        if platform:
            if platform not in self.COMMENT_PLATFORMS:
                print(f"[WARNING] Platform '{platform}' may not support comments")
            params["platform"] = platform

        if cursor:
            params["cursor"] = cursor

        try:
            response = self.client.get("/inbox/comments", params=params)
            response.raise_for_status()
            result = response.json()
            print(f"[INFO] Found {len(result.get('data', []))} posts with comments")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to list posts: {e.response.status_code}")
            raise

    def get_post_comments(
        self, post_id: str, limit: int = 50, cursor: str | None = None
    ) -> dict[str, Any]:
        """
        Get comments for a specific post.

        Args:
            post_id: Late post ID
            limit: Max comments per page
            cursor: Pagination cursor

        Returns:
            Dictionary with 'data' (comments) and 'cursor'
        """
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        try:
            response = self.client.get(f"/inbox/comments/{post_id}", params=params)
            response.raise_for_status()
            result = response.json()
            print(f"[INFO] Found {len(result.get('data', []))} comments on post")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to get comments: {e.response.status_code}")
            raise

    def reply_to_comment(
        self,
        post_id: str,
        account_id: str,
        message: str,
        comment_id: str | None = None,
        subreddit: str | None = None,
    ) -> dict[str, Any]:
        """
        Reply to a post or specific comment.

        Args:
            post_id: Late post ID
            account_id: Account ID to reply from
            message: Reply text
            comment_id: Specific comment to reply to (optional)
            subreddit: Subreddit name (Reddit only)

        Returns:
            API response with reply details
        """
        payload = {"accountId": account_id, "message": message}

        if comment_id:
            payload["commentId"] = comment_id

        if subreddit:
            payload["subreddit"] = subreddit

        try:
            response = self.client.post(f"/inbox/comments/{post_id}", json=payload)
            response.raise_for_status()
            result = response.json()
            print("[SUCCESS] Reply posted")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to reply: {e.response.status_code} - {e.response.text}")
            raise

    def delete_comment(self, post_id: str, comment_id: str) -> dict[str, Any]:
        """
        Delete a comment.

        Args:
            post_id: Late post ID
            comment_id: Comment ID to delete

        Returns:
            API response
        """
        try:
            response = self.client.delete(
                f"/inbox/comments/{post_id}", params={"commentId": comment_id}
            )
            response.raise_for_status()
            print("[SUCCESS] Comment deleted")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to delete comment: {e.response.status_code}")
            raise

    def hide_comment(self, post_id: str, comment_id: str) -> dict[str, Any]:
        """
        Hide a comment (Facebook/Instagram).

        Args:
            post_id: Late post ID
            comment_id: Comment ID to hide

        Returns:
            API response
        """
        try:
            response = self.client.post(f"/inbox/comments/{post_id}/{comment_id}/hide")
            response.raise_for_status()
            print("[SUCCESS] Comment hidden")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to hide comment: {e.response.status_code}")
            raise

    def like_comment(self, post_id: str, comment_id: str) -> dict[str, Any]:
        """
        Like a comment.

        Args:
            post_id: Late post ID
            comment_id: Comment ID to like

        Returns:
            API response
        """
        try:
            response = self.client.post(f"/inbox/comments/{post_id}/{comment_id}/like")
            response.raise_for_status()
            print("[SUCCESS] Comment liked")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to like comment: {e.response.status_code}")
            raise

    def private_reply(
        self, post_id: str, comment_id: str, account_id: str, message: str
    ) -> dict[str, Any]:
        """
        Send private reply to commenter (Instagram only).

        Args:
            post_id: Late post ID
            comment_id: Comment ID
            account_id: Account to send from
            message: Private message text

        Returns:
            API response
        """
        payload = {"accountId": account_id, "message": message}

        try:
            response = self.client.post(
                f"/inbox/comments/{post_id}/{comment_id}/private-reply", json=payload
            )
            response.raise_for_status()
            print("[SUCCESS] Private reply sent")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to send private reply: {e.response.status_code}")
            raise

    # ─────────────────────────────────────────────────────────────
    # MESSAGES/DMS API
    # ─────────────────────────────────────────────────────────────

    def list_conversations(
        self,
        platform: str | None = None,
        status: str = "active",
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        List DM conversations across platforms.

        Args:
            platform: Filter by platform (optional)
            status: Filter by status (active, archived)
            limit: Max results per page
            cursor: Pagination cursor

        Returns:
            Dictionary with 'data' (conversations) and 'cursor'
        """
        params = {"status": status, "limit": limit, "sortOrder": "desc"}

        if platform:
            if platform not in self.DM_PLATFORMS:
                print(f"[WARNING] Platform '{platform}' may not support DMs")
            params["platform"] = platform

        if cursor:
            params["cursor"] = cursor

        try:
            response = self.client.get("/inbox/conversations", params=params)
            response.raise_for_status()
            result = response.json()
            print(f"[INFO] Found {len(result.get('data', []))} conversations")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to list conversations: {e.response.status_code}")
            raise

    def get_conversation(self, conversation_id: str, account_id: str) -> dict[str, Any]:
        """
        Get conversation details.

        Args:
            conversation_id: Late conversation ID
            account_id: Account ID

        Returns:
            Conversation details
        """
        try:
            response = self.client.get(
                f"/inbox/conversations/{conversation_id}", params={"accountId": account_id}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to get conversation: {e.response.status_code}")
            raise

    def get_messages(
        self, conversation_id: str, account_id: str, limit: int = 50, cursor: str | None = None
    ) -> dict[str, Any]:
        """
        Get messages in a conversation.

        Args:
            conversation_id: Late conversation ID
            account_id: Account ID
            limit: Max messages per page
            cursor: Pagination cursor

        Returns:
            Dictionary with 'data' (messages) and 'cursor'
        """
        params = {"accountId": account_id, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        try:
            response = self.client.get(
                f"/inbox/conversations/{conversation_id}/messages", params=params
            )
            response.raise_for_status()
            result = response.json()
            print(f"[INFO] Found {len(result.get('data', []))} messages")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to get messages: {e.response.status_code}")
            raise

    def send_message(self, conversation_id: str, account_id: str, message: str) -> dict[str, Any]:
        """
        Send a DM reply.

        Args:
            conversation_id: Late conversation ID
            account_id: Account to send from
            message: Message text

        Returns:
            API response with message details
        """
        payload = {"accountId": account_id, "message": message}

        try:
            response = self.client.post(
                f"/inbox/conversations/{conversation_id}/messages", json=payload
            )
            response.raise_for_status()
            result = response.json()
            print("[SUCCESS] Message sent")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to send message: {e.response.status_code} - {e.response.text}")
            raise

    def archive_conversation(self, conversation_id: str, account_id: str) -> dict[str, Any]:
        """
        Archive a conversation.

        Args:
            conversation_id: Late conversation ID
            account_id: Account ID

        Returns:
            API response
        """
        payload = {"accountId": account_id, "status": "archived"}

        try:
            response = self.client.put(f"/inbox/conversations/{conversation_id}", json=payload)
            response.raise_for_status()
            print("[SUCCESS] Conversation archived")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to archive conversation: {e.response.status_code}")
            raise

    # ─────────────────────────────────────────────────────────────
    # WEBHOOKS
    # ─────────────────────────────────────────────────────────────

    def register_webhook(
        self, url: str, events: list[str], secret: str | None = None
    ) -> dict[str, Any]:
        """
        Register a webhook for events.

        Args:
            url: Webhook URL
            events: List of event types ['message.received', 'post.published']
            secret: Optional webhook secret for signature verification

        Returns:
            Webhook registration details
        """
        payload = {"url": url, "events": events}
        if secret:
            payload["secret"] = secret

        try:
            response = self.client.post("/webhooks", json=payload)
            response.raise_for_status()
            result = response.json()
            print(f"[SUCCESS] Webhook registered for events: {events}")
            return result
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to register webhook: {e.response.status_code}")
            raise

    def list_webhooks(self) -> dict[str, Any]:
        """
        List registered webhooks.

        Returns:
            List of webhooks
        """
        try:
            response = self.client.get("/webhooks")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to list webhooks: {e.response.status_code}")
            raise

    def delete_webhook(self, webhook_id: str) -> dict[str, Any]:
        """
        Delete a webhook.

        Args:
            webhook_id: Webhook ID to delete

        Returns:
            API response
        """
        try:
            response = self.client.delete(f"/webhooks/{webhook_id}")
            response.raise_for_status()
            print("[SUCCESS] Webhook deleted")
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"[ERROR] Failed to delete webhook: {e.response.status_code}")
            raise

    # ─────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ─────────────────────────────────────────────────────────────

    def test_connection(self) -> bool:
        """
        Test API connection.

        Returns:
            True if connection successful
        """
        try:
            # Try listing webhooks as a lightweight test
            self.list_webhooks()
            print("[SUCCESS] API connection verified")
            return True
        except Exception as e:
            print(f"[ERROR] API connection failed: {e}")
            return False

    def get_supported_platforms(self, feature: str = "comments") -> list[str]:
        """
        Get platforms supported for a feature.

        Args:
            feature: 'comments' or 'dms'

        Returns:
            List of supported platforms
        """
        if feature == "comments":
            return self.COMMENT_PLATFORMS.copy()
        elif feature in ["dms", "messages"]:
            return self.DM_PLATFORMS.copy()
        else:
            return []

    def close(self):
        """Close the HTTP client."""
        self.client.close()
        print("[INFO] Client closed")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Example usage
if __name__ == "__main__":
    try:
        client = LateEngagementClient()

        # Test connection
        if client.test_connection():
            # List posts with comments
            posts = client.list_posts_with_comments(limit=5)
            print(f"\nPosts with comments: {len(posts.get('data', []))}")

            for post in posts.get("data", [])[:3]:
                print(f"  - {post.get('platform')}: {post.get('content', '')[:50]}...")

            # List conversations
            convos = client.list_conversations(limit=5)
            print(f"\nActive conversations: {len(convos.get('data', []))}")

            for convo in convos.get("data", [])[:3]:
                print(f"  - {convo.get('platform')}: {convo.get('participantName', 'Unknown')}")

        client.close()

    except Exception as e:
        print(f"[ERROR] {e}")
        print("Make sure LATE_API_KEY is set and Inbox Add-on is enabled")
