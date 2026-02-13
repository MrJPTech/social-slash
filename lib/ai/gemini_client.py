#!/usr/bin/env python3
"""
Gemini AI Client for Content Enhancement

Uses Google's Gemini 2.0 Flash model for:
- Content optimization for specific platforms
- Hashtag generation
- Engagement improvement suggestions
"""

import os
import json
from typing import Dict, List, Optional, Any

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiClient:
    """
    Gemini AI client for social media content enhancement.

    Uses Gemini 2.0 Flash for fast, cost-effective content optimization.
    """

    MODEL = "gemini-2.0-flash"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini client.

        Args:
            api_key: Google API key. Defaults to GOOGLE_API_KEY env var.
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "google-genai package not installed. "
                "Run: pip install google-genai"
            )

        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')

        if not self.api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.client = genai.Client(api_key=self.api_key)

    def enhance_content(
        self,
        content: str,
        platform: str,
        style: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> Dict[str, Any]:
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

Respond in JSON format:
{{
    "enhanced_content": "The optimized content here",
    "changes_made": ["list", "of", "changes"],
    "engagement_tips": ["tip1", "tip2"],
    "suggested_hashtags": ["hashtag1", "hashtag2"]
}}
"""

        try:
            response = self.client.models.generate_content(model=self.MODEL, contents=prompt)
            result_text = response.text

            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            result['provider'] = 'gemini'
            result['model'] = self.MODEL

            print("[SUCCESS] Content enhanced with Gemini")
            return result

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                'enhanced_content': content,
                'changes_made': [],
                'engagement_tips': [],
                'suggested_hashtags': [],
                'provider': 'gemini',
                'model': self.MODEL,
                'error': 'Failed to parse AI response'
            }
        except Exception as e:
            print(f"[ERROR] Gemini enhancement failed: {e}")
            raise

    def generate_hashtags(
        self,
        content: str,
        platform: str,
        count: int = 5
    ) -> List[str]:
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
Return only the hashtags as a JSON array, without the # symbol.

Post:
{content}

Example response: ["developer", "coding", "tech"]
"""

        try:
            response = self.client.models.generate_content(model=self.MODEL, contents=prompt)
            result_text = response.text

            # Clean up response
            if "```" in result_text:
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.split("```")[0]

            hashtags = json.loads(result_text.strip())

            # Remove # if present
            hashtags = [h.lstrip('#') for h in hashtags]

            print(f"[SUCCESS] Generated {len(hashtags)} hashtags")
            return hashtags[:count]

        except Exception as e:
            print(f"[ERROR] Hashtag generation failed: {e}")
            return []

    def analyze_content(
        self,
        content: str,
        platform: str
    ) -> Dict[str, Any]:
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

Respond in JSON format:
{{
    "score": 0-100,
    "strengths": ["list", "of", "strengths"],
    "improvements": ["list", "of", "improvements"],
    "readability": "easy/medium/hard",
    "tone": "detected tone",
    "call_to_action": true/false,
    "estimated_engagement": "low/medium/high"
}}
"""

        try:
            response = self.client.models.generate_content(model=self.MODEL, contents=prompt)
            result_text = response.text

            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]

            result = json.loads(result_text.strip())
            result['provider'] = 'gemini'

            print(f"[SUCCESS] Content analyzed (score: {result.get('score', 'N/A')})")
            return result

        except Exception as e:
            print(f"[ERROR] Content analysis failed: {e}")
            raise


# Example usage
if __name__ == "__main__":
    client = GeminiClient()

    # Test enhancement
    result = client.enhance_content(
        content="Check out our new product launch!",
        platform="linkedin",
        style="professional"
    )

    print("\nEnhanced content:")
    print(result.get('enhanced_content', 'N/A'))
