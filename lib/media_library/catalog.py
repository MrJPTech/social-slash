"""SQLite-backed media catalog for the screenshot/photo library.

Indexes images with Gemini Vision metadata for content-to-image matching.
Follows the same patterns as lib/scheduler/approval_store.py.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DB_PATH = os.getenv("MEDIA_LIBRARY_DB_PATH", "data/media_library.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS media_items (
    id              TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    category        TEXT DEFAULT 'screenshot',
    storage_url     TEXT NOT NULL UNIQUE,
    width           INTEGER,
    height          INTEGER,
    file_size       INTEGER,
    mime_type       TEXT,
    description     TEXT NOT NULL DEFAULT '',
    tags            TEXT NOT NULL DEFAULT '[]',
    themes          TEXT NOT NULL DEFAULT '[]',
    text_content    TEXT DEFAULT '',
    mood            TEXT DEFAULT '',
    pillar_affinity TEXT DEFAULT '{}',
    platform_fit    TEXT DEFAULT '{}',
    times_used      INTEGER DEFAULT 0,
    last_used_at    TEXT,
    status          TEXT DEFAULT 'available',
    ingested_at     TEXT NOT NULL
);
"""


@contextmanager
def _conn():
    """Open a SQLite connection, ensure table exists, and auto-commit/close."""
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        con.execute(_CREATE_TABLE)
        con.commit()
        yield con
        con.commit()
    finally:
        con.close()


class MediaCatalog:
    """Persist and query media library items via SQLite."""

    def add(
        self,
        item_id: str,
        filename: str,
        storage_url: str,
        vision_data: Dict[str, Any],
        *,
        category: str = "screenshot",
        width: int = 0,
        height: int = 0,
        file_size: int = 0,
        mime_type: str = "",
    ) -> None:
        """Insert a new media item with vision analysis data."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with _conn() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO media_items
                  (id, filename, category, storage_url, width, height,
                   file_size, mime_type, description, tags, themes,
                   text_content, mood, pillar_affinity, platform_fit,
                   ingested_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    item_id,
                    filename,
                    category,
                    storage_url,
                    width,
                    height,
                    file_size,
                    mime_type,
                    vision_data.get("description", ""),
                    json.dumps(vision_data.get("tags", [])),
                    json.dumps(vision_data.get("themes", [])),
                    vision_data.get("text_content", ""),
                    vision_data.get("mood", ""),
                    json.dumps(vision_data.get("pillar_affinity", {})),
                    json.dumps(vision_data.get("platform_fit", {})),
                    now_iso,
                ),
            )

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Return a single media item by ID, or None."""
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM media_items WHERE id = ?", (item_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def exists_by_url(self, url: str) -> bool:
        """Check if an image with this storage URL is already indexed."""
        with _conn() as con:
            row = con.execute(
                "SELECT 1 FROM media_items WHERE storage_url = ?", (url,)
            ).fetchone()
        return row is not None

    def get_available(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Return available items sorted by least-used first."""
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM media_items WHERE status = 'available' "
                "ORDER BY times_used ASC, ingested_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def find_by_pillar(
        self, pillar: str, platform: str = "", limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find items whose pillar_affinity matches the given pillar.

        Uses a LIKE search on the JSON-encoded pillar_affinity field.
        """
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM media_items WHERE status = 'available' "
                "AND pillar_affinity LIKE ? "
                "ORDER BY times_used ASC LIMIT ?",
                (f"%{pillar}%", limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def find_by_query(self, keywords: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search items by keywords matching tags or description."""
        pattern = f"%{keywords}%"
        with _conn() as con:
            rows = con.execute(
                "SELECT * FROM media_items WHERE status = 'available' "
                "AND (tags LIKE ? OR description LIKE ?) "
                "ORDER BY times_used ASC LIMIT ?",
                (pattern, pattern, limit),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def mark_used(self, item_id: str, platform: str = "") -> None:
        """Increment usage counter and update last_used_at."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with _conn() as con:
            con.execute(
                "UPDATE media_items SET times_used = times_used + 1, "
                "last_used_at = ? WHERE id = ?",
                (now_iso, item_id),
            )

    def set_status(self, item_id: str, status: str) -> None:
        """Update item status: available, exhausted, or archived."""
        with _conn() as con:
            con.execute(
                "UPDATE media_items SET status = ? WHERE id = ?",
                (status, item_id),
            )

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate stats about the media library."""
        with _conn() as con:
            total = con.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
            available = con.execute(
                "SELECT COUNT(*) FROM media_items WHERE status = 'available'"
            ).fetchone()[0]
            used = con.execute(
                "SELECT COUNT(*) FROM media_items WHERE times_used > 0"
            ).fetchone()[0]
            categories = con.execute(
                "SELECT category, COUNT(*) as cnt FROM media_items GROUP BY category"
            ).fetchall()

        return {
            "total": total,
            "available": available,
            "used_at_least_once": used,
            "archived": total - available,
            "categories": {r["category"]: r["cnt"] for r in categories},
        }

    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "filename": row["filename"],
            "category": row["category"],
            "storage_url": row["storage_url"],
            "width": row["width"],
            "height": row["height"],
            "file_size": row["file_size"],
            "mime_type": row["mime_type"],
            "description": row["description"],
            "tags": json.loads(row["tags"]),
            "themes": json.loads(row["themes"]),
            "text_content": row["text_content"],
            "mood": row["mood"],
            "pillar_affinity": json.loads(row["pillar_affinity"]),
            "platform_fit": json.loads(row["platform_fit"]),
            "times_used": row["times_used"],
            "last_used_at": row["last_used_at"],
            "status": row["status"],
            "ingested_at": row["ingested_at"],
        }
