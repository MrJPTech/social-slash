#!/usr/bin/env python3
"""
Anthropic AI Client for Content Enhancement

Uses Claude 3.5 Haiku for:
- High-quality content optimization
- Professional writing assistance
- Engagement analysis
"""

import json
import os
from typing import Any

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AnthropicClient:
    """
    Anthropic Claude client for social media content enhancement.

    Uses Claude 3.5 Haiku for quality, cost-effective content optimization.
    """

    MODEL = "claude-3-5-haiku-20241022"

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def enhance_content(
        self, content: str, platform: str, style: str | None = None, max_length: int | None = None
    ) -> dict[str, Any]:
        """
        Enhance content for a specific platform.

        Args:
            content: Original post content
            platform: Target platform (linkedin, twitter, etc.)
            style: Optional style guide (professional, casual, humorous)
            max_length: Optional character limit

        Returns:
            Dictionary with enhanced_content, suggestions, and metadata
        """
        style_guide = style or "professional and engaging"
        length_guide = f"Keep under {max_length} characters." if max_length else ""

        prompt = f"""You are a social media content optimizer. Enhance the following
content for {platform}.

Original content:
{content}

Requirements:
- Optimize for {platform} best practices
- Use a {style_guide} tone
- Improve engagement potential
- Add relevant emojis if appropriate
- {length_guide}

Respond in JSON format only, no other text:
{{
    "enhanced_content": "The optimized content here",
    "changes_made": ["list", "of", "changes"],
    "engagement_tips": ["tip1", "tip2"],
    "suggested_hashtags": ["hashtag1", "hashtag2"]
}}"""

        try:
            response = self.client.messages.create(
                model=self.MODEL, max_tokens=1024, messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse JSON from response
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            result["provider"] = "anthropic"
            result["model"] = self.MODEL

            print("[SUCCESS] Content enhanced with Claude")
            return result

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "enhanced_content": content,
                "changes_made": [],
                "engagement_tips": [],
                "suggested_hashtags": [],
                "provider": "anthropic",
                "model": self.MODEL,
                "error": "Failed to parse AI response",
            }
        except Exception as e:
            print(f"[ERROR] Claude enhancement failed: {e}")
            raise

    def generate_hashtags(self, content: str, platform: str, count: int = 5) -> list[str]:
        """
        Generate relevant hashtags for content.

        Args:
            content: Post content to analyze
            platform: Target platform
            count: Number of hashtags to generate

        Returns:
            List of hashtag strings (without #)
        """
        prompt = f"""Generate {count} relevant hashtags for this {platform} post.
Return only the hashtags as a JSON array, without the # symbol. No other text.

Post:
{content}

Example response: ["developer", "coding", "tech"]"""

        try:
            response = self.client.messages.create(
                model=self.MODEL, max_tokens=256, messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Clean up response
            if "```" in result_text:
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.split("```")[0]

            hashtags = json.loads(result_text.strip())

            # Remove # if present
            hashtags = [h.lstrip("#") for h in hashtags]

            print(f"[SUCCESS] Generated {len(hashtags)} hashtags")
            return hashtags[:count]

        except Exception as e:
            print(f"[ERROR] Hashtag generation failed: {e}")
            return []

    def analyze_content(self, content: str, platform: str) -> dict[str, Any]:
        """
        Analyze content for potential issues and improvements.

        Args:
            content: Post content to analyze
            platform: Target platform

        Returns:
            Dictionary with analysis results
        """
        prompt = f"""Analyze this {platform} post for effectiveness.

Post:
{content}

Respond in JSON format only, no other text:
{{
    "score": 0-100,
    "strengths": ["list", "of", "strengths"],
    "improvements": ["list", "of", "improvements"],
    "readability": "easy/medium/hard",
    "tone": "detected tone",
    "call_to_action": true/false,
    "estimated_engagement": "low/medium/high"
}}"""

        try:
            response = self.client.messages.create(
                model=self.MODEL, max_tokens=512, messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            result["provider"] = "anthropic"

            print(f"[SUCCESS] Content analyzed (score: {result.get('score', 'N/A')})")
            return result

        except Exception as e:
            print(f"[ERROR] Content analysis failed: {e}")
            raise

    def generate_insights(
        self, content: str, platform: str, audience: str | None = None
    ) -> dict[str, Any]:
        """
        Generate strategic insights for content improvement.

        Args:
            content: Post content to analyze
            platform: Target platform
            audience: Optional target audience description

        Returns:
            Dictionary with strategic insights
        """
        audience_context = f"Target audience: {audience}" if audience else ""

        prompt = f"""Provide strategic insights for this {platform} post.

Post:
{content}

{audience_context}

Respond in JSON format only:
{{
    "key_message": "The main message being conveyed",
    "audience_fit": "low/medium/high",
    "timing_suggestion": "Best time to post",
    "content_format_suggestion": "Alternative formats to try",
    "engagement_hooks": ["hook1", "hook2"],
    "viral_potential": "low/medium/high",
    "improvement_priority": ["most important", "second", "third"]
}}"""

        try:
            response = self.client.messages.create(
                model=self.MODEL, max_tokens=512, messages=[{"role": "user", "content": prompt}]
            )

            result_text = response.content[0].text

            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            result["provider"] = "anthropic"

            print("[SUCCESS] Generated insights")
            return result

        except Exception as e:
            print(f"[ERROR] Insight generation failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    client = AnthropicClient()

    # Test enhancement
    result = client.enhance_content(
        content="Check out our new product launch!", platform="linkedin", style="professional"
    )

    print("\nEnhanced content:")
    print(result.get("enhanced_content", "N/A"))
