"""Content pipeline — generates A/B content bundles for SLASHERBOT approval.

Each bundle contains two copy options (Option A = SWIZZ voice, Option B = CEO voice)
plus matched library images (or no images if library empty). Bundles are sent to
Google Chat for human approval before posting; the daily scheduler auto-posts
after a 2-hour TTL.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Platforms that reject text-only posts
MEDIA_REQUIRED_PLATFORMS = frozenset({"instagram", "tiktok"})


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
    image_source: str = "none"  # "library" | "ai_generated" | "none"
    library_item_ids: List[str] = field(default_factory=list)


class ContentPipeline:
    """Generate ContentBundles by combining existing agents and media library."""

    # Alternate persona for Option A: even slots → professional, odd → personal
    _slot_counter: int = 0

    def generate_bundle(
        self,
        platform: str,
        time_slot: str,
        pillar: str,
        base_persona: str = "professional",
        subreddit: Optional[str] = None,
    ) -> Optional[ContentBundle]:
        """Generate a full A/B content bundle for one scheduling slot.

        Prefers real library images over AI-generated ones. If the library is
        empty and the platform requires media (Instagram/TikTok), returns None
        to signal the caller to skip this slot.

        Args:
            platform: Target platform (twitter, linkedin, etc.)
            time_slot: Human-readable slot label (e.g. "09:00")
            pillar: Content pillar for the day
            base_persona: Persona hint — "professional" or "personal"
            subreddit: For reddit posts, the subreddit to target

        Returns:
            ContentBundle with two copy options + library image URLs,
            or None if a media-required platform has no library images.
        """
        slot_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=2)

        logger.info(f"[pipeline] Generating bundle for {platform} @ {time_slot} — {pillar}")

        # ── Topic variation via ResearchAgent ──────────────────────────────
        topic = self._get_topic_variation(pillar, platform, subreddit)

        # ── Find matching library images ──────────────────────────────────
        matches = self._find_library_images(topic, pillar, platform, base_persona)

        if len(matches) >= 2:
            image_1_url = matches[0]["storage_url"]
            image_2_url = matches[1]["storage_url"]
            library_ids = [m["item_id"] for m in matches[:2]]
            image_source = "library"

            # Write copy ABOUT what's in the actual image
            option_a = self._generate_copy_for_image(
                matches[0]["description"], topic, platform, base_persona,
                tone="authentic", energy="high"
            )
            option_b = self._generate_copy_for_image(
                matches[1]["description"], topic, platform, "ceo",
                tone="direct", energy="medium"
            )

        elif len(matches) == 1:
            image_1_url = matches[0]["storage_url"]
            image_2_url = ""
            library_ids = [matches[0]["item_id"]]
            image_source = "library"

            option_a = self._generate_copy_for_image(
                matches[0]["description"], topic, platform, base_persona,
                tone="authentic", energy="high"
            )
            option_b = self._generate_copy(topic, platform, "ceo", tone="direct", energy="medium")

        else:
            # No library images — text-only (no AI image fallback)
            if platform in MEDIA_REQUIRED_PLATFORMS:
                logger.warning(
                    f"[pipeline] {platform} requires media but library empty — skipping slot"
                )
                return None

            image_1_url = ""
            image_2_url = ""
            library_ids = []
            image_source = "none"
            logger.warning(f"[pipeline] No library images for {platform} — text-only bundle")

            option_a = self._generate_copy(topic, platform, base_persona, tone="authentic", energy="high")
            option_b = self._generate_copy(topic, platform, "ceo", tone="direct", energy="medium")

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
            image_source=image_source,
            library_item_ids=library_ids,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_library_images(
        self, topic: str, pillar: str, platform: str, persona: str
    ) -> list:
        """Find matching images from the media library."""
        try:
            from lib.media_library.matcher import MediaMatcher

            matcher = MediaMatcher()
            return matcher.find_best(
                topic=topic,
                pillar=pillar,
                platform=platform,
                count=2,
                persona=persona,
            )
        except Exception as exc:
            logger.warning(f"[pipeline] MediaMatcher failed: {exc}")
            return []

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
                    stripped = line.strip(" -\u2022*123456789.")
                    if len(stripped) > 10:
                        topic = stripped[:120]
                        logger.info(f"[pipeline] Research topic: {topic[:60]}\u2026")
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

    def _generate_copy_for_image(
        self,
        image_description: str,
        topic: str,
        platform: str,
        persona_mode: str,
        tone: str,
        energy: str,
    ) -> Dict[str, Any]:
        """Write post copy that reacts to the REAL image content."""
        enriched_topic = (
            f"Write a {platform} post reacting to this screenshot/photo: "
            f"{image_description}. "
            f"Connect it to the theme of '{topic}'. "
            f"Sound like you're genuinely sharing what you see — "
            f"not describing an AI image."
        )
        return self._generate_copy(enriched_topic, platform, persona_mode, tone, energy)
