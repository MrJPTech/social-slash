#!/usr/bin/env python3
"""
Basic import tests for Social Slash package.

Run with: pytest tests/ -v
"""

import sys
import os

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))


class TestImports:
    """Test that all modules can be imported correctly."""

    def test_lib_import(self):
        """Test main lib package imports."""
        import lib
        assert hasattr(lib, '__version__')
        assert lib.__version__ == "0.1.0"

    def test_tools_import(self):
        """Test tools module imports."""
        from lib.tools import (
            SocialTool,
            Platform,
            Category,
            TOOLS,
            PYTHON_SDKS,
            SCHEDULING_TOOLS,
            get_tools_by_platform,
            search_tools
        )
        assert len(TOOLS) > 0
        assert len(PYTHON_SDKS) > 0
        assert len(SCHEDULING_TOOLS) > 0

    def test_api_clients_import(self):
        """Test API clients imports."""
        from lib.api_clients import LateDistributionClient, post_to_linkedin
        assert LateDistributionClient is not None

    def test_posting_import(self):
        """Test posting module imports."""
        from lib.posting import Poster
        assert Poster is not None

    def test_ai_clients_import(self):
        """Test AI clients imports (may warn about deprecation)."""
        from lib.ai import GeminiClient, AnthropicClient
        assert GeminiClient is not None
        assert AnthropicClient is not None


class TestPoster:
    """Test Poster class functionality."""

    def test_poster_creation_with_skip_late(self):
        """Test Poster can be created in dry-run mode without API key."""
        from lib.posting import Poster
        poster = Poster(skip_late_init=True)
        assert poster._skip_late_init is True
        assert poster._late_client is None

    def test_poster_dry_run(self):
        """Test Poster dry-run mode returns expected structure."""
        from lib.posting import Poster
        poster = Poster(skip_late_init=True)
        result = poster.post(
            content="Test content",
            platforms=["linkedin"],
            dry_run=True
        )
        assert result['status'] == 'dry-run'
        assert result['original_content'] == "Test content"
        assert result['platforms'] == ["linkedin"]
        assert result['would_post'] is True


class TestLateClient:
    """Test LateDistributionClient functionality."""

    def test_supported_platforms(self):
        """Test supported platforms list."""
        from lib.api_clients import LateDistributionClient
        expected = [
            'linkedin', 'tiktok', 'instagram', 'youtube', 'twitter',
            'facebook', 'pinterest', 'threads', 'bluesky', 'reddit',
            'snapchat', 'telegram', 'google_business'
        ]
        assert LateDistributionClient.SUPPORTED_PLATFORMS == expected


class TestToolsDatabase:
    """Test social tools database."""

    def test_get_tools_by_platform(self):
        """Test filtering tools by platform."""
        from lib.tools import get_tools_by_platform
        linkedin_tools = get_tools_by_platform('linkedin')
        assert len(linkedin_tools) > 0

    def test_search_tools(self):
        """Test searching tools."""
        from lib.tools import search_tools
        results = search_tools('twitter')
        assert len(results) > 0

    def test_python_sdks_have_install_commands(self):
        """Test that Python SDKs have install commands."""
        from lib.tools import PYTHON_SDKS
        for sdk in PYTHON_SDKS:
            assert sdk.install_command is not None
            assert sdk.install_command.startswith('pip install')
