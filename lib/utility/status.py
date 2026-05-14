#!/usr/bin/env python3
"""
Project Status Utility

Aggregates connected accounts, bot accounts, recent activity, and API health.
"""

import json
import os
from pathlib import Path


def show_accounts_status():
    """Show connected account count and list."""
    from lib.api_clients.late_client import LateDistributionClient

    try:
        client = LateDistributionClient()
        accounts = client.get_accounts()

        platforms = {}
        for acc in accounts:
            platform = getattr(acc, "platform", "unknown").lower()
            name = getattr(acc, "name", "") or getattr(acc, "username", "Unknown")
            platforms[platform] = name

        print(f"\n  Connected Accounts: {len(platforms)}")
        print("  " + "-" * 40)
        for platform, name in sorted(platforms.items()):
            print(f"    {platform:<18} {name}")
        print("  " + "-" * 40)

    except ValueError as e:
        print(f"  [ERROR] Late API: {e}")
    except Exception as e:
        print(f"  [ERROR] Failed to fetch accounts: {e}")


def show_bots_status():
    """Show bot account status from engagement database."""
    try:
        from lib.storage.database import EngagementDatabase

        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "engagement.db"

        if not db_path.exists():
            print("\n  Bot Accounts: No engagement database found")
            return

        db = EngagementDatabase(str(db_path))
        bots = db.get_bot_accounts()

        if not bots:
            print("\n  Bot Accounts: None configured")
            return

        active = [b for b in bots if getattr(b, "is_active", False)]
        print(f"\n  Bot Accounts: {len(active)} active / {len(bots)} total")
        print("  " + "-" * 40)
        for bot in bots:
            platform = getattr(bot, "platform", "unknown")
            name = getattr(bot, "name", "Unknown")
            is_active = getattr(bot, "is_active", False)
            is_primary = getattr(bot, "is_primary", False)
            status = "ACTIVE" if is_active else "INACTIVE"
            primary = " (PRIMARY)" if is_primary else ""
            print(f"    {platform:<15} {name:<20} {status}{primary}")
        print("  " + "-" * 40)

    except ImportError:
        print("\n  Bot Accounts: Engagement module not available")
    except Exception as e:
        print(f"\n  Bot Accounts: Error - {e}")


def show_api_status():
    """Check API connectivity."""
    print("\n  API Health Check")
    print("  " + "-" * 40)

    # Late API
    late_key = os.getenv("LATE_API_KEY")
    if late_key:
        try:
            from lib.api_clients.late_client import LateDistributionClient

            client = LateDistributionClient()
            accounts = client.get_accounts()
            print(f"    Late API:     OK ({len(accounts)} accounts)")
        except Exception as e:
            print(f"    Late API:     FAIL ({e})")
    else:
        print("    Late API:     NOT CONFIGURED (LATE_API_KEY missing)")

    # Gemini API
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        print("    Gemini API:   CONFIGURED (key present)")
    else:
        print("    Gemini API:   NOT CONFIGURED")

    # Anthropic API
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        print("    Anthropic:    CONFIGURED (key present)")
    else:
        print("    Anthropic:    NOT CONFIGURED")

    print("  " + "-" * 40)


def show_all(as_json: bool = False):
    """Show complete project status."""
    if as_json:
        status = collect_status_json()
        print(json.dumps(status, indent=2, default=str))
        return

    print()
    print("  ===========================================================")
    print("            Social Slash - Project Status")
    print("  ===========================================================")

    show_accounts_status()
    show_bots_status()
    show_api_status()
    print()


def collect_status_json():
    """Collect all status data as a dictionary."""
    status = {
        "accounts": [],
        "bots": [],
        "api": {},
    }

    # Accounts
    try:
        from lib.api_clients.late_client import LateDistributionClient

        client = LateDistributionClient()
        accounts = client.get_accounts()
        for acc in accounts:
            status["accounts"].append(
                {
                    "platform": getattr(acc, "platform", "unknown"),
                    "name": getattr(acc, "name", "") or getattr(acc, "username", ""),
                    "id": getattr(acc, "field_id", None) or getattr(acc, "id", ""),
                }
            )
    except Exception as e:
        status["accounts_error"] = str(e)

    # Bots
    try:
        from lib.storage.database import EngagementDatabase

        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "engagement.db"
        if db_path.exists():
            db = EngagementDatabase(str(db_path))
            bots = db.get_bot_accounts()
            for bot in bots:
                status["bots"].append(
                    {
                        "platform": getattr(bot, "platform", "unknown"),
                        "name": getattr(bot, "name", ""),
                        "active": getattr(bot, "is_active", False),
                        "primary": getattr(bot, "is_primary", False),
                    }
                )
    except Exception:
        pass

    # API status
    status["api"]["late"] = bool(os.getenv("LATE_API_KEY"))
    status["api"]["gemini"] = bool(os.getenv("GOOGLE_API_KEY"))
    status["api"]["anthropic"] = bool(os.getenv("ANTHROPIC_API_KEY"))

    return status


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Social Slash Status")
    parser.add_argument(
        "--section",
        choices=["all", "accounts", "bots", "api"],
        default="all",
        help="Status section to display",
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    args = parser.parse_args()

    if args.section == "all":
        show_all(as_json=args.as_json)
    elif args.section == "accounts":
        if args.as_json:
            status = collect_status_json()
            print(json.dumps({"accounts": status["accounts"]}, indent=2, default=str))
        else:
            show_accounts_status()
    elif args.section == "bots":
        if args.as_json:
            status = collect_status_json()
            print(json.dumps({"bots": status["bots"]}, indent=2, default=str))
        else:
            show_bots_status()
    elif args.section == "api":
        if args.as_json:
            status = collect_status_json()
            print(json.dumps({"api": status["api"]}, indent=2, default=str))
        else:
            show_api_status()


if __name__ == "__main__":
    main()
