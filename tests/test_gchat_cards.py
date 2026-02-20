"""Tests for GChatCards — cardsV2 structure, HMAC tokens, button URLs."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from lib.scheduler.content_pipeline import ContentBundle


def _make_bundle(slot_id="slot-abc123"):
    now = datetime.now(timezone.utc)
    return ContentBundle(
        slot_id=slot_id,
        platform="twitter",
        subreddit=None,
        pillar="AI tools and automation",
        topic="How AI is reshaping developer workflows",
        option_a={
            "content": "AI just changed how I ship code. Here's what I learned...",
            "hashtags": ["#AI", "#buildinpublic", "#devlife"],
            "persona_mode": "professional",
        },
        option_b={
            "content": "Most devs still code manually. The early AI adopters are already 10x ahead.",
            "hashtags": ["#startup", "#AItools"],
            "persona_mode": "ceo",
        },
        image_1_url="https://media.getlate.dev/temp/img1.jpg",
        image_2_url="https://media.getlate.dev/temp/img2.jpg",
        scheduled_time=now,
        expires_at=now + timedelta(hours=2),
    )


class TestHmacTokens:
    def test_make_and_verify_token(self):
        with patch("lib.scheduler.gchat_cards._TOKEN_SECRET", "test-secret-32-chars-abcdefghij"):
            from lib.scheduler.gchat_cards import _make_token, verify_token
            token = _make_token("slot-123", "A1")
            assert verify_token("slot-123", "A1", token)

    def test_wrong_choice_fails_verification(self):
        with patch("lib.scheduler.gchat_cards._TOKEN_SECRET", "test-secret-32-chars-abcdefghij"):
            from lib.scheduler.gchat_cards import _make_token, verify_token
            token = _make_token("slot-123", "A1")
            assert not verify_token("slot-123", "B2", token)

    def test_wrong_slot_fails_verification(self):
        with patch("lib.scheduler.gchat_cards._TOKEN_SECRET", "test-secret-32-chars-abcdefghij"):
            from lib.scheduler.gchat_cards import _make_token, verify_token
            token = _make_token("slot-123", "A1")
            assert not verify_token("slot-xyz", "A1", token)

    def test_no_secret_always_passes(self):
        with patch("lib.scheduler.gchat_cards._TOKEN_SECRET", ""):
            from lib.scheduler.gchat_cards import verify_token
            assert verify_token("anything", "A1", "garbage-token")


class TestApprovalUrl:
    def test_url_contains_slot_and_choice(self):
        with patch("lib.scheduler.gchat_cards._TOKEN_SECRET", "test-secret"):
            with patch("lib.scheduler.gchat_cards.APPROVAL_BASE_URL", "https://example.com"):
                from lib.scheduler.gchat_cards import build_approval_url
                url = build_approval_url("slot-123", "A1")
                assert "slot=slot-123" in url
                assert "choice=A1" in url
                assert url.startswith("https://example.com/approval")

    def test_url_contains_token_param(self):
        with patch("lib.scheduler.gchat_cards._TOKEN_SECRET", "test-secret"):
            with patch("lib.scheduler.gchat_cards.APPROVAL_BASE_URL", "https://example.com"):
                from lib.scheduler.gchat_cards import build_approval_url
                url = build_approval_url("slot-123", "A1")
                assert "token=" in url


class TestSendApprovalCard:
    def test_sends_post_request_to_webhook(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp) as mock_post:
            from lib.scheduler.gchat_cards import send_approval_card
            result = send_approval_card(bundle, "https://chat.googleapis.com/v1/spaces/FAKE/messages")
        assert result is True
        mock_post.assert_called_once()

    def test_payload_is_cardsv2(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp) as mock_post:
            from lib.scheduler.gchat_cards import send_approval_card
            send_approval_card(bundle, "https://chat.googleapis.com/v1/spaces/FAKE/messages")
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1].get("json") or call_kwargs[0][1]
        assert "cardsV2" in payload

    def test_card_has_all_four_approval_buttons(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp) as mock_post:
            from lib.scheduler.gchat_cards import send_approval_card
            send_approval_card(bundle, "https://chat.googleapis.com/v1/spaces/FAKE/messages")
        payload = mock_post.call_args[1]["json"]
        card = payload["cardsV2"][0]["card"]
        # Find the button section
        buttons = []
        for section in card["sections"]:
            for widget in section.get("widgets", []):
                if "buttonList" in widget:
                    buttons.extend(widget["buttonList"]["buttons"])
        button_texts = [b["text"] for b in buttons]
        assert "✅ A+Img1" in button_texts
        assert "✅ A+Img2" in button_texts
        assert "✅ B+Img1" in button_texts
        assert "✅ B+Img2" in button_texts

    def test_card_header_contains_platform(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp) as mock_post:
            from lib.scheduler.gchat_cards import send_approval_card
            send_approval_card(bundle, "https://chat.googleapis.com/v1/spaces/FAKE/messages")
        payload = mock_post.call_args[1]["json"]
        header_title = payload["cardsV2"][0]["card"]["header"]["title"]
        assert "TWITTER" in header_title

    def test_returns_false_when_no_webhook(self):
        bundle = _make_bundle()
        with patch("lib.scheduler.gchat_cards.SLASHERBOT_WEBHOOK", ""):
            from lib.scheduler.gchat_cards import send_approval_card
            result = send_approval_card(bundle, "")
        assert result is False

    def test_returns_false_on_http_error(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        with patch("requests.post", return_value=mock_resp):
            from lib.scheduler.gchat_cards import send_approval_card
            result = send_approval_card(bundle, "https://chat.googleapis.com/v1/spaces/FAKE/messages")
        assert result is False


class TestConfirmationCard:
    def test_confirmation_card_sent(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp) as mock_post:
            from lib.scheduler.gchat_cards import send_confirmation_card
            result = send_confirmation_card(bundle, "A1", {"status": "success"}, "https://webhook.url")
        assert result is True
        payload = mock_post.call_args[1]["json"]
        assert "cardsV2" in payload
        header_title = payload["cardsV2"][0]["card"]["header"]["title"]
        assert "TWITTER" in header_title


class TestAutoPostCard:
    def test_auto_post_card_sent(self):
        bundle = _make_bundle()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp) as mock_post:
            from lib.scheduler.gchat_cards import send_auto_post_card
            result = send_auto_post_card(bundle, "https://webhook.url")
        assert result is True
        payload = mock_post.call_args[1]["json"]
        header_title = payload["cardsV2"][0]["card"]["header"]["title"]
        assert "Auto-posted" in header_title
