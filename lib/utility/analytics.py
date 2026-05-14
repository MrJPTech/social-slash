#!/usr/bin/env python3
"""
Analytics Utility

View post status, engagement metrics, and recent activity.
"""

import json
import sys


def show_recent_posts(platform_filter: str | None = None, limit: int = 10, as_json: bool = False):
    """Show recent posts with status."""
    from lib.api_clients.late_client import LateDistributionClient

    try:
        client = LateDistributionClient()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    try:
        response = client.client.posts.list()
        posts = response.posts if hasattr(response, "posts") else []
    except Exception as e:
        print(f"[ERROR] Failed to fetch posts: {e}")
        sys.exit(1)

    # Extract post data
    post_list = []
    for post in posts:
        post_id = getattr(post, "field_id", None) or getattr(post, "id", "unknown")
        content = getattr(post, "content", "")[:60]
        status = getattr(post, "status", "unknown")
        created = getattr(post, "created_at", "") or getattr(post, "createdAt", "")

        # Get platforms from post
        platforms_data = getattr(post, "platforms", []) or []
        platforms = []
        for p in platforms_data:
            if isinstance(p, dict):
                platforms.append(p.get("platform", "unknown"))
            else:
                platforms.append(getattr(p, "platform", "unknown"))

        if platform_filter:
            if platform_filter.lower() not in [p.lower() for p in platforms]:
                continue

        post_list.append(
            {
                "id": str(post_id),
                "content": content,
                "status": status,
                "platforms": platforms,
                "created_at": str(created)[:19] if created else "",
            }
        )

    post_list = post_list[:limit]

    if as_json:
        print(json.dumps(post_list, indent=2))
        return

    if not post_list:
        print("[INFO] No recent posts found")
        return

    print(f"\n  Recent Posts ({len(post_list)})")
    print("  " + "-" * 70)
    print(f"  {'ID':<12} {'Status':<12} {'Platforms':<20} {'Content':<28}")
    print("  " + "-" * 70)

    for post in post_list:
        platforms_str = ", ".join(post["platforms"][:3])
        if len(post["platforms"]) > 3:
            platforms_str += f" +{len(post['platforms']) - 3}"
        content_display = post["content"].replace("\n", " ")[:26]
        id_display = post["id"][:10] + ".." if len(post["id"]) > 12 else post["id"]
        print(f"  {id_display:<12} {post['status']:<12} {platforms_str:<20} {content_display:<28}")

    print("  " + "-" * 70)
    print()


def show_post_details(post_id: str, as_json: bool = False):
    """Show detailed status and analytics for a single post."""
    from lib.api_clients.late_client import LateDistributionClient

    try:
        client = LateDistributionClient()
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    try:
        post = client.get_post_status(post_id)
    except Exception as e:
        print(f"[ERROR] Failed to get post: {e}")
        sys.exit(1)

    if as_json:
        if hasattr(post, "model_dump"):
            print(json.dumps(post.model_dump(), indent=2, default=str))
        elif isinstance(post, dict):
            print(json.dumps(post, indent=2, default=str))
        else:
            print(json.dumps({"raw": str(post)}, indent=2))
        return

    # Display post details
    content = (
        getattr(post, "content", str(post))
        if not isinstance(post, dict)
        else post.get("content", str(post))
    )
    status = (
        getattr(post, "status", "unknown")
        if not isinstance(post, dict)
        else post.get("status", "unknown")
    )

    print(f"\n  Post Details: {post_id}")
    print("  " + "-" * 50)
    print(f"  Status: {status}")
    print(f"  Content: {str(content)[:200]}")
    print("  " + "-" * 50)

    # Try to get analytics
    try:
        analytics = client.get_analytics(post_id)
        print("\n  Analytics:")
        if isinstance(analytics, dict):
            for key, value in analytics.items():
                print(f"    {key}: {value}")
        elif hasattr(analytics, "model_dump"):
            for key, value in analytics.model_dump().items():
                print(f"    {key}: {value}")
        else:
            print(f"    {analytics}")
    except Exception:
        print("  [INFO] Analytics not available for this post")

    print()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Social Slash Analytics")
    parser.add_argument(
        "--action", choices=["recent", "post"], default="recent", help="Action to perform"
    )
    parser.add_argument("--post-id", type=str, default=None, help="Post ID for detail view")
    parser.add_argument("--platform", type=str, default=None, help="Filter by platform")
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of recent posts (default: 10)"
    )
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")

    args = parser.parse_args()

    if args.action == "recent":
        show_recent_posts(
            platform_filter=args.platform,
            limit=args.limit,
            as_json=args.as_json,
        )
    elif args.action == "post":
        if not args.post_id:
            print("[ERROR] --post-id required for post action")
            sys.exit(1)
        show_post_details(args.post_id, as_json=args.as_json)


if __name__ == "__main__":
    main()
