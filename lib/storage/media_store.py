"""Media Storage Module

Handles image upload with persistent, own-domain hosting:
  - Primary:  Supabase Storage (own domain, permanent public URLs)
  - Fallback: Late SDK        (media.getlate.dev, ~7-day temp URLs)

Environment variables:
  SUPABASE_URL         — Supabase project URL (e.g. https://xxx.supabase.co)
  SUPABASE_SERVICE_KEY — Service role key (required for storage write access)
  MEDIA_BUCKET         — Supabase Storage bucket name (default: "social-media")
"""

from __future__ import annotations

import hashlib
import logging
import os
import time

logger = logging.getLogger(__name__)

MEDIA_BUCKET = os.getenv("MEDIA_BUCKET", "social-media")


def upload_image(local_path: str, prefix: str = "generated") -> str:
    """Upload an image file to persistent storage.

    Tries Supabase Storage first (own-domain, permanent URLs). Falls back
    to Late SDK temp hosting if Supabase is not configured.

    Args:
        local_path: Absolute path to the local image file.
        prefix:     Storage path prefix (e.g. "generated", "scheduler").

    Returns:
        Public HTTPS URL for the uploaded image.

    Raises:
        RuntimeError: If all upload backends fail.
    """
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")

    if supabase_url and supabase_key:
        try:
            url = _upload_to_supabase(local_path, prefix, supabase_url, supabase_key)
            logger.info(f"[media_store] Uploaded to Supabase: {url}")
            return url
        except Exception as exc:
            logger.warning(f"[media_store] Supabase upload failed, falling back to Late: {exc}")

    # Fallback: Late SDK
    try:
        url = _upload_to_late(local_path)
        logger.info(f"[media_store] Uploaded to Late (fallback): {url}")
        return url
    except Exception as exc:
        raise RuntimeError(f"All upload backends failed: {exc}") from exc


def _upload_to_supabase(
    local_path: str,
    prefix: str,
    supabase_url: str,
    supabase_key: str,
) -> str:
    """Upload image to Supabase Storage and return public URL.

    Builds a unique storage path: {prefix}/{timestamp}_{hash}.{ext}
    The bucket must already exist in the Supabase project with public access.
    """
    try:
        from supabase import create_client
    except ImportError:
        raise ImportError(
            "supabase package not installed. Run: pip install 'supabase>=2.0.0'"
        )

    ext = os.path.splitext(local_path)[1] or ".png"
    with open(local_path, "rb") as f:
        content = f.read()

    # Short hash for dedup — not security-critical
    file_hash = hashlib.md5(content).hexdigest()[:8]  # noqa: S324
    filename = f"{prefix}/{int(time.time())}_{file_hash}{ext}"

    content_type = "image/png" if ext.lower() == ".png" else "image/jpeg"

    client = create_client(supabase_url, supabase_key)
    bucket = client.storage.from_(MEDIA_BUCKET)

    bucket.upload(
        path=filename,
        file=content,
        file_options={"content-type": content_type, "cache-control": "3600"},
    )

    public_url = bucket.get_public_url(filename)
    return str(public_url)


def _upload_to_late(local_path: str) -> str:
    """Upload image to Late SDK media hosting (fallback path)."""
    from late import Late

    api_key = os.getenv("LATE_API_KEY", "")
    if not api_key:
        raise ValueError("LATE_API_KEY required for Late media upload")

    client = Late(api_key=api_key)
    response = client.media.upload(local_path)
    return str(response.files[0].url)
