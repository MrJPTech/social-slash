"""Gemini 2.0 Flash Vision analysis for media library images.

Analyzes screenshots/photos and returns structured metadata for indexing:
description, tags, themes, text_content, mood, pillar_affinity, platform_fit.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Weekly pillars from data/weekly_pillars.json
PILLARS = [
    "AI tools and automation",
    "developer life and vibe coding",
    "building in public",
    "startup mindset and execution",
    "tech trends and future thinking",
]

ANALYSIS_PROMPT = f"""Analyze this image for social media content planning.

Return a JSON object with these exact keys:

{{
  "description": "1-2 sentence description of what you see in the image",
  "tags": ["10-15 keywords describing the image content, tools, topics"],
  "themes": ["which broad themes this image relates to"],
  "text_content": "any text/code visible in the image (OCR). Empty string if none.",
  "mood": "one of: vibrant, minimal, dark, professional, casual, technical, creative",
  "pillar_affinity": {{
    "pillar_name": 0.0-1.0 relevance score
  }},
  "platform_fit": {{
    "twitter": 0.0-1.0,
    "linkedin": 0.0-1.0,
    "instagram": 0.0-1.0,
    "tiktok": 0.0-1.0,
    "facebook": 0.0-1.0,
    "threads": 0.0-1.0,
    "reddit": 0.0-1.0,
    "bluesky": 0.0-1.0
  }}
}}

Content pillars to score against:
{json.dumps(PILLARS)}

Platform fit guidelines:
- twitter: Works if image is shareable, has a clear point, or shows something interesting
- linkedin: Professional/technical content, work achievements, tools, insights
- instagram: Visually appealing, lifestyle, behind-the-scenes, workspace shots
- tiktok: Eye-catching, trendy, would work as a still frame for video
- facebook: Broad appeal, community-oriented, discussion-worthy
- threads: Conversation-starting, opinion-worthy, tech community relevant
- reddit: Technical depth, useful info, interesting finds, niche community value
- bluesky: Similar to twitter — shareable, clear point, tech community

Return ONLY valid JSON. No markdown formatting, no code blocks."""

MODEL = "gemini-2.0-flash"


class VisionAnalyzer:
    """Analyze images using Gemini 2.0 Flash multimodal API."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        if not self._api_key:
            raise ValueError("GOOGLE_API_KEY required for vision analysis")

    def _get_client(self):
        from google import genai

        return genai.Client(api_key=self._api_key)

    def analyze_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> dict[str, Any]:
        """Analyze image from raw bytes.

        Args:
            image_bytes: Raw image bytes
            mime_type: MIME type of the image

        Returns:
            Vision analysis dict with description, tags, themes, etc.
        """
        from google.genai import types

        client = self._get_client()
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ANALYSIS_PROMPT,
        ]

        response = client.models.generate_content(model=MODEL, contents=contents)
        return self._parse_response(response.text)

    def analyze_file(self, file_path: str) -> dict[str, Any]:
        """Analyze image from a local file path.

        Args:
            file_path: Path to the image file

        Returns:
            Vision analysis dict
        """
        ext = os.path.splitext(file_path)[1].lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")

        with open(file_path, "rb") as f:
            image_bytes = f.read()

        return self.analyze_bytes(image_bytes, mime_type)

    def _parse_response(self, text: str) -> dict[str, Any]:
        """Parse Gemini's JSON response, handling markdown code blocks."""
        cleaned = text.strip()
        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [line for line in lines if not line.strip().startswith("```")]
            cleaned = "\n".join(lines)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("[vision] Failed to parse Gemini response as JSON, using defaults")
            data = {}

        # Ensure all expected keys exist with proper types
        return {
            "description": data.get("description", ""),
            "tags": data.get("tags", []),
            "themes": data.get("themes", []),
            "text_content": data.get("text_content", ""),
            "mood": data.get("mood", ""),
            "pillar_affinity": data.get("pillar_affinity", {}),
            "platform_fit": data.get("platform_fit", {}),
        }
