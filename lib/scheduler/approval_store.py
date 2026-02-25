"""SQLite-backed approval store for SLASHERBOT content bundles.

Stores generated content bundles with a 2-hour approval TTL.
If no human approves within the TTL, the daily scheduler auto-posts.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from lib.scheduler.content_pipeline import ContentBundle

DB_PATH = os.getenv("APPROVAL_DB_PATH", "data/approvals.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS approvals (
    slot_id      TEXT PRIMARY KEY,
    platform     TEXT NOT NULL,
    subreddit    TEXT,
    pillar       TEXT NOT NULL,
    topic        TEXT NOT NULL,
    option_a     TEXT NOT NULL,
    option_b     TEXT NOT NULL,
    image_1_url  TEXT NOT NULL,
    image_2_url  TEXT NOT NULL,
    scheduled_time TEXT NOT NULL,
    expires_at   TEXT NOT NULL,
    posted       INTEGER NOT NULL DEFAULT 0,
    choice       TEXT,
    image_source TEXT DEFAULT 'none',
    library_item_ids TEXT DEFAULT '[]'
);
"""

# Migration: add new columns to existing tables (idempotent)
_MIGRATIONS = [
    "ALTER TABLE approvals ADD COLUMN image_source TEXT DEFAULT 'none'",
    "ALTER TABLE approvals ADD COLUMN library_item_ids TEXT DEFAULT '[]'",
]


@contextmanager
def _conn():
    """Open a SQLite connection, ensure table exists, and auto-commit/close."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.execute(_CREATE_TABLE)
        # Run migrations (safe on new tables — column already exists → no-op)
        for migration in _MIGRATIONS:
            try:
                con.execute(migration)
            except sqlite3.OperationalError:
                pass  # Column already exists
        con.commit()
        yield con
        con.commit()
    finally:
        con.close()


class ApprovalStore:
    """Persist and query SLASHERBOT content bundles via SQLite."""

    def save(self, bundle: "ContentBundle") -> None:
        """Insert or replace a ContentBundle in the store."""
        with _conn() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO approvals
                  (slot_id, platform, subreddit, pillar, topic,
                   option_a, option_b, image_1_url, image_2_url,
                   scheduled_time, expires_at, posted, choice,
                   image_source, library_item_ids)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    bundle.slot_id,
                    bundle.platform,
                    bundle.subreddit,
                    bundle.pillar,
                    bundle.topic,
                    json.dumps(bundle.option_a),
                    json.dumps(bundle.option_b),
                    bundle.image_1_url,
                    bundle.image_2_url,
                    bundle.scheduled_time.isoformat(),
                    bundle.expires_at.isoformat(),
                    1 if bundle.posted else 0,
                    bundle.choice,
                    getattr(bundle, "image_source", "none"),
                    json.dumps(getattr(bundle, "library_item_ids", [])),
                ),
            )

    def get(self, slot_id: str) -> Optional["ContentBundle"]:
        """Return a ContentBundle by slot_id, or None if not found."""
        from lib.scheduler.content_pipeline import ContentBundle  # local import avoids circular

        with _conn() as con:
            row = con.execute(
                "SELECT * FROM approvals WHERE slot_id = ?", (slot_id,)
            ).fetchone()
        if not row:
            return None
        return self._row_to_bundle(row)

    def mark_posted(self, slot_id: str, choice: str) -> None:
        """Mark a bundle as posted with the given choice (A1/A2/B1/B2)."""
        with _conn() as con:
            con.execute(
                "UPDATE approvals SET posted = 1, choice = ? WHERE slot_id = ?",
                (choice, slot_id),
            )

    def is_posted(self, slot_id: str) -> bool:
        """Return True if this slot has already been posted."""
        with _conn() as con:
            row = con.execute(
                "SELECT posted FROM approvals WHERE slot_id = ?", (slot_id,)
            ).fetchone()
        return bool(row and row["posted"])

    def get_pending_expired(self) -> List["ContentBundle"]:
        """Return all bundles whose TTL has passed but have not been posted."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM approvals WHERE posted = 0 AND expires_at < ?",
                (now_iso,),
            ).fetchall()
        return [self._row_to_bundle(r) for r in rows]

    def get_pending_active(self) -> List["ContentBundle"]:
        """Return all non-posted bundles ordered by expires_at ascending."""
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM approvals WHERE posted = 0 ORDER BY expires_at ASC"
            ).fetchall()
        return [self._row_to_bundle(r) for r in rows]

    def get_by_prefix(self, slot_prefix: str) -> Optional["ContentBundle"]:
        """Look up a bundle by the first N characters of its slot_id."""
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM approvals WHERE slot_id LIKE ? LIMIT 1",
                (f"{slot_prefix}%",),
            ).fetchone()
        return self._row_to_bundle(row) if row else None

    def cleanup_old(self, days: int = 7) -> int:
        """Delete records older than `days` days. Returns count deleted."""
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with _conn() as con:
            cur = con.execute(
                "DELETE FROM approvals WHERE scheduled_time < ?", (cutoff,)
            )
            return cur.rowcount

    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_bundle(row: sqlite3.Row) -> "ContentBundle":
        from lib.scheduler.content_pipeline import ContentBundle  # local import

        # Safely read new columns (may be absent in old DBs before migration)
        try:
            image_source = row["image_source"] or "none"
        except (IndexError, KeyError):
            image_source = "none"
        try:
            library_ids = json.loads(row["library_item_ids"] or "[]")
        except (IndexError, KeyError, json.JSONDecodeError):
            library_ids = []

        return ContentBundle(
            slot_id=row["slot_id"],
            platform=row["platform"],
            subreddit=row["subreddit"],
            pillar=row["pillar"],
            topic=row["topic"],
            option_a=json.loads(row["option_a"]),
            option_b=json.loads(row["option_b"]),
            image_1_url=row["image_1_url"],
            image_2_url=row["image_2_url"],
            scheduled_time=datetime.fromisoformat(row["scheduled_time"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            posted=bool(row["posted"]),
            choice=row["choice"],
            image_source=image_source,
            library_item_ids=library_ids,
        )
