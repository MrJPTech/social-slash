"""Supabase Storage bucket scanner for unindexed media library images.

Scans the library/ prefix in the configured Supabase bucket, compares
against the MediaCatalog, and ingests new files through VisionAnalyzer.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

MEDIA_BUCKET = os.getenv("MEDIA_BUCKET", "social-media")
LIBRARY_PREFIX = "library"


class BucketScanner:
    """Scan Supabase Storage for unindexed images and ingest them."""

    def __init__(self) -> None:
        self._supabase_url = os.getenv("SUPABASE_URL", "")
        self._supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not self._supabase_url or not self._supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_KEY required for bucket scanning"
            )

    def _get_client(self):
        from supabase import create_client
        return create_client(self._supabase_url, self._supabase_key)

    def scan(self) -> List[Dict[str, Any]]:
        """List files in the library/ prefix that aren't yet indexed.

        Returns:
            List of dicts with filename, public_url, and metadata for unindexed files.
        """
        from lib.media_library.catalog import MediaCatalog

        client = self._get_client()
        bucket = client.storage.from_(MEDIA_BUCKET)
        catalog = MediaCatalog()

        try:
            files = bucket.list(LIBRARY_PREFIX)
        except Exception as exc:
            logger.error(f"[scanner] Failed to list bucket: {exc}")
            return []

        unindexed = []
        for file_info in files:
            name = file_info.get("name", "")
            if not name:
                continue

            # Skip directory placeholders
            if name.endswith("/") or file_info.get("id") is None:
                continue

            # Build public URL
            storage_path = f"{LIBRARY_PREFIX}/{name}"
            public_url = str(bucket.get_public_url(storage_path))

            if catalog.exists_by_url(public_url):
                continue

            unindexed.append({
                "filename": name,
                "storage_path": storage_path,
                "public_url": public_url,
                "metadata": file_info.get("metadata", {}),
            })

        logger.info(f"[scanner] Found {len(unindexed)} unindexed file(s) in {LIBRARY_PREFIX}/")
        return unindexed

    def ingest_new(self) -> Dict[str, Any]:
        """Full pipeline: scan -> download bytes -> vision analyze -> add to catalog.

        Returns:
            {ingested: N, skipped: N, errors: [...]}
        """
        from lib.media_library.catalog import MediaCatalog
        from lib.media_library.vision import VisionAnalyzer

        unindexed = self.scan()
        if not unindexed:
            return {"ingested": 0, "skipped": 0, "errors": []}

        client = self._get_client()
        bucket = client.storage.from_(MEDIA_BUCKET)
        catalog = MediaCatalog()

        try:
            analyzer = VisionAnalyzer()
        except ValueError as exc:
            return {"ingested": 0, "skipped": len(unindexed), "errors": [str(exc)]}

        ingested = 0
        skipped = 0
        errors: List[str] = []

        for file_info in unindexed:
            filename = file_info["filename"]
            storage_path = file_info["storage_path"]
            public_url = file_info["public_url"]

            try:
                # Download file bytes from Supabase
                file_bytes = bucket.download(storage_path)

                # Determine mime type
                ext = os.path.splitext(filename)[1].lower()
                mime_map = {
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".gif": "image/gif",
                    ".webp": "image/webp",
                }
                mime_type = mime_map.get(ext, "image/png")

                # Analyze with Gemini Vision
                vision_data = analyzer.analyze_bytes(file_bytes, mime_type)

                # Index in catalog
                item_id = str(uuid.uuid4())
                catalog.add(
                    item_id=item_id,
                    filename=filename,
                    storage_url=public_url,
                    vision_data=vision_data,
                    mime_type=mime_type,
                    file_size=len(file_bytes),
                )

                ingested += 1
                logger.info(f"[scanner] Ingested: {filename} -> {item_id[:8]}")

            except Exception as exc:
                errors.append(f"{filename}: {exc}")
                skipped += 1
                logger.error(f"[scanner] Failed to ingest {filename}: {exc}")

        return {"ingested": ingested, "skipped": skipped, "errors": errors}
