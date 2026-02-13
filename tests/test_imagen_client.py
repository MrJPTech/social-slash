#!/usr/bin/env python3
"""Tests for ImagenClient - Google Imagen 3 image generation."""

import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ─────────────────────────────────────────────────────────────────────
# INIT & CONFIG TESTS
# ─────────────────────────────────────────────────────────────────────


class TestImagenClientInit:
    """Test ImagenClient initialization."""

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key-123"})
    @patch("lib.ai.imagen_client.genai")
    def test_init_with_env_key(self, mock_genai):
        """Init uses GOOGLE_API_KEY env var."""
        from lib.ai.imagen_client import ImagenClient
        client = ImagenClient()
        assert client.api_key == "test-key-123"
        mock_genai.Client.assert_called_once_with(api_key="test-key-123")

    @patch("lib.ai.imagen_client.genai")
    def test_init_with_explicit_key(self, mock_genai):
        """Init accepts explicit api_key parameter."""
        from lib.ai.imagen_client import ImagenClient
        client = ImagenClient(api_key="explicit-key")
        assert client.api_key == "explicit-key"
        mock_genai.Client.assert_called_once_with(api_key="explicit-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_init_raises_without_key(self):
        """Init raises ValueError when no API key available."""
        # Remove GOOGLE_API_KEY if set
        os.environ.pop("GOOGLE_API_KEY", None)
        from lib.ai.imagen_client import ImagenClient
        with pytest.raises(ValueError, match="Google API key not found"):
            ImagenClient()

    def test_model_constant(self):
        """MODEL constant is set correctly."""
        from lib.ai.imagen_client import ImagenClient
        assert ImagenClient.MODEL == "imagen-3.0-generate-002"


# ─────────────────────────────────────────────────────────────────────
# PLATFORM PRESET TESTS
# ─────────────────────────────────────────────────────────────────────


class TestPlatformPresets:
    """Test PLATFORM_PRESETS dict and get_preset()."""

    def test_presets_has_all_major_platforms(self):
        """Presets cover all major social platforms."""
        from lib.ai.imagen_client import ImagenClient
        preset_keys = set(ImagenClient.PLATFORM_PRESETS.keys())

        expected_platforms = [
            "instagram", "twitter", "linkedin", "youtube",
            "tiktok", "facebook", "pinterest", "threads",
            "reddit", "googlebusiness",
        ]
        for platform in expected_platforms:
            matching = [k for k in preset_keys if k.startswith(platform)]
            assert len(matching) > 0, f"No preset for {platform}"

    def test_presets_values_are_valid_ratios(self):
        """All preset values are valid aspect ratio strings."""
        from lib.ai.imagen_client import ImagenClient
        valid_ratios = {"1:1", "16:9", "9:16", "4:3", "3:4"}
        for key, ratio in ImagenClient.PLATFORM_PRESETS.items():
            assert ratio in valid_ratios, f"{key} has invalid ratio {ratio}"

    def test_get_preset_returns_ratio(self):
        """get_preset() returns correct aspect ratio for known platform."""
        from lib.ai.imagen_client import ImagenClient
        assert ImagenClient.get_preset("instagram", "post") == "1:1"
        assert ImagenClient.get_preset("instagram", "story") == "9:16"
        assert ImagenClient.get_preset("twitter", "post") == "16:9"
        assert ImagenClient.get_preset("linkedin", "post") == "4:3"
        assert ImagenClient.get_preset("youtube", "thumbnail") == "16:9"
        assert ImagenClient.get_preset("pinterest", "pin") == "3:4"

    def test_get_preset_case_insensitive(self):
        """get_preset() is case-insensitive."""
        from lib.ai.imagen_client import ImagenClient
        assert ImagenClient.get_preset("Instagram", "Post") == "1:1"
        assert ImagenClient.get_preset("TWITTER", "POST") == "16:9"

    def test_get_preset_returns_none_for_unknown(self):
        """get_preset() returns None for unknown platform/type combo."""
        from lib.ai.imagen_client import ImagenClient
        assert ImagenClient.get_preset("myspace", "post") is None
        assert ImagenClient.get_preset("instagram", "banner") is None


# ─────────────────────────────────────────────────────────────────────
# GENERATE IMAGE TESTS (mocked SDK)
# ─────────────────────────────────────────────────────────────────────


class TestGenerateImage:
    """Test generate_image() with mocked SDK calls."""

    @patch("lib.ai.imagen_client.genai")
    @patch("lib.ai.imagen_client.types")
    def test_generate_image_calls_sdk(self, mock_types, mock_genai):
        """generate_image() calls client.models.generate_images correctly."""
        from lib.ai.imagen_client import ImagenClient

        # Mock the response
        mock_img = MagicMock()
        mock_img.image.image_bytes = b"fake-png-bytes"
        mock_response = MagicMock()
        mock_response.generated_images = [mock_img]
        mock_genai.Client.return_value.models.generate_images.return_value = mock_response

        client = ImagenClient(api_key="test-key")
        results = client.generate_image("test prompt", aspect_ratio="1:1", num_images=1)

        assert len(results) == 1
        assert results[0]["image_bytes"] == b"fake-png-bytes"
        assert os.path.exists(results[0]["local_path"])

        # Cleanup temp file
        os.unlink(results[0]["local_path"])

    @patch("lib.ai.imagen_client.genai")
    @patch("lib.ai.imagen_client.types")
    def test_generate_image_multiple(self, mock_types, mock_genai):
        """generate_image() handles multiple images."""
        from lib.ai.imagen_client import ImagenClient

        mock_imgs = [MagicMock() for _ in range(3)]
        for m in mock_imgs:
            m.image.image_bytes = b"fake-bytes"
        mock_response = MagicMock()
        mock_response.generated_images = mock_imgs
        mock_genai.Client.return_value.models.generate_images.return_value = mock_response

        client = ImagenClient(api_key="test-key")
        results = client.generate_image("test", num_images=3)

        assert len(results) == 3

        # Cleanup
        for r in results:
            os.unlink(r["local_path"])

    @patch("lib.ai.imagen_client.genai")
    @patch("lib.ai.imagen_client.types")
    def test_generate_image_clamps_num_images(self, mock_types, mock_genai):
        """generate_image() clamps num_images to 1-4 range."""
        from lib.ai.imagen_client import ImagenClient

        mock_response = MagicMock()
        mock_response.generated_images = []
        mock_genai.Client.return_value.models.generate_images.return_value = mock_response

        client = ImagenClient(api_key="test-key")
        client.generate_image("test", num_images=10)

        # Check the config passed to SDK
        call_kwargs = mock_genai.Client.return_value.models.generate_images.call_args
        config = call_kwargs.kwargs.get("config") or call_kwargs[1].get("config")
        mock_types.GenerateImagesConfig.assert_called_once()
        # Verify num_images was clamped to 4
        config_kwargs = mock_types.GenerateImagesConfig.call_args
        assert config_kwargs.kwargs["number_of_images"] == 4

    @patch("lib.ai.imagen_client.genai")
    def test_generate_image_raises_on_sdk_error(self, mock_genai):
        """generate_image() raises when SDK call fails."""
        from lib.ai.imagen_client import ImagenClient

        mock_genai.Client.return_value.models.generate_images.side_effect = Exception("API error")

        client = ImagenClient(api_key="test-key")
        with pytest.raises(Exception, match="API error"):
            client.generate_image("test")


# ─────────────────────────────────────────────────────────────────────
# GENERATE FOR PLATFORM TESTS
# ─────────────────────────────────────────────────────────────────────


class TestGenerateForPlatform:
    """Test generate_for_platform() preset resolution."""

    @patch("lib.ai.imagen_client.genai")
    @patch("lib.ai.imagen_client.types")
    def test_resolves_platform_preset(self, mock_types, mock_genai):
        """generate_for_platform() resolves platform to correct aspect ratio."""
        from lib.ai.imagen_client import ImagenClient

        mock_response = MagicMock()
        mock_img = MagicMock()
        mock_img.image.image_bytes = b"bytes"
        mock_response.generated_images = [mock_img]
        mock_genai.Client.return_value.models.generate_images.return_value = mock_response

        client = ImagenClient(api_key="test-key")
        results = client.generate_for_platform("test", platform="instagram", image_type="story")

        assert len(results) == 1
        assert results[0]["aspect_ratio"] == "9:16"
        assert results[0]["platform"] == "instagram"
        assert results[0]["image_type"] == "story"

        os.unlink(results[0]["local_path"])

    @patch("lib.ai.imagen_client.genai")
    @patch("lib.ai.imagen_client.types")
    def test_defaults_to_square_for_unknown(self, mock_types, mock_genai):
        """generate_for_platform() defaults to 1:1 for unknown platform."""
        from lib.ai.imagen_client import ImagenClient

        mock_response = MagicMock()
        mock_response.generated_images = []
        mock_genai.Client.return_value.models.generate_images.return_value = mock_response

        client = ImagenClient(api_key="test-key")
        client.generate_for_platform("test", platform="myspace", image_type="post")

        # Check that 1:1 was used as fallback
        config_call = mock_types.GenerateImagesConfig.call_args
        assert config_call.kwargs["aspect_ratio"] == "1:1"


# ─────────────────────────────────────────────────────────────────────
# TEMP FILE TESTS
# ─────────────────────────────────────────────────────────────────────


class TestSaveToTemp:
    """Test _save_to_temp() creates valid files."""

    @patch("lib.ai.imagen_client.genai")
    def test_save_creates_png_file(self, mock_genai):
        """_save_to_temp() creates a .png file with correct content."""
        from lib.ai.imagen_client import ImagenClient

        client = ImagenClient(api_key="test-key")
        test_bytes = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"

        path = client._save_to_temp(test_bytes)

        assert path.endswith(".png")
        assert os.path.exists(path)

        with open(path, "rb") as f:
            assert f.read() == test_bytes

        os.unlink(path)

    @patch("lib.ai.imagen_client.genai")
    def test_save_creates_unique_files(self, mock_genai):
        """_save_to_temp() creates unique files for each call."""
        from lib.ai.imagen_client import ImagenClient

        client = ImagenClient(api_key="test-key")
        path1 = client._save_to_temp(b"image1")
        path2 = client._save_to_temp(b"image2")

        assert path1 != path2
        assert os.path.exists(path1)
        assert os.path.exists(path2)

        os.unlink(path1)
        os.unlink(path2)


# ─────────────────────────────────────────────────────────────────────
# UPLOAD TESTS
# ─────────────────────────────────────────────────────────────────────


class TestUploadToLate:
    """Test _upload_to_late() and generate_and_upload()."""

    @patch.dict(os.environ, {"LATE_API_KEY": ""})
    @patch("lib.ai.imagen_client.genai")
    def test_upload_raises_without_late_key(self, mock_genai):
        """_upload_to_late() raises ValueError without LATE_API_KEY."""
        from lib.ai.imagen_client import ImagenClient

        client = ImagenClient(api_key="test-key")
        with pytest.raises(ValueError, match="LATE_API_KEY required"):
            client._upload_to_late("/tmp/fake.png")
