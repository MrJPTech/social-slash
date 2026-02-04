#!/usr/bin/env python3
"""
Data Models for Engagement Automation

Dataclasses representing:
- Tracked social media posts
- Comments and replies
- DM conversations and messages
- Bot account configurations
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ReviewStatus(Enum):
    """Status for items pending human review."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"


class ConversationStatus(Enum):
    """Status for DM conversations."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    MUTED = "muted"


@dataclass
class TrackedPost:
    """
    A social media post being monitored for comments.

    Attributes:
        id: Local database ID
        platform: Platform name (instagram, reddit, etc.)
        late_post_id: Late API's post ID
        account_id: Late account ID used to post
        content: Original post content
        title: Optional post title (Reddit, YouTube)
        created_at: When the post was created
        last_checked: Last time comments were checked
        comment_count: Number of comments found
        is_active: Whether to continue monitoring
    """
    id: int
    platform: str
    late_post_id: str
    account_id: str
    content: str
    created_at: datetime
    title: Optional[str] = None
    last_checked: Optional[datetime] = None
    comment_count: int = 0
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'platform': self.platform,
            'late_post_id': self.late_post_id,
            'account_id': self.account_id,
            'content': self.content,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'comment_count': self.comment_count,
            'is_active': self.is_active
        }


@dataclass
class Comment:
    """
    A comment on a tracked post.

    Attributes:
        id: Local database ID
        post_id: Foreign key to TrackedPost
        late_comment_id: Late API's comment ID
        author: Comment author's display name
        author_id: Comment author's platform ID
        content: Comment text
        platform: Platform name
        created_at: When comment was posted
        replied: Whether we've replied
        reply_content: Our reply text (if replied)
        replied_at: When we replied
        pending_review: Whether awaiting human approval
        review_status: Current review status
        sentiment: Detected sentiment (positive/neutral/negative)
    """
    id: int
    post_id: int
    late_comment_id: str
    author: str
    author_id: str
    content: str
    platform: str
    created_at: datetime
    replied: bool = False
    reply_content: Optional[str] = None
    replied_at: Optional[datetime] = None
    pending_review: bool = False
    review_status: ReviewStatus = ReviewStatus.PENDING
    sentiment: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'post_id': self.post_id,
            'late_comment_id': self.late_comment_id,
            'author': self.author,
            'author_id': self.author_id,
            'content': self.content,
            'platform': self.platform,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'replied': self.replied,
            'reply_content': self.reply_content,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None,
            'pending_review': self.pending_review,
            'review_status': self.review_status.value,
            'sentiment': self.sentiment
        }


@dataclass
class Conversation:
    """
    A DM conversation.

    Attributes:
        id: Local database ID
        late_conversation_id: Late API's conversation ID
        platform: Platform name
        account_id: Late account ID
        participant_id: Other party's platform ID
        participant_name: Other party's display name
        last_message: Most recent message preview
        updated_at: Last message timestamp
        status: Conversation status
        unread_count: Number of unread messages
        auto_reply_enabled: Whether auto-reply is on
    """
    id: int
    late_conversation_id: str
    platform: str
    account_id: str
    participant_id: str
    participant_name: str
    last_message: str
    updated_at: datetime
    status: ConversationStatus = ConversationStatus.ACTIVE
    unread_count: int = 0
    auto_reply_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'late_conversation_id': self.late_conversation_id,
            'platform': self.platform,
            'account_id': self.account_id,
            'participant_id': self.participant_id,
            'participant_name': self.participant_name,
            'last_message': self.last_message,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status.value,
            'unread_count': self.unread_count,
            'auto_reply_enabled': self.auto_reply_enabled
        }


@dataclass
class DirectMessage:
    """
    A single DM in a conversation.

    Attributes:
        id: Local database ID
        conversation_id: Foreign key to Conversation
        late_message_id: Late API's message ID
        sender_id: Sender's platform ID
        sender_name: Sender's display name
        content: Message text
        direction: 'incoming' or 'outgoing'
        received_at: When message was received/sent
        replied: Whether we've replied to this
        reply_content: Our reply text
        replied_at: When we replied
        pending_review: Whether awaiting human approval
    """
    id: int
    conversation_id: int
    late_message_id: str
    sender_id: str
    sender_name: str
    content: str
    direction: str  # 'incoming' or 'outgoing'
    received_at: datetime
    replied: bool = False
    reply_content: Optional[str] = None
    replied_at: Optional[datetime] = None
    pending_review: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'late_message_id': self.late_message_id,
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'content': self.content,
            'direction': self.direction,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'replied': self.replied,
            'reply_content': self.reply_content,
            'replied_at': self.replied_at.isoformat() if self.replied_at else None,
            'pending_review': self.pending_review
        }


@dataclass
class BotAccount:
    """
    A bot account configuration for automated responses.

    Attributes:
        id: Local database ID
        name: Bot display name
        platform: Platform name
        late_account_id: Late account ID for this bot
        is_primary: Whether this is the primary bot
        is_active: Whether bot is enabled
        response_style: Style guide for responses
        max_replies_per_hour: Rate limit
        cooldown_seconds: Cooldown between replies to same user
        created_at: When bot was added
    """
    id: int
    name: str
    platform: str
    late_account_id: str
    is_primary: bool = False
    is_active: bool = True
    response_style: str = "professional"
    max_replies_per_hour: int = 60
    cooldown_seconds: int = 300
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'platform': self.platform,
            'late_account_id': self.late_account_id,
            'is_primary': self.is_primary,
            'is_active': self.is_active,
            'response_style': self.response_style,
            'max_replies_per_hour': self.max_replies_per_hour,
            'cooldown_seconds': self.cooldown_seconds,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class PendingReview:
    """
    An item pending human review before sending.

    Attributes:
        id: Local database ID
        item_type: 'comment' or 'dm'
        item_id: ID of the comment or DM
        platform: Platform name
        original_content: Original message we're replying to
        author: Author of original message
        generated_reply: AI-generated reply
        review_status: Current status
        reviewed_by: Who reviewed it
        reviewed_at: When it was reviewed
        final_reply: Approved/modified reply
        notes: Reviewer notes
    """
    id: int
    item_type: str  # 'comment' or 'dm'
    item_id: int
    platform: str
    original_content: str
    author: str
    generated_reply: str
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    final_reply: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'item_type': self.item_type,
            'item_id': self.item_id,
            'platform': self.platform,
            'original_content': self.original_content,
            'author': self.author,
            'generated_reply': self.generated_reply,
            'review_status': self.review_status.value,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'final_reply': self.final_reply,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
