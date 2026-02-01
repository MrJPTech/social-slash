#!/usr/bin/env python3
"""
Test API Connection Script

Verifies that Late API and Gemini API credentials are working correctly.
"""

import os
import sys

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from dotenv import load_dotenv
load_dotenv('.env.local')


def test_late_api():
    """Test Late API connection."""
    print("\n" + "=" * 50)
    print("Testing Late API Connection")
    print("=" * 50)

    try:
        from api_clients.late_client import LateDistributionClient

        client = LateDistributionClient()
        print("[SUCCESS] Late client initialized")

        accounts = client.get_accounts()
        print(f"[INFO] Connected accounts: {len(accounts)}")

        for acc in accounts:
            # Handle SocialAccount objects from Late SDK
            platform = getattr(acc, 'platform', 'unknown')
            name = getattr(acc, 'displayName', None) or getattr(acc, 'username', 'Unknown')
            print(f"  - {platform}: {name}")

        return True

    except Exception as e:
        print(f"[ERROR] Late API test failed: {e}")
        return False


def test_gemini_api():
    """Test Gemini API connection."""
    print("\n" + "=" * 50)
    print("Testing Gemini API Connection")
    print("=" * 50)

    try:
        from ai.gemini_client import GeminiClient

        client = GeminiClient()
        print("[SUCCESS] Gemini client initialized")

        # Quick test with a simple prompt
        result = client.generate_hashtags(
            content="Testing social media automation",
            platform="linkedin",
            count=3
        )

        print(f"[INFO] Generated hashtags: {result}")
        return True

    except ImportError as e:
        print(f"[WARNING] Gemini package not available: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Gemini API test failed: {e}")
        return False


def main():
    """Run all API tests."""
    print("\n" + "#" * 50)
    print("# Social Slash - API Connection Test")
    print("#" * 50)

    late_ok = test_late_api()
    gemini_ok = test_gemini_api()

    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"  Late API:   {'PASS' if late_ok else 'FAIL'}")
    print(f"  Gemini API: {'PASS' if gemini_ok else 'FAIL'}")
    print()

    return 0 if (late_ok and gemini_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
