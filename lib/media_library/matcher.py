"""Content-to-image scoring and matching engine.

Ranks library images for a content slot using weighted multi-factor scoring:
pillar affinity, tag overlap, platform fit, freshness, and mood match.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Scoring weights
W_PILLAR = 0.30
W_TAGS = 0.25
W_PLATFORM = 0.20
W_FRESHNESS = 0.15
W_MOOD = 0.10

# Persona → preferred moods
PERSONA_MOODS: Dict[str, Set[str]] = {
    "professional": {"professional", "minimal", "technical", "creative"},
    "personal": {"vibrant", "casual", "creative"},
    "ceo": {"professional", "dark", "minimal", "technical"},
}


class MediaMatcher:
    """Score and rank library images for content slots."""

    def find_best(
        self,
        topic: str,
        pillar: str,
        platform: str,
        count: int = 2,
        exclude_ids: Optional[List[str]] = None,
        persona: str = "professional",
    ) -> List[Dict[str, Any]]:
        """Find the best-matching library images for a content slot.

        Args:
            topic: Content topic or keywords
            pillar: Today's content pillar
            platform: Target platform
            count: Number of images to return
            exclude_ids: Item IDs to skip (already used in this batch)
            persona: Voice persona (affects mood preference)

        Returns:
            List of scored items: [{item_id, storage_url, description, score, match_reasons}]
        """
        from lib.media_library.catalog import MediaCatalog

        catalog = MediaCatalog()
        # Get a generous pool of candidates
        candidates = catalog.get_available(limit=50)

        if not candidates:
            return []

        exclude = set(exclude_ids or [])
        topic_words = self._extract_keywords(topic)

        scored = []
        for item in candidates:
            if item["id"] in exclude:
                continue

            score, reasons = self._score_item(
                item, pillar, platform, topic_words, persona
            )
            scored.append({
                "item_id": item["id"],
                "storage_url": item["storage_url"],
                "description": item["description"],
                "score": round(score, 3),
                "match_reasons": reasons,
                "filename": item["filename"],
            })

        # Sort by score descending
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:count]

    def _score_item(
        self,
        item: Dict[str, Any],
        pillar: str,
        platform: str,
        topic_words: Set[str],
        persona: str,
    ) -> tuple[float, List[str]]:
        """Score a single item against the content slot.

        Returns (score, list_of_reasons).
        """
        reasons: List[str] = []
        scores: Dict[str, float] = {}

        # 1. Pillar affinity (0.30)
        affinity = item.get("pillar_affinity", {})
        pillar_score = 0.0
        if isinstance(affinity, dict):
            # Find best matching pillar key (partial match)
            for key, value in affinity.items():
                if pillar.lower() in key.lower() or key.lower() in pillar.lower():
                    pillar_score = max(pillar_score, float(value))
        scores["pillar"] = pillar_score
        if pillar_score > 0.5:
            reasons.append(f"pillar match ({pillar_score:.1f})")

        # 2. Tag overlap (0.25)
        tags = set(t.lower() for t in item.get("tags", []))
        if tags and topic_words:
            overlap = len(tags & topic_words)
            tag_score = min(overlap / max(len(topic_words), 1), 1.0)
        else:
            tag_score = 0.0
        scores["tags"] = tag_score
        if tag_score > 0.2:
            reasons.append(f"tag overlap ({tag_score:.1f})")

        # 3. Platform fit (0.20)
        platform_fit = item.get("platform_fit", {})
        plat_score = 0.0
        if isinstance(platform_fit, dict):
            plat_score = float(platform_fit.get(platform, 0.0))
        scores["platform"] = plat_score
        if plat_score > 0.5:
            reasons.append(f"{platform} fit ({plat_score:.1f})")

        # 4. Freshness (0.15) — least-used preferred
        times_used = item.get("times_used", 0)
        freshness_score = max(0.0, 1.0 - (times_used * 0.2))
        scores["freshness"] = freshness_score
        if times_used == 0:
            reasons.append("never used")

        # 5. Mood match (0.10)
        mood = item.get("mood", "").lower()
        preferred = PERSONA_MOODS.get(persona, PERSONA_MOODS["professional"])
        mood_score = 1.0 if mood in preferred else 0.3
        scores["mood"] = mood_score
        if mood in preferred:
            reasons.append(f"mood: {mood}")

        # Weighted total
        total = (
            scores["pillar"] * W_PILLAR
            + scores["tags"] * W_TAGS
            + scores["platform"] * W_PLATFORM
            + scores["freshness"] * W_FRESHNESS
            + scores["mood"] * W_MOOD
        )

        return total, reasons

    @staticmethod
    def _extract_keywords(text: str) -> Set[str]:
        """Extract lowercase keywords from topic text."""
        # Remove common stop words for better matching
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might",
            "can", "this", "that", "these", "those", "it", "its",
            "about", "how", "what", "which", "who", "when", "where",
        }
        words = set()
        for word in text.lower().split():
            cleaned = word.strip(".,!?;:\"'()[]{}#@")
            if len(cleaned) > 2 and cleaned not in stop_words:
                words.add(cleaned)
        return words
