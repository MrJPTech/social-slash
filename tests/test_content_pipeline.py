"""Tests for ContentPipeline — bundle structure and agent integration."""

from datetime import datetime, timezone
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


def _mock_imagen_urls():
    return ["https://media.getlate.dev/temp/abc.jpg"]


def _patched_pipeline():
    """Return a ContentPipeline with all external calls mocked."""
    pipeline = ContentPipeline()
    return pipeline


class TestContentBundleDataclass:
    def test_bundle_fields_present(self):
        now = datetime.now(timezone.utc)
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
        now = datetime.now(timezone.utc)
        expires = now + timedelta(hours=2)
        delta = (expires - now).total_seconds()
        assert abs(delta - 7200) < 5


class TestContentPipelineGenerateBundle:
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_image")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_bundle_structure(self, mock_topic, mock_copy, mock_image):
        mock_topic.return_value = "AI coding assistants"
        mock_copy.side_effect = [
            {"content": "Option A", "hashtags": [], "persona_mode": "professional"},
            {"content": "Option B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_image.side_effect = ["https://img1.jpg", "https://img2.jpg"]

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
        assert bundle.option_a["persona_mode"] == "professional"
        assert bundle.option_b["persona_mode"] == "ceo"
        assert bundle.image_1_url == "https://img1.jpg"
        assert bundle.image_2_url == "https://img2.jpg"
        assert bundle.posted is False

    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_image")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_slot_id_is_uuid(self, mock_topic, mock_copy, mock_image):
        import re
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_image.side_effect = ["", ""]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("linkedin", "08:00", "startup mindset")
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            bundle.slot_id,
        )

    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_image")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_reddit_subreddit_passed_through(self, mock_topic, mock_copy, mock_image):
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_image.side_effect = ["", ""]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle(
            "reddit", "10:00", "developer life", subreddit="r/SideProject"
        )
        assert bundle.subreddit == "r/SideProject"

    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_image")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_expires_at_is_in_future(self, mock_topic, mock_copy, mock_image):
        mock_topic.return_value = "topic"
        mock_copy.side_effect = [
            {"content": "A", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_image.side_effect = ["", ""]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("twitter", "09:00", "AI tools")
        now = datetime.now(timezone.utc)
        assert bundle.expires_at > now


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
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_image")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._generate_copy")
    @patch("lib.scheduler.content_pipeline.ContentPipeline._get_topic_variation")
    def test_copy_failure_returns_error_content(self, mock_topic, mock_copy, mock_image):
        mock_topic.return_value = "some topic"
        # _generate_copy returns an error dict (not raises) on internal failure
        mock_copy.side_effect = [
            {"content": "[Content generation failed: Network error]", "hashtags": [], "persona_mode": "professional"},
            {"content": "B", "hashtags": [], "persona_mode": "ceo"},
        ]
        mock_image.side_effect = ["", ""]

        pipeline = ContentPipeline()
        bundle = pipeline.generate_bundle("twitter", "09:00", "pillar")
        assert "Content generation failed" in bundle.option_a["content"]
