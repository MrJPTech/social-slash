"""
Unit tests for platform-specific options.

Tests the PlatformOptions data models and their conversion to Late SDK format.
"""

import os
import sys

import pytest

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from models.platform_options import (
    InstagramOptions,
    LinkedInOptions,
    PlatformOptions,
    RedditOptions,
    ThreadsOptions,
    TwitterOptions,
)


class TestInstagramOptions:
    """Test Instagram-specific options."""

    def test_default_options_returns_none(self):
        """Default options should return None (no override needed)."""
        opts = InstagramOptions()
        assert opts.to_platform_data() is None

    def test_story_content_type(self):
        """Story content type should be passed."""
        opts = InstagramOptions(content_type="story")
        data = opts.to_platform_data()
        assert data == {"contentType": "story"}

    def test_reel_content_type(self):
        """Reel content type should be passed."""
        opts = InstagramOptions(content_type="reel")
        data = opts.to_platform_data()
        assert data == {"contentType": "reel"}

    def test_first_comment(self):
        """First comment should be included."""
        opts = InstagramOptions(first_comment="Follow for more!")
        data = opts.to_platform_data()
        assert data == {"firstComment": "Follow for more!"}

    def test_no_feed_option(self):
        """Share to feed=False should be included."""
        opts = InstagramOptions(share_to_feed=False)
        data = opts.to_platform_data()
        assert data == {"shareToFeed": False}

    def test_collaborators(self):
        """Collaborators should be included."""
        opts = InstagramOptions(collaborators=["user1", "user2"])
        data = opts.to_platform_data()
        assert data == {"collaborators": ["user1", "user2"]}

    def test_collaborators_max_three(self):
        """Collaborators should be truncated to max 3."""
        opts = InstagramOptions(collaborators=["user1", "user2", "user3", "user4"])
        data = opts.to_platform_data()
        assert data == {"collaborators": ["user1", "user2", "user3"]}

    def test_combined_options(self):
        """Multiple options should be combined."""
        opts = InstagramOptions(content_type="story", first_comment="Check link in bio!")
        data = opts.to_platform_data()
        assert data == {"contentType": "story", "firstComment": "Check link in bio!"}


class TestLinkedInOptions:
    """Test LinkedIn-specific options."""

    def test_default_options_returns_none(self):
        """Default options should return None."""
        opts = LinkedInOptions()
        assert opts.to_platform_data() is None

    def test_first_comment(self):
        """First comment should be included."""
        opts = LinkedInOptions(first_comment="See link in comments")
        data = opts.to_platform_data()
        assert data == {"firstComment": "See link in comments"}

    def test_disable_link_preview(self):
        """Disable link preview should be included."""
        opts = LinkedInOptions(disable_link_preview=True)
        data = opts.to_platform_data()
        assert data == {"disableLinkPreview": True}

    def test_organization_urn(self):
        """Organization URN should be included."""
        opts = LinkedInOptions(organization_urn="urn:li:organization:12345")
        data = opts.to_platform_data()
        assert data == {"organizationUrn": "urn:li:organization:12345"}

    def test_combined_options(self):
        """Multiple options should be combined."""
        opts = LinkedInOptions(first_comment="More info in comments", disable_link_preview=True)
        data = opts.to_platform_data()
        assert data == {"firstComment": "More info in comments", "disableLinkPreview": True}


class TestThreadsOptions:
    """Test Threads-specific options."""

    def test_default_options_returns_none(self):
        """Default options should return None."""
        opts = ThreadsOptions()
        assert opts.to_platform_data() is None

    def test_auto_thread(self):
        """Auto thread should be included."""
        opts = ThreadsOptions(auto_thread=True)
        data = opts.to_platform_data()
        assert data == {"thread": True}

    def test_thread_number(self):
        """Thread numbering should be included."""
        opts = ThreadsOptions(thread_number=True)
        data = opts.to_platform_data()
        assert data == {"threadNumber": True}

    def test_combined_options(self):
        """Multiple options should be combined."""
        opts = ThreadsOptions(auto_thread=True, thread_number=True)
        data = opts.to_platform_data()
        assert data == {"thread": True, "threadNumber": True}


class TestTwitterOptions:
    """Test Twitter-specific options."""

    def test_default_options_returns_none(self):
        """Default options should return None."""
        opts = TwitterOptions()
        assert opts.to_platform_data() is None

    def test_auto_thread_returns_none(self):
        """Auto thread doesn't generate platformSpecificData (handled separately)."""
        opts = TwitterOptions(auto_thread=True)
        assert opts.to_platform_data() is None


class TestRedditOptions:
    """Test Reddit-specific options."""

    def test_to_platform_data_returns_none(self):
        """Reddit uses top-level title, not platformSpecificData."""
        opts = RedditOptions(title="My Title")
        assert opts.to_platform_data() is None


