"""Tests for the MediaMatcher scoring algorithm."""

from __future__ import annotations

import os
import tempfile
import unittest

from lib.media_library.catalog import MediaCatalog
from lib.media_library.matcher import PERSONA_MOODS, MediaMatcher


class TestMediaMatcher(unittest.TestCase):
    """Scoring and matching tests for MediaMatcher."""

    def setUp(self):
        self._tmpfile = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmpfile.close()
        import lib.media_library.catalog as mod

        self._orig_path = mod.DB_PATH
        mod.DB_PATH = self._tmpfile.name
        self.catalog = MediaCatalog()
        self.matcher = MediaMatcher()

    def tearDown(self):
        import lib.media_library.catalog as mod

        mod.DB_PATH = self._orig_path
        os.unlink(self._tmpfile.name)

    def _add_item(self, item_id, **vision_overrides):
        """Helper to add a test item to the catalog."""
        vision = {
            "description": "Test image",
            "tags": ["python", "coding", "developer"],
            "themes": ["developer life"],
            "text_content": "",
            "mood": "technical",
            "pillar_affinity": {"developer life and vibe coding": 0.8},
            "platform_fit": {"twitter": 0.7, "linkedin": 0.6, "instagram": 0.5},
        }
        vision.update(vision_overrides)
        self.catalog.add(item_id, f"{item_id}.png", f"https://example.com/{item_id}.png", vision)

    # ---- BASIC MATCHING ----

    def test_find_best_returns_items(self):
        self._add_item("a")
        self._add_item("b")
        results = self.matcher.find_best(
            "python coding", "developer life and vibe coding", "twitter"
        )
        self.assertGreater(len(results), 0)
        self.assertIn("score", results[0])
        self.assertIn("storage_url", results[0])

    def test_find_best_empty_catalog(self):
        results = self.matcher.find_best("test", "AI tools", "twitter")
        self.assertEqual(results, [])

    def test_find_best_respects_count(self):
        for i in range(5):
            self._add_item(f"item-{i}")
        results = self.matcher.find_best("code", "developer life", "twitter", count=3)
        self.assertEqual(len(results), 3)

    def test_find_best_excludes_ids(self):
        self._add_item("keep")
        self._add_item("exclude")
        results = self.matcher.find_best(
            "code", "developer life", "twitter", count=5, exclude_ids=["exclude"]
        )
        ids = [r["item_id"] for r in results]
        self.assertNotIn("exclude", ids)

    # ---- PILLAR SCORING ----

    def test_pillar_affinity_boosts_score(self):
        self._add_item("high", pillar_affinity={"AI tools and automation": 0.95})
        self._add_item("low", pillar_affinity={"AI tools and automation": 0.1})

        results = self.matcher.find_best("AI tools", "AI tools and automation", "twitter", count=2)
        self.assertEqual(results[0]["item_id"], "high")
        self.assertGreater(results[0]["score"], results[1]["score"])

    # ---- TAG OVERLAP ----

    def test_tag_overlap_scoring(self):
        self._add_item("match", tags=["react", "nextjs", "frontend", "typescript"])
        self._add_item("nomatch", tags=["python", "backend", "django", "api"])

        results = self.matcher.find_best(
            "react nextjs frontend", "developer life", "twitter", count=2
        )
        # The item with matching tags should rank higher
        self.assertEqual(results[0]["item_id"], "match")

    # ---- PLATFORM FIT ----

    def test_platform_fit_scoring(self):
        self._add_item("insta_good", platform_fit={"instagram": 0.95, "twitter": 0.3})
        self._add_item("insta_bad", platform_fit={"instagram": 0.1, "twitter": 0.9})

        results = self.matcher.find_best("photo", "building in public", "instagram", count=2)
        self.assertEqual(results[0]["item_id"], "insta_good")

    # ---- FRESHNESS ----

    def test_freshness_prefers_unused(self):
        self._add_item("fresh")
        self._add_item("stale")
        # Use stale 5 times
        for _ in range(5):
            self.catalog.mark_used("stale")

        results = self.matcher.find_best("code", "developer life", "twitter", count=2)
        self.assertEqual(results[0]["item_id"], "fresh")

    # ---- MOOD MATCH ----

    def test_mood_match_persona_professional(self):
        self._add_item("pro", mood="professional")
        self._add_item("cas", mood="casual")

        results = self.matcher.find_best(
            "business", "startup mindset", "linkedin", count=2, persona="professional"
        )
        # Professional mood should score higher for professional persona
        pro_score = next(r["score"] for r in results if r["item_id"] == "pro")
        cas_score = next(r["score"] for r in results if r["item_id"] == "cas")
        self.assertGreater(pro_score, cas_score)

    def test_mood_match_persona_personal(self):
        self._add_item("vib", mood="vibrant")
        self._add_item("drk", mood="dark")

        results = self.matcher.find_best(
            "lifestyle", "building in public", "instagram", count=2, persona="personal"
        )
        vib_score = next(r["score"] for r in results if r["item_id"] == "vib")
        drk_score = next(r["score"] for r in results if r["item_id"] == "drk")
        self.assertGreater(vib_score, drk_score)

    # ---- KEYWORD EXTRACTION ----

    def test_extract_keywords_filters_stop_words(self):
        keywords = MediaMatcher._extract_keywords("How to build the best AI tools for developers")
        self.assertIn("build", keywords)
        self.assertIn("best", keywords)
        self.assertIn("tools", keywords)
        self.assertIn("developers", keywords)
        self.assertNotIn("how", keywords)
        self.assertNotIn("the", keywords)
        self.assertNotIn("to", keywords)

    def test_extract_keywords_strips_punctuation(self):
        keywords = MediaMatcher._extract_keywords("Python, React, and TypeScript!")
        self.assertIn("python", keywords)
        self.assertIn("react", keywords)
        self.assertIn("typescript", keywords)

    # ---- MATCH REASONS ----

    def test_match_reasons_populated(self):
        self._add_item(
            "rich",
            pillar_affinity={"AI tools and automation": 0.9},
            tags=["automation", "tools", "productivity"],
            platform_fit={"twitter": 0.8},
            mood="professional",
        )
        results = self.matcher.find_best(
            "AI automation tools",
            "AI tools and automation",
            "twitter",
            count=1,
            persona="professional",
        )
        self.assertGreater(len(results), 0)
        reasons = results[0]["match_reasons"]
        self.assertIsInstance(reasons, list)
        # Should have at least pillar match and mood
        self.assertTrue(any("pillar" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
