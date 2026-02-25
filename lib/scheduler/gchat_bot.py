"""SLASHERBOT Google Chat two-way conversational bot handler.

Receives Google Chat App HTTP events and routes them to command handlers,
returning synchronous JSON responses that appear as bot messages in the
SLASHERBOT space.

Setup in Google Cloud Console:
  1. APIs & Services → Google Chat API → Configuration
  2. App name: SLASHERBOT
  3. Connection type: HTTP endpoint URL
  4. App URL: https://web-production-c9cb9.up.railway.app/gchat/events?secret=<GCHAT_BOT_SECRET>
  5. Slash Commands: optional (plain text commands work without them)
  6. Add the bot to your SLASHERBOT space

Commands (type in the SLASHERBOT space):
  help                                   Show available commands
  status                                 Scheduler status + bundle counts
  pending                                List bundles awaiting approval
  approve <slot> <A1|A2|B1|B2>           Post and mark slot approved
  skip <slot>                            Skip a slot (no post)
  trigger [platform]                     Manually fire a content slot
  write <topic> [--platform=X]           Generate post content in SWIZZ voice
  post <content> --platform=<name>       Post content directly
  <any free text>                        Generate content for that topic

Environment variable:
  GCHAT_BOT_SECRET — pre-shared token included in the endpoint URL so only
                     Google Chat can invoke this handler.  Leave unset in dev.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

_HELP_TEXT = """\
*⚡ SLASHERBOT Commands*

`status` — Scheduler status + pending bundle counts
`pending` — List bundles awaiting your approval
`approve <slot> <A1|A2|B1|B2>` — Post and mark slot approved
`skip <slot>` — Skip a slot (no post)
`trigger [platform]` — Manually fire a content slot (default: twitter)
`write <topic>` — Generate a post in SWIZZ voice
`post <content> --platform=<name>` — Post content directly
`library` — Media library stats
`help` — Show this message

📷 *Send an image* — I'll analyze it and add it to the media library

