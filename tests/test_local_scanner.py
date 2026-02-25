"""Tests for the LocalFolderScanner — local iCloud/Desktop media sync."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from lib.media_library.local_scanner import (
    ALL_MEDIA_EXTENSIONS,
    DEFAULT_SYNC_FOLDERS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    LocalFolderScanner,
    _sanitize_filename,
)


class TestSanitizeFilename(unittest.TestCase):
    """Filename sanitization for Supabase storage paths."""

    def test_spaces_replaced(self):
        self.assertEqual(_sanitize_filename("my photo.png"), "my_photo.png")

    def test_special_chars_replaced(self):
        self.assertEqual(
            _sanitize_filename("screen (1) @2x.png"),
            "screen_1_2x.png",
        )

    def test_apostrophe_replaced(self):
        self.assertEqual(
            _sanitize_filename("jordan's-pic.jpg"),
            "jordan_s-pic.jpg",
        )

    def test_already_clean(self):
        self.assertEqual(_sanitize_filename("clean_file.png"), "clean_file.png")

    def test_lowercase(self):
        self.assertEqual(_sanitize_filename("IMG_1234.PNG"), "img_1234.png")

    def test_collapses_underscores(self):
        self.assertEqual(_sanitize_filename("a___b.jpg"), "a_b.jpg")


class TestFolderConfig(unittest.TestCase):
    """Folder configuration loading."""

    def test_defaults_have_three_folders(self):
        self.assertEqual(len(DEFAULT_SYNC_FOLDERS), 3)

    def test_default_categories(self):
        cats = {f["category"] for f in DEFAULT_SYNC_FOLDERS}
        self.assertEqual(cats, {"photo", "video", "screenshot"})

    def test_env_override(self):
        env_val = r"C:\photos|photo,C:\screenshots|screenshot"
        with patch.dict(os.environ, {"MEDIA_SYNC_FOLDERS": env_val}):
            scanner = LocalFolderScanner()
            self.assertEqual(len(scanner.folders), 2)
            self.assertEqual(scanner.folders[0]["path"], r"C:\photos")
            self.assertEqual(scanner.folders[0]["category"], "photo")
            self.assertEqual(scanner.folders[1]["path"], r"C:\screenshots")
            self.assertEqual(scanner.folders[1]["category"], "screenshot")

    def test_env_override_default_category(self):
        env_val = r"C:\media"
        with patch.dict(os.environ, {"MEDIA_SYNC_FOLDERS": env_val}):
            scanner = LocalFolderScanner()
            self.assertEqual(scanner.folders[0]["category"], "screenshot")

    def test_explicit_folders_override(self):
        custom = [{"path": "/tmp/custom", "category": "photo"}]
        scanner = LocalFolderScanner(folders=custom)
        self.assertEqual(scanner.folders, custom)


class TestExtensions(unittest.TestCase):
    """File extension sets are correct."""

    def test_image_extensions(self):
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic"]:
            self.assertIn(ext, IMAGE_EXTENSIONS)

    def test_video_extensions(self):
        for ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            self.assertIn(ext, VIDEO_EXTENSIONS)

    def test_all_is_union(self):
        self.assertEqual(ALL_MEDIA_EXTENSIONS, IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)


class TestScan(unittest.TestCase):
    """Scanning local folders for new media files."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._folders = [{"path": self._tmpdir, "category": "screenshot"}]

    def _create_file(self, name: str, content: bytes = b"fake image data") -> Path:
        p = Path(self._tmpdir) / name
        p.write_bytes(content)
        return p

    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    def test_finds_new_images(self, mock_exists, mock_url):
        mock_url.return_value = "https://example.com/test.png"
        self._create_file("test.png")
        self._create_file("photo.jpg")

        scanner = LocalFolderScanner(folders=self._folders)
        results = scanner.scan()

        self.assertEqual(len(results), 2)
        names = {r["filename"] for r in results}
        self.assertEqual(names, {"test.png", "photo.jpg"})

    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    def test_ignores_non_media_files(self, mock_exists, mock_url):
        mock_url.return_value = "https://example.com/file"
        self._create_file("readme.txt")
        self._create_file("data.csv")
        self._create_file("good.png")

        scanner = LocalFolderScanner(folders=self._folders)
        results = scanner.scan()

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["filename"], "good.png")

    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=True)
    def test_skips_already_indexed(self, mock_exists, mock_url):
        mock_url.return_value = "https://example.com/already.png"
        self._create_file("already.png")

        scanner = LocalFolderScanner(folders=self._folders)
        results = scanner.scan()

        self.assertEqual(len(results), 0)

    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    def test_video_flagged(self, mock_exists, mock_url):
        mock_url.return_value = "https://example.com/clip.mp4"
        self._create_file("clip.mp4")

        scanner = LocalFolderScanner(folders=self._folders)
        results = scanner.scan()

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["is_video"])
        self.assertEqual(results[0]["mime_type"], "video/mp4")

    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    def test_category_from_folder_config(self, mock_exists, mock_url):
        mock_url.return_value = "https://example.com/file"
        self._create_file("shot.png")
        folders = [{"path": self._tmpdir, "category": "photo"}]

        scanner = LocalFolderScanner(folders=folders)
        results = scanner.scan()

        self.assertEqual(results[0]["category"], "photo")

    def test_missing_folder_skipped_gracefully(self):
        folders = [{"path": "/nonexistent/folder/12345", "category": "photo"}]
        scanner = LocalFolderScanner(folders=folders)
        results = scanner.scan()
        self.assertEqual(results, [])


