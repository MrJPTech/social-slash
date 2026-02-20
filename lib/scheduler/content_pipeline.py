"""Content pipeline — generates A/B content bundles for SLASHERBOT approval.

Each bundle contains two copy options (Option A = SWIZZ voice, Option B = CEO voice)
plus two Imagen 4 images. Bundles are sent to Google Chat for human approval before
posting; the daily scheduler auto-posts after a 2-hour TTL.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ContentBundle:
    """A single scheduled post slot with two content options and two images."""

    slot_id: str
    platform: str
    subreddit: Optional[str]
    pillar: str
    topic: str
    option_a: Dict[str, Any]   # {content, hashtags, persona_mode}
    option_b: Dict[str, Any]   # {content, hashtags, persona_mode}
    image_1_url: str
    image_2_url: str
    scheduled_time: datetime
    expires_at: datetime        # +2 hours from scheduled_time
    posted: bool = False
    choice: Optional[str] = None  # "A1"|"A2"|"B1"|"B2" after approval


class ContentPipeline:
    """Generate ContentBundles by combining existing agents and ImagenClient."""

    # Alternate persona for Option A: even slots → professional, odd → personal
    _slot_counter: int = 0

    def generate_bundle(
        self,
        platform: str,
        time_slot: str,
        pillar: str,
        base_persona: str = "professional",
        subreddit: Optional[str] = None,
    ) -> ContentBundle:
        """Generate a full A/B content bundle for one scheduling slot.

        Args:
            platform: Target platform (twitter, linkedin, etc.)
            time_slot: Human-readable slot label (e.g. "09:00")
            pillar: Content pillar for the day
            base_persona: Persona hint — "professional" or "personal"
            subreddit: For reddit posts, the subreddit to target

        Returns:
            ContentBundle with two copy options + two uploaded image URLs.
        """
        slot_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=2)

        logger.info(f"[pipeline] Generating bundle for {platform} @ {time_slot} — {pillar}")

        # ── Topic variation via ResearchAgent ──────────────────────────────
        topic = self._get_topic_variation(pillar, platform, subreddit)

        # ── Option A: SWIZZ voice (professional or personal alternates) ────
        persona_a = base_persona  # "professional" or "personal"
        option_a = self._generate_copy(topic, platform, persona_a, tone="authentic", energy="high")

        # ── Option B: Jordan Ward CEO voice ────────────────────────────────
        option_b = self._generate_copy(topic, platform, "ceo", tone="direct", energy="medium")

        # ── Image 1: vibrant abstract ───────────────────────────────────────
        image_1_url = self._generate_image(topic, platform, style_hint="vibrant abstract")

        # ── Image 2: minimal corporate ──────────────────────────────────────
        image_2_url = self._generate_image(topic, platform, style_hint="minimal corporate")

        self._slot_counter += 1

        return ContentBundle(
            slot_id=slot_id,
            platform=platform,
            subreddit=subreddit,
            pillar=pillar,
            topic=topic,
            option_a=option_a,
            option_b=option_b,
            image_1_url=image_1_url,
            image_2_url=image_2_url,
            scheduled_time=now,
            expires_at=expires_at,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_topic_variation(
        self, pillar: str, platform: str, subreddit: Optional[str]
    ) -> str:
        """Use ResearchAgent to suggest a fresh topic angle for the pillar."""
        try:
            from lib.mcp._client_helpers import build_agent_config, suppress_stdout
            from lib.agents.research_agent import ResearchAgent

            config = build_agent_config("professional", platform)
            with suppress_stdout():
                agent = ResearchAgent(config)
                result = agent.suggest_content_ideas(pillar, count=1)

            # Extract the first idea text
            ideas_text = result.get("ideas", "")
            if ideas_text:
                # Take first non-empty line as the topic angle
                for line in ideas_text.split("\n"):
                    stripped = line.strip(" -•*123456789.")
                    if len(stripped) > 10:
                        topic = stripped[:120]
                        logger.info(f"[pipeline] Research topic: {topic[:60]}…")
                        return topic
        except Exception as exc:
            logger.warning(f"[pipeline] ResearchAgent failed, using pillar as topic: {exc}")

        # Fallback: use pillar directly with platform context
        sub_note = f" for {subreddit}" if subreddit else ""
        return f"{pillar}{sub_note}"

    def _generate_copy(
        self,
        topic: str,
        platform: str,
        persona_mode: str,
        tone: str,
        energy: str,
    ) -> Dict[str, Any]:
        """Generate post copy via WritingAgent and return a normalised dict."""
        try:
            from lib.mcp._client_helpers import build_agent_config, suppress_stdout
            from lib.agents.writing_agent import WritingAgent

            config = build_agent_config(persona_mode, platform)
            with suppress_stdout():
                agent = WritingAgent(config)
                result = agent.generate_post(
                    topic=topic,
                    platform=platform,
                    post_type="auto",
                    persona_mode=persona_mode,
                    tone=tone,
                    energy=energy,
                )

            return {
                "content": result.get("content", ""),
                "hashtags": result.get("hashtags", []),
                "persona_mode": persona_mode,
                "tone": tone,
                "energy": energy,
                "char_count": result.get("char_count", 0),
            }
        except Exception as exc:
            logger.error(f"[pipeline] WritingAgent failed ({persona_mode}): {exc}")
            return {
                "content": f"[Content generation failed: {exc}]",
                "hashtags": [],
                "persona_mode": persona_mode,
                "tone": tone,
                "energy": energy,
                "char_count": 0,
            }

    def _generate_image(
        self, topic: str, platform: str, style_hint: str
    ) -> str:
        """Generate and upload one image, return its Late cloud URL.

        Returns empty string on failure so the caller can decide whether to
        proceed without an image.
        """
        try:
            from lib.ai.imagen_client import ImagenClient
            from lib.mcp._client_helpers import suppress_stdout

            # Choose aspect ratio: media-required platforms get their native ratio
            image_type = "cover" if platform == "tiktok" else "post"

            prompt = (
                f"Professional social media visual for {platform}. "
                f"Theme: {topic[:100]}. "
                f"Style: {style_hint}. "
                "No text or words in the image. "
                "High-quality digital art, sharp composition, cinematic lighting."
            )

            with suppress_stdout():
                client = ImagenClient()
                urls = client.generate_and_upload(
                    prompt=prompt,
                    platform=platform,
                    image_type=image_type,
                    num_images=1,
                )

            url = urls[0] if urls else ""
            if url:
                logger.info(f"[pipeline] Image uploaded: {url[:60]}…")
            return url

        except Exception as exc:
            logger.error(f"[pipeline] Image generation failed ({style_hint}): {exc}")
            return ""
