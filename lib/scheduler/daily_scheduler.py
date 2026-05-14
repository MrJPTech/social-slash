"""Daily posting scheduler for SLASHERBOT.

APScheduler-backed system that:
  1. Fires per-platform jobs according to POSTING_SCHEDULE
  2. Generates content bundles via ContentPipeline
  3. Sends approval cards to Google Chat
  4. Auto-posts after 2-hour TTL if no human responds

Run as part of the MCP server by setting SCHEDULER_ENABLED=true.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# (time_EST, persona_rotation)
POSTING_SCHEDULE: dict[str, list[tuple[str, str]]] = {
    "twitter": [
        ("09:00", "professional"),
        ("12:00", "personal"),
        ("17:00", "ceo"),
        ("21:00", "professional"),
    ],
    "linkedin": [("08:00", "professional"), ("12:00", "ceo"), ("17:00", "professional")],
    "instagram": [("11:00", "personal"), ("19:00", "professional")],
    "tiktok": [("10:00", "personal"), ("21:00", "ceo")],
    "facebook": [("09:00", "professional"), ("13:00", "ceo"), ("19:00", "personal")],
    "threads": [("11:00", "personal"), ("17:00", "ceo")],
    "reddit": [("10:00", "professional"), ("14:00", "ceo"), ("20:00", "personal")],
    "bluesky": [("12:00", "professional"), ("18:00", "personal")],
    "google_business": [("09:00", "professional")],
}

_PILLARS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "weekly_pillars.json")
_PILLARS_PATH = os.path.normpath(_PILLARS_PATH)

SLASHERBOT_WEBHOOK = os.getenv("GCHAT_WEBHOOK_SOCIAL_SLASH", "")


def _load_pillars() -> dict:
    try:
        with open(_PILLARS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        logger.warning(f"[scheduler] Could not load weekly_pillars.json: {exc}")
        return {
            "day_assignments": {},
            "subreddit_rotation": ["r/entrepreneur"],
            "subreddit_index": 0,
        }


def _get_today_pillar() -> str:
    data = _load_pillars()
    day_name = datetime.now(UTC).strftime("%A").lower()
    return data.get("day_assignments", {}).get(day_name, "building in public")


def _get_next_subreddit() -> str:
    """Return the next subreddit in rotation and increment the index atomically."""
    data = _load_pillars()
    rotation: list[str] = data.get("subreddit_rotation", ["r/entrepreneur"])
    idx: int = data.get("subreddit_index", 0) % len(rotation)
    subreddit = rotation[idx]

    # Persist the incremented index
    try:
        data["subreddit_index"] = (idx + 1) % len(rotation)
        with open(_PILLARS_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
    except Exception as exc:
        logger.warning(f"[scheduler] Could not update subreddit_index: {exc}")

    return subreddit


class DailyScheduler:
    """APScheduler wrapper for automated daily posting."""

    def __init__(self) -> None:
        from apscheduler.schedulers.background import BackgroundScheduler

        tz = os.getenv("SCHEDULER_TIMEZONE", "America/New_York")
        self.scheduler = BackgroundScheduler(timezone=tz)
        self._tz = tz

        from lib.scheduler.approval_store import ApprovalStore
        from lib.scheduler.content_pipeline import ContentPipeline

        self.pipeline = ContentPipeline()
        self.store = ApprovalStore()

    def start(self) -> None:
        """Register all platform jobs and start the scheduler."""
        self._register_jobs()

        # Auto-post checker: every 5 minutes
        self.scheduler.add_job(
            self._auto_post_check,
            trigger="interval",
            minutes=5,
            id="auto_post_check",
            replace_existing=True,
        )

        # Library scan: every 30 minutes (ingest new uploads from Supabase)
        self.scheduler.add_job(
            self._scan_media_library,
            trigger="interval",
            minutes=30,
            id="library_scan",
            replace_existing=True,
        )

        # Local folder sync: every 15 minutes (iCloud/Desktop → Supabase)
        # Only registers if at least one sync folder actually exists on disk.
        if self._local_folders_exist():
            self.scheduler.add_job(
                self._sync_local_folders,
                trigger="interval",
                minutes=15,
                id="local_folder_sync",
                replace_existing=True,
            )
            logger.info("[scheduler] Local folder sync enabled (15-min interval)")

        # Daily DB cleanup: every day at 03:00
        self.scheduler.add_job(
            self._cleanup_old_records,
            trigger="cron",
            hour=3,
            minute=0,
            id="db_cleanup",
            replace_existing=True,
        )

        self.scheduler.start()
        total = sum(len(slots) for slots in POSTING_SCHEDULE.values())
        logger.info(
            f"[scheduler] Started — {total} daily slots across {len(POSTING_SCHEDULE)} platforms"
        )

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("[scheduler] Stopped")

    def trigger_slot(
        self, platform: str, time_label: str = "manual", persona: str = "professional"
    ) -> str | None:
        """Manually trigger a single content slot. Returns slot_id or None."""
        try:
            return self._run_slot(platform, time_label, persona)
        except Exception as exc:
            logger.error(f"[scheduler] Manual trigger failed for {platform}: {exc}")
            return None

    def get_status(self) -> dict:
        """Return next run times for all registered jobs (JSON-serialisable)."""
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append(
                {
                    "id": job.id,
                    "next_run": next_run.isoformat() if next_run else None,
                }
            )
        return {"running": self.scheduler.running, "jobs": jobs}

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _register_jobs(self) -> None:
        for platform, slots in POSTING_SCHEDULE.items():
            for time_str, persona in slots:
                hour, minute = map(int, time_str.split(":"))
                job_id = f"{platform}_{time_str.replace(':', '')}"
                self.scheduler.add_job(
                    self._run_slot,
                    trigger="cron",
                    hour=hour,
                    minute=minute,
                    kwargs={"platform": platform, "time_label": time_str, "base_persona": persona},
                    id=job_id,
                    replace_existing=True,
                )
        logger.info(
            f"[scheduler] Registered {sum(len(s) for s in POSTING_SCHEDULE.values())} cron jobs"
        )

    def _run_slot(self, platform: str, time_label: str, base_persona: str) -> str | None:
        """Generate a bundle, save it, and send a Google Chat approval card."""
        pillar = _get_today_pillar()
        subreddit = _get_next_subreddit() if platform == "reddit" else None

        logger.info(f"[scheduler] Running slot: {platform} @ {time_label} | {pillar}")

        try:
            bundle = self.pipeline.generate_bundle(
                platform=platform,
                time_slot=time_label,
                pillar=pillar,
                base_persona=base_persona,
                subreddit=subreddit,
            )
        except Exception as exc:
            logger.error(f"[scheduler] Pipeline failed for {platform}: {exc}")
            from lib.scheduler.gchat_cards import send_error_card

            send_error_card(platform, str(exc), SLASHERBOT_WEBHOOK)
            return None

        if bundle is None:
            # Pipeline returns None when media-required platform has no library images
            logger.warning(f"[scheduler] Skipping slot for {platform} — no media available")
            return None

        self.store.save(bundle)

        from lib.scheduler.gchat_cards import send_approval_card

        sent = send_approval_card(bundle, SLASHERBOT_WEBHOOK)
        if not sent:
            logger.warning(f"[scheduler] Approval card not delivered for slot {bundle.slot_id[:8]}")

        logger.info(
            f"[scheduler] Slot {bundle.slot_id[:8]} saved — expires {bundle.expires_at.isoformat()}"
        )
        return bundle.slot_id

    def _auto_post_check(self) -> None:
        """Find expired, unposted bundles and post Option A + Image 1."""
        expired = self.store.get_pending_expired()
        if not expired:
            return

        logger.info(f"[scheduler] Auto-posting {len(expired)} expired bundle(s)")
        for bundle in expired:
            try:
                self._do_post(bundle, choice="A1")
                from lib.scheduler.gchat_cards import send_auto_post_card

                send_auto_post_card(bundle, SLASHERBOT_WEBHOOK)
                logger.info(
                    f"[scheduler] Auto-posted slot {bundle.slot_id[:8]} → {bundle.platform}"
                )
            except Exception as exc:
                logger.error(f"[scheduler] Auto-post failed for {bundle.slot_id[:8]}: {exc}")
                from lib.scheduler.gchat_cards import send_error_card

                send_error_card(bundle.platform, f"Auto-post failed: {exc}", SLASHERBOT_WEBHOOK)

    def _do_post(self, bundle, choice: str) -> dict:
        """Execute a post for the given bundle+choice and mark it posted."""
        option = bundle.option_a if choice.startswith("A") else bundle.option_b
        image_url = bundle.image_1_url if choice.endswith("1") else bundle.image_2_url

        content = option.get("content", "")
        media_urls = [image_url] if image_url else None

        from lib.mcp._client_helpers import suppress_stdout
        from lib.posting.poster import Poster

        with suppress_stdout():
            poster = Poster()
            result = poster.post(
                content=content,
                platforms=[bundle.platform],
                media_urls=media_urls,
            )

        self.store.mark_posted(bundle.slot_id, choice)

        # Mark library images as used
        library_ids = getattr(bundle, "library_item_ids", [])
        if library_ids:
            try:
                from lib.media_library.catalog import MediaCatalog

                catalog = MediaCatalog()
                for item_id in library_ids:
                    catalog.mark_used(item_id, bundle.platform)
            except Exception as exc:
                logger.warning(f"[scheduler] Failed to mark library images used: {exc}")

        return result if isinstance(result, dict) else {}

    def _scan_media_library(self) -> None:
        """Scan Supabase bucket for new unindexed images and ingest them."""
        try:
            from lib.media_library.scanner import BucketScanner

            scanner = BucketScanner()
            result = scanner.ingest_new()
            if result["ingested"] > 0:
                logger.info(
                    f"[scheduler] Library scan: ingested {result['ingested']}, "
                    f"skipped {result['skipped']}"
                )
        except ValueError:
            pass  # Supabase not configured — skip silently
        except Exception as exc:
            logger.warning(f"[scheduler] Library scan failed: {exc}")

    def _sync_local_folders(self) -> None:
        """Sync local iCloud/Desktop folders into the media library."""
        try:
            from lib.media_library.local_scanner import LocalFolderScanner

            scanner = LocalFolderScanner()
            result = scanner.ingest_new()
            if result["ingested"] > 0:
                logger.info(
                    f"[scheduler] Local sync: ingested {result['ingested']}, "
                    f"skipped {result['skipped']}"
                )
                if result["details"]:
                    for d in result["details"]:
                        logger.info(
                            f"[scheduler]   [{d['category']}] {d['filename']}: {d['description']}"
                        )
        except ValueError:
            pass  # Supabase not configured — skip silently
        except Exception as exc:
            logger.warning(f"[scheduler] Local folder sync failed: {exc}")

    @staticmethod
    def _local_folders_exist() -> bool:
        """Check if any configured local sync folders exist on disk."""
        try:
            from lib.media_library.local_scanner import LocalFolderScanner

            scanner = LocalFolderScanner()
            return any(Path(f["path"]).exists() for f in scanner.folders)
        except Exception:
            return False

    def _cleanup_old_records(self) -> None:
        deleted = self.store.cleanup_old(days=7)
        if deleted:
            logger.info(f"[scheduler] Cleaned up {deleted} old approval records")
