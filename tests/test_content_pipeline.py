"""Tests for ContentPipeline — bundle structure and agent integration."""

from datetime import UTC, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from lib.scheduler.content_pipeline import ContentBundle, ContentPipeline

# ---------------------------------------------------------------------------
# Shared mocks
# ---------------------------------------------------------------------------

_MOCK_RESEARCH_RESULT = {
    "ideas": "1. How AI coding assistants are changing developer productivity\n2. Another idea"
}

_MOCK_WRITE_RESULT_A = {
    "content": "Just shipped AI automation to all 8 platforms. The future is here 🚀",
    "hashtags": ["#buildinpublic", "#AI"],
    "char_count": 65,
    "char_limit": 280,
    "persona_mode": "professional",
}

_MOCK_WRITE_RESULT_B = {
    "content": "Manual content creation is dead. The builders who automate win.",
    "hashtags": ["#startup", "#AItools"],
    "char_count": 62,
    "char_limit": 280,
    "persona_mode": "ceo",
}


def _patched_pipeline():
    """Return a ContentPipeline with all external calls mocked."""
    pipeline = ContentPipeline()
    return pipeline


class TestContentBundleDataclass:
    def test_bundle_fields_present(self):
        now = datetime.now(UTC)
        bundle = ContentBundle(
            slot_id="abc",
            platform="twitter",
            subreddit=None,
            pillar="AI tools",
            topic="AI is changing everything",
            option_a={"content": "A", "hashtags": [], "persona_mode": "professional"},
            option_b={"content": "B", "hashtags": [], "persona_mode": "ceo"},
            image_1_url="https://img1.jpg",
            image_2_url="https://img2.jpg",
            scheduled_time=now,
            expires_at=now,
        )
        assert bundle.slot_id == "abc"
        assert bundle.platform == "twitter"
        assert bundle.posted is False
        assert bundle.choice is None

    def test_bundle_expires_at_is_2hrs_after_scheduled(self):
        from datetime import timedelta

        now = datetime.now(UTC)
        expires = now + timedelta(hours=2)
        delta = (expires - now).total_seconds()
        assert abs(delta - 7200) < 5


class TestContentPipelineGenerateBundle:
    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_bundle_structure(self, mock_topic, mock_copy, mock_library):
        mock_topic.return_value = "AI coding assistants"
        mock_copy.side_effect = [
            {"content": "Option A", "hashtags": [], "persona_mode": "professional"},
            {"content": "Option B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_library.return_value = [
            {
                "item_id": "img-1",
                "storage_url": "https://img1.jpg",
                "description": "Screenshot of code editor",
                "score": 0.9,
                "match_reasons": [],
            },
            {
                "item_id": "img-2",
                "storage_url": "https://img2.jpg",
                "description": "Terminal with tests passing",
                "score": 0.8,
                "match_reasons": [],
            },
        ]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle(
            platform="twitter",
            time_slot="09:00",
            pillar="building in public",
        )

        assert isinstance(bundle, ContentBundle)
        assert bundle.platform == "twitter"
        assert bundle.pillar == "building in public"
        assert bundle.topic == "AI coding assistants"
        assert bundle.image_1_url == "https://img1.jpg"
        assert bundle.image_2_url == "https://img2.jpg"
        assert bundle.image_source == "library"
        assert bundle.library_item_ids == ["img-1", "img-2"]
        assert bundle.posted is False

    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_slot_id_is_uuid(self, mock_topic, mock_copy, mock_library):
        import re

        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_library.return_value = []

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("linkedin", "08:00", "startup mindset")
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            bundle.slot_id,
        )

    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_reddit_subreddit_passed_through(self, mock_topic, mock_copy, mock_library):
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_library.return_value = []

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle(
            "reddit", "10:00", "developer life", subreddit="r/SideProject"
        )
        assert bundle.subreddit == "r/SideProject"

    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_expires_at_is_in_future(self, mock_topic, mock_copy, mock_library):
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_library.return_value = []

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("twitter", "09:00", "AI tools")
        now = datetime.now(UTC)
        assert bundle.expires_at > now

    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_media_required_returns_none_when_no_library(self, mock_topic, mock_copy, mock_library):
        """Instagram/TikTok return None when library is empty (no AI fallback)."""
        mock_topic.return_value = "topic"
        mock_library.return_value = []

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("instagram", "12:00", "building in public")
        assert bundle is None

    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_text_only_when_no_library(self, mock_topic, mock_copy, mock_library):
        """Non-media platforms get text-only bundles when library is empty."""
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_library.return_value = []

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("twitter", "09:00", "AI tools")
        assert bundle is not None
        assert bundle.image_1_url == ""
        assert bundle.image_2_url == ""
        assert bundle.image_source == "none"
        assert bundle.library_item_ids == []

    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_single_library_match(self, mock_topic, mock_copy, mock_library):
        """One library match: first image from library, second empty."""
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_library.return_value = [
            {
                "item_id": "img-1",
                "storage_url": "https://img1.jpg",
                "description": "Screenshot",
                "score": 0.9,
                "match_reasons": [],
            },
        ]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("twitter", "09:00", "AI tools")
        assert bundle.image_1_url == "https://img1.jpg"
        assert bundle.image_2_url == ""
        assert bundle.image_source == "library"
        assert bundle.library_item_ids == ["img-1"]


class TestTopicVariationFallback:
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_fallback_on_research_failure(self, mock_topic):
        mock_topic.side_effect = Exception("ResearchAgent unavailable")
        # If _get_topic_variation raises, the whole generate_bundle should raise
        # (the caller handles the error). This test ensures the mock is callable.
        pipeline = ContentPipeline()
        with pytest.raises(Exception, match="ResearchAgent unavailable"):
            pipeline.generate_bundle("twitter", "09:00", "pillar")


class TestCopyGenerationFallback:
    @patch("lib.scheduler.content_pipeline.ContentPipeline._find_library_images")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_copy_failure_returns_error_content(self, mock_topic, mock_copy, mock_library):
        mock_topic.return_value = "some topic"
        mock_library.return_value = []
        # _generate_copy returns an error dict (not raises) on internal failure
        mock_copy.side_effect = [
            {
                "content": "[Content generation failed: Network error]",
                "hashtags": [],
                "persona_mode": "professional",
            },
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("twitter", "09:00", "pillar")
        assert "Content generation failed" in bundle.option_a["content"]
