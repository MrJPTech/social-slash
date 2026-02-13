#!/usr/bin/env python3
"""Tests for ImageAgent - AI image generation agent."""

import os
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ─────────────────────────────────────────────────────────────────────
# INIT TESTS
# ─────────────────────────────────────────────────────────────────────


class TestImageAgentInit:
    """Test ImageAgent initialization."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_init_default_config(self, mock_persona, mock_db):
        """Agent initializes with default config."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional", "default_platform": "instagram"}
        agent = ImageAgent(config)

        assert agent.name == "ImageAgent"
        assert agent.default_platform == "instagram"
        assert agent.ai_provider == "gemini"

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_init_custom_platform(self, mock_persona, mock_db):
        """Agent accepts custom default platform."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "ceo", "default_platform": "linkedin"}
        agent = ImageAgent(config)

        assert agent.default_platform == "linkedin"

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_init_lazy_imagen_client(self, mock_persona, mock_db):
        """ImagenClient is not created until first use."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        assert agent._imagen_client is None

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_inherits_base_agent(self, mock_persona, mock_db):
        """ImageAgent inherits from BaseAgent."""
        from lib.agents.image_agent import ImageAgent
        from lib.agents.base_agent import BaseAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        assert isinstance(agent, BaseAgent)


# ─────────────────────────────────────────────────────────────────────
# PROMPT ENHANCEMENT TESTS
# ─────────────────────────────────────────────────────────────────────


class TestPromptEnhancement:
    """Test enhance_prompt() method."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_enhance_prompt_calls_generator(self, mock_persona, mock_db):
        """enhance_prompt() calls response_generator._generate()."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        # Mock the response generator
        mock_gen = MagicMock()
        mock_gen._generate.return_value = "Enhanced professional image prompt"
        agent._response_generator = mock_gen

        result = agent.enhance_prompt(
            "A tech startup office", "linkedin", "modern", "professional"
        )

        assert result == "Enhanced professional image prompt"
        mock_gen._generate.assert_called_once()

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_enhance_prompt_includes_persona_style(self, mock_persona, mock_db):
        """enhance_prompt() includes persona-specific style hints."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "ceo"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced"
        agent._response_generator = mock_gen

        agent.enhance_prompt("test", persona_mode="ceo")

        # Check that the prompt sent to generator includes CEO style hints
        call_args = mock_gen._generate.call_args[0][0]
        assert "authoritative" in call_args or "executive" in call_args

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_enhance_prompt_fallback_on_error(self, mock_persona, mock_db):
        """enhance_prompt() returns raw prompt when generator fails."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.side_effect = Exception("API error")
        agent._response_generator = mock_gen

        result = agent.enhance_prompt("raw prompt text")
        assert result == "raw prompt text"


# ─────────────────────────────────────────────────────────────────────
# PERSONA STYLE MAP TESTS
# ─────────────────────────────────────────────────────────────────────


class TestPersonaStyleMap:
    """Test PERSONA_STYLE_MAP constant."""

    def test_all_persona_modes_have_styles(self):
        """All three persona modes have style definitions."""
        from lib.agents.image_agent import PERSONA_STYLE_MAP

        assert "professional" in PERSONA_STYLE_MAP
        assert "personal" in PERSONA_STYLE_MAP
        assert "ceo" in PERSONA_STYLE_MAP

    def test_styles_are_nonempty_strings(self):
        """Style values are non-empty strings."""
        from lib.agents.image_agent import PERSONA_STYLE_MAP

        for mode, style in PERSONA_STYLE_MAP.items():
            assert isinstance(style, str)
            assert len(style) > 10, f"{mode} style is too short"


# ─────────────────────────────────────────────────────────────────────
# GENERATION METHOD TESTS (mocked ImagenClient)
# ─────────────────────────────────────────────────────────────────────


class TestGeneratePostGraphic:
    """Test generate_post_graphic()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_returns_expected_keys(self, mock_persona, mock_db):
        """generate_post_graphic() returns dict with expected keys."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        # Mock response generator and imagen client
        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced prompt"
        agent._response_generator = mock_gen

        mock_imagen = MagicMock()
        mock_imagen.generate_for_platform.return_value = [{
            "local_path": "/tmp/test.png",
            "aspect_ratio": "1:1",
        }]
        mock_imagen.get_preset.return_value = "1:1"
        agent._imagen_client = mock_imagen

        result = agent.generate_post_graphic(
            topic="Tech workspace",
            platform="instagram",
        )

        assert "prompt_used" in result
        assert "platform" in result
        assert "aspect_ratio" in result
        assert result["platform"] == "instagram"
        assert result["uploaded"] is False


class TestGenerateThumbnail:
    """Test generate_thumbnail()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_returns_16_9_ratio(self, mock_persona, mock_db):
        """generate_thumbnail() always returns 16:9 aspect ratio."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced"
        agent._response_generator = mock_gen

        mock_imagen = MagicMock()
        mock_imagen.generate_for_platform.return_value = [{
            "local_path": "/tmp/thumb.png",
            "aspect_ratio": "16:9",
        }]
        agent._imagen_client = mock_imagen

        result = agent.generate_thumbnail(title="My Video Title")
        assert result["aspect_ratio"] == "16:9"