class TestPlatformOptions:
    """Test the main PlatformOptions container."""

    def test_get_platform_data_instagram(self):
        """Should return Instagram-specific data."""
        options = PlatformOptions(instagram=InstagramOptions(content_type="story"))
        data = options.get_platform_data("instagram")
        assert data == {"contentType": "story"}

    def test_get_platform_data_linkedin(self):
        """Should return LinkedIn-specific data."""
        options = PlatformOptions(linkedin=LinkedInOptions(first_comment="Comment!"))
        data = options.get_platform_data("linkedin")
        assert data == {"firstComment": "Comment!"}

    def test_get_platform_data_threads(self):
        """Should return Threads-specific data."""
        options = PlatformOptions(threads=ThreadsOptions(auto_thread=True))
        data = options.get_platform_data("threads")
        assert data == {"thread": True}

    def test_get_platform_data_unknown_returns_none(self):
        """Should return None for unknown platform."""
        options = PlatformOptions()
        assert options.get_platform_data("unknown") is None

    def test_get_platform_data_case_insensitive(self):
        """Platform name should be case insensitive."""
        options = PlatformOptions(instagram=InstagramOptions(content_type="story"))
        assert options.get_platform_data("INSTAGRAM") == {"contentType": "story"}
        assert options.get_platform_data("Instagram") == {"contentType": "story"}

    def test_raw_platform_data_override(self):
        """Raw platform data should override typed options."""
        options = PlatformOptions(
            instagram=InstagramOptions(content_type="story"),
            raw_platform_data={"instagram": {"contentType": "reel", "extra": "value"}},
        )
        data = options.get_platform_data("instagram")
        assert data == {"contentType": "reel", "extra": "value"}


class TestRedditTitleExtraction:
    """Test Reddit title auto-generation."""

    def test_explicit_title(self):
        """Explicit title should be used if provided."""
        options = PlatformOptions(reddit=RedditOptions(title="My Explicit Title"))
        title = options.get_reddit_title("Content here")
        assert title == "My Explicit Title"

    def test_auto_extract_from_first_line(self):
        """Title should be extracted from first line."""
        options = PlatformOptions()
        content = "My Awesome Title\n\nThis is the post body."
        title = options.get_reddit_title(content)
        assert title == "My Awesome Title"

    def test_auto_extract_removes_hashtags(self):
        """Hashtags should be removed from auto-extracted title."""
        options = PlatformOptions()
        content = "#Python Tips for Beginners"
        title = options.get_reddit_title(content)
        assert title == "Tips for Beginners"

    def test_auto_extract_truncates_long_title(self):
        """Long titles should be truncated to 300 chars."""
        options = PlatformOptions()
        content = "A" * 400
        title = options.get_reddit_title(content)
        assert len(title) <= 300
        assert title.endswith("...")

    def test_auto_extract_empty_returns_default(self):
        """Empty/hashtag-only content returns default title."""
        options = PlatformOptions()
        content = "#hashtag #only"
        title = options.get_reddit_title(content)
        assert title == "New Post"


class TestPlatformOptionsValidation:
    """Test platform options validation."""

    def test_validate_matching_platforms(self):
        """No warnings when options match platforms."""
        options = PlatformOptions(instagram=InstagramOptions(content_type="story"))
        warnings = options.validate_for_platforms(["instagram"])
        assert len(warnings) == 0

    def test_validate_mismatched_instagram(self):
        """Warning when Instagram options but not posting to Instagram."""
        options = PlatformOptions(instagram=InstagramOptions(content_type="story"))
        warnings = options.validate_for_platforms(["twitter"])
        assert len(warnings) == 1
        assert "Instagram" in warnings[0]

    def test_validate_mismatched_linkedin(self):
        """Warning when LinkedIn options but not posting to LinkedIn."""
        options = PlatformOptions(linkedin=LinkedInOptions(first_comment="Comment"))
        warnings = options.validate_for_platforms(["twitter"])
        assert len(warnings) == 1
        assert "LinkedIn" in warnings[0]

    def test_validate_multiple_mismatches(self):
        """Multiple warnings for multiple mismatches."""
        options = PlatformOptions(
            instagram=InstagramOptions(content_type="story"),
            linkedin=LinkedInOptions(first_comment="Comment"),
        )
        warnings = options.validate_for_platforms(["twitter"])
        assert len(warnings) == 2

    def test_validate_case_insensitive(self):
        """Validation should be case insensitive."""
        options = PlatformOptions(instagram=InstagramOptions(content_type="story"))
        warnings = options.validate_for_platforms(["INSTAGRAM"])
        assert len(warnings) == 0


class TestCLIOptionsBuilding:
    """Test CLI argument parsing to PlatformOptions."""

    def test_build_instagram_options(self):
        """Test building Instagram options from CLI-like args."""
        instagram = InstagramOptions(
            content_type="story",
            first_comment="Links in bio!",
            collaborators=["user1", "user2"],
            share_to_feed=False,
        )
        data = instagram.to_platform_data()
        assert data == {
            "contentType": "story",
            "firstComment": "Links in bio!",
            "collaborators": ["user1", "user2"],
            "shareToFeed": False,
        }

    def test_build_combined_platform_options(self):
        """Test building combined options for multi-platform posting."""
        options = PlatformOptions(
            instagram=InstagramOptions(content_type="story"),
            linkedin=LinkedInOptions(first_comment="DM me!"),
            threads=ThreadsOptions(auto_thread=True),
            reddit=RedditOptions(title="My Reddit Post"),
        )

        assert options.get_platform_data("instagram") == {"contentType": "story"}
        assert options.get_platform_data("linkedin") == {"firstComment": "DM me!"}
        assert options.get_platform_data("threads") == {"thread": True}
        assert options.get_reddit_title("Any content") == "My Reddit Post"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
