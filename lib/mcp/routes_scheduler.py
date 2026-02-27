"""Scheduler routes — SLASHERBOT approval, GChat bot, status, and trigger endpoints."""

from __future__ import annotations

import json
import logging
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from ._shared import mcp, _get_scheduler
from ._client_helpers import suppress_stdout

logger = logging.getLogger(__name__)


# ============================================================================
# SLASHERBOT APPROVAL ENDPOINT
# ============================================================================


@mcp.custom_route("/approval", methods=["GET"])
async def approval_handler(request: Request) -> HTMLResponse:
    """Handle approval button clicks from Google Chat cards.

    Query params: slot (slot_id), choice (A1/A2/B1/B2/SKIP/REGEN), token (HMAC)
    """
    params = request.query_params
    slot_id = params.get("slot", "")
    choice = params.get("choice", "")
    token = params.get("token", "")

    def _html(title: str, body: str, color: str = "#1a73e8") -> HTMLResponse:
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SLASHERBOT — {title}</title>
<style>
  body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;
       display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0}}
  .card{{background:#161b22;border:1px solid #30363d;border-radius:12px;
         padding:2rem 3rem;max-width:500px;text-align:center}}
  h1{{color:{color};margin-bottom:0.5rem}}
  p{{color:#8b949e;margin-top:0.5rem}}
  code{{background:#21262d;padding:0.2em 0.5em;border-radius:4px;font-size:0.85em}}
</style></head>
<body><div class="card"><h1>{title}</h1>{body}</div></body></html>"""
        )

    # Validate inputs
    if not slot_id or not choice:
        return _html("❌ Invalid Link", "<p>Missing slot or choice parameter.</p>", "#da3633")

    # Verify HMAC token
    from lib.scheduler.gchat_cards import verify_token
    if not verify_token(slot_id, choice, token):
        return _html("❌ Invalid Token", "<p>This link has expired or been tampered with.</p>", "#da3633")

    # Handle SKIP
    if choice == "SKIP":
        from lib.scheduler.approval_store import ApprovalStore
        store = ApprovalStore()
        store.mark_posted(slot_id, "SKIP")
        return _html("⏭ Skipped", "<p>This post has been skipped.</p>", "#8b949e")

    # Handle REGEN (placeholder — full regen would re-trigger the pipeline)
    if choice == "REGEN":
        return _html(
            "🔄 Regenerate",
            "<p>Regeneration is not yet automated. Use the MCP trigger endpoint to create a new slot.</p>",
            "#e3b341",
        )

    # Load bundle
    from lib.scheduler.approval_store import ApprovalStore
    store = ApprovalStore()
    bundle = store.get(slot_id)
    if not bundle:
        return _html("❌ Not Found", f"<p>Slot <code>{slot_id[:8]}</code> not found. It may have expired.</p>", "#da3633")

    if bundle.posted:
        return _html(
            "✅ Already Posted",
            f"<p>Slot <code>{slot_id[:8]}</code> was already posted (choice: <code>{bundle.choice}</code>).</p>",
        )

    # Map choice to content + image
    if choice.startswith("A"):
        option = bundle.option_a
    elif choice.startswith("B"):
        option = bundle.option_b
    else:
        return _html("❌ Unknown Choice", f"<p>Unknown choice <code>{choice}</code>.</p>", "#da3633")

    image_url = bundle.image_1_url if choice.endswith("1") else bundle.image_2_url
    content = option.get("content", "")
    media_urls = [image_url] if image_url else None

    # Post
    try:
        with suppress_stdout():
            from lib.posting.poster import Poster
            poster = Poster()
            result = poster.post(
                content=content,
                platforms=[bundle.platform],
                media_urls=media_urls,
            )
        if not isinstance(result, dict):
            result = {}
    except Exception as exc:
        logger.error(f"[approval] Post failed for slot {slot_id[:8]}: {exc}")
        return _html("❌ Post Failed", f"<p>Error: <code>{str(exc)[:200]}</code></p>", "#da3633")

    # Mark posted
    store.mark_posted(slot_id, choice)

    # Send confirmation card to SLASHERBOT
    try:
        from lib.scheduler.gchat_cards import send_confirmation_card, SLASHERBOT_WEBHOOK
        send_confirmation_card(bundle, choice, result, SLASHERBOT_WEBHOOK)
    except Exception as exc:
        logger.warning(f"[approval] Confirmation card failed: {exc}")

    platform_label = bundle.platform.upper()
    preview = content[:100].replace("<", "&lt;").replace(">", "&gt;")
    return _html(
        f"✅ Posted to {platform_label}!",
        f"<p>Choice: <code>{choice}</code></p><p>{preview}…</p>",
        "#3fb950",
    )


# ============================================================================
# SLASHERBOT GOOGLE CHAT TWO-WAY BOT
# ============================================================================


@mcp.custom_route("/gchat/events", methods=["POST"])
async def gchat_events_handler(request: Request) -> JSONResponse:
    """Receive Google Chat App events for two-way SLASHERBOT conversation.

    Configure in Google Cloud Console -> APIs & Services -> Chat API:
      App URL: https://web-production-c9cb9.up.railway.app/gchat/events?secret=<GCHAT_BOT_SECRET>

    Security: validate the pre-shared GCHAT_BOT_SECRET query parameter.
    Leave GCHAT_BOT_SECRET unset in local dev to disable auth.
    """
    bot_secret = os.getenv("GCHAT_BOT_SECRET", "")
    if bot_secret:
        incoming = request.query_params.get("secret", "")
        if incoming != bot_secret:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    try:
        from lib.scheduler.gchat_bot import SlasherbotChatHandler
        handler = SlasherbotChatHandler(scheduler=_get_scheduler())
        response = handler.handle_event(body)
    except Exception as exc:
        logger.error(f"[gchat-bot] Event handling error: {exc}")
        return JSONResponse({"text": f"⚠️ Internal error: {exc}"})

    return JSONResponse(response)


# ============================================================================
# SCHEDULER STATUS & MANUAL TRIGGER
# ============================================================================


@mcp.custom_route("/scheduler/status", methods=["GET"])
async def scheduler_status_handler(request: Request) -> JSONResponse:
    """Return scheduler status and next run times for all platform jobs."""
    sched = _get_scheduler()
    if not sched:
        return JSONResponse({"enabled": False, "message": "Set SCHEDULER_ENABLED=true to activate"})
    return JSONResponse({"enabled": True, **sched.get_status()})


@mcp.custom_route("/scheduler/trigger", methods=["POST"])
async def scheduler_trigger_handler(request: Request) -> JSONResponse:
    """Manually trigger a content slot for testing. Body: {platform, time_label, persona}"""
    sched = _get_scheduler()
    if not sched:
        return JSONResponse({"error": "Scheduler not running"}, status_code=503)

    try:
        body_bytes = await request.body()
        if body_bytes:
            params = json.loads(body_bytes)
        else:
            params = {}
    except Exception:
        params = {}

    platform = params.get("platform", request.query_params.get("platform", "twitter"))
    time_label = params.get("time_label", "manual")
    persona = params.get("persona", "professional")

    slot_id = sched.trigger_slot(platform, time_label, persona)
    if slot_id:
        return JSONResponse({"status": "triggered", "slot_id": slot_id, "platform": platform})
    return JSONResponse({"error": "Trigger failed — check server logs"}, status_code=500)