class TestGenerateCarouselImages:
    """Test generate_carousel_images()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_generates_one_per_slide(self, mock_persona, mock_db):
        """generate_carousel_images() generates one image per slide."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced"
        agent._response_generator = mock_gen

        mock_imagen = MagicMock()
        mock_imagen.generate_for_platform.return_value = [{
            "local_path": "/tmp/slide.png",
            "aspect_ratio": "1:1",
        }]
        agent._imagen_client = mock_imagen

        result = agent.generate_carousel_images(
            slides=["Intro", "Feature 1", "CTA"],
            platform="instagram",
        )

        assert result["slide_count"] == 3
        assert len(result["slide_images"]) == 3
        assert result["slide_images"][0]["slide"] == 1
        assert result["slide_images"][2]["slide"] == 3


class TestGenerateStoryImage:
    """Test generate_story_image()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_returns_9_16_ratio(self, mock_persona, mock_db):
        """generate_story_image() returns 9:16 aspect ratio."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "personal"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced"
        agent._response_generator = mock_gen

        mock_imagen = MagicMock()
        mock_imagen.generate_for_platform.return_value = [{
            "local_path": "/tmp/story.png",
            "aspect_ratio": "9:16",
        }]
        agent._imagen_client = mock_imagen

        result = agent.generate_story_image(context="Behind the scenes")
        assert result["aspect_ratio"] == "9:16"


class TestGenerateTextOverlay:
    """Test generate_text_overlay()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_includes_overlay_text(self, mock_persona, mock_db):
        """generate_text_overlay() includes the overlay text in result."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced"
        agent._response_generator = mock_gen

        mock_imagen = MagicMock()
        mock_imagen.generate_for_platform.return_value = [{
            "local_path": "/tmp/overlay.png",
            "aspect_ratio": "1:1",
        }]
        agent._imagen_client = mock_imagen

        result = agent.generate_text_overlay(
            text="Innovation starts here",
            background_style="gradient",
        )
        assert result["overlay_text"] == "Innovation starts here"


class TestGenerateAiArt:
    """Test generate_ai_art()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_uses_custom_aspect_ratio(self, mock_persona, mock_db):
        """generate_ai_art() uses the user-specified aspect ratio."""
        from lib.agents.image_agent import ImageAgent

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        mock_gen = MagicMock()
        mock_gen._generate.return_value = "enhanced"
        agent._response_generator = mock_gen

        mock_imagen = MagicMock()
        mock_imagen.generate_image.return_value = [{
            "local_path": "/tmp/art.png",
            "image_bytes": b"bytes",
        }]
        agent._imagen_client = mock_imagen

        result = agent.generate_ai_art(
            description="Abstract fractal art",
            aspect_ratio="16:9",
        )
        assert result["aspect_ratio"] == "16:9"

        # Verify aspect_ratio passed to generate_image
        mock_imagen.generate_image.assert_called_once()
        call_kwargs = mock_imagen.generate_image.call_args
        assert call_kwargs.kwargs["aspect_ratio"] == "16:9"


class TestListPresets:
    """Test list_presets()."""

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_returns_all_presets(self, mock_persona, mock_db):
        """list_presets() returns all platform presets."""
        from lib.agents.image_agent import ImageAgent
        from lib.ai.imagen_client import ImagenClient

        config = {"persona_mode": "professional"}
        agent = ImageAgent(config)

        presets = agent.list_presets()
        assert isinstance(presets, dict)
        assert len(presets) == len(ImagenClient.PLATFORM_PRESETS)


# ─────────────────────────────────────────────────────────────────────
# CLI TESTS
# ─────────────────────────────────────────────────────────────────────


class TestCLI:
    """Test CLI main() entry point."""

    def test_main_function_exists(self):
        """main() function is importable."""
        from lib.agents.image_agent import main
        assert callable(main)

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_status_action(self, mock_persona, mock_db, capsys):
        """CLI status action prints stats."""
        import sys
        from lib.agents.image_agent import main

        with patch.object(sys, 'argv', ['image_agent', '--action', 'status']):
            main()

        captured = capsys.readouterr()
        assert "Image Agent Status" in captured.out

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_presets_action(self, mock_persona, mock_db, capsys):
        """CLI presets action prints platform presets."""
        import sys
        from lib.agents.image_agent import main

        with patch.object(sys, 'argv', ['image_agent', '--action', 'presets']):
            main()

        captured = capsys.readouterr()
        assert "platform presets" in captured.out.lower()
        assert "instagram_post" in captured.out

    @patch("lib.agents.image_agent.EngagementDatabase")
    @patch("lib.agents.image_agent.SwizzPersona")
    def test_graphic_requires_prompt(self, mock_persona, mock_db, capsys):
        """CLI graphic action requires --prompt."""
        import sys
        from lib.agents.image_agent import main

        with patch.object(sys, 'argv', ['image_agent', '--action', 'graphic']):
            main()

        captured = capsys.readouterr()
        assert "ERROR" in captured.out
