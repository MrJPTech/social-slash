r"""Local folder scanner for the media library.

Watches configured local directories (iCloud, Desktop, etc.) for new
media files, uploads them to Supabase Storage, analyzes with Gemini Vision,
and indexes in the MediaCatalog.

Default sync folders (override with MEDIA_SYNC_FOLDERS env var):
  D:\ICLOUD-OCTOBER'25\iCloudDrive\DAILY-UPDATES\SocialSlasher\Media\photos
  D:\ICLOUD-OCTOBER'25\iCloudDrive\DAILY-UPDATES\SocialSlasher\Media\videos
  D:\ICLOUD-OCTOBER'25\iCloudDrive\DAILY-UPDATES\SocialSlasher\Media\screenshots
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Default iCloud sync folders ──────────────────────────────────────────

_ICLOUD_BASE = (
    r"D:\ICLOUD-OCTOBER'25\iCloudDrive\DAILY-UPDATES\SocialSlasher\Media"
)

DEFAULT_SYNC_FOLDERS: List[Dict[str, str]] = [
    {"path": os.path.join(_ICLOUD_BASE, "photos"), "category": "photo"},
    {"path": os.path.join(_ICLOUD_BASE, "videos"), "category": "video"},
    {"path": os.path.join(_ICLOUD_BASE, "screenshots"), "category": "screenshot"},
]

# ── Supported file types ─────────────────────────────────────────────────

IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif"}
)
VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".webm"})
ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

MIME_MAP: Dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
}


def _sanitize_filename(name: str) -> str:
    """Sanitize a filename for safe Supabase storage paths."""
    # Replace non-alphanumeric (except dots, hyphens, underscores) with _
    name = re.sub(r"[^\w.\-]", "_", name)
    # Collapse runs of underscores
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower()


class LocalFolderScanner:
    """Scan local folders for new media and ingest into the library.

    Folders are configured via ``DEFAULT_SYNC_FOLDERS`` or the
    ``MEDIA_SYNC_FOLDERS`` environment variable (comma-separated
    ``path|category`` pairs, pipe-delimited to avoid Windows colon issues).
    """

    def __init__(self, folders: Optional[List[Dict[str, str]]] = None) -> None:
        self._folders = folders or self._load_folders()

    # ── Configuration ────────────────────────────────────────────────────

    @staticmethod
    def _load_folders() -> List[Dict[str, str]]:
        """Load folder config from env or use defaults."""
        env_val = os.getenv("MEDIA_SYNC_FOLDERS", "")
        if not env_val:
            return DEFAULT_SYNC_FOLDERS

        # Format: "path|category,path|category,..."
        # Uses pipe (|) separator so Windows drive letters (C:\) don't clash.
        folders: List[Dict[str, str]] = []
        for entry in env_val.split(","):
            entry = entry.strip()
            if "|" in entry:
                path, category = entry.rsplit("|", 1)
            else:
                path, category = entry, "screenshot"
            folders.append({"path": path.strip(), "category": category.strip()})
        return folders

    @property
    def folders(self) -> List[Dict[str, str]]:
        """Return the configured folder list (for inspection / testing)."""
        return list(self._folders)

    # ── Scanning ─────────────────────────────────────────────────────────

    def scan(self) -> List[Dict[str, Any]]:
        """Find new media files across all configured folders.

        Skips files already indexed in the catalog (by expected storage URL).

        Returns:
            List of file-info dicts for *unindexed* files.
        """
        from lib.media_library.catalog import MediaCatalog

        catalog = MediaCatalog()
        new_files: List[Dict[str, Any]] = []

        for folder_cfg in self._folders:
            folder_path = Path(folder_cfg["path"])
            category = folder_cfg["category"]

            if not folder_path.exists():
                logger.warning(f"[local_scanner] Folder not found: {folder_path}")
                continue

            for file_path in sorted(folder_path.iterdir()):
                if not file_path.is_file():
                    continue

                ext = file_path.suffix.lower()
                if ext not in ALL_MEDIA_EXTENSIONS:
                    continue

                # Deterministic storage name from content hash + sanitized name
                file_hash = self._file_hash(file_path)
                safe_name = _sanitize_filename(file_path.name)
                storage_name = f"{file_hash}_{safe_name}"
                storage_prefix = f"library/{category}"
                expected_url = self._build_expected_url(
                    f"{storage_prefix}/{storage_name}"
                )

                if catalog.exists_by_url(expected_url):
                    continue

                new_files.append(
                    {
                        "local_path": str(file_path),
                        "filename": file_path.name,
                        "category": category,
                        "storage_name": storage_name,
                        "storage_prefix": storage_prefix,
                        "expected_url": expected_url,
                        "extension": ext,
                        "mime_type": MIME_MAP.get(ext, "application/octet-stream"),
                        "file_size": file_path.stat().st_size,
                        "is_video": ext in VIDEO_EXTENSIONS,
                    }
                )

        logger.info(
            f"[local_scanner] Found {len(new_files)} new file(s) "
            f"across {len(self._folders)} folder(s)"
        )
        return new_files

    # ── Ingestion ────────────────────────────────────────────────────────

    def ingest_new(self) -> Dict[str, Any]:
        """Full pipeline: scan → upload to Supabase → vision analyze → index.

        Returns:
            {ingested, skipped, errors, details}
        """
        from lib.media_library.catalog import MediaCatalog
        from lib.media_library.vision import VisionAnalyzer

        new_files = self.scan()
        if not new_files:
            return {"ingested": 0, "skipped": 0, "errors": [], "details": []}

        catalog = MediaCatalog()

        try:
            analyzer = VisionAnalyzer()
        except ValueError as exc:
            return {
                "ingested": 0,
                "skipped": len(new_files),
                "errors": [str(exc)],
                "details": [],
            }

        ingested = 0
        skipped = 0
        errors: List[str] = []
        details: List[Dict[str, str]] = []

        for file_info in new_files:
            local_path = file_info["local_path"]
            filename = file_info["filename"]
            category = file_info["category"]
            mime_type = file_info["mime_type"]
            is_video = file_info["is_video"]

            try:
                # Step 1: Upload to Supabase Storage
                storage_url = self._upload_file(
                    local_path,
                    file_info["storage_prefix"],
                    file_info["storage_name"],
                    mime_type,
                )

                # Step 2: Vision analysis
                if is_video:
                    # Videos: basic metadata — Gemini Vision for video TBD
                    vision_data = self._video_metadata(filename, category)
                else:
                    with open(local_path, "rb") as f:
                        image_bytes = f.read()
                    vision_data = analyzer.analyze_bytes(image_bytes, mime_type)

                # Step 3: Index in catalog
                item_id = str(uuid.uuid4())
                catalog.add(
                    item_id=item_id,
                    filename=filename,
                    storage_url=storage_url,
                    vision_data=vision_data,
                    category=category,
                    mime_type=mime_type,
                    file_size=file_info["file_size"],
                )

                ingested += 1
                desc = vision_data.get("description", "")[:80]
                tags = ", ".join(vision_data.get("tags", [])[:5])
                details.append(
                    {
                        "filename": filename,
                        "item_id": item_id,
                        "category": category,
                        "description": desc,
                        "tags": tags,
                    }
                )
                logger.info(
                    f"[local_scanner] Ingested: {filename} ({category}) "
                    f"-> {item_id[:8]}"
                )

            except Exception as exc:
                errors.append(f"{filename}: {exc}")
                skipped += 1
                logger.error(f"[local_scanner] Failed to ingest {filename}: {exc}")

        return {
            "ingested": ingested,
            "skipped": skipped,
            "errors": errors,
            "details": details,
        }

    # ── Stats ────────────────────────────────────────────────────────────

    def get_folder_stats(self) -> Dict[str, Any]:
        """Return info about each configured sync folder."""
        stats: List[Dict[str, Any]] = []
        total_files = 0

        for folder_cfg in self._folders:
            folder_path = Path(folder_cfg["path"])
            category = folder_cfg["category"]

            if not folder_path.exists():
                stats.append(
                    {
                        "path": str(folder_path),
                        "category": category,
                        "exists": False,
                        "file_count": 0,
                    }
                )
                continue

            files = [
                f
                for f in folder_path.iterdir()
                if f.is_file() and f.suffix.lower() in ALL_MEDIA_EXTENSIONS
            ]
            total_files += len(files)
            stats.append(
                {
                    "path": str(folder_path),
                    "category": category,
                    "exists": True,
                    "file_count": len(files),
                }
            )

        return {"folders": stats, "total_folders": len(stats), "total_files": total_files}

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _file_hash(path: Path) -> str:
        """Short content hash (first 64 KB) for dedup."""
        h = hashlib.md5()  # noqa: S324 — not security-critical
        with open(path, "rb") as f:
            h.update(f.read(65_536))
        return h.hexdigest()[:10]

    @staticmethod
    def _build_expected_url(storage_path: str) -> str:
        """Construct the canonical Supabase public URL for a storage path."""
        supabase_url = os.getenv("SUPABASE_URL", "")
        bucket = os.getenv("MEDIA_BUCKET", "social-media")
        return (
            f"{supabase_url}/storage/v1/object/public/{bucket}/{storage_path}"
        )

    @staticmethod
    def _upload_file(
        local_path: str,
        prefix: str,
        storage_name: str,
        content_type: str,
    ) -> str:
        """Upload a local file to Supabase Storage and return its public URL."""
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")

        from supabase import create_client

        with open(local_path, "rb") as f:
            content = f.read()

        storage_path = f"{prefix}/{storage_name}"
        bucket_name = os.getenv("MEDIA_BUCKET", "social-media")

        client = create_client(supabase_url, supabase_key)
        bucket = client.storage.from_(bucket_name)
        bucket.upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "cache-control": "3600"},
        )

        return str(bucket.get_public_url(storage_path))

    @staticmethod
    def _video_metadata(filename: str, category: str) -> Dict[str, Any]:
        """Return placeholder vision data for video files."""
        return {
            "description": f"Video: {filename}",
            "tags": ["video", category],
            "themes": [],
            "text_content": "",
            "mood": "",
            "pillar_affinity": {},
            "platform_fit": {
                "tiktok": 0.9,
                "instagram": 0.8,
                "youtube": 0.9,
                "facebook": 0.7,
                "twitter": 0.5,
                "linkedin": 0.4,
                "threads": 0.5,
                "reddit": 0.4,
            },
        }
