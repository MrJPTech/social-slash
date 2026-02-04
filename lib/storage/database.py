#!/usr/bin/env python3
"""
SQLite Database Wrapper for Engagement Automation

Provides persistent storage for:
- Tracked posts and comments
- DM conversations and messages
- Bot account configurations
- Pending review queue
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from pathlib import Path

from .models import (
    TrackedPost,
    Comment,
    Conversation,
    DirectMessage,
    BotAccount,
    PendingReview,
    ReviewStatus,
    ConversationStatus
)


class EngagementDatabase:
    """
    SQLite database wrapper for engagement automation.

    Handles all CRUD operations for posts, comments, conversations,
    messages, bot accounts, and the review queue.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database connection.

        Args:
            db_path: Path to SQLite database file.
                     Defaults to data/engagement.db
        """
        if db_path is None:
            # Default to project's data directory
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "engagement.db")

        self.db_path = db_path
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_database(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tracked posts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tracked_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    late_post_id TEXT NOT NULL UNIQUE,
                    account_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    title TEXT,
                    created_at TIMESTAMP NOT NULL,
                    last_checked TIMESTAMP,
                    comment_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')

            # Comments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    late_comment_id TEXT NOT NULL UNIQUE,
                    author TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    replied BOOLEAN DEFAULT 0,
                    reply_content TEXT,
                    replied_at TIMESTAMP,
                    pending_review BOOLEAN DEFAULT 0,
                    review_status TEXT DEFAULT 'pending',
                    sentiment TEXT,
                    FOREIGN KEY (post_id) REFERENCES tracked_posts(id)
                )
            ''')

            # Conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    late_conversation_id TEXT NOT NULL UNIQUE,
                    platform TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    participant_id TEXT NOT NULL,
                    participant_name TEXT NOT NULL,
                    last_message TEXT,
                    updated_at TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'active',
                    unread_count INTEGER DEFAULT 0,
                    auto_reply_enabled BOOLEAN DEFAULT 1
                )
            ''')

            # Direct messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS direct_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    late_message_id TEXT NOT NULL UNIQUE,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    received_at TIMESTAMP NOT NULL,
                    replied BOOLEAN DEFAULT 0,
                    reply_content TEXT,
                    replied_at TIMESTAMP,
                    pending_review BOOLEAN DEFAULT 0,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            ''')

            # Bot accounts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    late_account_id TEXT NOT NULL,
                    is_primary BOOLEAN DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    response_style TEXT DEFAULT 'professional',
                    max_replies_per_hour INTEGER DEFAULT 60,
                    cooldown_seconds INTEGER DEFAULT 300,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(platform, late_account_id)
                )
            ''')

            # Pending review queue
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    original_content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    generated_reply TEXT NOT NULL,
                    review_status TEXT DEFAULT 'pending',
                    reviewed_by TEXT,
                    reviewed_at TIMESTAMP,
                    final_reply TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes for performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_comments_post_id
                ON comments(post_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_comments_platform
                ON comments(platform)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                ON direct_messages(conversation_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_pending_reviews_status
                ON pending_reviews(review_status)
            ''')

        print(f"[INFO] Database initialized at {self.db_path}")

    def close(self):
        """Close the database connection.

        Note: This class uses a context manager pattern for connections,
        so there's no persistent connection to close. This method exists
        for API compatibility with test fixtures.
        """
        pass  # Connections are managed per-operation via context manager

    # ─────────────────────────────────────────────────────────────
    # TRACKED POSTS
    # ─────────────────────────────────────────────────────────────

    def save_post(
        self,
        platform: str,
        late_post_id: str,
        account_id: str,
        content: str,
        title: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> TrackedPost:
        """Save a new tracked post."""
        created_at = created_at or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO tracked_posts
                (platform, late_post_id, account_id, content, title, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (platform, late_post_id, account_id, content, title, created_at))

            # Get the inserted/existing row
            cursor.execute(
                'SELECT * FROM tracked_posts WHERE late_post_id = ?',
                (late_post_id,)
            )
            row = cursor.fetchone()

        return self._row_to_tracked_post(row)

    def get_post(self, post_id: int) -> Optional[TrackedPost]:
        """Get a tracked post by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tracked_posts WHERE id = ?', (post_id,))
            row = cursor.fetchone()

        return self._row_to_tracked_post(row) if row else None

    def get_post_by_late_id(self, late_post_id: str) -> Optional[TrackedPost]:
        """Get a tracked post by Late API post ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM tracked_posts WHERE late_post_id = ?',
                (late_post_id,)
            )
            row = cursor.fetchone()

        return self._row_to_tracked_post(row) if row else None

    def get_active_posts(self, platform: Optional[str] = None) -> List[TrackedPost]:
        """Get all active posts, optionally filtered by platform."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute(
                    'SELECT * FROM tracked_posts WHERE is_active = 1 AND platform = ?',
                    (platform,)
                )
            else:
                cursor.execute('SELECT * FROM tracked_posts WHERE is_active = 1')
            rows = cursor.fetchall()

        return [self._row_to_tracked_post(row) for row in rows]

    def update_post_checked(self, post_id: int, comment_count: int = 0):
        """Update last_checked timestamp for a post."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE tracked_posts
                SET last_checked = ?, comment_count = ?
                WHERE id = ?
            ''', (datetime.now(), comment_count, post_id))

    def deactivate_post(self, post_id: int):
        """Stop monitoring a post."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tracked_posts SET is_active = 0 WHERE id = ?',
                (post_id,)
            )

    def _row_to_tracked_post(self, row: sqlite3.Row) -> TrackedPost:
        """Convert a database row to TrackedPost object."""
        return TrackedPost(
            id=row['id'],
            platform=row['platform'],
            late_post_id=row['late_post_id'],
            account_id=row['account_id'],
            content=row['content'],
            title=row['title'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            last_checked=datetime.fromisoformat(row['last_checked']) if row['last_checked'] else None,
            comment_count=row['comment_count'],
            is_active=bool(row['is_active'])
        )

    # ─────────────────────────────────────────────────────────────
    # COMMENTS
    # ─────────────────────────────────────────────────────────────

    def save_comment(
        self,
        post_id: int,
        late_comment_id: str,
        author: str,
        author_id: str,
        content: str,
        platform: str,
        created_at: Optional[datetime] = None
    ) -> Comment:
        """Save a new comment."""
        created_at = created_at or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO comments
                (post_id, late_comment_id, author, author_id, content, platform, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (post_id, late_comment_id, author, author_id, content, platform, created_at))

            cursor.execute(
                'SELECT * FROM comments WHERE late_comment_id = ?',
                (late_comment_id,)
            )
            row = cursor.fetchone()

        return self._row_to_comment(row)

    def comment_exists(self, late_comment_id: str) -> bool:
        """Check if a comment already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM comments WHERE late_comment_id = ?',
                (late_comment_id,)
            )
            return cursor.fetchone() is not None

    def get_comment(self, comment_id: int) -> Optional[Comment]:
        """Get a comment by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
            row = cursor.fetchone()

        return self._row_to_comment(row) if row else None

    def get_unreplied_comments(
        self,
        platform: Optional[str] = None,
        limit: int = 50
    ) -> List[Comment]:
        """Get comments that haven't been replied to."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute('''
                    SELECT * FROM comments
                    WHERE replied = 0 AND pending_review = 0 AND platform = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (platform, limit))
            else:
                cursor.execute('''
                    SELECT * FROM comments
                    WHERE replied = 0 AND pending_review = 0
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
            rows = cursor.fetchall()

        return [self._row_to_comment(row) for row in rows]

    def mark_comment_replied(
        self,
        comment_id: int,
        reply_content: str,
        replied_at: Optional[datetime] = None
    ):
        """Mark a comment as replied."""
        replied_at = replied_at or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE comments
                SET replied = 1, reply_content = ?, replied_at = ?, pending_review = 0
                WHERE id = ?
            ''', (reply_content, replied_at, comment_id))

    def queue_comment_for_review(self, comment_id: int, generated_reply: str):
        """Queue a comment reply for human review."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE comments SET pending_review = 1 WHERE id = ?',
                (comment_id,)
            )

            # Get comment details
            cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
            comment = cursor.fetchone()

            # Add to review queue
            cursor.execute('''
                INSERT INTO pending_reviews
                (item_type, item_id, platform, original_content, author, generated_reply)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('comment', comment_id, comment['platform'],
                  comment['content'], comment['author'], generated_reply))

    def _row_to_comment(self, row: sqlite3.Row) -> Comment:
        """Convert a database row to Comment object."""
        return Comment(
            id=row['id'],
            post_id=row['post_id'],
            late_comment_id=row['late_comment_id'],
            author=row['author'],
            author_id=row['author_id'],
            content=row['content'],
            platform=row['platform'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            replied=bool(row['replied']),
            reply_content=row['reply_content'],
            replied_at=datetime.fromisoformat(row['replied_at']) if row['replied_at'] else None,
            pending_review=bool(row['pending_review']),
            review_status=ReviewStatus(row['review_status']) if row['review_status'] else ReviewStatus.PENDING,
            sentiment=row['sentiment']
        )

    # ─────────────────────────────────────────────────────────────
    # CONVERSATIONS
    # ─────────────────────────────────────────────────────────────

    def save_conversation(
        self,
        late_conversation_id: str,
        platform: str,
        account_id: str,
        participant_id: str,
        participant_name: str,
        last_message: str = "",
        updated_at: Optional[datetime] = None
    ) -> Conversation:
        """Save or update a conversation."""
        updated_at = updated_at or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations
                (late_conversation_id, platform, account_id, participant_id,
                 participant_name, last_message, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(late_conversation_id) DO UPDATE SET
                    last_message = excluded.last_message,
                    updated_at = excluded.updated_at
            ''', (late_conversation_id, platform, account_id, participant_id,
                  participant_name, last_message, updated_at))

            cursor.execute(
                'SELECT * FROM conversations WHERE late_conversation_id = ?',
                (late_conversation_id,)
            )
            row = cursor.fetchone()

        return self._row_to_conversation(row)

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM conversations WHERE id = ?',
                (conversation_id,)
            )
            row = cursor.fetchone()

        return self._row_to_conversation(row) if row else None

    def get_active_conversations(
        self,
        platform: Optional[str] = None
    ) -> List[Conversation]:
        """Get all active conversations."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute('''
                    SELECT * FROM conversations
                    WHERE status = 'active' AND platform = ?
                    ORDER BY updated_at DESC
                ''', (platform,))
            else:
                cursor.execute('''
                    SELECT * FROM conversations
                    WHERE status = 'active'
                    ORDER BY updated_at DESC
                ''')
            rows = cursor.fetchall()

        return [self._row_to_conversation(row) for row in rows]

    def archive_conversation(self, conversation_id: int):
        """Archive a conversation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE conversations SET status = ? WHERE id = ?',
                (ConversationStatus.ARCHIVED.value, conversation_id)
            )

    def _row_to_conversation(self, row: sqlite3.Row) -> Conversation:
        """Convert a database row to Conversation object."""
        return Conversation(
            id=row['id'],
            late_conversation_id=row['late_conversation_id'],
            platform=row['platform'],
            account_id=row['account_id'],
            participant_id=row['participant_id'],
            participant_name=row['participant_name'],
            last_message=row['last_message'],
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None,
            status=ConversationStatus(row['status']) if row['status'] else ConversationStatus.ACTIVE,
            unread_count=row['unread_count'],
            auto_reply_enabled=bool(row['auto_reply_enabled'])
        )

    # ─────────────────────────────────────────────────────────────
    # DIRECT MESSAGES
    # ─────────────────────────────────────────────────────────────

    def save_dm(
        self,
        conversation_id: int,
        late_message_id: str,
        sender_id: str,
        sender_name: str,
        content: str,
        direction: str,
        received_at: Optional[datetime] = None
    ) -> DirectMessage:
        """Save a new direct message."""
        received_at = received_at or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO direct_messages
                (conversation_id, late_message_id, sender_id, sender_name,
                 content, direction, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (conversation_id, late_message_id, sender_id, sender_name,
                  content, direction, received_at))

            cursor.execute(
                'SELECT * FROM direct_messages WHERE late_message_id = ?',
                (late_message_id,)
            )
            row = cursor.fetchone()

        return self._row_to_dm(row)

    def dm_exists(self, late_message_id: str) -> bool:
        """Check if a DM already exists."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM direct_messages WHERE late_message_id = ?',
                (late_message_id,)
            )
            return cursor.fetchone() is not None

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 50
    ) -> List[DirectMessage]:
        """Get messages in a conversation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM direct_messages
                WHERE conversation_id = ?
                ORDER BY received_at DESC
                LIMIT ?
            ''', (conversation_id, limit))
            rows = cursor.fetchall()

        return [self._row_to_dm(row) for row in rows]

    def mark_dm_replied(
        self,
        dm_id: int,
        reply_content: str,
        replied_at: Optional[datetime] = None
    ):
        """Mark a DM as replied."""
        replied_at = replied_at or datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE direct_messages
                SET replied = 1, reply_content = ?, replied_at = ?, pending_review = 0
                WHERE id = ?
            ''', (reply_content, replied_at, dm_id))

    def queue_dm_for_review(self, dm_id: int, generated_reply: str):
        """Queue a DM reply for human review."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE direct_messages SET pending_review = 1 WHERE id = ?',
                (dm_id,)
            )

            # Get DM details
            cursor.execute('SELECT dm.*, c.platform FROM direct_messages dm JOIN conversations c ON dm.conversation_id = c.id WHERE dm.id = ?', (dm_id,))
            dm = cursor.fetchone()

            # Add to review queue
            cursor.execute('''
                INSERT INTO pending_reviews
                (item_type, item_id, platform, original_content, author, generated_reply)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('dm', dm_id, dm['platform'],
                  dm['content'], dm['sender_name'], generated_reply))

    def _row_to_dm(self, row: sqlite3.Row) -> DirectMessage:
        """Convert a database row to DirectMessage object."""
        return DirectMessage(
            id=row['id'],
            conversation_id=row['conversation_id'],
            late_message_id=row['late_message_id'],
            sender_id=row['sender_id'],
            sender_name=row['sender_name'],
            content=row['content'],
            direction=row['direction'],
            received_at=datetime.fromisoformat(row['received_at']) if row['received_at'] else None,
            replied=bool(row['replied']),
            reply_content=row['reply_content'],
            replied_at=datetime.fromisoformat(row['replied_at']) if row['replied_at'] else None,
            pending_review=bool(row['pending_review'])
        )

    # ─────────────────────────────────────────────────────────────
    # BOT ACCOUNTS
    # ─────────────────────────────────────────────────────────────

    def save_bot_account(
        self,
        name: str,
        platform: str,
        late_account_id: str,
        is_primary: bool = False,
        is_active: bool = True,
        response_style: str = "professional",
        max_replies_per_hour: int = 60,
        cooldown_seconds: int = 300
    ) -> BotAccount:
        """Save or update a bot account."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bot_accounts
                (name, platform, late_account_id, is_primary, is_active, response_style,
                 max_replies_per_hour, cooldown_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(platform, late_account_id) DO UPDATE SET
                    name = excluded.name,
                    is_primary = excluded.is_primary,
                    is_active = excluded.is_active,
                    response_style = excluded.response_style,
                    max_replies_per_hour = excluded.max_replies_per_hour,
                    cooldown_seconds = excluded.cooldown_seconds
            ''', (name, platform, late_account_id, is_primary, is_active, response_style,
                  max_replies_per_hour, cooldown_seconds))

            cursor.execute(
                'SELECT * FROM bot_accounts WHERE platform = ? AND late_account_id = ?',
                (platform, late_account_id)
            )
            row = cursor.fetchone()

        return self._row_to_bot_account(row)

    def get_bot_accounts(
        self,
        platform: Optional[str] = None,
        active_only: bool = True
    ) -> List[BotAccount]:
        """Get bot accounts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if platform:
                if active_only:
                    cursor.execute(
                        'SELECT * FROM bot_accounts WHERE platform = ? AND is_active = 1',
                        (platform,)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM bot_accounts WHERE platform = ?',
                        (platform,)
                    )
            else:
                if active_only:
                    cursor.execute('SELECT * FROM bot_accounts WHERE is_active = 1')
                else:
                    cursor.execute('SELECT * FROM bot_accounts')
            rows = cursor.fetchall()

        return [self._row_to_bot_account(row) for row in rows]

    def get_primary_bot(self, platform: str) -> Optional[BotAccount]:
        """Get the primary bot account for a platform."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM bot_accounts
                WHERE platform = ? AND is_primary = 1 AND is_active = 1
            ''', (platform,))
            row = cursor.fetchone()

        return self._row_to_bot_account(row) if row else None

    def get_bot_for_platform(
        self,
        platform: str,
        prefer_primary: bool = True
    ) -> Optional[BotAccount]:
        """Get a bot account for the specified platform.

        Args:
            platform: Platform name
            prefer_primary: If True, prefer primary bot; otherwise return any active bot

        Returns:
            BotAccount or None
        """
        if prefer_primary:
            bot = self.get_primary_bot(platform)
            if bot:
                return bot

        # Fallback to any active bot for this platform
        bots = self.get_bot_accounts(platform=platform, active_only=True)
        return bots[0] if bots else None

    def get_bots_by_platform(self, platform: str) -> List[BotAccount]:
        """Get all active bot accounts for a platform.

        Alias for get_bot_accounts(platform=platform, active_only=True).
        """
        return self.get_bot_accounts(platform=platform, active_only=True)

    def _row_to_bot_account(self, row: sqlite3.Row) -> BotAccount:
        """Convert a database row to BotAccount object."""
        return BotAccount(
            id=row['id'],
            name=row['name'],
            platform=row['platform'],
            late_account_id=row['late_account_id'],
            is_primary=bool(row['is_primary']),
            is_active=bool(row['is_active']),
            response_style=row['response_style'],
            max_replies_per_hour=row['max_replies_per_hour'],
            cooldown_seconds=row['cooldown_seconds'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

    # ─────────────────────────────────────────────────────────────
    # PENDING REVIEWS
    # ─────────────────────────────────────────────────────────────

    def get_review(self, review_id: int) -> Optional[PendingReview]:
        """Get a pending review by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pending_reviews WHERE id = ?', (review_id,))
            row = cursor.fetchone()

        return self._row_to_pending_review(row) if row else None

    def get_pending_reviews(
        self,
        item_type: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 50
    ) -> List[PendingReview]:
        """Get items pending human review."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM pending_reviews WHERE review_status = 'pending'"
            params = []

            if item_type:
                query += " AND item_type = ?"
                params.append(item_type)
            if platform:
                query += " AND platform = ?"
                params.append(platform)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

        return [self._row_to_pending_review(row) for row in rows]

    def approve_review(
        self,
        review_id: int,
        reviewed_by: str,
        final_reply: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """Approve a pending review."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get the review
            cursor.execute('SELECT * FROM pending_reviews WHERE id = ?', (review_id,))
            review = cursor.fetchone()

            if not review:
                raise ValueError(f"Review {review_id} not found")

            # Use generated reply if no final reply provided
            final_reply = final_reply or review['generated_reply']

            # Update review
            cursor.execute('''
                UPDATE pending_reviews
                SET review_status = 'approved', reviewed_by = ?,
                    reviewed_at = ?, final_reply = ?, notes = ?
                WHERE id = ?
            ''', (reviewed_by, datetime.now(), final_reply, notes, review_id))

            # Update the source item
            if review['item_type'] == 'comment':
                cursor.execute('''
                    UPDATE comments
                    SET pending_review = 0, review_status = 'approved'
                    WHERE id = ?
                ''', (review['item_id'],))
            elif review['item_type'] == 'dm':
                cursor.execute('''
                    UPDATE direct_messages
                    SET pending_review = 0
                    WHERE id = ?
                ''', (review['item_id'],))

        return final_reply

    def reject_review(
        self,
        review_id: int,
        reviewed_by: str,
        notes: Optional[str] = None
    ):
        """Reject a pending review."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM pending_reviews WHERE id = ?', (review_id,))
            review = cursor.fetchone()

            if not review:
                raise ValueError(f"Review {review_id} not found")

            # Update review
            cursor.execute('''
                UPDATE pending_reviews
                SET review_status = 'rejected', reviewed_by = ?,
                    reviewed_at = ?, notes = ?
                WHERE id = ?
            ''', (reviewed_by, datetime.now(), notes, review_id))

            # Update source item
            if review['item_type'] == 'comment':
                cursor.execute('''
                    UPDATE comments
                    SET pending_review = 0, review_status = 'rejected'
                    WHERE id = ?
                ''', (review['item_id'],))
            elif review['item_type'] == 'dm':
                cursor.execute('''
                    UPDATE direct_messages
                    SET pending_review = 0
                    WHERE id = ?
                ''', (review['item_id'],))

    def _row_to_pending_review(self, row: sqlite3.Row) -> PendingReview:
        """Convert a database row to PendingReview object."""
        return PendingReview(
            id=row['id'],
            item_type=row['item_type'],
            item_id=row['item_id'],
            platform=row['platform'],
            original_content=row['original_content'],
            author=row['author'],
            generated_reply=row['generated_reply'],
            review_status=ReviewStatus(row['review_status']) if row['review_status'] else ReviewStatus.PENDING,
            reviewed_by=row['reviewed_by'],
            reviewed_at=datetime.fromisoformat(row['reviewed_at']) if row['reviewed_at'] else None,
            final_reply=row['final_reply'],
            notes=row['notes'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

    # ─────────────────────────────────────────────────────────────
    # STATISTICS
    # ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) FROM tracked_posts WHERE is_active = 1')
            active_posts = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM comments')
            total_comments = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM comments WHERE replied = 1')
            replied_comments = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM conversations WHERE status = "active"')
            active_conversations = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM direct_messages')
            total_dms = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM pending_reviews WHERE review_status = "pending"')
            pending_reviews = cursor.fetchone()[0]

        return {
            'active_posts': active_posts,
            'total_comments': total_comments,
            'replied_comments': replied_comments,
            'reply_rate': f"{(replied_comments / total_comments * 100):.1f}%" if total_comments > 0 else "0%",
            'active_conversations': active_conversations,
            'total_dms': total_dms,
            'pending_reviews': pending_reviews
        }


# Example usage
if __name__ == "__main__":
    db = EngagementDatabase()
    stats = db.get_stats()
    print("\nDatabase Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
