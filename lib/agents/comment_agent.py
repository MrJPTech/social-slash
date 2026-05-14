#!/usr/bin/env python3
"""
Comment Reply Agent for Engagement Automation

Monitors posts for new comments and generates AI-powered replies.
Uses Late API unified inbox for cross-platform comment management.

Features:
- Multi-platform comment monitoring
- AI-generated contextual replies
- Human-in-the-loop review queue
- Rate limiting and cooldowns
- Sentiment-based filtering
"""

import asyncio
from typing import Any

from lib.agents.base_agent import AgentState, BaseAgent
from lib.engagement.late_engagement_client import LateEngagementClient
from lib.storage.database import EngagementDatabase


class CommentAgent(BaseAgent):
    """
    Agent that monitors and replies to comments using Late API.

    Polls for new comments across configured platforms,
    generates AI replies, and either auto-posts or queues
    for human review.
    """

    def __init__(
        self,
        config: dict[str, Any],
        late_client: LateEngagementClient | None = None,
        db: EngagementDatabase | None = None,
        ai_provider: str = "gemini",
    ):
        """
        Initialize the comment agent.

        Args:
            config: Agent configuration dictionary
            late_client: Late engagement client (optional, creates new if not provided)
            db: Database instance (optional, creates new if not provided)
            ai_provider: AI provider for response generation
        """
        super().__init__(config, ai_provider, name="CommentAgent")

        # Initialize clients
        self.late_client = late_client or LateEngagementClient()
        self.db = db or EngagementDatabase()

        # Configuration
        self.poll_interval = config.get("poll_interval_seconds", 60)
        self.auto_approve = config.get("auto_approve", False)
        self.platforms = config.get("platforms", ["instagram", "reddit"])
        self.max_replies_per_post = config.get("max_replies_per_post", 10)
        self.min_comment_length = config.get("min_comment_length", 3)
        self.like_before_reply = config.get("like_before_reply", True)

        # Brand voice
        brand_voice = config.get("brand_voice", "professional")
        self.response_generator.brand_voice = brand_voice

        self.logger.info(
            f"Configured for platforms: {', '.join(self.platforms)}, "
            f"auto_approve: {self.auto_approve}"
        )

    async def start(self):
        """Start the comment monitoring loop."""
        self.transition(AgentState.MONITORING)
        self._running = True

        while self._running:
            try:
                await self._poll_all_platforms()

                # Check for stop signal
                if self._stop_event and self._stop_event.is_set():
                    break

                # Wait for next poll
                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats["errors"] += 1
                self.transition(AgentState.ERROR)
                self.logger.error(f"Poll error: {e}")
                await asyncio.sleep(self.poll_interval * 2)  # Back off on error
                self.transition(AgentState.MONITORING)

        self.transition(AgentState.STOPPING)

    async def stop(self):
        """Gracefully stop the agent."""
        self.logger.info("Stop requested")
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    async def process_item(self, comment_data: dict[str, Any]) -> bool:
        """
        Process a single comment.

        Args:
            comment_data: Comment data from Late API

        Returns:
            True if processed successfully
        """
        try:
            comment_id = comment_data.get("id", "unknown")
            author = comment_data.get("username", "unknown")
            content = comment_data.get("text", "")
            platform = comment_data.get("platform", "unknown")
            post_id = comment_data.get("postId", "")
            account_id = comment_data.get("accountId", "")

            self.log_item("comment", platform, author, content)

            # Skip if already processed
            if self.db.comment_exists(comment_id):
                return False

            # Skip based on filters
            if self.should_skip(content, author):
                self.logger.debug(f"Skipping comment from {author}")
                return False

            # Get post data for context
            post = self.db.get_post_by_late_id(post_id)
            post_content = post.content if post else ""

            # Save comment to database
            saved_comment = self.db.save_comment(
                post_id=post.id if post else 0,
                late_comment_id=comment_id,
                author=author,
                author_id=comment_data.get("userId", ""),
                content=content,
                platform=platform,
            )

            self.stats["items_processed"] += 1

            # Check if requires escalation
            if self.requires_escalation(content):
                self.db.queue_comment_for_review(saved_comment.id, "[ESCALATION REQUIRED]")
                self.stats["items_queued"] += 1
                self.format_console_output("warning", f"Escalated comment from @{author}")
                return True

            # Generate reply
            self.transition(AgentState.GENERATING)
            reply = self.response_generator.generate_comment_reply(
                comment=content,
                author=author,
                platform=platform,
                original_post=post_content,
                custom_instructions=self.config.get("custom_instructions"),
            )

            # Check rate limits
            rate_limit_key = f"comment:{platform}:{author}"
            if not self.check_rate_limit(
                rate_limit_key,
                max_per_hour=self.config.get("max_replies_per_hour", 60),
                cooldown_seconds=self.config.get("cooldown_per_user_seconds", 300),
            ):
                self.db.queue_comment_for_review(saved_comment.id, reply)
                self.stats["items_queued"] += 1
                self.format_console_output("queued", f"Rate limited - queued reply for @{author}")
                return True

            if self.auto_approve:
                # Send reply immediately
                self.transition(AgentState.RESPONDING)

                # Like comment first if configured
                if self.like_before_reply:
                    try:
                        self.late_client.like_comment(post_id, comment_id)
                    except Exception as e:
                        self.logger.debug(f"Could not like comment: {e}")

                # Post reply
                self.late_client.reply_to_comment(
                    post_id=post_id, account_id=account_id, message=reply, comment_id=comment_id
                )

                self.db.mark_comment_replied(saved_comment.id, reply)
                self.record_action(rate_limit_key)
                self.stats["items_responded"] += 1

                self.format_console_output("success", f"Replied to @{author} on {platform}")
            else:
                # Queue for human review
                self.transition(AgentState.REVIEWING)
                self.db.queue_comment_for_review(saved_comment.id, reply)
                self.stats["items_queued"] += 1

                self.format_console_output("queued", f"Review needed: @{author} on {platform}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to process comment: {e}")
            self.stats["errors"] += 1
            return False

    async def _poll_all_platforms(self):
        """Poll for new comments across all platforms."""
        self.transition(AgentState.PROCESSING)

        for platform in self.platforms:
            try:
                await self._poll_platform_comments(platform)
            except Exception as e:
                self.logger.error(f"Error polling {platform}: {e}")

        self.transition(AgentState.MONITORING)

    async def _poll_platform_comments(self, platform: str):
        """Poll for comments on a single platform."""
        # Get posts with comments
        try:
            result = self.late_client.list_posts_with_comments(
                platform=platform, min_comments=1, limit=20
            )
        except Exception as e:
            self.logger.error(f"Failed to list posts for {platform}: {e}")
            return

        posts = result.get("data", [])
        self.logger.debug(f"Found {len(posts)} posts with comments on {platform}")

        for post_data in posts:
            post_id = post_data.get("id", "")
            account_id = post_data.get("accountId", "")
            content = post_data.get("content", "")

            # Track post if not already tracked
            if not self.db.get_post_by_late_id(post_id):
                self.db.save_post(
                    platform=platform,
                    late_post_id=post_id,
                    account_id=account_id,
                    content=content,
                    title=post_data.get("title"),
                )

            # Get comments for this post
            try:
                comments_result = self.late_client.get_post_comments(post_id, limit=50)
            except Exception as e:
                self.logger.error(f"Failed to get comments for post {post_id}: {e}")
                continue

            comments = comments_result.get("data", [])
            replies_this_post = 0

            for comment in comments:
                # Check max replies per post
                if replies_this_post >= self.max_replies_per_post:
                    self.logger.debug(f"Max replies reached for post {post_id}")
                    break

                # Add post context to comment data
                comment["postId"] = post_id
                comment["accountId"] = account_id
                comment["platform"] = platform

                # Process comment
                if await self.process_item(comment):
                    replies_this_post += 1

            # Update post check timestamp
            post = self.db.get_post_by_late_id(post_id)
            if post:
                self.db.update_post_checked(post.id, len(comments))

    # ─────────────────────────────────────────────────────────────
    # REVIEW QUEUE MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    def get_pending_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get pending comment reviews.

        Args:
            limit: Max reviews to return

        Returns:
            List of pending review items
        """
        reviews = self.db.get_pending_reviews(item_type="comment", limit=limit)
        return [r.to_dict() for r in reviews]

    def approve_review(
        self, review_id: int, reviewed_by: str = "user", modified_reply: str | None = None
    ) -> bool:
        """
        Approve a pending review and send the reply.

        Args:
            review_id: Review ID
            reviewed_by: Who approved
            modified_reply: Modified reply text (optional)

        Returns:
            True if successful
        """
        try:
            final_reply = self.db.approve_review(
                review_id, reviewed_by=reviewed_by, final_reply=modified_reply
            )

            # Get the original comment
            reviews = self.db.get_pending_reviews()
            review = next((r for r in reviews if r.id == review_id), None)

            if review:
                comment = self.db.get_comment(review.item_id)
                if comment:
                    post = self.db.get_post(comment.post_id)
                    if post:
                        # Send the reply
                        self.late_client.reply_to_comment(
                            post_id=post.late_post_id,
                            account_id=post.account_id,
                            message=final_reply,
                            comment_id=comment.late_comment_id,
                        )

                        self.db.mark_comment_replied(comment.id, final_reply)
                        self.format_console_output(
                            "success", f"Approved reply sent to @{comment.author}"
                        )
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to approve review: {e}")
            return False

    def reject_review(
        self, review_id: int, reviewed_by: str = "user", reason: str | None = None
    ) -> bool:
        """
        Reject a pending review.

        Args:
            review_id: Review ID
            reviewed_by: Who rejected
            reason: Rejection reason

        Returns:
            True if successful
        """
        try:
            self.db.reject_review(review_id, reviewed_by, notes=reason)
            self.format_console_output("info", f"Review {review_id} rejected")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reject review: {e}")
            return False


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Comment Reply Agent")
    parser.add_argument(
        "--action",
        choices=["start", "status", "review", "approve", "reject"],
        default="status",
        help="Action to perform",
    )
    parser.add_argument(
        "--platforms", type=str, default="instagram,reddit", help="Comma-separated platforms"
    )
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve replies")
    parser.add_argument("--poll-interval", type=int, default=60, help="Poll interval in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--review-id", type=int, help="Review ID for approve/reject")

    args = parser.parse_args()

    config = {
        "platforms": args.platforms.split(","),
        "auto_approve": args.auto_approve and not args.dry_run,
        "poll_interval_seconds": args.poll_interval,
        "brand_voice": "professional",
    }

    agent = CommentAgent(config)

    if args.action == "status":
        stats = agent.get_stats()
        print("\nComment Agent Status:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        db_stats = agent.db.get_stats()
        print("\nDatabase Statistics:")
        for key, value in db_stats.items():
            print(f"  {key}: {value}")

    elif args.action == "review":
        reviews = agent.get_pending_reviews()
        print(f"\nPending Reviews: {len(reviews)}")
        for r in reviews[:10]:
            print(f"\n  ID: {r['id']}")
            print(f"  Platform: {r['platform']}")
            print(f"  Author: @{r['author']}")
            print(f"  Comment: {r['original_content'][:100]}...")
            print(f"  Generated Reply: {r['generated_reply'][:100]}...")

    elif args.action == "approve" and args.review_id:
        if agent.approve_review(args.review_id):
            print(f"[SUCCESS] Review {args.review_id} approved and sent")
        else:
            print(f"[ERROR] Failed to approve review {args.review_id}")

    elif args.action == "reject" and args.review_id:
        if agent.reject_review(args.review_id):
            print(f"[SUCCESS] Review {args.review_id} rejected")
        else:
            print(f"[ERROR] Failed to reject review {args.review_id}")

    elif args.action == "start":
        print("\n[INFO] Starting Comment Agent...")
        print(f"[INFO] Platforms: {', '.join(config['platforms'])}")
        print(f"[INFO] Auto-approve: {config['auto_approve']}")
        print(f"[INFO] Poll interval: {config['poll_interval_seconds']}s")
        if args.dry_run:
            print("[INFO] DRY RUN MODE - No actual replies will be sent")
        print("\nPress Ctrl+C to stop\n")

        try:
            asyncio.run(agent.run())
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down...")
