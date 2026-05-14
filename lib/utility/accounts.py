#!/usr/bin/env python3
"""
Account Management Utility

List and manage connected Late SDK social media accounts.
"""

import json
import sys


def list_accounts(platform_filter: str | None = None, as_json: bool = False):
    """List all connected social media accounts."""
    from lib.api_clients.late_client import LateDistributionClient

    try:
        client = LateDistributionClient()
        accounts = client.get_accounts()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to connect to Late API: {e}")
        sys.exit(1)

    # Extract account data
    account_list = []
    for acc in accounts:
        platform = getattr(acc, "platform", "unknown").lower()
        account_id = getattr(acc, "field_id", None) or getattr(acc, "id", "unknown")
        name = getattr(acc, "name", "") or getattr(acc, "username", "Unknown")

        if platform_filter and platform != platform_filter.lower():
            continue

        account_list.append(
            {
                "platform": platform,
                "name": name,
                "account_id": account_id,
            }
        )

    if as_json:
        print(json.dumps(account_list, indent=2))
        return

    if not account_list:
        if platform_filter:
            print(f"[INFO] No accounts found for platform: {platform_filter}")
        else:
            print("[INFO] No connected accounts found")
        return

    # Table output
    print(f"\n  Connected Accounts ({len(account_list)})")
    print("  " + "-" * 56)
    print(f"  {'Platform':<18} {'Name':<25} {'Account ID':<15}")
    print("  " + "-" * 56)

    for acc in sorted(account_list, key=lambda x: x["platform"]):
        name_display = acc["name"][:23] + ".." if len(acc["name"]) > 25 else acc["name"]
        id_display = (
            acc["account_id"][:13] + ".."
            if len(str(acc["account_id"])) > 15
            else str(acc["account_id"])
        )
        print(f"  {acc['platform']:<18} {name_display:<25} {id_display:<15}")

    print("  " + "-" * 56)
    print()


def refresh_cache():
    """Clear account cache and re-fetch."""
    from lib.api_clients.late_client import LateDistributionClient

    try:
        client = LateDistributionClient()
        client.clear_cache()
        accounts = client.get_accounts()
        print(f"[SUCCESS] Cache refreshed. {len(accounts)} accounts found.")
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to refresh: {e}")
        sys.exit(1)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Social Slash Account Manager")
    parser.add_argument(
        "--action", choices=["list", "refresh"], default="list", help="Action to perform"
    )
    parser.add_argument("--platform", type=str, default=None, help="Filter by platform")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    args = parser.parse_args()

    if args.action == "list":
        list_accounts(platform_filter=args.platform, as_json=args.as_json)
    elif args.action == "refresh":
        refresh_cache()


if __name__ == "__main__":
    main()
