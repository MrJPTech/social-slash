#!/usr/bin/env python3
"""
DM Reply Agent for Engagement Automation

Monitors direct message conversations and generates AI-powered replies.
Uses Late API unified inbox for cross-platform DM management.

Features:
- Multi-platform DM monitoring
- AI-generated contextual replies
- Conversation history awareness
- Human-in-the-loop review queue
- Natural response delays
"""

import asyncio
from queue import Queue
from typing import Any

from lib.agents.base_agent import AgentState, BaseAgent
from lib.engagement.late_engagement_client import LateEngagementClient
from lib.storage.database import EngagementDatabase


class DMAgent(BaseAgent):
    """
    Agent that monitors and replies to DMs using Late API.

    Monitors conversations across platforms, generates AI replies,
    and either auto-sends or queues for human review.
    """

    def __init__(
        self,
        config: dict[str, Any],
        late_client: LateEngagementClient | None = None,
        db: EngagementDatabase | None = None,
        ai_provider: str = "gemini",
    ):
        """
        Initialize the DM agent.

        Args:
            config: Agent configuration dictionary
            late_client: Late engagement client (optional)
            db: Database instance (optional)
            ai_provider: AI provider for response generation
        """
        super().__init__(config, ai_provider, name="DMAgent")

        # Initialize clients
        self.late_client = late_client or LateEngagementClient()
        self.db = db or EngagementDatabase()

        # Configuration
        self.poll_interval = config.get("poll_interval_seconds", 30)
        self.auto_reply = config.get("auto_reply", False)
        self.platforms = config.get("platforms", ["instagram", "telegram", "reddit"])
        self.response_delay = config.get("response_delay_seconds", 30)
        self.max_context_messages = config.get("max_context_messages", 10)

        # Webhook queue for real-time messages
        self._message_queue: Queue = Queue()

        # Brand voice
        brand_voice = config.get("brand_voice", "friendly")
        self.response_generator.brand_voice = brand_voice

        self.logger.info(
            f"Configured for platforms: {', '.join(self.platforms)}, auto_reply: {self.auto_reply}"
        )

    async def start(self):
        """Start the DM monitoring loop."""
        self.transition(AgentState.MONITORING)
        self._running = True

        while self._running:
            try:
                # Process webhook queue first
                while not self._message_queue.empty():
                    msg_data = self._message_queue.get_nowait()
                    await self.process_item(msg_data)

                # Poll for new messages
                await self._poll_all_conversations()

                # Check for stop signal
                if self._stop_event and self._stop_event.is_set():
                    break

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.stats["errors"] += 1
                self.transition(AgentState.ERROR)
                self.logger.error(f"Poll error: {e}")
                await asyncio.sleep(self.poll_interval * 2)
                self.transition(AgentState.MONITORING)

        self.transition(AgentState.STOPPING)

    async def stop(self):
        """Gracefully stop the agent."""
        self.logger.info("Stop requested")
        self._running = False
        if self._stop_event:
            self._stop_event.set()

    def queue_webhook_message(self, message_data: dict[str, Any]):
        """
        Queue a message from webhook for processing.

        Args:
            message_data: Message data from Late webhook
        """
        self._message_queue.put(message_data)
        self.logger.debug("Webhook message queued")

    async def process_item(self, message_data: dict[str, Any]) -> bool:
        """
        Process a single DM.

        Args:
            message_data: Message data from Late API or webhook

        Returns:
            True if processed successfully
        """
        try:
            message_id = message_data.get("id", "unknown")
            conversation_id = message_data.get("conversationId", "")
            account_id = message_data.get("accountId", "")
            platform = message_data.get("platform", "unknown")
            sender_name = message_data.get("senderName", "unknown")
            sender_id = message_data.get("senderId", "")
            content = message_data.get("message", "")

            self.log_item("DM", platform, sender_name, content)

            # Skip if already processed
            if self.db.dm_exists(message_id):
                return False

            # Skip based on filters
            if self.should_skip(content, sender_name):
                self.logger.debug(f"Skipping DM from {sender_name}")
                return False

            # Get or create conversation
            conversation = self.db.save_conversation(
                late_conversation_id=conversation_id,
                platform=platform,
                account_id=account_id,
                participant_id=sender_id,
                participant_name=sender_name,
                last_message=content,
            )

            # Save message
            saved_dm = self.db.save_dm(
                conversation_id=conversation.id,
                late_message_id=message_id,
                sender_id=sender_id,
                sender_name=sender_name,
                content=content,
                direction="incoming",
            )

            self.stats["items_processed"] += 1

            # Check if requires escalation
            if self.requires_escalation(content):
                self.db.queue_dm_for_review(saved_dm.id, "[ESCALATION REQUIRED]")
                self.stats["items_queued"] += 1
                self.format_console_output("warning", f"Escalated DM from {sender_name}")
                return True

            # Get conversation history for context
            history = await self._get_conversation_history(conversation_id, account_id)

            # Generate reply
            self.transition(AgentState.GENERATING)
            reply = self.response_generator.generate_dm_reply(
                message=content,
                sender_name=sender_name,
                platform=platform,
                conversation_history=history,
                custom_instructions=self.config.get("custom_instructions"),
            )

            # Check rate limits
            rate_limit_key = f"dm:{platform}:{sender_id}"
            if not self.check_rate_limit(
                rate_limit_key,
                max_per_hour=self.config.get("max_replies_per_hour", 30),
                cooldown_seconds=self.config.get("cooldown_per_user_seconds", 60),
            ):
                self.db.queue_dm_for_review(saved_dm.id, reply)
                self.stats["items_queued"] += 1
                self.format_console_output(
                    "queued", f"Rate limited - queued reply for {sender_name}"
                )
                return True

            if self.auto_reply:
                # Add natural delay
                self.transition(AgentState.RESPONDING)
                if self.response_delay > 0:
                    self.logger.debug(f"Waiting {self.response_delay}s before reply...")
                    await asyncio.sleep(self.response_delay)

                # Send reply
                self.late_client.send_message(
                    conversation_id=conversation_id, account_id=account_id, message=reply
                )

                self.db.mark_dm_replied(saved_dm.id, reply)
                self.record_action(rate_limit_key)
                self.stats["items_responded"] += 1

                self.format_console_output("success", f"Replied to {sender_name} on {platform}")
            else:
                # Queue for human review
                self.transition(AgentState.REVIEWING)
                self.db.queue_dm_for_review(saved_dm.id, reply)
                self.stats["items_queued"] += 1

                self.format_console_output("queued", f"Review needed: {sender_name} on {platform}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to process DM: {e}")
            self.stats["errors"] += 1
            return False

    async def _poll_all_conversations(self):
        """Poll for new messages across all platforms."""
        self.transition(AgentState.PROCESSING)

        for platform in self.platforms:
            try:
                await self._poll_platform_conversations(platform)
            except Exception as e:
                self.logger.error(f"Error polling {platform}: {e}")

        self.transition(AgentState.MONITORING)

    async def _poll_platform_conversations(self, platform: str):
        """Poll for new messages on a single platform."""
        try:
            result = self.late_client.list_conversations(
                platform=platform, status="active", limit=20
            )
        except Exception as e:
            self.logger.error(f"Failed to list conversations for {platform}: {e}")
            return

        conversations = result.get("data", [])
        self.logger.debug(f"Found {len(conversations)} active conversations on {platform}")

        for convo_data in conversations:
            convo_id = convo_data.get("id", "")
            account_id = convo_data.get("accountId", "")

            # Get messages for this conversation
            try:
                messages_result = self.late_client.get_messages(
                    conversation_id=convo_id, account_id=account_id, limit=10
                )
            except Exception as e:
                self.logger.error(f"Failed to get messages for conversation {convo_id}: {e}")
                continue

            messages = messages_result.get("data", [])

            for msg in messages:
                # Only process incoming messages
                if msg.get("direction") == "incoming":
                    msg["conversationId"] = convo_id
                    msg["accountId"] = account_id
                    msg["platform"] = platform
                    await self.process_item(msg)

    async def _get_conversation_history(
        self, conversation_id: str, account_id: str
    ) -> list[dict[str, Any]]:
        """
        Get conversation history for context.

        Args:
            conversation_id: Late conversation ID
            account_id: Account ID

        Returns:
            List of messages with is_me and content keys
        """
        try:
            result = self.late_client.get_messages(
                conversation_id=conversation_id,
                account_id=account_id,
                limit=self.max_context_messages,
            )

            messages = result.get("data", [])
            history = []

            for msg in reversed(messages):  # Oldest first
                history.append(
                    {"is_me": msg.get("direction") == "outgoing", "content": msg.get("message", "")}
                )

            return history

        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            return []

    # ─────────────────────────────────────────────────────────────
    # REVIEW QUEUE MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    def get_pending_reviews(self, limit: int = 20) -> list[dict[str, Any]]:
        """
        Get pending DM reviews.

        Args:
            limit: Max reviews to return

        Returns:
            List of pending review items
        """
        reviews = self.db.get_pending_reviews(item_type="dm", limit=limit)
        return [r.to_dict() for r in reviews]

    def approve_review(
        self, review_id: int, reviewed_by: str = "user", modified_reply: str | None = None
    ) -> bool:
        """
        Approve a pending DM review and send the reply.

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

            # Get the review details
            reviews = self.db.get_pending_reviews(item_type="dm")
            review = next((r for r in reviews if r.id == review_id), None)

            if review:
                # Get DM and conversation
                dm_messages = self.db.get_conversation_messages(review.item_id)
                if dm_messages:
                    dm = dm_messages[0]
                    conversation = self.db.get_conversation(dm.conversation_id)

                    if conversation:
                        # Send the reply
                        self.late_client.send_message(
                            conversation_id=conversation.late_conversation_id,
                            account_id=conversation.account_id,
                            message=final_reply,
                        )

                        self.db.mark_dm_replied(dm.id, final_reply)
                        self.format_console_output(
                            "success", f"Approved reply sent to {conversation.participant_name}"
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
        Reject a pending DM review.

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

    parser = argparse.ArgumentParser(description="DM Reply Agent")
    parser.add_argument(
        "--action",
        choices=["start", "status", "review", "approve", "reject"],
        default="status",
        help="Action to perform",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        default="instagram,telegram,reddit",
        help="Comma-separated platforms",
    )
    parser.add_argument("--auto-reply", action="store_true", help="Auto-send replies")
    parser.add_argument("--poll-interval", type=int, default=30, help="Poll interval in seconds")
    parser.add_argument("--response-delay", type=int, default=30, help="Delay before sending reply")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--review-id", type=int, help="Review ID for approve/reject")

    args = parser.parse_args()

    config = {
        "platforms": args.platforms.split(","),
        "auto_reply": args.auto_reply and not args.dry_run,
        "poll_interval_seconds": args.poll_interval,
        "response_delay_seconds": args.response_delay,
        "brand_voice": "friendly",
    }

    agent = DMAgent(config)

    if args.action == "status":
        stats = agent.get_stats()
        print("\nDM Agent Status:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        db_stats = agent.db.get_stats()
        print("\nDatabase Statistics:")
        for key, value in db_stats.items():
            print(f"  {key}: {value}")

    elif args.action == "review":
        reviews = agent.get_pending_reviews()
        print(f"\nPending DM Reviews: {len(reviews)}")
        for r in reviews[:10]:
            print(f"\n  ID: {r['id']}")
            print(f"  Platform: {r['platform']}")
            print(f"  From: {r['author']}")
            print(f"  Message: {r['original_content'][:100]}...")
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
        print("\n[INFO] Starting DM Agent...")
        print(f"[INFO] Platforms: {', '.join(config['platforms'])}")
        print(f"[INFO] Auto-reply: {config['auto_reply']}")
        print(f"[INFO] Poll interval: {config['poll_interval_seconds']}s")
        print(f"[INFO] Response delay: {config['response_delay_seconds']}s")
        if args.dry_run:
            print("[INFO] DRY RUN MODE - No actual replies will be sent")
        print("\nPress Ctrl+C to stop\n")

        try:
            asyncio.run(agent.run())
        except KeyboardInterrupt:
            print("\n[INFO] Shutting down...")
