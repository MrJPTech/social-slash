"""Google Chat cardsV2 builder for SLASHERBOT approval workflow.

Sends rich approval cards to the SLASHERBOT Google Chat space.
Each card shows Option A and Option B content, image previews, and
four approval buttons that open Railway approval URLs via HMAC tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import urllib.parse
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from lib.scheduler.content_pipeline import ContentBundle

logger = logging.getLogger(__name__)

# Environment variables
SLASHERBOT_WEBHOOK = os.getenv("GCHAT_WEBHOOK_SOCIAL_SLASH", "")
APPROVAL_BASE_URL = os.getenv(
    "APPROVAL_BASE_URL",
    os.getenv("RAILWAY_PUBLIC_DOMAIN", "https://web-production-c9cb9.up.railway.app"),
)
_TOKEN_SECRET = os.getenv("APPROVAL_TOKEN_SECRET", "")


# ---------------------------------------------------------------------------
# HMAC token helpers
# ---------------------------------------------------------------------------


def _make_token(slot_id: str, choice: str) -> str:
    """Generate an HMAC-SHA256 hex token for the given slot+choice."""
    if not _TOKEN_SECRET:
        logger.warning("[gchat] APPROVAL_TOKEN_SECRET not set — approval links are insecure!")
        return "no-secret"
    key = _TOKEN_SECRET.encode()
    msg = f"{slot_id}:{choice}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_token(slot_id: str, choice: str, token: str) -> bool:
    """Return True if the token matches the expected HMAC for slot+choice."""
    if not _TOKEN_SECRET:
        return True  # Dev mode — no secret set
    expected = _make_token(slot_id, choice)
    return hmac.compare_digest(expected, token)


def build_approval_url(slot_id: str, choice: str) -> str:
    """Build the Railway /approval URL with HMAC token for a choice."""
    token = _make_token(slot_id, choice)
    params = urllib.parse.urlencode({"slot": slot_id, "choice": choice, "token": token})
    return f"{APPROVAL_BASE_URL}/approval?{params}"


# ---------------------------------------------------------------------------
# Card builders
# ---------------------------------------------------------------------------


def _persona_label(persona_mode: str) -> str:
    return {
        "professional": "@swizzimatic",
        "personal": "@BigSwizzi",
        "ceo": "Jordan Ward (CEO)",
    }.get(persona_mode, persona_mode)


def _truncate(text: str, max_chars: int = 300) -> str:
    return text[:max_chars] + "…" if len(text) > max_chars else text


def _hashtag_line(hashtags: list[str]) -> str:
    if not hashtags:
        return ""
    tags = " ".join(hashtags[:6])
    return f"\n`{tags}`"


def _source_label(bundle: "ContentBundle") -> str:
    """Return a short label indicating the image source."""
    source = getattr(bundle, "image_source", "none")
    if source == "library":
        return "📷 Real"
    elif source == "ai_generated":
        return "🎨 AI"
    return "📝 Text"


def send_approval_card(bundle: "ContentBundle", webhook_url: str = "") -> bool:
    """Send a cardsV2 approval message to the SLASHERBOT space.

    Args:
        bundle: The ContentBundle to present for approval.
        webhook_url: Override the default SLASHERBOT webhook URL.

    Returns:
        True if the card was delivered (HTTP 200), False otherwise.
    """
    url = webhook_url or SLASHERBOT_WEBHOOK
    if not url:
        logger.error("[gchat] No webhook URL configured (GCHAT_WEBHOOK_SOCIAL_SLASH)")
        return False

    slot_id = bundle.slot_id
    platform_label = bundle.platform.upper()
    subreddit_note = f" • {bundle.subreddit}" if bundle.subreddit else ""
    scheduled_str = bundle.scheduled_time.strftime("%I:%M %p EST")

    option_a = bundle.option_a
    option_b = bundle.option_b
    persona_a = _persona_label(option_a.get("persona_mode", "professional"))
    persona_b = _persona_label(option_b.get("persona_mode", "ceo"))
    content_a = _truncate(option_a.get("content", ""))
    content_b = _truncate(option_b.get("content", ""))
    hashtags_a = _hashtag_line(option_a.get("hashtags", []))
    hashtags_b = _hashtag_line(option_b.get("hashtags", []))

    # Build four approval button URLs
    choices = [("A1", "✅ A+Img1"), ("A2", "✅ A+Img2"), ("B1", "✅ B+Img1"), ("B2", "✅ B+Img2")]
    regen_url = build_approval_url(slot_id, "REGEN")
    skip_url = build_approval_url(slot_id, "SKIP")

    approval_buttons = [
        {
            "text": label,
            "onClick": {"openLink": {"url": build_approval_url(slot_id, code)}},
        }
        for code, label in choices
    ]
    approval_buttons += [
        {"text": "🔄 Regen", "onClick": {"openLink": {"url": regen_url}}},
        {"text": "❌ Skip", "onClick": {"openLink": {"url": skip_url}}},
    ]

    card = {
        "cardsV2": [
            {
                "cardId": f"slasherbot-{slot_id[:8]}",
                "card": {
                    "header": {
                        "title": f"📱 {platform_label}{subreddit_note} • {scheduled_str}",
                        "subtitle": f"{bundle.pillar} • {_source_label(bundle)} • ⏰ Auto-posts in 2 hours",
                        "imageType": "CIRCLE",
                    },
                    "sections": [
                        # Option A
                        {
                            "header": f"OPTION A — {persona_a}",
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"{content_a}{hashtags_a}"
                                    }
                                }
                            ],
                        },
                        # Option B
                        {
                            "header": f"OPTION B — {persona_b}",
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"{content_b}{hashtags_b}"
                                    }
                                }
                            ],
                        },
                        # Image previews — inline renders via cardsV2 image widget
                        {
                            "header": "🖼 Images",
                            "widgets": [
                                *(
                                    [{"image": {"imageUrl": bundle.image_1_url, "altText": "Image 1 — vibrant"}}]
                                    if bundle.image_1_url
                                    else [{"textParagraph": {"text": "⚠️ Image 1 not generated"}}]
                                ),
                                *(
                                    [{"image": {"imageUrl": bundle.image_2_url, "altText": "Image 2 — minimal"}}]
                                    if bundle.image_2_url
                                    else [{"textParagraph": {"text": "⚠️ Image 2 not generated"}}]
                                ),
                            ],
                        },
                        # Approval buttons
                        {
                            "widgets": [
                                {
                                    "buttonList": {
                                        "buttons": approval_buttons
                                    }
                                }
                            ]
                        },
                    ],
                },
            }
        ]
    }

    try:
        resp = requests.post(url, json=card, timeout=10)
        if resp.status_code == 200:
            logger.info(f"[gchat] Approval card sent for slot {slot_id[:8]}")
            return True
        logger.error(f"[gchat] Webhook returned {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as exc:
        logger.error(f"[gchat] Failed to send approval card: {exc}")
        return False


def send_confirmation_card(
    bundle: "ContentBundle",
    choice: str,
    post_result: dict,
    webhook_url: str = "",
) -> bool:
    """Send a '✅ Posted!' confirmation card after successful approval posting."""
    url = webhook_url or SLASHERBOT_WEBHOOK
    if not url:
        return False

    platform_label = bundle.platform.upper()
    option_key = "option_a" if choice.startswith("A") else "option_b"
    content_preview = _truncate(getattr(bundle, option_key, {}).get("content", ""), 150)
    post_id = post_result.get("post_id", "")
    status = post_result.get("status", "unknown")
    image_url = bundle.image_1_url if choice.endswith("1") else bundle.image_2_url

    card = {
        "cardsV2": [
            {
                "cardId": f"slasherbot-confirm-{bundle.slot_id[:8]}",
                "card": {
                    "header": {
                        "title": f"✅ Posted to {platform_label}!",
                        "subtitle": f"Choice: {choice} • Status: {status}",
                    },
                    "sections": [
                        {
                            "widgets": [
                                {"textParagraph": {"text": content_preview}},
                            ]
                        }
                    ]
                    + (
                        [{"widgets": [{"image": {"imageUrl": image_url, "altText": f"Posted image ({choice})"}}]}]
                        if image_url
                        else []
                    )
                    + (
                        [{"widgets": [{"textParagraph": {"text": f"Post ID: `{post_id}`"}}]}]
                        if post_id
                        else []
                    ),
                },
            }
        ]
    }

    try:
        resp = requests.post(url, json=card, timeout=10)
        return resp.status_code == 200
    except Exception as exc:
        logger.error(f"[gchat] Failed to send confirmation card: {exc}")
        return False


def send_auto_post_card(bundle: "ContentBundle", webhook_url: str = "") -> bool:
    """Send a notification card when a slot is auto-posted after the 2-hour TTL."""
    url = webhook_url or SLASHERBOT_WEBHOOK
    if not url:
        return False

    platform_label = bundle.platform.upper()
    content_preview = _truncate(bundle.option_a.get("content", ""), 150)

    card = {
        "cardsV2": [
            {
                "cardId": f"slasherbot-auto-{bundle.slot_id[:8]}",
                "card": {
                    "header": {
                        "title": f"⏰ Auto-posted to {platform_label}",
                        "subtitle": "No approval received — posted Option A + Image 1",
                    },
                    "sections": [
                        {
                            "widgets": [
                                {"textParagraph": {"text": content_preview}},
                            ]
                        }
                    ]
                    + (
                        [{"widgets": [{"image": {"imageUrl": bundle.image_1_url, "altText": "Auto-posted image"}}]}]
                        if bundle.image_1_url
                        else []
                    ),
                },
            }
        ]
    }

    try:
        resp = requests.post(url, json=card, timeout=10)
        return resp.status_code == 200
    except Exception as exc:
        logger.error(f"[gchat] Failed to send auto-post card: {exc}")
        return False


def send_error_card(platform: str, error: str, webhook_url: str = "") -> bool:
    """Send a lightweight error notification to SLASHERBOT."""
    url = webhook_url or SLASHERBOT_WEBHOOK
    if not url:
        return False

    payload = {
        "text": f"⚠️ *SLASHERBOT error* — {platform.upper()}: `{error[:200]}`"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception:
        return False
