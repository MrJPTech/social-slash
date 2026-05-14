#!/usr/bin/env python3
"""
Bot Account Manager for Engagement Automation

Manages dedicated bot accounts for automated engagement.
Configures which accounts respond on which platforms.

Features:
- Bot account registration and configuration
- Primary/secondary bot designation
- Response style customization per bot
- Rate limit management per account
"""

from typing import Any

from lib.api_clients.late_client import LateDistributionClient
from lib.storage.database import EngagementDatabase
from lib.storage.models import BotAccount


class BotManager:
    """
    Manages bot accounts for engagement automation.

    Handles:
    - Registering Late accounts as bots
    - Configuring bot behavior per platform
    - Selecting appropriate bot for responses
    """

    def __init__(
        self,
        late_client: LateDistributionClient | None = None,
        db: EngagementDatabase | None = None,
    ):
        """
        Initialize the bot manager.

        Args:
            late_client: Late distribution client for account info
            db: Database instance
        """
        self.late_client = late_client or LateDistributionClient()
        self.db = db or EngagementDatabase()

    def list_available_accounts(self) -> list[dict[str, Any]]:
        """
        List all Late accounts available to use as bots.

        Returns:
            List of account info dictionaries
        """
        accounts = self.late_client.get_accounts()
        result = []

        for acc in accounts:
            platform = getattr(acc, "platform", "unknown").lower()
            account_id = getattr(acc, "field_id", None)
            name = getattr(acc, "name", "Unknown")

            result.append(
                {
                    "platform": platform,
                    "account_id": account_id,
                    "name": name,
                    "is_bot": self._is_registered_bot(account_id) if account_id else False,
                }
            )

        return result

    def _is_registered_bot(self, account_id: str) -> bool:
        """Check if account is registered as bot."""
        bots = self.db.get_bot_accounts(active_only=False)
        return any(b.late_account_id == account_id for b in bots)

    def register_bot(
        self,
        platform: str,
        late_account_id: str,
        name: str | None = None,
        is_primary: bool = False,
        response_style: str = "professional",
        max_replies_per_hour: int = 60,
        cooldown_seconds: int = 300,
    ) -> BotAccount:
        """
        Register a Late account as a bot.

        Args:
            platform: Platform name
            late_account_id: Late account ID
            name: Bot display name
            is_primary: Whether this is the primary bot for the platform
            response_style: Response style key
            max_replies_per_hour: Rate limit
            cooldown_seconds: Cooldown between replies

        Returns:
            Registered BotAccount
        """
        # Get account name from Late if not provided
        if not name:
            accounts = self.late_client.get_accounts()
            for acc in accounts:
                if getattr(acc, "field_id", None) == late_account_id:
                    name = getattr(acc, "name", f"Bot-{platform}")
                    break
            else:
                name = f"Bot-{platform}"

        # If setting as primary, unset other primaries for this platform
        if is_primary:
            existing_bots = self.db.get_bot_accounts(platform=platform)
            for bot in existing_bots:
                if bot.is_primary:
                    self.db.save_bot_account(
                        name=bot.name,
                        platform=bot.platform,
                        late_account_id=bot.late_account_id,
                        is_primary=False,
                        response_style=bot.response_style,
                        max_replies_per_hour=bot.max_replies_per_hour,
                        cooldown_seconds=bot.cooldown_seconds,
                    )

        bot = self.db.save_bot_account(
            name=name,
            platform=platform,
            late_account_id=late_account_id,
            is_primary=is_primary,
            response_style=response_style,
            max_replies_per_hour=max_replies_per_hour,
            cooldown_seconds=cooldown_seconds,
        )

        print(f"[SUCCESS] Registered bot: {name} ({platform})")
        return bot

    def get_bot(self, platform: str, prefer_primary: bool = True) -> BotAccount | None:
        """
        Get a bot account for a platform.

        Args:
            platform: Platform name
            prefer_primary: Whether to prefer the primary bot

        Returns:
            BotAccount or None if no bot configured
        """
        if prefer_primary:
            bot = self.db.get_primary_bot(platform)
            if bot:
                return bot

        # Get any active bot for this platform
        bots = self.db.get_bot_accounts(platform=platform)
        return bots[0] if bots else None

    def list_bots(self, platform: str | None = None, active_only: bool = True) -> list[BotAccount]:
        """
        List configured bot accounts.

        Args:
            platform: Filter by platform
            active_only: Only active bots

        Returns:
            List of BotAccount objects
        """
        return self.db.get_bot_accounts(platform=platform, active_only=active_only)

    def update_bot(self, late_account_id: str, **kwargs) -> BotAccount | None:
        """
        Update a bot's configuration.

        Args:
            late_account_id: Late account ID
            **kwargs: Fields to update (name, is_primary, is_active,
                     response_style, max_replies_per_hour, cooldown_seconds)

        Returns:
            Updated BotAccount or None if not found
        """
        bots = self.db.get_bot_accounts(active_only=False)
        bot = next((b for b in bots if b.late_account_id == late_account_id), None)

        if not bot:
            print(f"[ERROR] Bot not found: {late_account_id}")
            return None

        # Merge existing values with updates
        return self.db.save_bot_account(
            name=kwargs.get("name", bot.name),
            platform=bot.platform,
            late_account_id=late_account_id,
            is_primary=kwargs.get("is_primary", bot.is_primary),
            is_active=kwargs.get("is_active", bot.is_active),
            response_style=kwargs.get("response_style", bot.response_style),
            max_replies_per_hour=kwargs.get("max_replies_per_hour", bot.max_replies_per_hour),
            cooldown_seconds=kwargs.get("cooldown_seconds", bot.cooldown_seconds),
        )

    def deactivate_bot(self, late_account_id: str) -> bool:
        """
        Deactivate a bot account.

        Args:
            late_account_id: Late account ID

        Returns:
            True if deactivated
        """
        result = self.update_bot(late_account_id, is_active=False)
        if result:
            print(f"[SUCCESS] Bot deactivated: {result.name}")
            return True
        return False

    def activate_bot(self, late_account_id: str) -> bool:
        """
        Activate a bot account.

        Args:
            late_account_id: Late account ID

        Returns:
            True if activated
        """
        result = self.update_bot(late_account_id, is_active=True)
        if result:
            print(f"[SUCCESS] Bot activated: {result.name}")
            return True
        return False

    def set_primary(self, late_account_id: str) -> bool:
        """
        Set a bot as primary for its platform.

        Args:
            late_account_id: Late account ID

        Returns:
            True if set as primary
        """
        bots = self.db.get_bot_accounts(active_only=False)
        bot = next((b for b in bots if b.late_account_id == late_account_id), None)

        if not bot:
            print(f"[ERROR] Bot not found: {late_account_id}")
            return False

        # Unset other primaries
        for other in bots:
            if (
                other.platform == bot.platform
                and other.is_primary
                and other.late_account_id != late_account_id
            ):
                self.update_bot(other.late_account_id, is_primary=False)

        # Set this one as primary
        result = self.update_bot(late_account_id, is_primary=True)
        if result:
            print(f"[SUCCESS] {result.name} is now primary for {result.platform}")
            return True
        return False

    def get_stats(self) -> dict[str, Any]:
        """
        Get bot statistics.

        Returns:
            Dictionary with bot stats
        """
        all_bots = self.db.get_bot_accounts(active_only=False)
        active_bots = [b for b in all_bots if b.is_active]

        platforms = {}
        for bot in all_bots:
            if bot.platform not in platforms:
                platforms[bot.platform] = {"active": 0, "total": 0, "primary": None}
            platforms[bot.platform]["total"] += 1
            if bot.is_active:
                platforms[bot.platform]["active"] += 1
            if bot.is_primary:
                platforms[bot.platform]["primary"] = bot.name

        return {
            "total_bots": len(all_bots),
            "active_bots": len(active_bots),
            "platforms": platforms,
        }


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bot Account Manager")
    parser.add_argument(
        "--action",
        choices=["list", "available", "register", "deactivate", "activate", "set-primary", "stats"],
        default="list",
        help="Action to perform",
    )
    parser.add_argument("--platform", type=str, help="Platform filter")
    parser.add_argument("--account-id", type=str, help="Late account ID")
    parser.add_argument("--name", type=str, help="Bot name")
    parser.add_argument("--primary", action="store_true", help="Set as primary")
    parser.add_argument(
        "--style",
        type=str,
        default="professional",
        choices=["professional", "friendly", "casual", "enthusiastic", "supportive"],
        help="Response style",
    )
    parser.add_argument("--max-replies", type=int, default=60, help="Max replies per hour")
    parser.add_argument("--cooldown", type=int, default=300, help="Cooldown in seconds")

    args = parser.parse_args()

    manager = BotManager()

    if args.action == "list":
        bots = manager.list_bots(platform=args.platform)
        print(f"\nConfigured Bots: {len(bots)}")
        for bot in bots:
            primary_badge = " [PRIMARY]" if bot.is_primary else ""
            active_badge = "" if bot.is_active else " [INACTIVE]"
            print(f"\n  {bot.name}{primary_badge}{active_badge}")
            print(f"    Platform: {bot.platform}")
            print(f"    Account ID: {bot.late_account_id}")
            print(f"    Style: {bot.response_style}")
            print(
                f"    Rate limit: {bot.max_replies_per_hour}/hour, {bot.cooldown_seconds}s cooldown"
            )

    elif args.action == "available":
        accounts = manager.list_available_accounts()
        print(f"\nAvailable Late Accounts: {len(accounts)}")
        for acc in accounts:
            bot_badge = " [BOT]" if acc["is_bot"] else ""
            print(f"\n  {acc['name']}{bot_badge}")
            print(f"    Platform: {acc['platform']}")
            print(f"    Account ID: {acc['account_id']}")

    elif args.action == "register":
        if not args.platform or not args.account_id:
            print("[ERROR] --platform and --account-id required for register")
        else:
            bot = manager.register_bot(
                platform=args.platform,
                late_account_id=args.account_id,
                name=args.name,
                is_primary=args.primary,
                response_style=args.style,
                max_replies_per_hour=args.max_replies,
                cooldown_seconds=args.cooldown,
            )
            print(f"\nRegistered: {bot.name}")

    elif args.action == "deactivate":
        if not args.account_id:
            print("[ERROR] --account-id required")
        else:
            manager.deactivate_bot(args.account_id)

    elif args.action == "activate":
        if not args.account_id:
            print("[ERROR] --account-id required")
        else:
            manager.activate_bot(args.account_id)

    elif args.action == "set-primary":
        if not args.account_id:
            print("[ERROR] --account-id required")
        else:
            manager.set_primary(args.account_id)

    elif args.action == "stats":
        stats = manager.get_stats()
        print("\nBot Statistics:")
        print(f"  Total bots: {stats['total_bots']}")
        print(f"  Active bots: {stats['active_bots']}")
        print("\n  Platforms:")
        for platform, data in stats["platforms"].items():
            primary = f" (primary: {data['primary']})" if data["primary"] else ""
            print(f"    {platform}: {data['active']}/{data['total']} active{primary}")
