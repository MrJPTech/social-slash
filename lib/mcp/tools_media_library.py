"""Media library tools — scan, search, preview, and sync local photo/screenshot library."""

from __future__ import annotations

import json

from ._shared import mcp


@mcp.tool()
def media_library_scan() -> str:
    """Scan Supabase bucket for new unindexed images and ingest them.

    Looks in the social-media/library/ prefix for images not yet in the
    catalog, analyzes them with Gemini Vision, and indexes them for
    content matching.

    Requires SUPABASE_URL, SUPABASE_SERVICE_KEY, and GOOGLE_API_KEY.
    """
    try:
        from lib.media_library.scanner import BucketScanner

        scanner = BucketScanner()
        result = scanner.ingest_new()
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error scanning library: {e}"


@mcp.tool()
def media_library_search(
    query: str = "",
    pillar: str = "",
    platform: str = "",
    limit: int = 5,
) -> str:
    """Search the media library for images matching criteria.

    Args:
        query: Text to match against tags and descriptions
        pillar: Content pillar to filter by affinity
        platform: Target platform to filter by fit
        limit: Max results to return (default 5)
    """
    try:
        from lib.media_library.catalog import MediaCatalog

        catalog = MediaCatalog()

        if pillar:
            items = catalog.find_by_pillar(pillar, platform, limit)
        elif query:
            items = catalog.find_by_query(query, limit)
        else:
            items = catalog.get_available(limit)

        return json.dumps(items, indent=2, default=str)
    except Exception as e:
        return f"Error searching library: {e}"


@mcp.tool()
def media_library_stats() -> str:
    """Show media library statistics.

    Returns total/available/used counts and category breakdown.
    """
    try:
        from lib.media_library.catalog import MediaCatalog

        catalog = MediaCatalog()
        stats = catalog.get_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        return f"Error getting library stats: {e}"


@mcp.tool()
def media_library_preview(item_id: str) -> str:
    """Get full vision analysis details for a single library image.

    Args:
        item_id: The media item UUID to look up
    """
    try:
        from lib.media_library.catalog import MediaCatalog

        catalog = MediaCatalog()
        item = catalog.get_item(item_id)
        if not item:
            return f"Item {item_id} not found in library"
        return json.dumps(item, indent=2, default=str)
    except Exception as e:
        return f"Error previewing item: {e}"


@mcp.tool()
def media_library_sync_local() -> str:
    """Sync media from local iCloud/Desktop folders into the library.

    Scans configured local folders for new photos, screenshots, and videos.
    Uploads them to Supabase Storage, analyzes with Gemini Vision, and
    indexes in the catalog for content matching.

    Default folders (iCloud):
      .../SocialSlasher/Media/photos
      .../SocialSlasher/Media/videos
      .../SocialSlasher/Media/screenshots

    Override with MEDIA_SYNC_FOLDERS env var (pipe-delimited: path|category).
    Requires SUPABASE_URL, SUPABASE_SERVICE_KEY, and GOOGLE_API_KEY.
    """
    try:
        from lib.media_library.local_scanner import LocalFolderScanner

        scanner = LocalFolderScanner()

        # Show folder stats first
        stats = scanner.get_folder_stats()
        accessible = sum(1 for f in stats["folders"] if f["exists"])
        if accessible == 0:
            folder_lines = "\n".join(f"  - {f['path']} ({f['category']})" for f in stats["folders"])
            return (
                f"No sync folders accessible.\n"
                f"Configured folders:\n{folder_lines}\n\n"
                f"Make sure the folders exist or set MEDIA_SYNC_FOLDERS env var."
            )

        result = scanner.ingest_new()

        parts = [
            f"Local sync: {result['ingested']} ingested, {result['skipped']} skipped",
            f"Folders: {accessible}/{stats['total_folders']} accessible, "
            f"{stats['total_files']} total files",
        ]

        if result["details"]:
            parts.append("\nNew items:")
            for d in result["details"]:
                parts.append(f"  [{d['category']}] {d['filename']}: {d['description']}")

        if result["errors"]:
            parts.append(f"\nErrors: {', '.join(result['errors'])}")

        return "\n".join(parts)
    except Exception as e:
        return f"Error syncing local folders: {e}"


@mcp.tool()
def media_library_folder_stats() -> str:
    """Show configured local media sync folders and file counts.

    Lists each folder path, whether it exists, and how many media files
    are in it. Useful for verifying iCloud sync is working.
    """
    try:
        from lib.media_library.local_scanner import LocalFolderScanner

        scanner = LocalFolderScanner()
        stats = scanner.get_folder_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        return f"Error getting folder stats: {e}"
