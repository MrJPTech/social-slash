"""Tests for the MediaCatalog SQLite index."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from lib.media_library.catalog import MediaCatalog


class TestMediaCatalog(unittest.TestCase):
    """CRUD and search tests for MediaCatalog."""

    def setUp(self):
        """Use a temp DB for each test."""
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()
        # Patch DB_PATH at the module level
        import lib.media_library.catalog as mod

        self._orig_path = mod.DB_PATH
        mod.DB_PATH = self._tmpfile.name
        self.catalog = MediaCatalog()

    def tearDown(self):
        import lib.media_library.catalog as mod

        mod.DB_PATH = self._orig_path
        os.unlink(self._tmpfile.name)

    def _sample_vision(self, **overrides):
        data = {
            "description": "A screenshot of VS Code with Python code open",
            "tags": ["python", "vscode", "ide", "coding", "developer"],
            "themes": ["developer life", "building in public"],
            "text_content": "def hello():\n    print('world')",
            "mood": "technical",
            "pillar_affinity": {
                "developer life and vibe coding": 0.9,
                "building in public": 0.6,
                "AI tools and automation": 0.2,
            },
            "platform_fit": {
                "twitter": 0.8,
                "linkedin": 0.7,
                "instagram": 0.5,
                "reddit": 0.9,
            },
        }
        data.update(overrides)
        return data

    # ---- ADD + GET ----

    def test_add_and_get(self):
        vision = self._sample_vision()
        self.catalog.add("item-1", "screenshot.png", "https://example.com/img1.png", vision)

        item = self.catalog.get_item("item-1")
        self.assertIsNotNone(item)
        self.assertEqual(item["filename"], "screenshot.png")
        self.assertEqual(item["description"], vision["description"])
        self.assertEqual(item["tags"], vision["tags"])
        self.assertEqual(item["status"], "available")
        self.assertEqual(item["times_used"], 0)

    def test_get_nonexistent(self):
        self.assertIsNone(self.catalog.get_item("does-not-exist"))

    def test_add_duplicate_url_replaces(self):
        v1 = self._sample_vision(description="First version")
        v2 = self._sample_vision(description="Second version")
        self.catalog.add("item-1", "img.png", "https://example.com/img.png", v1)
        self.catalog.add("item-1", "img.png", "https://example.com/img.png", v2)

        item = self.catalog.get_item("item-1")
        self.assertEqual(item["description"], "Second version")

    # ---- EXISTS BY URL ----

    def test_exists_by_url_true(self):
        self.catalog.add("x", "f.png", "https://example.com/exists.png", self._sample_vision())
        self.assertTrue(self.catalog.exists_by_url("https://example.com/exists.png"))

    def test_exists_by_url_false(self):
        self.assertFalse(self.catalog.exists_by_url("https://example.com/nope.png"))

    # ---- GET AVAILABLE ----

    def test_get_available_sorted_by_usage(self):
        v = self._sample_vision()
        self.catalog.add("a", "a.png", "https://example.com/a.png", v)
        self.catalog.add("b", "b.png", "https://example.com/b.png", v)
        self.catalog.add("c", "c.png", "https://example.com/c.png", v)

        # Use 'b' twice, 'a' once
        self.catalog.mark_used("b")
        self.catalog.mark_used("b")
        self.catalog.mark_used("a")

        items = self.catalog.get_available(limit=10)
        ids = [i["id"] for i in items]
        # c (0 uses) should come first, then a (1), then b (2)
        self.assertEqual(ids[0], "c")
        self.assertEqual(ids[-1], "b")

    def test_get_available_excludes_archived(self):
        v = self._sample_vision()
        self.catalog.add("a", "a.png", "https://example.com/a.png", v)
        self.catalog.add("b", "b.png", "https://example.com/b.png", v)
        self.catalog.set_status("b", "archived")

        items = self.catalog.get_available()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "a")

    # ---- FIND BY PILLAR ----

    def test_find_by_pillar(self):
        v_dev = self._sample_vision(pillar_affinity={"developer life and vibe coding": 0.9})
        v_ai = self._sample_vision(pillar_affinity={"AI tools and automation": 0.8})
        self.catalog.add("dev1", "dev.png", "https://example.com/dev.png", v_dev)
        self.catalog.add("ai1", "ai.png", "https://example.com/ai.png", v_ai)

        results = self.catalog.find_by_pillar("developer life")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "dev1")

    # ---- FIND BY QUERY ----

    def test_find_by_query_tags(self):
        v = self._sample_vision(tags=["react", "nextjs", "frontend", "tailwind"])
        self.catalog.add("r1", "react.png", "https://example.com/react.png", v)

        results = self.catalog.find_by_query("react")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "r1")

    def test_find_by_query_description(self):
        v = self._sample_vision(description="Dashboard showing revenue metrics")
        self.catalog.add("d1", "dash.png", "https://example.com/dash.png", v)

        results = self.catalog.find_by_query("revenue")
        self.assertEqual(len(results), 1)

    def test_find_by_query_no_match(self):
        v = self._sample_vision()
        self.catalog.add("x", "x.png", "https://example.com/x.png", v)
        results = self.catalog.find_by_query("kubernetes")
        self.assertEqual(len(results), 0)

    # ---- MARK USED ----

    def test_mark_used_increments(self):
        v = self._sample_vision()
        self.catalog.add("u1", "u.png", "https://example.com/u.png", v)

        self.catalog.mark_used("u1", "twitter")
        self.catalog.mark_used("u1", "linkedin")

        item = self.catalog.get_item("u1")
        self.assertEqual(item["times_used"], 2)
        self.assertIsNotNone(item["last_used_at"])

    # ---- SET STATUS ----

    def test_set_status(self):
        v = self._sample_vision()
        self.catalog.add("s1", "s.png", "https://example.com/s.png", v)

        self.catalog.set_status("s1", "exhausted")
        item = self.catalog.get_item("s1")
        self.assertEqual(item["status"], "exhausted")

    # ---- STATS ----

    def test_get_stats(self):
        v = self._sample_vision()
        self.catalog.add("a", "a.png", "https://example.com/a.png", v, category="screenshot")
        self.catalog.add("b", "b.png", "https://example.com/b.png", v, category="photo")
        self.catalog.add("c", "c.png", "https://example.com/c.png", v, category="screenshot")
        self.catalog.mark_used("a")
        self.catalog.set_status("c", "archived")

        stats = self.catalog.get_stats()
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["available"], 2)
        self.assertEqual(stats["used_at_least_once"], 1)
        self.assertEqual(stats["categories"]["screenshot"], 2)
        self.assertEqual(stats["categories"]["photo"], 1)


if __name__ == "__main__":
    unittest.main()
