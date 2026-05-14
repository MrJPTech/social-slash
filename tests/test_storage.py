"""
Unit tests for engagement storage module.

Tests the database models and SQLite storage operations.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from storage.database import EngagementDatabase
from storage.models import (
    BotAccount,
    Comment,
    Conversation,
    ConversationStatus,
    DirectMessage,
    PendingReview,
    ReviewStatus,
    TrackedPost,
)


class TestTrackedPostModel:
    """Test TrackedPost dataclass."""

    def test_create_tracked_post(self):
        """Create a tracked post with required fields."""
        post = TrackedPost(
            id=1,
            platform="instagram",
            late_post_id="late_123",
            account_id="acc_123",
            content="Test content",
            created_at=datetime.now(),
        )
        assert post.id == 1
        assert post.platform == "instagram"
        assert post.late_post_id == "late_123"
        assert post.account_id == "acc_123"
        assert post.last_checked is None

    def test_tracked_post_defaults(self):
        """Verify default values."""
        post = TrackedPost(
            id=1,
            platform="instagram",
            late_post_id="late_123",
            account_id="acc_123",
            content="Test content",
            created_at=datetime.now(),
        )
        assert post.last_checked is None
        assert post.comment_count == 0


class TestCommentModel:
    """Test Comment dataclass."""

    def test_create_comment(self):
        """Create a comment with required fields."""
        comment = Comment(
            id=1,
            post_id=1,
            late_comment_id="late_comment_123",
            author="user1",
            author_id="author_123",
            content="Great post!",
            platform="instagram",
            created_at=datetime.now(),
        )
        assert comment.id == 1
        assert comment.author == "user1"
        assert comment.replied is False

    def test_comment_defaults(self):
        """Verify default values."""
        comment = Comment(
            id=1,
            post_id=1,
            late_comment_id="late_comment_123",
            author="user1",
            author_id="author_123",
            content="Great post!",
            platform="instagram",
            created_at=datetime.now(),
        )
        assert comment.replied is False
        assert comment.reply_content is None
        assert comment.pending_review is False


class TestBotAccountModel:
    """Test BotAccount dataclass."""

    def test_create_bot_account(self):
        """Create a bot account."""
        bot = BotAccount(
            id=1,
            platform="instagram",
            late_account_id="late_acc_123",
            name="Support Bot",
            is_primary=True,
            is_active=True,
            created_at=datetime.now(),
        )
        assert bot.platform == "instagram"
        assert bot.is_primary is True

    def test_bot_account_defaults(self):
        """Verify default values."""
        bot = BotAccount(
            id=1,
            platform="instagram",
            late_account_id="late_acc_123",
            name="Support Bot",
            is_primary=False,
            is_active=True,
            created_at=datetime.now(),
        )
        assert bot.response_style == "professional"
        assert bot.max_replies_per_hour == 60
        assert bot.cooldown_seconds == 300


class TestPendingReviewModel:
    """Test PendingReview dataclass."""

    def test_create_pending_review(self):
        """Create a pending review."""
        review = PendingReview(
            id=1,
            item_type="comment",
            item_id=1,
            platform="instagram",
            original_content="User comment",
            author="test_user",
            generated_reply="Bot reply",
            review_status=ReviewStatus.PENDING,
            created_at=datetime.now(),
        )
        assert review.review_status == ReviewStatus.PENDING

    def test_review_status_enum(self):
        """Test review status enum values."""
        assert ReviewStatus.PENDING.value == "pending"
        assert ReviewStatus.APPROVED.value == "approved"
        assert ReviewStatus.REJECTED.value == "rejected"
        assert ReviewStatus.EXPIRED.value == "expired"


class TestEngagementDatabase:
    """Test EngagementDatabase class."""

    @pytest.fixture
    def db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        database = EngagementDatabase(db_path)
        yield database
        database.close()
        try:
            os.unlink(db_path)
        except PermissionError:
            pass  # Windows may hold file lock

    def test_init_creates_tables(self, db):
        """Verify tables are created on init."""
        # Use the context manager to access database
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "tracked_posts" in tables
        assert "comments" in tables
        assert "conversations" in tables
        assert "direct_messages" in tables
        assert "bot_accounts" in tables
        assert "pending_reviews" in tables

    def test_save_post(self, db):
        """Save a tracked post."""
        post = db.save_post(
            platform="instagram",
            late_post_id="late_123",
            account_id="acc_123",
            content="Test content",
        )
        assert post.id == 1
        assert post.platform == "instagram"
        assert post.late_post_id == "late_123"

    def test_get_post(self, db):
        """Retrieve a saved post."""
        saved = db.save_post("instagram", "late_123", "acc_123", "Test content")
        post = db.get_post(saved.id)
        assert post is not None
        assert post.content == "Test content"

    def test_get_post_by_late_id(self, db):
        """Retrieve a saved post by Late ID."""
        db.save_post("instagram", "late_123", "acc_123", "Test content")
        post = db.get_post_by_late_id("late_123")
        assert post is not None
        assert post.content == "Test content"

    def test_get_post_not_found(self, db):
        """Return None for non-existent post."""
        post = db.get_post(9999)
        assert post is None

    def test_save_comment(self, db):
        """Save a comment."""
        # First save a post
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")

        comment = db.save_comment(
            post_id=post.id,
            late_comment_id="late_comment_123",
            author="user1",
            author_id="author_123",
            content="Great post!",
            platform="instagram",
        )
        assert comment.id == 1
        assert comment.author == "user1"

    def test_comment_exists(self, db):
        """Check if comment exists."""
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")
        db.save_comment(post.id, "late_comment_123", "user1", "author_123", "Comment", "instagram")

        assert db.comment_exists("late_comment_123") is True
        assert db.comment_exists("nonexistent") is False

    def test_mark_comment_replied(self, db):
        """Mark a comment as replied."""
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")
        comment = db.save_comment(
            post.id, "late_comment_123", "user1", "author_123", "Comment", "instagram"
        )

        db.mark_comment_replied(comment.id, "Thank you!")

        updated = db.get_comment(comment.id)
        assert updated.replied is True
        assert updated.reply_content == "Thank you!"

    def test_queue_comment_for_review(self, db):
        """Queue a comment for review."""
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")
        comment = db.save_comment(
            post.id, "late_comment_123", "user1", "author_123", "Comment", "instagram"
        )

        # queue_comment_for_review returns None, it modifies the database
        db.queue_comment_for_review(comment.id, "Generated reply")

        reviews = db.get_pending_reviews()
        assert len(reviews) == 1
        assert reviews[0].review_status == ReviewStatus.PENDING
        assert reviews[0].generated_reply == "Generated reply"

    def test_get_pending_reviews(self, db):
        """Get pending reviews."""
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")
        comment = db.save_comment(
            post.id, "late_comment_123", "user1", "author_123", "Comment", "instagram"
        )
        db.queue_comment_for_review(comment.id, "Generated reply")

        reviews = db.get_pending_reviews()
        assert len(reviews) == 1
        assert reviews[0].review_status == ReviewStatus.PENDING

    def test_approve_review(self, db):
        """Approve a pending review."""
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")
        comment = db.save_comment(
            post.id, "late_comment_123", "user1", "author_123", "Comment", "instagram"
        )
        db.queue_comment_for_review(comment.id, "Generated reply")

        reviews = db.get_pending_reviews()
        review_id = reviews[0].id

        # approve_review returns the final_reply string
        final_reply = db.approve_review(review_id, "admin", "Approved reply")
        assert final_reply == "Approved reply"

        updated = db.get_review(review_id)
        assert updated.review_status == ReviewStatus.APPROVED
        assert updated.final_reply == "Approved reply"

    def test_reject_review(self, db):
        """Reject a pending review."""
        post = db.save_post("instagram", "late_post_123", "acc_123", "Post content")
        comment = db.save_comment(
            post.id, "late_comment_123", "user1", "author_123", "Comment", "instagram"
        )
        db.queue_comment_for_review(comment.id, "Generated reply")

        reviews = db.get_pending_reviews()
        review_id = reviews[0].id

        # reject_review returns None
        db.reject_review(review_id, "admin")

        updated = db.get_review(review_id)
        assert updated.review_status == ReviewStatus.REJECTED

    def test_save_bot_account(self, db):
        """Save a bot account."""
        bot = db.save_bot_account(
            name="Support Bot",
            platform="instagram",
            late_account_id="late_acc_123",
            is_primary=True,
        )
        assert bot.id == 1
        assert bot.platform == "instagram"
        assert bot.is_primary is True

    def test_get_bot_for_platform(self, db):
        """Get bot for a platform."""
        db.save_bot_account("Bot 1", "instagram", "late_acc_123", is_primary=False)
        db.save_bot_account("Bot 2", "instagram", "late_acc_456", is_primary=True)

        bot = db.get_bot_for_platform("instagram", prefer_primary=True)
        assert bot is not None
        assert bot.is_primary is True
        assert bot.late_account_id == "late_acc_456"

    def test_get_bot_nonprimary(self, db):
        """Get non-primary bot when primary not available."""
        db.save_bot_account("Bot 1", "instagram", "late_acc_123", is_primary=False)

        bot = db.get_bot_for_platform("instagram", prefer_primary=True)
        assert bot is not None
        assert bot.is_primary is False

    def test_save_conversation(self, db):
        """Save a conversation."""
        conv = db.save_conversation(
            late_conversation_id="late_conv_123",
            platform="instagram",
            account_id="acc_123",
            participant_id="part_123",
            participant_name="John Doe",
        )
        assert conv.id == 1
        assert conv.platform == "instagram"

    def test_save_dm(self, db):
        """Save a direct message."""
        conv = db.save_conversation("late_conv_123", "instagram", "acc_123", "part_123", "John Doe")

        dm = db.save_dm(
            conversation_id=conv.id,
            late_message_id="late_msg_123",
            sender_id="sender_123",
            sender_name="John",
            content="Hello!",
            direction="incoming",
        )
        assert dm.id == 1
        assert dm.content == "Hello!"
        assert dm.direction == "incoming"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
