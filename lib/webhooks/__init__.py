#!/usr/bin/env python3
"""
Webhooks Module - Late SDK Webhook Handler

Provides FastAPI webhook server for real-time event handling:
- message.received - New DM received
- post.published - Track new posts
- post.failed - Handle posting failures
"""

from lib.webhooks.late_webhook import WebhookHandler, app, verify_signature

__all__ = ["app", "verify_signature", "WebhookHandler"]
