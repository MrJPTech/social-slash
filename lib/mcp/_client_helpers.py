"""Client helpers for MCP server - Late client factory, stdout suppression, config builders."""

import io
import os
import sys
from contextlib import contextmanager

from late import Late


@contextmanager
def suppress_stdout():
    """Suppress stdout to prevent print() calls from corrupting MCP JSON-RPC stream.

    LateDistributionClient and ResponseGenerator both call print() for status messages.
    MCP uses stdout for JSON-RPC, so any stray print() corrupts the protocol.
    """
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old_stdout


def get_late_client() -> Late:
    """Create a Late SDK client from LATE_API_KEY env var.

    Returns:
        Late client instance.

    Raises:
        ValueError: If LATE_API_KEY is not set.
    """
    api_key = os.getenv("LATE_API_KEY", "")
    if not api_key:
        raise ValueError(
            "LATE_API_KEY environment variable is required. "
            "Set it in .env.local or pass via Docker env."
        )
    base_url = os.getenv("LATE_BASE_URL", None)
    return Late(api_key=api_key, base_url=base_url)


def build_agent_config(persona_mode: str = "professional", platform: str = "instagram") -> dict:
    """Build a config dict for agent constructors (WritingAgent, ResearchAgent, MediaAgent).

    Args:
        persona_mode: "professional" or "personal"
        platform: Default target platform

    Returns:
        Config dict compatible with BaseAgent.__init__
    """
    return {
        "persona_mode": persona_mode,
        "default_platform": platform,
        "auto_approve": True,
        "poll_interval_seconds": 30,
    }
