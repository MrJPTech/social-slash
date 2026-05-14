"""Tests for DailyScheduler — job registration, trigger, auto-post check."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest


def _make_bundle(slot_id="slot-test-001", posted=False, hours_to_expire=2):
    from lib.scheduler.content_pipeline import ContentBundle

    now = datetime.now(UTC)
    return ContentBundle(
        slot_id=slot_id,
        platform="twitter",
        subreddit=None,
        pillar="building in public",
        topic="AI tools for developers",
        option_a={"content": "Option A text", "hashtags": [], "persona_mode": "professional"},
        option_b={"content": "Option B text", "hashtags": [], "persona_mode": "ceo"},
        image_1_url="https://media.getlate.dev/temp/img1.jpg",
        image_2_url="https://media.getlate.dev/temp/img2.jpg",
        scheduled_time=now,
        expires_at=now + timedelta(hours=hours_to_expire),
        posted=posted,
    )


class TestSchedulerInit:
    @patch("lib.scheduler.daily_scheduler.DailyScheduler.__init__", return_value=None)
    def test_init_does_not_raise(self, mock_init):
        from lib.scheduler.daily_scheduler import DailyScheduler

        sched = DailyScheduler()
        assert sched is not None


class TestJobRegistration:
    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_all_platform_jobs_registered(self, MockScheduler):
        mock_sched = MagicMock()
        MockScheduler.return_value = mock_sched

        from lib.scheduler.daily_scheduler import POSTING_SCHEDULE, DailyScheduler

        sched = DailyScheduler.__new__(DailyScheduler)
        sched.scheduler = mock_sched
        sched.pipeline = MagicMock()
        sched.store = MagicMock()
        sched._tz = "America/New_York"

        sched._register_jobs()

        expected_job_count = sum(len(slots) for slots in POSTING_SCHEDULE.values())
        # Each add_job call should have been made once per slot
        assert mock_sched.add_job.call_count == expected_job_count

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_twitter_jobs_registered(self, MockScheduler):
        from lib.scheduler.daily_scheduler import POSTING_SCHEDULE

        assert "twitter" in POSTING_SCHEDULE
        assert len(POSTING_SCHEDULE["twitter"]) == 4  # 4 slots per day


class TestTriggerSlot:
    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_trigger_slot_calls_run_slot(self, MockScheduler):
        mock_sched = MagicMock()
        MockScheduler.return_value = mock_sched

        from lib.scheduler.daily_scheduler import DailyScheduler

        sched = DailyScheduler.__new__(DailyScheduler)
        sched.scheduler = mock_sched
        sched.pipeline = MagicMock()
        sched.store = MagicMock()
        sched._tz = "America/New_York"

        bundle = _make_bundle()
        sched.pipeline.generate_bundle.return_value = bundle
        sched.store.save = MagicMock()

        with patch("lib.scheduler.gchat_cards.send_approval_card", return_value=True):
            slot_id = sched._run_slot("twitter", "09:00", "professional")

        assert slot_id == bundle.slot_id
        sched.pipeline.generate_bundle.assert_called_once()
        sched.store.save.assert_called_once_with(bundle)

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_trigger_slot_returns_none_on_pipeline_failure(self, MockScheduler):
        mock_sched = MagicMock()
        MockScheduler.return_value = mock_sched

        from lib.scheduler.daily_scheduler import DailyScheduler

        sched = DailyScheduler.__new__(DailyScheduler)
        sched.scheduler = mock_sched
        sched.pipeline = MagicMock()
        sched.store = MagicMock()
        sched._tz = "America/New_York"

        sched.pipeline.generate_bundle.side_effect = Exception("Pipeline error")

        with patch("lib.scheduler.gchat_cards.send_error_card", return_value=True):
            result = sched._run_slot("twitter", "09:00", "professional")

        assert result is None


class TestAutoPostCheck:
    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_auto_post_fires_for_expired_bundles(self, MockScheduler):
        mock_sched = MagicMock()
        MockScheduler.return_value = mock_sched

        from lib.scheduler.daily_scheduler import DailyScheduler

        sched = DailyScheduler.__new__(DailyScheduler)
        sched.scheduler = mock_sched
        sched.pipeline = MagicMock()
        sched.store = MagicMock()
        sched._tz = "America/New_York"

        expired_bundle = _make_bundle(slot_id="exp-001", hours_to_expire=-1)
        sched.store.get_pending_expired.return_value = [expired_bundle]
        sched._do_post = MagicMock(return_value={})

        with patch("lib.scheduler.gchat_cards.send_auto_post_card", return_value=True):
            sched._auto_post_check()

        sched._do_post.assert_called_once_with(expired_bundle, choice="A1")

    @patch("apscheduler.schedulers.background.BackgroundScheduler")
    def test_auto_post_check_no_expired_bundles(self, MockScheduler):
        mock_sched = MagicMock()
        MockScheduler.return_value = mock_sched

        from lib.scheduler.daily_scheduler import DailyScheduler

        sched = DailyScheduler.__new__(DailyScheduler)
        sched.scheduler = mock_sched
        sched.pipeline = MagicMock()
        sched.store = MagicMock()
        sched._tz = "America/New_York"

        sched.store.get_pending_expired.return_value = []
        sched._do_post = MagicMock()
        sched._auto_post_check()

        sched._do_post.assert_not_called()


class TestPillarsLoader:
    def test_get_today_pillar_returns_string(self):
        from lib.scheduler.daily_scheduler import _get_today_pillar

        pillar = _get_today_pillar()
        assert isinstance(pillar, str)
        assert len(pillar) > 0

    def test_get_next_subreddit_returns_string(self, tmp_path):
        import json as _json

        pillars_data = {
            "subreddit_rotation": ["r/test1", "r/test2"],
            "subreddit_index": 0,
        }
        path = tmp_path / "weekly_pillars.json"
        path.write_text(_json.dumps(pillars_data))
        with patch("lib.scheduler.daily_scheduler._PILLARS_PATH", str(path)):
            from lib.scheduler.daily_scheduler import _get_next_subreddit

            sub = _get_next_subreddit()
        assert sub in ["r/test1", "r/test2"]

    def test_subreddit_index_increments(self, tmp_path):
        import json as _json

        pillars_data = {
            "subreddit_rotation": ["r/a", "r/b", "r/c"],
            "subreddit_index": 0,
        }
        path = tmp_path / "weekly_pillars.json"
        path.write_text(_json.dumps(pillars_data))
        with patch("lib.scheduler.daily_scheduler._PILLARS_PATH", str(path)):
            from lib.scheduler.daily_scheduler import _get_next_subreddit

            s1 = _get_next_subreddit()
            s2 = _get_next_subreddit()
        assert s1 != s2
