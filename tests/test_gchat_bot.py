"""Tests for SlasherbotChatHandler — event routing, commands, helpers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Pre-import lib.mcp so it's registered as an attribute on the `lib` module
# before other test files import lib.posting.* (which doesn't trigger lib.mcp
# registration, causing patch("lib.mcp._client_helpers...") to fail).
import lib.mcp._client_helpers  # noqa: F401

from lib.scheduler.gchat_bot import (
    SlasherbotChatHandler,
    _COMMAND_ID_MAP,
    _extract_flag,
    _strip_flags,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_message_event(text: str) -> dict:
    return {
        "type": "MESSAGE",
        "message": {"argumentText": f" {text}", "text": f"@SLASHERBOT {text}"},
    }


def _make_bundle(slot_id: str = "aabbccdd-1234-5678-abcd-ef0123456789", posted: bool = False):
    from lib.scheduler.content_pipeline import ContentBundle
    now = datetime.now(timezone.utc)
    return ContentBundle(
        slot_id=slot_id,
        platform="twitter",
        subreddit=None,
        pillar="AI tools",
        topic="AI is changing everything",
        option_a={"content": "Option A content here", "hashtags": ["#AI"], "persona_mode": "professional"},
        option_b={"content": "Option B CEO content", "hashtags": ["#startup"], "persona_mode": "ceo"},
        image_1_url="https://media.getlate.dev/temp/img1.jpg",
        image_2_url="https://media.getlate.dev/temp/img2.jpg",
        scheduled_time=now,
        expires_at=now + timedelta(hours=2),
        posted=posted,
    )


# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------


class TestExtractFlag:
    def test_equals_style(self):
        assert _extract_flag("write topic --platform=linkedin", "platform") == "linkedin"

    def test_space_style(self):
        assert _extract_flag("write topic --platform linkedin", "platform") == "linkedin"

    def test_missing_flag_returns_none(self):
        assert _extract_flag("write some topic", "platform") is None

    def test_multiple_flags(self):
        assert _extract_flag("write topic --platform=twitter --persona=ceo", "persona") == "ceo"


class TestStripFlags:
    def test_strips_equals_style(self):
        result = _strip_flags("my topic --platform=twitter")
        assert "--platform" not in result
        assert "my topic" in result

    def test_strips_space_style(self):
        result = _strip_flags("my topic --persona professional")
        assert "--persona" not in result

    def test_clean_text_unchanged(self):
        result = _strip_flags("just a clean topic")
        assert result == "just a clean topic"


# ---------------------------------------------------------------------------
# Event routing
# ---------------------------------------------------------------------------


class TestHandleEvent:
    def test_added_to_space_returns_welcome(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({"type": "ADDED_TO_SPACE"})
        assert "text" in resp
        assert "SLASHERBOT" in resp["text"]

    def test_removed_from_space_returns_empty(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({"type": "REMOVED_FROM_SPACE"})
        assert resp == {}

    def test_unknown_type_returns_empty(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({"type": "COMPLETELY_UNKNOWN"})
        assert resp == {}

    def test_message_routes_help(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event(_make_message_event("help"))
        assert "text" in resp
        assert "status" in resp["text"].lower()

    def test_empty_message_returns_help(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({"type": "MESSAGE", "message": {"argumentText": ""}})
        assert "text" in resp

    def test_card_clicked_unknown_action(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({
            "type": "CARD_CLICKED",
            "action": {"actionMethodName": "noop", "parameters": []},
        })
        assert "text" in resp

    def test_empty_event_type_returns_empty(self):
        """Google endpoint-verification pings arrive with empty/missing type — return {}."""
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({"type": ""})
        assert resp == {}

    def test_missing_event_type_returns_empty(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({})
        assert resp == {}

    def test_empty_event_type_with_slash_command_routes(self):
        """Slash commands arriving without a MESSAGE type should still route."""
        handler = SlasherbotChatHandler()
        resp = handler.handle_event({
            "type": "",
            "slashCommand": {"commandId": 1},  # status
            "message": {"argumentText": ""},
        })
        assert "text" in resp
        assert "Status" in resp["text"] or "Disabled" in resp["text"] or "Scheduler" in resp["text"]


# ---------------------------------------------------------------------------
# Slash command commandId routing
# ---------------------------------------------------------------------------


class TestCommandIdMap:
    def test_map_has_eight_entries(self):
        assert len(_COMMAND_ID_MAP) == 8

    def test_status_is_id_1(self):
        assert _COMMAND_ID_MAP[1] == "status"

    def test_help_is_id_2(self):
        assert _COMMAND_ID_MAP[2] == "help"

    def test_all_ids_map_to_known_commands(self):
        known = {"status", "help", "pending", "approve", "skip", "trigger", "write", "post"}
        assert set(_COMMAND_ID_MAP.values()) == known


class TestSlashCommandByCommandId:
    def _slash_event(self, command_id: int, args: str = "") -> dict:
        """Build a MESSAGE event containing a slashCommand with commandId only."""
        return {
            "type": "MESSAGE",
            "message": {
                "slashCommand": {"commandId": command_id},
                "argumentText": args,
                "text": f"/{_COMMAND_ID_MAP.get(command_id, '?')} {args}",
            },
        }

    def test_status_by_command_id(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event(self._slash_event(1))
        assert "Status" in resp["text"] or "Scheduler" in resp["text"]

    def test_help_by_command_id(self):
        handler = SlasherbotChatHandler()
        resp = handler.handle_event(self._slash_event(2))
        assert "status" in resp["text"].lower()
        assert "approve" in resp["text"].lower()

    def test_pending_by_command_id(self):
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_pending_active", return_value=[]):
            resp = handler.handle_event(self._slash_event(3))
        assert "text" in resp

    def test_unknown_command_id_falls_back_to_freetext(self):
        """An unmapped commandId should fall through to freetext (write) not crash."""
        handler = SlasherbotChatHandler()
        # commandId=99 is not in the map — route text should be empty → help
        resp = handler.handle_event(self._slash_event(99))
        assert "text" in resp

    def test_slash_command_by_command_name_still_works(self):
        """commandName field (if present) should still route correctly."""
        handler = SlasherbotChatHandler()
        event = {
            "type": "MESSAGE",
            "message": {
                "slashCommand": {"commandName": "/help", "commandId": 2},
                "argumentText": "",
            },
        }
        resp = handler.handle_event(event)
        assert "status" in resp["text"].lower()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


class TestCmdHelp:
    def test_returns_commands_list(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_help("")
        assert "status" in resp["text"]
        assert "pending" in resp["text"]
        assert "approve" in resp["text"]


class TestCmdStatus:
    def test_no_scheduler_shows_disabled(self):
        handler = SlasherbotChatHandler(scheduler=None)
        with patch.dict("os.environ", {"SCHEDULER_ENABLED": "false"}):
            resp = handler._cmd_status("")
        assert "text" in resp
        assert "Disabled" in resp["text"] or "disabled" in resp["text"].lower()

    def test_running_scheduler_shows_running(self):
        mock_sched = MagicMock()
        mock_sched.scheduler.running = True
        mock_sched.get_status.return_value = {
            "jobs": [{"platform": "twitter", "next_run": "09:00 AM EST"}]
        }
        handler = SlasherbotChatHandler(scheduler=mock_sched)
        with patch("lib.scheduler.approval_store.ApprovalStore.get_pending_active", return_value=[]):
            with patch("lib.scheduler.approval_store.ApprovalStore.get_pending_expired", return_value=[]):
                resp = handler._cmd_status("")
        assert "Running" in resp["text"] or "🟢" in resp["text"]


class TestCmdPending:
    def test_empty_store_says_no_pending(self):
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_pending_active", return_value=[]):
            resp = handler._cmd_pending("")
        assert "No pending" in resp["text"] or "✅" in resp["text"]

    def test_shows_bundle_details(self):
        bundle = _make_bundle()
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_pending_active", return_value=[bundle]):
            resp = handler._cmd_pending("")
        text = resp["text"]
        assert "TWITTER" in text.upper()
        assert "aabbccdd" in text.lower()  # slot_id prefix

    def test_shows_approve_hint(self):
        bundle = _make_bundle()
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_pending_active", return_value=[bundle]):
            resp = handler._cmd_pending("")
        assert "approve" in resp["text"]


class TestCmdApprove:
    def test_missing_args_returns_usage(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_approve("")
        assert "Usage" in resp["text"]

    def test_missing_choice_returns_usage(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_approve("abc12345")
        assert "Usage" in resp["text"]

    def test_invalid_choice_rejected(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_approve("abc12345 X9")
        assert "Invalid choice" in resp["text"] or "❌" in resp["text"]

    def test_slot_not_found_returns_error(self):
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_by_prefix", return_value=None):
            resp = handler._cmd_approve("nonexistent A1")
        assert "not found" in resp["text"] or "❌" in resp["text"]

    def test_already_posted_returns_warning(self):
        bundle = _make_bundle(posted=True)
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_by_prefix", return_value=bundle):
            resp = handler._cmd_approve("aabbccdd A1")
        assert "already handled" in resp["text"] or "⚠️" in resp["text"]

    def test_valid_approve_calls_poster(self):
        bundle = _make_bundle()
        mock_result = {"status": "success", "post_id": "tweet123"}
        handler = SlasherbotChatHandler()

        with patch("lib.scheduler.approval_store.ApprovalStore.get_by_prefix", return_value=bundle):
            with patch("lib.scheduler.approval_store.ApprovalStore.mark_posted") as mock_mark:
                with patch("lib.mcp._client_helpers.suppress_stdout"):
                    with patch("lib.posting.poster.Poster.post", return_value=mock_result):
                        with patch("lib.scheduler.gchat_cards.send_confirmation_card"):
                            resp = handler._cmd_approve("aabbccdd A1")

        assert "✅" in resp["text"]
        assert "TWITTER" in resp["text"]


class TestCmdSkip:
    def test_missing_args_returns_usage(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_skip("")
        assert "Usage" in resp["text"]

    def test_slot_not_found(self):
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_by_prefix", return_value=None):
            resp = handler._cmd_skip("unknown99")
        assert "not found" in resp["text"] or "❌" in resp["text"]

    def test_skips_unposted_bundle(self):
        bundle = _make_bundle()
        handler = SlasherbotChatHandler()
        with patch("lib.scheduler.approval_store.ApprovalStore.get_by_prefix", return_value=bundle):
            with patch("lib.scheduler.approval_store.ApprovalStore.mark_posted") as mock_mark:
                resp = handler._cmd_skip("aabbccdd")
        assert "⏭" in resp["text"] or "skipped" in resp["text"].lower()
        mock_mark.assert_called_once_with(bundle.slot_id, "SKIP")


class TestCmdTrigger:
    def test_no_scheduler_returns_warning(self):
        handler = SlasherbotChatHandler(scheduler=None)
        resp = handler._cmd_trigger("")
        assert "Scheduler not running" in resp["text"] or "⚠️" in resp["text"]

    def test_invalid_platform_rejected(self):
        mock_sched = MagicMock()
        handler = SlasherbotChatHandler(scheduler=mock_sched)
        resp = handler._cmd_trigger("myspace")
        assert "Unknown platform" in resp["text"] or "❌" in resp["text"]

    def test_valid_trigger_calls_scheduler(self):
        mock_sched = MagicMock()
        mock_sched.trigger_slot.return_value = "aabbccdd-1234-5678-abcd-ef0123456789"
        handler = SlasherbotChatHandler(scheduler=mock_sched)
        resp = handler._cmd_trigger("twitter")
        assert "🚀" in resp["text"] or "triggered" in resp["text"].lower()
        mock_sched.trigger_slot.assert_called_once_with("twitter", "manual", "professional")

    def test_default_platform_is_twitter(self):
        mock_sched = MagicMock()
        mock_sched.trigger_slot.return_value = "slot-id"
        handler = SlasherbotChatHandler(scheduler=mock_sched)
        handler._cmd_trigger("")
        call_args = mock_sched.trigger_slot.call_args
        assert call_args[0][0] == "twitter"


class TestCmdWrite:
    def test_no_args_returns_usage(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_write("")
        assert "Usage" in resp["text"]

    def test_writes_content_with_mocked_agent(self):
        mock_result = {
            "content": "AI is transforming how developers work every day.",
            "hashtags": ["#AI", "#devlife"],
        }
        handler = SlasherbotChatHandler()
        with patch("lib.mcp._client_helpers.suppress_stdout"):
            with patch("lib.mcp._client_helpers.build_agent_config", return_value={}):
                with patch("lib.agents.writing_agent.WritingAgent") as MockAgent:
                    MockAgent.return_value.generate_post.return_value = mock_result
                    resp = handler._cmd_write("AI tools")

        assert "text" in resp
        assert "AI is transforming" in resp["text"]

    def test_platform_flag_parsed(self):
        mock_result = {"content": "Content for LinkedIn", "hashtags": []}
        handler = SlasherbotChatHandler()
        with patch("lib.mcp._client_helpers.suppress_stdout"):
            with patch("lib.mcp._client_helpers.build_agent_config", return_value={}):
                with patch("lib.agents.writing_agent.WritingAgent") as MockAgent:
                    MockAgent.return_value.generate_post.return_value = mock_result
                    resp = handler._cmd_write("leadership tips --platform=linkedin")

        assert "LINKEDIN" in resp["text"]

    def test_handles_string_result(self):
        """Agent returning a plain string (markdown) should be handled gracefully."""
        handler = SlasherbotChatHandler()
        with patch("lib.mcp._client_helpers.suppress_stdout"):
            with patch("lib.mcp._client_helpers.build_agent_config", return_value={}):
                with patch("lib.agents.writing_agent.WritingAgent") as MockAgent:
                    MockAgent.return_value.generate_post.return_value = "Plain markdown content"
                    resp = handler._cmd_write("topic")

        assert "Plain markdown content" in resp["text"]


class TestCmdPost:
    def test_no_content_returns_usage(self):
        handler = SlasherbotChatHandler()
        resp = handler._cmd_post("--platform=twitter")
        assert "Usage" in resp["text"]

    def test_posts_with_mocked_poster(self):
        handler = SlasherbotChatHandler()
        mock_result = {"status": "success", "post_id": "t123"}
        with patch("lib.mcp._client_helpers.suppress_stdout"):
            with patch("lib.posting.poster.Poster.post", return_value=mock_result):
                resp = handler._cmd_post("My test post content --platform=twitter")

        assert "✅" in resp["text"]
        assert "TWITTER" in resp["text"]


class TestCmdFreetext:
    def test_routes_to_write(self):
        handler = SlasherbotChatHandler()
        mock_result = {"content": "Generated from freetext", "hashtags": []}
        with patch("lib.mcp._client_helpers.suppress_stdout"):
            with patch("lib.mcp._client_helpers.build_agent_config", return_value={}):
                with patch("lib.agents.writing_agent.WritingAgent") as MockAgent:
                    MockAgent.return_value.generate_post.return_value = mock_result
                    resp = handler._cmd_freetext("AI productivity hacks")

        assert "Generated from freetext" in resp["text"]
