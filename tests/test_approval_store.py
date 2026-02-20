"""Tests for ApprovalStore — SQLite TTL, get/save/mark, expiry detection."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from lib.scheduler.content_pipeline import ContentBundle


def _make_bundle(slot_id="test-slot-001", posted=False, hours_until_expire=2):
    now = datetime.now(timezone.utc)
    return ContentBundle(
        slot_id=slot_id,
        platform="twitter",
        subreddit=None,
        pillar="building in public",
        topic="AI automation tools for developers",
        option_a={"content": "Option A content", "hashtags": ["#buildinpublic"], "persona_mode": "professional"},
        option_b={"content": "Option B content", "hashtags": ["#startup"], "persona_mode": "ceo"},
        image_1_url="https://media.getlate.dev/temp/img1.jpg",
        image_2_url="https://media.getlate.dev/temp/img2.jpg",
        scheduled_time=now,
        expires_at=now + timedelta(hours=hours_until_expire),
        posted=posted,
    )


@pytest.fixture()
def store(tmp_path):
    """Return an ApprovalStore backed by a temp SQLite file."""
    db_path = str(tmp_path / "approvals.db")
    with patch("lib.scheduler.approval_store.DB_PATH", db_path):
        from lib.scheduler.approval_store import ApprovalStore
        yield ApprovalStore()


class TestSaveAndGet:
    def test_save_and_retrieve(self, store):
        bundle = _make_bundle()
        store.save(bundle)
        retrieved = store.get(bundle.slot_id)
        assert retrieved is not None
        assert retrieved.slot_id == bundle.slot_id
        assert retrieved.platform == "twitter"
        assert retrieved.pillar == "building in public"

    def test_get_nonexistent_returns_none(self, store):
        assert store.get("nonexistent-slot") is None

    def test_option_a_roundtrip(self, store):
        bundle = _make_bundle()
        store.save(bundle)
        retrieved = store.get(bundle.slot_id)
        assert retrieved.option_a["content"] == "Option A content"
        assert retrieved.option_a["hashtags"] == ["#buildinpublic"]

    def test_option_b_roundtrip(self, store):
        bundle = _make_bundle()
        store.save(bundle)
        retrieved = store.get(bundle.slot_id)
        assert retrieved.option_b["persona_mode"] == "ceo"

    def test_posted_flag_false_by_default(self, store):
        bundle = _make_bundle()
        store.save(bundle)
        assert not store.is_posted(bundle.slot_id)

    def test_subreddit_roundtrip(self, store):
        bundle = _make_bundle()
        bundle.subreddit = "r/SideProject"
        store.save(bundle)
        retrieved = store.get(bundle.slot_id)
        assert retrieved.subreddit == "r/SideProject"


class TestMarkPosted:
    def test_mark_posted(self, store):
        bundle = _make_bundle()
        store.save(bundle)
        store.mark_posted(bundle.slot_id, "A1")
        assert store.is_posted(bundle.slot_id)

    def test_choice_persisted(self, store):
        bundle = _make_bundle()
        store.save(bundle)
        store.mark_posted(bundle.slot_id, "B2")
        retrieved = store.get(bundle.slot_id)
        assert retrieved.choice == "B2"
        assert retrieved.posted is True

    def test_is_posted_unknown_slot(self, store):
        assert not store.is_posted("unknown-slot")


class TestExpiry:
    def test_expired_bundle_returned(self, store):
        bundle = _make_bundle(hours_until_expire=-1)  # expired 1 hour ago
        store.save(bundle)
        expired = store.get_pending_expired()
        assert any(b.slot_id == bundle.slot_id for b in expired)

    def test_active_bundle_not_in_expired(self, store):
        bundle = _make_bundle(hours_until_expire=1)  # still 1 hour to go
        store.save(bundle)
        expired = store.get_pending_expired()
        assert not any(b.slot_id == bundle.slot_id for b in expired)

    def test_posted_bundle_not_in_expired(self, store):
        bundle = _make_bundle(hours_until_expire=-1, posted=True)
        store.save(bundle)
        expired = store.get_pending_expired()
        assert not any(b.slot_id == bundle.slot_id for b in expired)


class TestCleanup:
    def test_cleanup_old_deletes_old_records(self, store):
        # Create a bundle with scheduled_time 8 days ago
        bundle = _make_bundle(slot_id="old-slot")
        bundle.scheduled_time = datetime.now(timezone.utc) - timedelta(days=8)
        store.save(bundle)
        deleted = store.cleanup_old(days=7)
        assert deleted >= 1
        assert store.get("old-slot") is None

    def test_cleanup_keeps_recent_records(self, store):
        bundle = _make_bundle(slot_id="recent-slot")
        store.save(bundle)
        deleted = store.cleanup_old(days=7)
        # Recent slot should still exist
        assert store.get("recent-slot") is not None
