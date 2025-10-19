#!/usr/bin/env python3
"""
Quick test script for bot_detector module.
Tests detection with various User-Agent strings.
"""

from bot_detector import BotDetector

def main():
    detector = BotDetector()

    # Test cases with known user agents
    test_cases = [
        # Search Engines
        ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Search Engine", "googlebot"),
        ("Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)", "Search Engine", "bingbot"),
        ("Mozilla/5.0 (compatible; Yahoo! Slurp; http://help.yahoo.com/help/us/ysearch/slurp)", "Search Engine", "yahoo! slurp"),

        # Social Media
        ("facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)", "Social Media", "facebookexternalhit"),
        ("Twitterbot/1.0", "Social Media", "twitterbot"),

        # SEO/Analytics
        ("Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/)", "SEO/Analytics", "ahrefsbot"),
        ("Mozilla/5.0 (compatible; SemrushBot/7~bl; +http://www.semrush.com/bot.html)", "SEO/Analytics", "semrushbot"),

        # Monitoring
        ("UptimeRobot/2.0 (http://www.uptimerobot.com/)", "Monitoring", "uptimerobot"),

        # Security
        ("Mozilla/5.0 (compatible; Censys/1.0 (+https://censys.io/))", "Security", "censys"),

        # AI/LLM
        ("Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.0; +https://openai.com/gptbot)", "AI/LLM", "gptbot"),
        ("CCBot/2.0 (https://commoncrawl.org/faq/)", "AI/LLM", "ccbot"),

        # Generic bots
        ("curl/7.68.0", "Other Bot", "curl"),
        ("python-requests/2.28.1", "Other Bot", "python-requests"),

        # Real human browsers (should NOT be detected as bots)
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", None, None),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36", None, None),
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1", None, None),
    ]

    print("=" * 80)
    print("BOT DETECTOR TEST RESULTS")
    print("=" * 80)

    passed = 0
    failed = 0

    for user_agent, expected_category, expected_pattern in test_cases:
        result = detector.detect(user_agent)

        # For human browsers, we expect is_bot=False
        if expected_category is None:
            if not result['is_bot']:
                status = "✓ PASS"
                passed += 1
            else:
                status = "✗ FAIL"
                failed += 1
                print(f"\n{status}: Expected human, got bot")
                print(f"  User-Agent: {user_agent[:80]}")
                print(f"  Result: {result}")
        else:
            # For bots, check category matches
            if result['is_bot'] and result['category'] == expected_category:
                status = "✓ PASS"
                passed += 1
            else:
                status = "✗ FAIL"
                failed += 1
                print(f"\n{status}: Expected {expected_category}, got {result['category']}")
                print(f"  User-Agent: {user_agent[:80]}")
                print(f"  Expected pattern: {expected_pattern}")
                print(f"  Result: {result}")

    print(f"\n{'=' * 80}")
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"{'=' * 80}")

    # Show pattern statistics
    print(f"\nPattern Statistics:")
    stats = detector.get_stats()
    total_patterns = sum(stats.values())
    for category, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category:20s}: {count:3d} patterns")
    print(f"  {'Total':20s}: {total_patterns:3d} patterns")

    return 0 if failed == 0 else 1

if __name__ == '__main__':
    exit(main())
