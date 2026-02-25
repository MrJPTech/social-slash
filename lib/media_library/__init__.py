"""Media Library — real photo/screenshot index for authentic social posts.

Upload screenshots to Supabase Storage (or sync from local iCloud/Desktop
folders), analyze with Gemini Vision, and match to scheduled content slots.
"""

from lib.media_library.catalog import MediaCatalog
from lib.media_library.local_scanner import LocalFolderScanner
from lib.media_library.matcher import MediaMatcher
from lib.media_library.scanner import BucketScanner
from lib.media_library.vision import VisionAnalyzer

__all__ = [
    "MediaCatalog",
    "MediaMatcher",
    "BucketScanner",
    "LocalFolderScanner",
    "VisionAnalyzer",
]
