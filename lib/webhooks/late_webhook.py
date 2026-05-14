#!/usr/bin/env python3
"""
Late SDK Webhook Handler

FastAPI server for handling Late API webhooks.
Receives real-time notifications for messages and posts.

Events:
- message.received - New DM received (Instagram, Telegram)
- post.published - Track new posts for comment monitoring
- post.failed - Handle posting failures
- webhook.test - Test webhook connectivity

Deployment: Railway or any FastAPI-compatible host
"""

import hashlib
import hmac
import os
from datetime import datetime
from queue import Queue
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Create FastAPI app
app = FastAPI(
    title="Social Slash Webhooks",
    description="Late SDK webhook handler for engagement automation",
    version="1.0.0",
)

# Global queues for agent processing
dm_queue: Queue = Queue()
post_queue: Queue = Queue()

# Webhook secret for signature verification
WEBHOOK_SECRET = os.getenv("LATE_WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature from X-Late-Signature header.

    Args:
        payload: Raw request body bytes
        signature: Signature from header
        secret: Webhook secret

    Returns:
        True if signature is valid
    """
    if not secret:
        return True  # Skip verification if no secret configured

    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, signature)


class WebhookEvent(BaseModel):
    """Webhook event data model."""

    event: str
    data: dict[str, Any]
    timestamp: str | None = None


class WebhookHandler:
    """
    Handler for Late webhook events.

    Processes incoming events and routes them to appropriate queues.
    """

    def __init__(self):
        self.handlers = {
            "message.received": self._handle_message,
            "post.published": self._handle_post_published,
            "post.failed": self._handle_post_failed,
            "webhook.test": self._handle_test,
        }
        self.stats = {
            "events_received": 0,
            "messages_queued": 0,
            "posts_tracked": 0,
            "errors": 0,
            "last_event": None,
        }

    async def handle(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Handle an incoming webhook event.

        Args:
            event_type: Event type string
            data: Event data dictionary

        Returns:
            Response dictionary
        """
        self.stats["events_received"] += 1
        self.stats["last_event"] = datetime.now().isoformat()

        handler = self.handlers.get(event_type)
        if handler:
            try:
                return await handler(data)
            except Exception as e:
                self.stats["errors"] += 1
                print(f"[ERROR] Webhook handler failed: {e}")
                return {"status": "error", "message": str(e)}
        else:
            print(f"[WARNING] Unknown event type: {event_type}")
            return {"status": "ignored", "message": f"Unknown event: {event_type}"}

    async def _handle_message(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming DM."""
        dm_queue.put(data)
        self.stats["messages_queued"] += 1

        sender = data.get("senderName", "unknown")
        platform = data.get("platform", "unknown")
        print(f"[WEBHOOK] DM received from {sender} on {platform}")

        return {"status": "queued", "type": "message"}

    async def _handle_post_published(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle new post published - track for comment monitoring."""
        post_queue.put(data)
        self.stats["posts_tracked"] += 1

        platform = data.get("platform", "unknown")
        post_id = data.get("id", "unknown")
        print(f"[WEBHOOK] Post published on {platform}: {post_id}")

        return {"status": "tracked", "type": "post", "id": post_id}

    async def _handle_post_failed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle post failure."""
        platform = data.get("platform", "unknown")
        error = data.get("error", "Unknown error")
        print(f"[WEBHOOK] Post failed on {platform}: {error}")

        return {"status": "logged", "type": "failure"}

    async def _handle_test(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle test webhook."""
        print("[WEBHOOK] Test event received")
        return {"status": "ok", "type": "test", "timestamp": datetime.now().isoformat()}

    def get_stats(self) -> dict[str, Any]:
        """Get handler statistics."""
        return {
            **self.stats,
            "dm_queue_size": dm_queue.qsize(),
            "post_queue_size": post_queue.qsize(),
        }


# Global handler instance
webhook_handler = WebhookHandler()


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Root endpoint - basic info."""
    return {"service": "Social Slash Webhooks", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint for deployment."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/stats")
async def stats():
    """Get webhook statistics."""
    return webhook_handler.get_stats()


@app.post("/webhooks/late")
async def handle_late_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle Late SDK webhooks.

    Verifies signature and routes to appropriate handler.
    """
    # Get signature header
    signature = request.headers.get("X-Late-Signature", "")

    # Get raw body
    body = await request.body()

    # Verify signature if secret is configured
    if WEBHOOK_SECRET and not verify_signature(body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event", "")
    data = payload.get("data", {})

    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event type")

    # Handle event
    result = await webhook_handler.handle(event_type, data)

    return JSONResponse(content=result)


@app.post("/webhooks/test")
async def test_webhook():
    """Test endpoint to verify webhook is working."""
    return {
        "status": "ok",
        "message": "Webhook endpoint is working",
        "timestamp": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# QUEUE ACCESS (for agents)
# ─────────────────────────────────────────────────────────────


def get_dm_queue() -> Queue:
    """Get the DM queue for agent processing."""
    return dm_queue


def get_post_queue() -> Queue:
    """Get the post queue for tracking."""
    return post_queue


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Late Webhook Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"""
╔════════════════════════════════════════════════════════════╗
║           Social Slash Webhook Server                      ║
╠════════════════════════════════════════════════════════════╣
║  Host: {args.host:<52}║
║  Port: {args.port:<52}║
║  Signature verification: {"Enabled" if WEBHOOK_SECRET else "Disabled":<30}║
╚════════════════════════════════════════════════════════════╝
""")

    uvicorn.run("lib.webhooks.late_webhook:app", host=args.host, port=args.port, reload=args.reload)