class TestIngestNew(unittest.TestCase):
    """Full ingest pipeline with mocked uploads and vision."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._folders = [{"path": self._tmpdir, "category": "screenshot"}]

    def _create_file(self, name: str, content: bytes = b"fake image data") -> Path:
        p = Path(self._tmpdir) / name
        p.write_bytes(content)
        return p

    @patch("lib.media_library.local_scanner.LocalFolderScanner._upload_file")
    @patch("lib.media_library.vision.VisionAnalyzer.analyze_bytes")
    @patch("lib.media_library.catalog.MediaCatalog.add")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    def test_ingest_image_full_pipeline(
        self, mock_url, mock_exists, mock_add, mock_vision, mock_upload
    ):
        mock_url.return_value = "https://example.com/test.png"
        mock_upload.return_value = "https://supabase.co/storage/v1/object/public/social-media/library/screenshot/abc_test.png"
        mock_vision.return_value = {
            "description": "Code editor with Python",
            "tags": ["python", "vscode", "coding"],
            "themes": ["developer life"],
            "text_content": "def hello():",
            "mood": "technical",
            "pillar_affinity": {"developer life and vibe coding": 0.9},
            "platform_fit": {"twitter": 0.8, "linkedin": 0.7},
        }

        self._create_file("test.png")
        scanner = LocalFolderScanner(folders=self._folders)
        result = scanner.ingest_new()

        self.assertEqual(result["ingested"], 1)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(len(result["errors"]), 0)
        self.assertEqual(len(result["details"]), 1)
        self.assertEqual(result["details"][0]["category"], "screenshot")
        self.assertIn("Code editor", result["details"][0]["description"])

        mock_upload.assert_called_once()
        mock_vision.assert_called_once()
        mock_add.assert_called_once()

    @patch("lib.media_library.local_scanner.LocalFolderScanner._upload_file")
    @patch("lib.media_library.catalog.MediaCatalog.add")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    def test_ingest_video_skips_vision(
        self, mock_url, mock_exists, mock_add, mock_upload
    ):
        mock_url.return_value = "https://example.com/clip.mp4"
        mock_upload.return_value = "https://supabase.co/storage/v1/object/public/social-media/library/screenshot/abc_clip.mp4"

        self._create_file("clip.mp4")
        scanner = LocalFolderScanner(folders=self._folders)
        result = scanner.ingest_new()

        self.assertEqual(result["ingested"], 1)
        # Video gets placeholder metadata, not vision analysis
        detail = result["details"][0]
        self.assertIn("Video", detail["description"])

        # Verify catalog.add was called with video platform_fit
        call_kwargs = mock_add.call_args
        vision_data = call_kwargs[1]["vision_data"] if "vision_data" in (call_kwargs[1] or {}) else call_kwargs[0][3]
        self.assertIn("tiktok", vision_data.get("platform_fit", {}))

    @patch("lib.media_library.local_scanner.LocalFolderScanner._upload_file")
    @patch("lib.media_library.vision.VisionAnalyzer.analyze_bytes")
    @patch("lib.media_library.catalog.MediaCatalog.add")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    def test_ingest_error_counted(
        self, mock_url, mock_exists, mock_add, mock_vision, mock_upload
    ):
        mock_url.return_value = "https://example.com/bad.png"
        mock_upload.side_effect = RuntimeError("Upload failed")

        self._create_file("bad.png")
        scanner = LocalFolderScanner(folders=self._folders)
        result = scanner.ingest_new()

        self.assertEqual(result["ingested"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("Upload failed", result["errors"][0])

    @patch("lib.media_library.local_scanner.LocalFolderScanner._upload_file")
    @patch("lib.media_library.vision.VisionAnalyzer.analyze_bytes")
    @patch("lib.media_library.catalog.MediaCatalog.add")
    @patch("lib.media_library.catalog.MediaCatalog.exists_by_url", return_value=False)
    @patch("lib.media_library.local_scanner.LocalFolderScanner._build_expected_url")
    def test_ingest_multiple_files(
        self, mock_url, mock_exists, mock_add, mock_vision, mock_upload
    ):
        mock_url.return_value = "https://example.com/file"
        mock_upload.return_value = "https://supabase.co/storage/v1/object/public/social-media/library/test.png"
        mock_vision.return_value = {
            "description": "Test",
            "tags": ["test"],
            "themes": [],
            "text_content": "",
            "mood": "technical",
            "pillar_affinity": {},
            "platform_fit": {},
        }

        self._create_file("a.png")
        self._create_file("b.jpg")
        self._create_file("c.jpeg")

        scanner = LocalFolderScanner(folders=self._folders)
        result = scanner.ingest_new()

        self.assertEqual(result["ingested"], 3)
        self.assertEqual(mock_add.call_count, 3)


class TestFolderStats(unittest.TestCase):
    """Folder stats reporting."""

    def test_stats_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.png").write_bytes(b"img")
            (Path(tmpdir) / "b.jpg").write_bytes(b"img")
            (Path(tmpdir) / "notes.txt").write_bytes(b"txt")

            scanner = LocalFolderScanner(
                folders=[{"path": tmpdir, "category": "photo"}]
            )
            stats = scanner.get_folder_stats()

            self.assertEqual(stats["total_folders"], 1)
            self.assertEqual(stats["total_files"], 2)  # txt excluded
            self.assertTrue(stats["folders"][0]["exists"])
            self.assertEqual(stats["folders"][0]["file_count"], 2)

    def test_stats_missing_folder(self):
        scanner = LocalFolderScanner(
            folders=[{"path": "/nonexistent/12345", "category": "photo"}]
        )
        stats = scanner.get_folder_stats()

        self.assertEqual(stats["total_files"], 0)
        self.assertFalse(stats["folders"][0]["exists"])


class TestFileHash(unittest.TestCase):
    """Content-based hashing for dedup."""

    def test_same_content_same_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = Path(tmpdir) / "a.png"
            p2 = Path(tmpdir) / "b.png"
            p1.write_bytes(b"identical content")
            p2.write_bytes(b"identical content")

            h1 = LocalFolderScanner._file_hash(p1)
            h2 = LocalFolderScanner._file_hash(p2)
            self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p1 = Path(tmpdir) / "a.png"
            p2 = Path(tmpdir) / "b.png"
            p1.write_bytes(b"content A")
            p2.write_bytes(b"content B")

            h1 = LocalFolderScanner._file_hash(p1)
            h2 = LocalFolderScanner._file_hash(p2)
            self.assertNotEqual(h1, h2)

    def test_hash_length(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "test.png"
            p.write_bytes(b"data")
            h = LocalFolderScanner._file_hash(p)
            self.assertEqual(len(h), 10)


class TestVideoMetadata(unittest.TestCase):
    """Placeholder metadata for video files."""

    def test_has_video_platform_fit(self):
        meta = LocalFolderScanner._video_metadata("clip.mp4", "video")
        self.assertGreater(meta["platform_fit"]["tiktok"], 0.8)
        self.assertGreater(meta["platform_fit"]["instagram"], 0.7)
        self.assertGreater(meta["platform_fit"]["youtube"], 0.8)

    def test_description_includes_filename(self):
        meta = LocalFolderScanner._video_metadata("my_clip.mov", "video")
        self.assertIn("my_clip.mov", meta["description"])

    def test_tags_include_video(self):
        meta = LocalFolderScanner._video_metadata("clip.mp4", "photo")
        self.assertIn("video", meta["tags"])


if __name__ == "__main__":
    unittest.main()
