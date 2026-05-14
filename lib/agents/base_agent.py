#!/usr/bin/env python3
"""
Base Agent Class for Engagement Automation

Provides abstract base class with:
- State machine (IDLE → MONITORING → PROCESSING → RESPONDING)
- AI provider integration
- Common utility methods
- Event logging
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any


class AgentState(Enum):
    """Agent operational states."""

    IDLE = "idle"
    STARTING = "starting"
    MONITORING = "monitoring"
    PROCESSING = "processing"
    GENERATING = "generating"
    REVIEWING = "reviewing"  # Human-in-the-loop
    RESPONDING = "responding"
    STOPPING = "stopping"
    ERROR = "error"


class BaseAgent(ABC):
    """
    Abstract base class for engagement automation agents.

    Provides:
    - State machine for agent lifecycle
    - AI provider integration (Gemini/Anthropic)
    - Common utilities for rate limiting, logging
    - Abstract methods for subclass implementation

    Subclasses must implement:
    - start(): Begin monitoring loop
    - stop(): Gracefully shutdown
    - process_item(): Handle a single item (comment/DM)
    """

    def __init__(
        self, config: dict[str, Any], ai_provider: str = "gemini", name: str | None = None
    ):
        """
        Initialize the base agent.

        Args:
            config: Agent configuration dictionary
            ai_provider: AI provider for response generation ('gemini' or 'anthropic')
            name: Agent name for logging
        """
        self.config = config
        self.ai_provider = ai_provider
        self.name = name or self.__class__.__name__
        self.state = AgentState.IDLE

        # Stats tracking
        self.stats = {
            "started_at": None,
            "items_processed": 0,
            "items_responded": 0,
            "items_queued": 0,
            "errors": 0,
        }

        # Rate limiting
        self._last_action_time: dict[str, datetime] = {}
        self._action_counts: dict[str, int] = {}

        # Response generator (lazy init)
        self._response_generator = None

        # Logging
        self.logger = logging.getLogger(f"social-slash.{self.name}")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
                )
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Event loop control
        self._running = False
        self._stop_event: asyncio.Event | None = None

    @property
    def response_generator(self):
        """Lazy-load response generator."""
        if self._response_generator is None:
            from lib.engagement.response_generator import ResponseGenerator

            self._response_generator = ResponseGenerator(provider=self.ai_provider)
        return self._response_generator

    # ─────────────────────────────────────────────────────────────
    # STATE MACHINE
    # ─────────────────────────────────────────────────────────────

    def transition(self, new_state: AgentState):
        """
        Transition to a new state with logging.

        Args:
            new_state: Target state
        """
        old_state = self.state
        self.state = new_state
        self.logger.debug(f"State: {old_state.value} → {new_state.value}")

        # Log significant transitions
        if new_state == AgentState.MONITORING:
            self.logger.info("Agent is now monitoring")
        elif new_state == AgentState.ERROR:
            self.logger.warning("Agent entered error state")
        elif new_state == AgentState.STOPPING:
            self.logger.info("Agent is shutting down")

    def is_running(self) -> bool:
        """Check if agent is actively running."""
        return self.state in [
            AgentState.MONITORING,
            AgentState.PROCESSING,
            AgentState.GENERATING,
            AgentState.RESPONDING,
        ]

    # ─────────────────────────────────────────────────────────────
    # RATE LIMITING
    # ─────────────────────────────────────────────────────────────

    def check_rate_limit(
        self, key: str, max_per_hour: int = 60, cooldown_seconds: int = 60
    ) -> bool:
        """
        Check if an action is allowed under rate limits.

        Args:
            key: Unique identifier (e.g., user_id, platform)
            max_per_hour: Maximum actions per hour
            cooldown_seconds: Minimum seconds between actions

        Returns:
            True if action is allowed, False if rate limited
        """
        now = datetime.now()

        # Check cooldown
        if key in self._last_action_time:
            elapsed = (now - self._last_action_time[key]).total_seconds()
            if elapsed < cooldown_seconds:
                self.logger.debug(
                    f"Rate limited: {key} (cooldown {cooldown_seconds - elapsed:.0f}s remaining)"
                )
                return False

        # Check hourly limit
        hour_key = f"{key}:{now.hour}"
        count = self._action_counts.get(hour_key, 0)
        if count >= max_per_hour:
            self.logger.debug(f"Rate limited: {key} (hourly limit {max_per_hour} reached)")
            return False

        return True

    def record_action(self, key: str):
        """
        Record that an action was taken.

        Args:
            key: Unique identifier for the action
        """
        now = datetime.now()
        self._last_action_time[key] = now

        hour_key = f"{key}:{now.hour}"
        self._action_counts[hour_key] = self._action_counts.get(hour_key, 0) + 1

        # Clean old hour counts (keep last 2 hours)
        old_keys = [
            k
            for k in self._action_counts
            if not k.endswith(f":{now.hour}") and not k.endswith(f":{(now.hour - 1) % 24}")
        ]
        for k in old_keys:
            del self._action_counts[k]

    # ─────────────────────────────────────────────────────────────
    # FILTERING
    # ─────────────────────────────────────────────────────────────

    def should_skip(self, content: str, author: str) -> bool:
        """
        Check if content should be skipped based on filters.

        Args:
            content: Message content
            author: Author name/ID

        Returns:
            True if should skip, False if should process
        """
        # Skip own content
        skip_authors = self.config.get("skip_authors", [])
        if author.lower() in [a.lower() for a in skip_authors]:
            return True

        # Skip blocked keywords
        blocked_keywords = self.config.get("blocked_keywords", [])
        content_lower = content.lower()
        for keyword in blocked_keywords:
            if keyword.lower() in content_lower:
                self.logger.debug(f"Skipping: blocked keyword '{keyword}'")
                return True

        # Skip if too short
        min_length = self.config.get("min_content_length", 3)
        if len(content.strip()) < min_length:
            return True

        return False

    def requires_escalation(self, content: str) -> bool:
        """
        Check if content requires human escalation.

        Args:
            content: Message content

        Returns:
            True if should escalate to human
        """
        escalation_keywords = self.config.get(
            "escalation_keywords",
            [
                "urgent",
                "help",
                "emergency",
                "problem",
                "issue",
                "refund",
                "cancel",
                "lawsuit",
                "legal",
            ],
        )

        content_lower = content.lower()
        for keyword in escalation_keywords:
            if keyword.lower() in content_lower:
                self.logger.info(f"Escalation triggered: '{keyword}' found")
                return True

        return False

    # ─────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def start(self):
        """
        Start the agent's monitoring loop.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def stop(self):
        """
        Gracefully stop the agent.

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def process_item(self, item: Any) -> bool:
        """
        Process a single item (comment or DM).

        Args:
            item: The item to process

        Returns:
            True if processed successfully, False otherwise

        Must be implemented by subclasses.
        """
        pass

    async def run(self):
        """
        Main run loop with error handling.

        Wraps start() with error recovery.
        """
        self._running = True
        self._stop_event = asyncio.Event()

        try:
            self.transition(AgentState.STARTING)
            self.stats["started_at"] = datetime.now()
            self.logger.info(f"Starting {self.name}")

            await self.start()

        except asyncio.CancelledError:
            self.logger.info("Agent cancelled")
        except Exception as e:
            self.stats["errors"] += 1
            self.transition(AgentState.ERROR)
            self.logger.error(f"Agent error: {e}")
            raise
        finally:
            self._running = False
            self.transition(AgentState.IDLE)
            self.logger.info(f"Agent stopped. Stats: {self.get_stats()}")

    def request_stop(self):
        """Request the agent to stop."""
        if self._stop_event:
            self._stop_event.set()

    def get_stats(self) -> dict[str, Any]:
        """Get agent statistics."""
        stats = self.stats.copy()
        stats["state"] = self.state.value
        stats["is_running"] = self._running

        if stats["started_at"]:
            runtime = datetime.now() - stats["started_at"]
            stats["runtime_seconds"] = int(runtime.total_seconds())

        return stats

    # ─────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────

    def log_item(self, item_type: str, platform: str, author: str, content: str):
        """Log a processed item."""
        preview = content[:50] + "..." if len(content) > 50 else content
        self.logger.info(f"[{platform.upper()}] {item_type} from @{author}: {preview}")

    def format_console_output(self, status: str, message: str):
        """Format console output with status prefix."""
        status_map = {
            "success": "[SUCCESS]",
            "info": "[INFO]",
            "warning": "[WARNING]",
            "error": "[ERROR]",
            "queued": "[QUEUED]",
        }
        prefix = status_map.get(status.lower(), f"[{status.upper()}]")
        print(f"{prefix} {message}")


# Example usage
if __name__ == "__main__":
    # This is an abstract class, see comment_agent.py and dm_agent.py for implementations
    print("BaseAgent is an abstract class. Use CommentAgent or DMAgent.")
