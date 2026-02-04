"""
Unit tests for response generator.

Tests AI-powered response generation.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from engagement.response_generator import ResponseGenerator


class TestResponseGeneratorInit:
    """Test response generator initialization."""

    def test_init_default_provider(self):
        """Initialize with default Gemini provider."""
        gen = ResponseGenerator()
        assert gen.provider == 'gemini'

    @pytest.mark.skipif(
        not os.getenv('ANTHROPIC_API_KEY'),
        reason="ANTHROPIC_API_KEY not set"
    )
    def test_init_anthropic_provider(self):
        """Initialize with Anthropic provider."""
        gen = ResponseGenerator(provider='anthropic')
        assert gen.provider == 'anthropic'

    def test_init_custom_brand_voice(self):
        """Initialize with custom brand voice."""
        gen = ResponseGenerator(brand_voice='casual')
        assert gen.brand_voice == 'casual'

    def test_default_brand_voice_professional(self):
        """Default brand voice is professional."""
        gen = ResponseGenerator()
        assert gen.brand_voice == 'professional'


class TestPlatformGuidelines:
    """Test platform-specific guidelines."""

    def test_instagram_guidelines(self):
        """Instagram has specific guidelines."""
        assert 'instagram' in ResponseGenerator.PLATFORM_GUIDELINES
        ig = ResponseGenerator.PLATFORM_GUIDELINES['instagram']
        assert 'max_length' in ig
        assert ig['max_length'] == 2200

    def test_reddit_guidelines(self):
        """Reddit has specific guidelines."""
        assert 'reddit' in ResponseGenerator.PLATFORM_GUIDELINES
        reddit = ResponseGenerator.PLATFORM_GUIDELINES['reddit']
        assert 'conversational' in reddit['tone'] or 'community' in reddit['tone']
        assert reddit['use_emojis'] is False

    def test_twitter_guidelines(self):
        """Twitter has specific guidelines."""
        assert 'twitter' in ResponseGenerator.PLATFORM_GUIDELINES
        twitter = ResponseGenerator.PLATFORM_GUIDELINES['twitter']
        assert twitter['max_length'] == 280

    def test_telegram_guidelines(self):
        """Telegram has specific guidelines."""
        assert 'telegram' in ResponseGenerator.PLATFORM_GUIDELINES
        telegram = ResponseGenerator.PLATFORM_GUIDELINES['telegram']
        assert 'direct' in telegram['tone'] or 'helpful' in telegram['tone']


class TestBrandVoiceTemplates:
    """Test brand voice templates."""

    def test_professional_template(self):
        """Professional brand voice template."""
        assert 'professional' in ResponseGenerator.BRAND_VOICES
        template = ResponseGenerator.BRAND_VOICES['professional']
        assert 'formal' in template.lower() or 'professional' in template.lower()

    def test_friendly_template(self):
        """Friendly brand voice template."""
        assert 'friendly' in ResponseGenerator.BRAND_VOICES
        template = ResponseGenerator.BRAND_VOICES['friendly']
        assert 'warm' in template.lower() or 'friendly' in template.lower()

    def test_casual_template(self):
        """Casual brand voice template."""
        assert 'casual' in ResponseGenerator.BRAND_VOICES
        template = ResponseGenerator.BRAND_VOICES['casual']
        assert 'relaxed' in template.lower() or 'casual' in template.lower()

    def test_enthusiastic_template(self):
        """Enthusiastic brand voice template."""
        assert 'enthusiastic' in ResponseGenerator.BRAND_VOICES

    def test_supportive_template(self):
        """Supportive brand voice template."""
        assert 'supportive' in ResponseGenerator.BRAND_VOICES


class TestCommentReplyGeneration:
    """Test comment reply generation."""

    @pytest.fixture
    def generator(self):
        """Create generator with mocked AI client."""
        gen = ResponseGenerator(provider='gemini')
        gen._ai_client = MagicMock()
        gen._ai_client.generate_content.return_value = MagicMock(
            text='Thank you for your feedback!'
        )
        return gen

    def test_generate_comment_reply(self, generator):
        """Generate a comment reply."""
        reply = generator.generate_comment_reply(
            comment='Great post!',
            author='user123',
            platform='instagram'
        )
        assert reply is not None
        assert isinstance(reply, str)

    def test_generate_reply_with_original_post(self, generator):
        """Generate reply with original post context."""
        reply = generator.generate_comment_reply(
            comment='What is this?',
            author='curious_user',
            platform='instagram',
            original_post='Check out our new product!'
        )
        assert reply is not None

    def test_generate_reply_respects_max_length(self, generator):
        """Generated reply respects platform max length."""
        # Mock a very long response
        generator._ai_client.generate_content.return_value = MagicMock(
            text='A' * 5000
        )

        reply = generator.generate_comment_reply(
            comment='Tell me more',
            author='user',
            platform='twitter'  # 280 char limit
        )

        # Response should be truncated
        assert len(reply) <= 280


class TestDMReplyGeneration:
    """Test DM reply generation."""

    @pytest.fixture
    def generator(self):
        """Create generator with mocked AI client."""
        gen = ResponseGenerator(provider='gemini')
        gen._ai_client = MagicMock()
        gen._ai_client.generate_content.return_value = MagicMock(
            text='Hi! How can I help you today?'
        )
        return gen

    def test_generate_dm_reply(self, generator):
        """Generate a DM reply."""
        reply = generator.generate_dm_reply(
            message='Hello!',
            sender_name='John',
            platform='instagram'
        )
        assert reply is not None
        assert isinstance(reply, str)

    def test_generate_dm_reply_with_history(self, generator):
        """Generate DM reply with conversation history."""
        history = [
            {'is_me': False, 'content': 'Hi there'},
            {'is_me': True, 'content': 'Hello! How can I help?'},
            {'is_me': False, 'content': 'I have a question'}
        ]

        reply = generator.generate_dm_reply(
            message='Can you help me?',
            sender_name='Jane',
            platform='telegram',
            conversation_history=history
        )
        assert reply is not None


class TestSentimentAnalysis:
    """Test sentiment analysis."""

    @pytest.fixture
    def generator(self):
        """Create generator with mocked AI client."""
        gen = ResponseGenerator(provider='gemini')
        gen._ai_client = MagicMock()
        return gen

    def test_analyze_positive_sentiment(self, generator):
        """Analyze positive sentiment."""
        generator._ai_client.generate_content.return_value = MagicMock(
            text='{"sentiment": "positive", "score": 0.9, "category": "praise"}'
        )

        result = generator.analyze_sentiment('This is amazing!')
        assert result['sentiment'] == 'positive'
        assert result['score'] > 0.5

    def test_analyze_negative_sentiment(self, generator):
        """Analyze negative sentiment."""
        generator._ai_client.generate_content.return_value = MagicMock(
            text='{"sentiment": "negative", "score": 0.85, "category": "complaint"}'
        )

        result = generator.analyze_sentiment('This is terrible!')
        assert result['sentiment'] == 'negative'

    def test_analyze_question_intent(self, generator):
        """Detect question category."""
        generator._ai_client.generate_content.return_value = MagicMock(
            text='{"sentiment": "neutral", "score": 0.8, "category": "question"}'
        )

        result = generator.analyze_sentiment('How does this work?')
        assert result['category'] == 'question'


class TestPromptBuilding:
    """Test internal prompt building."""

    def test_get_platform_guidelines_instagram(self):
        """Get Instagram guidelines."""
        gen = ResponseGenerator()
        guidelines = gen._get_platform_guidelines('instagram')
        assert guidelines is not None
        assert 'Max length' in guidelines or 'max_length' in str(guidelines)

    def test_get_platform_guidelines_unknown(self):
        """Unknown platform returns default."""
        gen = ResponseGenerator()
        guidelines = gen._get_platform_guidelines('unknown_platform')
        # Should return default or empty, not raise error
        assert guidelines is not None or guidelines == ''

    def test_get_brand_voice_instructions(self):
        """Get brand voice instructions."""
        gen = ResponseGenerator(brand_voice='friendly')
        instructions = gen._get_brand_voice_instructions()
        assert 'warm' in instructions.lower() or 'friendly' in instructions.lower()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_comment(self):
        """Handle empty comment."""
        gen = ResponseGenerator()
        gen._ai_client = MagicMock()
        gen._ai_client.generate_content.return_value = MagicMock(
            text='Thanks for engaging!'
        )

        reply = gen.generate_comment_reply(
            comment='',
            author='user',
            platform='instagram'
        )
        # Should not raise, should return something reasonable
        assert reply is not None

    def test_very_long_comment(self):
        """Handle very long comment."""
        gen = ResponseGenerator()
        gen._ai_client = MagicMock()
        gen._ai_client.generate_content.return_value = MagicMock(
            text='Thank you for your detailed feedback!'
        )

        long_comment = 'This is great! ' * 1000
        reply = gen.generate_comment_reply(
            comment=long_comment,
            author='verbose_user',
            platform='reddit'
        )
        assert reply is not None

    def test_special_characters_in_comment(self):
        """Handle special characters."""
        gen = ResponseGenerator()
        gen._ai_client = MagicMock()
        gen._ai_client.generate_content.return_value = MagicMock(
            text='Thanks!'
        )

        reply = gen.generate_comment_reply(
            comment='Love this! <3 @user #hashtag $$$',
            author='emoji_fan',
            platform='instagram'
        )
        assert reply is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