*Tip:* Type any topic and I'll write content for it.
_Platforms: twitter, linkedin, instagram, tiktok, facebook, threads, reddit, bluesky, google_business_"""

_VALID_PLATFORMS = frozenset({
    "twitter", "linkedin", "instagram", "tiktok", "facebook",
    "threads", "reddit", "bluesky", "google_business",
})

# Map Google Chat commandId integers → command names.
# IDs must match those registered in Google Cloud Console →
# APIs & Services → Google Chat API → Configuration → Slash Commands.
# Google sends commandId (int) in slashCommand objects, NOT commandName.
_COMMAND_ID_MAP: dict[int, str] = {
    1: "status",
    2: "help",
    3: "pending",
    4: "approve",
    5: "skip",
    6: "trigger",
    7: "write",
    8: "post",
}

_VALID_CHOICES = frozenset({"A1", "A2", "B1", "B2"})


class SlasherbotChatHandler:
    """Routes Google Chat messages to SLASHERBOT command handlers.

    The ``scheduler`` argument accepts the live DailyScheduler instance from
    server.py so the bot can call trigger_slot() without re-creating APScheduler.
    """

    def __init__(self, scheduler: Any = None) -> None:
        self._scheduler = scheduler  # DailyScheduler instance or None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def handle_event(self, event: dict) -> dict:
        """Process a Google Chat event and return a synchronous response dict.

        Google Chat displays the returned ``{"text": "..."}`` (or cardsV2) as
        a bot message in the same thread.
        """
        event_type = event.get("type", "")

        if event_type == "ADDED_TO_SPACE":
            return self._welcome()
        elif event_type == "REMOVED_FROM_SPACE":
            return {}
        elif event_type == "MESSAGE":
            return self._handle_message(event)
        elif event_type == "CARD_CLICKED":
            action = event.get("action", {})
            action_method = action.get("actionMethodName", "")
            params = {p["key"]: p["value"] for p in action.get("parameters", [])}
            return self._handle_card_action(action_method, params)

        # Empty or unknown event_type — can happen for Google endpoint verification
        # pings or system events (REACTION_ADDED etc.).  If a slashCommand is present
        # at the top level, still try to route it.
        if event.get("slashCommand"):
            return self._handle_slash_command(event["slashCommand"], event.get("message", {}))

        if event_type:
            logger.warning("Unhandled Google Chat event type: %s", event_type)
        # Silent OK for empty/unknown types — returning {} tells Google Chat "acknowledged"
        return {}

    def _handle_message(self, event: dict) -> dict:
        """Handle MESSAGE events — slash commands, image uploads, or free-text @mentions."""
        message = event.get("message", {})

        # Check for image attachments FIRST — user sent a screenshot to the bot
        attachments = message.get("attachment", [])
        image_attachments = [
            a for a in attachments
            if a.get("contentType", "").startswith("image/")
        ]
        if image_attachments:
            caption = message.get("argumentText", message.get("text", "")).strip()
            return self._cmd_upload_image(image_attachments, caption)

        # Slash command: Google Chat populates message.slashCommand with commandId (int).
        # NOTE: Google's API sends commandId, NOT commandName — commandName is unreliable
        # and may be absent entirely.  Use _COMMAND_ID_MAP to resolve the name.
        slash_cmd = message.get("slashCommand", {})
        if slash_cmd:
            return self._handle_slash_command(slash_cmd, message)

        # Regular @mention: argumentText strips the @SLASHERBOT prefix automatically.
        text = message.get("argumentText", message.get("text", "")).strip()
        return self._route(text)

    def _handle_slash_command(self, slash_cmd: dict, message: dict) -> dict:
        """Resolve command name from a slashCommand object and route it.

        Google Chat sends ``commandId`` (int) in slash command payloads.
        ``commandName`` is not present in most payloads.  Fall back to
        ``_COMMAND_ID_MAP`` keyed by commandId.
        """
        # Try commandName first (future-proof / some API versions include it).
        cmd_name = slash_cmd.get("commandName", "").lstrip("/").lower()
        if not cmd_name:
            cmd_id = int(slash_cmd.get("commandId", 0) or 0)
            cmd_name = _COMMAND_ID_MAP.get(cmd_id, "")
            if cmd_id and not cmd_name:
                logger.warning("Unknown slash commandId: %s — routing as free text", cmd_id)

        args = message.get("argumentText", "").strip()
        synthetic = f"{cmd_name} {args}".strip() if cmd_name else args
        return self._route(synthetic)

    # ------------------------------------------------------------------
    # Command router
    # ------------------------------------------------------------------

    def _route(self, text: str) -> dict:
        if not text:
            return {"text": _HELP_TEXT}

        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lstrip("/").lower()  # strip leading / so /status == status
        args = parts[1].strip() if len(parts) > 1 else ""

        router = {
            "help": self._cmd_help,
            "status": self._cmd_status,
            "pending": self._cmd_pending,
            "approve": self._cmd_approve,
            "skip": self._cmd_skip,
            "trigger": self._cmd_trigger,
            "write": self._cmd_write,
            "post": self._cmd_post,
            "library": self._cmd_library,
        }

        handler = router.get(cmd)
        if handler:
            return handler(args)

        # Free text → generate content
        return self._cmd_freetext(text)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _cmd_help(self, _args: str) -> dict:
        return {"text": _HELP_TEXT}

    def _cmd_status(self, _args: str) -> dict:
        """Show scheduler running state and pending bundle counts."""
        lines = ["*📊 SLASHERBOT Status*"]

        if self._scheduler and getattr(self._scheduler, "scheduler", None):
            running = self._scheduler.scheduler.running
            lines.append(f"• Scheduler: {'🟢 Running' if running else '🔴 Stopped'}")
            try:
                status = self._scheduler.get_status()
                jobs = status.get("jobs", [])
                if jobs:
                    next_job = jobs[0]
                    lines.append(
                        f"• Next slot: `{next_job.get('platform', '?')}` "
                        f"at {next_job.get('next_run', '?')}"
                    )
                    lines.append(f"• Total jobs registered: {len(jobs)}")
            except Exception:
                pass
        else:
            enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"
            state = "⏳ Starting…" if enabled else "⚠️ Disabled (SCHEDULER_ENABLED=false)"
            lines.append(f"• Scheduler: {state}")

        try:
            from lib.scheduler.approval_store import ApprovalStore
            store = ApprovalStore()
            pending = store.get_pending_active()
            expired = store.get_pending_expired()
            lines.append(f"• Pending approval: {len(pending)} bundle(s)")
            lines.append(f"• Expired / auto-post due: {len(expired)} bundle(s)")
        except Exception as exc:
            lines.append(f"• Store: Error ({exc})")

        return {"text": "\n".join(lines)}

    def _cmd_pending(self, _args: str) -> dict:
        """List all pending approval bundles."""
        try:
            from lib.scheduler.approval_store import ApprovalStore
            store = ApprovalStore()
            bundles = store.get_pending_active()
        except Exception as exc:
            return {"text": f"⚠️ Error loading pending bundles: {exc}"}

        if not bundles:
            return {"text": "✅ No pending bundles — all slots are handled!"}

        count = len(bundles)
        noun = "bundle" if count == 1 else "bundles"
        lines = [f"*⏳ Pending Approval ({count} {noun})*", ""]

        for b in bundles[:8]:  # cap output
            expires_str = b.expires_at.strftime("%I:%M %p UTC")
            content_a = b.option_a.get("content", "")[:80].replace("\n", " ")
            slot_short = b.slot_id[:8]
            lines.append(
                f"• `{slot_short}` — *{b.platform.upper()}* (expires {expires_str})\n"
                f"  A: _{content_a}_…\n"
                f"  → `approve {slot_short} A1` to post"
            )
            lines.append("")

        if count > 8:
            lines.append(f"_…and {count - 8} more._")

        return {"text": "\n".join(lines)}

    def _cmd_approve(self, args: str) -> dict:
        """approve <slot_id> <A1|A2|B1|B2>"""
        parts = args.strip().split()
        if len(parts) < 2:
            return {
                "text": (
                    "Usage: `approve <slot_id> <A1|A2|B1|B2>`\n"
                    "Example: `approve abc12345 A1`\n"
                    "Run `pending` to see slot IDs."
                )
            }

        slot_prefix, choice = parts[0], parts[1].upper()
        if choice not in _VALID_CHOICES:
            return {"text": f"❌ Invalid choice `{choice}`. Valid: A1, A2, B1, B2"}

        try:
            from lib.scheduler.approval_store import ApprovalStore
            store = ApprovalStore()
            bundle = store.get_by_prefix(slot_prefix)
        except Exception as exc:
            return {"text": f"⚠️ Store error: {exc}"}

        if not bundle:
            return {
                "text": (
                    f"❌ Slot `{slot_prefix}` not found.\n"
                    "Run `pending` to see active slot IDs."
                )
            }

        if bundle.posted:
            return {
                "text": f"⚠️ Slot `{slot_prefix}` was already handled (choice: {bundle.choice})."
            }

        # Map choice → content + image
        option = bundle.option_a if choice.startswith("A") else bundle.option_b
        image_url = bundle.image_1_url if choice.endswith("1") else bundle.image_2_url
        content = option.get("content", "")
        media_urls = [image_url] if image_url else None

        try:
            from lib.mcp._client_helpers import suppress_stdout
            with suppress_stdout():
                from lib.posting.poster import Poster
                poster = Poster()
                result = poster.post(
                    content=content,
                    platforms=[bundle.platform],
                    media_urls=media_urls,
                )
        except Exception as exc:
            return {"text": f"❌ Post failed: {exc}"}

        store.mark_posted(bundle.slot_id, choice)

        platform_label = bundle.platform.upper()
        status = result.get("status", "posted") if isinstance(result, dict) else "posted"
        preview = content[:100].replace("\n", " ")

        # Send confirmation card to SLASHERBOT webhook as well
        try:
            from lib.scheduler.gchat_cards import send_confirmation_card
            send_confirmation_card(bundle, choice, result if isinstance(result, dict) else {})
        except Exception:
            pass

        return {
            "text": (
                f"✅ *Posted to {platform_label}!*\n"
                f"Choice: `{choice}` • Status: {status}\n"
                f"_{preview}_"
            )
        }

    def _cmd_skip(self, args: str) -> dict:
        """skip <slot_id>"""
        parts = args.strip().split()
        slot_prefix = parts[0] if parts else ""
        if not slot_prefix:
            return {"text": "Usage: `skip <slot_id>`\nExample: `skip abc12345`"}

        try:
            from lib.scheduler.approval_store import ApprovalStore
            store = ApprovalStore()
            bundle = store.get_by_prefix(slot_prefix)
        except Exception as exc:
            return {"text": f"⚠️ Store error: {exc}"}

        if not bundle:
            return {"text": f"❌ Slot `{slot_prefix}` not found."}

        if bundle.posted:
            return {"text": f"⚠️ Slot `{slot_prefix}` already handled (choice: {bundle.choice})."}

        store.mark_posted(bundle.slot_id, "SKIP")
        return {"text": f"⏭ Slot `{slot_prefix}` skipped — no post will be made."}

    def _cmd_trigger(self, args: str) -> dict:
        """trigger [platform]"""
        platform = args.strip().split()[0].lower() if args.strip() else "twitter"
        if platform not in _VALID_PLATFORMS:
            return {
                "text": (
                    f"❌ Unknown platform `{platform}`.\n"
                    f"Valid: {', '.join(sorted(_VALID_PLATFORMS))}"
                )
            }

        if not self._scheduler:
            return {
                "text": "⚠️ Scheduler not running. Set `SCHEDULER_ENABLED=true` on Railway."
            }

        try:
            slot_id = self._scheduler.trigger_slot(platform, "manual", "professional")
        except Exception as exc:
            return {"text": f"❌ Trigger failed: {exc}"}

        if slot_id:
            return {
                "text": (
                    f"🚀 *Slot triggered for {platform.upper()}!*\n"
                    f"Slot ID: `{slot_id[:8]}`\n"
                    "Check this space in a moment for the approval card."
                )
            }
        return {"text": f"⚠️ Trigger returned no slot — check Railway logs."}

    def _cmd_write(self, args: str) -> dict:
        """write <topic> [--platform=twitter] [--persona=professional] [--tone=authentic]"""
        if not args.strip():
            return {
                "text": (
                    "Usage: `write <topic>`\n"
                    "Example: `write AI tools changing developer productivity`\n"
                    "Optional: `write <topic> --platform=linkedin --persona=ceo`"
                )
            }

        platform = _extract_flag(args, "platform") or "twitter"
        persona = _extract_flag(args, "persona") or "professional"
        tone = _extract_flag(args, "tone") or "authentic"
        topic = _strip_flags(args).strip() or args.strip()

        try:
            from lib.mcp._client_helpers import suppress_stdout, build_agent_config
            with suppress_stdout():
                from lib.agents.writing_agent import WritingAgent
                config = build_agent_config(persona, platform)
                agent = WritingAgent(config)
                result = agent.generate_post(
                    topic=topic,
                    platform=platform,
                    post_type="post",
                    persona_mode=persona,
                    tone=tone,
                    energy="high",
                )
        except Exception as exc:
            return {"text": f"❌ Writing failed: {exc}\nEnsure GOOGLE_API_KEY is set."}

        if isinstance(result, dict):
            content = result.get("content", "")
            hashtags = result.get("hashtags", [])
        else:
            content = str(result)
            hashtags = []

        hashtag_str = " ".join(hashtags[:5]) if hashtags else ""
        lines = [
            f"✍️ *{persona.upper()} voice — {platform.upper()}*",
            "",
            content,
        ]
        if hashtag_str:
            lines.extend(["", f"`{hashtag_str}`"])
        lines.extend([
            "",
            f"_→ `post {content[:40].replace(chr(10), ' ')}... --platform={platform}` to publish_",
        ])

        return {"text": "\n".join(lines)}

    def _cmd_post(self, args: str) -> dict:
        """post <content> --platform=<platform>"""
        platform = _extract_flag(args, "platform") or "twitter"
        content = _strip_flags(args).strip()

        if not content:
            return {
                "text": (
                    "Usage: `post <content> --platform=<platform>`\n"
                    "Example: `post Just shipped AI to 8 platforms! --platform=twitter`"
                )
            }

        try:
            from lib.mcp._client_helpers import suppress_stdout
            with suppress_stdout():
                from lib.posting.poster import Poster
                poster = Poster()
                result = poster.post(content=content, platforms=[platform])
        except Exception as exc:
            return {"text": f"❌ Post failed: {exc}"}

        status = result.get("status", "posted") if isinstance(result, dict) else "posted"
        return {
            "text": (
                f"✅ *Posted to {platform.upper()}!*\n"
                f"Status: {status}\n"
                f"_{content[:100]}_"
            )
        }

    def _cmd_library(self, _args: str) -> dict:
        """Show media library stats."""
        try:
            from lib.media_library.catalog import MediaCatalog
            catalog = MediaCatalog()
            stats = catalog.get_stats()
        except Exception as exc:
            return {"text": f"⚠️ Library error: {exc}"}

        lines = [
            "*📷 Media Library*",
            f"• Total images: {stats['total']}",
            f"• Available: {stats['available']}",
            f"• Used at least once: {stats['used_at_least_once']}",
            f"• Archived: {stats['archived']}",
        ]
        cats = stats.get("categories", {})
        if cats:
            cat_str = ", ".join(f"{k}: {v}" for k, v in cats.items())
            lines.append(f"• Categories: {cat_str}")
        lines.append("")
        lines.append("_Send an image to add it to the library._")
        return {"text": "\n".join(lines)}

    def _cmd_upload_image(self, attachments: list, caption: str = "") -> dict:
        """Download image from GChat, analyze with Vision, index in library."""
        results = []
        for att in attachments[:4]:  # cap at 4 images per message
            filename = att.get("contentName", "upload.png")
            # Use thumbnailUri (public Google-hosted URL, typically 1600px+)
            download_url = att.get("thumbnailUri", "") or att.get("downloadUri", "")

            if not download_url:
                results.append(f"⚠️ No download URL for {filename}")
                continue

            try:
                # Download image bytes
                image_bytes = self._download_gchat_attachment(download_url)

                # Upload to Supabase Storage
                import tempfile
                ext = os.path.splitext(filename)[1] or ".png"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    tmp.write(image_bytes)
                    tmp_path = tmp.name

                from lib.storage.media_store import upload_image
                storage_url = upload_image(tmp_path, prefix="library")
                os.unlink(tmp_path)

                # Vision analysis
                from lib.media_library.vision import VisionAnalyzer
                analyzer = VisionAnalyzer()
                content_type = att.get("contentType", "image/png")
                vision_data = analyzer.analyze_bytes(image_bytes, content_type)

                # Index in catalog
                from lib.media_library.catalog import MediaCatalog
                import uuid
                catalog = MediaCatalog()
                item_id = str(uuid.uuid4())
                catalog.add(
                    item_id, filename, storage_url, vision_data,
                    mime_type=content_type, file_size=len(image_bytes),
                )

                desc_preview = vision_data.get("description", "")[:80]
                tags_preview = ", ".join(vision_data.get("tags", [])[:5])
                results.append(
                    f"✅ *{filename}* indexed\n"
                    f"  _{desc_preview}_\n"
                    f"  Tags: `{tags_preview}`"
                )

            except Exception as exc:
                results.append(f"❌ {filename}: {exc}")

        header = f"📷 *{len(results)} image(s) processed*\n\n"
        return {"text": header + "\n\n".join(results)}

    @staticmethod
    def _download_gchat_attachment(url: str) -> bytes:
        """Download an image from a Google Chat thumbnail/download URL."""
        import urllib.request
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return resp.read()

    def _cmd_freetext(self, text: str) -> dict:
        """Treat free-form text as a write topic."""
        return self._cmd_write(text)

    # ------------------------------------------------------------------
    # Card action handler (for future interactive buttons)
    # ------------------------------------------------------------------

    def _handle_card_action(self, action_method: str, params: dict) -> dict:
        """Handle interactive card button clicks (CARD_CLICKED events)."""
        if action_method == "approve":
            slot_id = params.get("slot_id", "")
            choice = params.get("choice", "A1")
            return self._cmd_approve(f"{slot_id} {choice}")
        elif action_method == "skip":
            slot_id = params.get("slot_id", "")
            return self._cmd_skip(slot_id)
        return {"text": "Action received."}

    # ------------------------------------------------------------------
    # Welcome message
    # ------------------------------------------------------------------

    def _welcome(self) -> dict:
        return {"text": f"👋 *SLASHERBOT is connected!*\n\n{_HELP_TEXT}"}


# ---------------------------------------------------------------------------
# Argument parsing helpers
# ---------------------------------------------------------------------------


def _extract_flag(text: str, flag: str) -> Optional[str]:
    """Extract --flag=value or --flag value from text, return the value or None."""
    # --flag=value
    m = re.search(rf"--{flag}=(\S+)", text)
    if m:
        return m.group(1)
    # --flag value
    m = re.search(rf"--{flag}\s+(\S+)", text)
    if m:
        return m.group(1)
    return None


def _strip_flags(text: str) -> str:
    """Remove all --flag=value and --flag value patterns from text."""
    text = re.sub(r"--\w+=\S+", "", text)
    text = re.sub(r"--\w+\s+\S+", "", text)
    return text.strip()
