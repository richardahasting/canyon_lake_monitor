"""
Bot Detection Module

Comprehensive bot/crawler detection with categorization.
Identifies web crawlers, search engines, monitoring services, and other automated traffic.

Categories:
- Search Engines: Google, Bing, Yandex, Baidu, etc.
- Social Media: Facebook, Twitter, LinkedIn, etc.
- Monitoring: UptimeRobot, Pingdom, StatusCake, etc.
- SEO/Analytics: Ahrefs, SEMrush, Moz, Majestic, etc.
- Security: Shodan, Censys, security scanners
- AI/LLM: ChatGPT, Claude, other AI crawlers
- Other: Generic bots and unclassified crawlers

Author: Richard Hasting
"""

import re
from typing import Dict, Optional


class BotDetector:
    """
    Detects and classifies web crawlers and bots based on User-Agent strings.

    Uses comprehensive pattern matching with 200+ known bot signatures.
    Patterns are case-insensitive and organized by category for analytics.
    """

    # Search Engine Crawlers
    SEARCH_ENGINES = [
        r'googlebot',
        r'google-inspectiontool',
        r'googleweblight',
        r'storebot-google',
        r'bingbot',
        r'bingpreview',
        r'msnbot',
        r'duckduckbot',
        r'duckduckgo-favicons-bot',
        r'baiduspider',
        r'yandexbot',
        r'yandexmobilebot',
        r'yahoo! slurp',
        r'yahoomobile',
        r'slurp',
        r'exabot',
        r'sogou',
        r'qwantify',
        r'applebot',
        r'seznambot',
        r'mojeekbot',
        r'startmebot',
        r'cliqzbot',
        r'neevabot',
    ]

    # Social Media Platform Crawlers
    SOCIAL_MEDIA = [
        r'facebookexternalhit',
        r'facebookcatalog',
        r'facebot',
        r'twitterbot',
        r'whatsapp',
        r'linkedinbot',
        r'slackbot',
        r'slackbot-linkexpanding',
        r'telegrambot',
        r'telegram',
        r'discordbot',
        r'pinterestbot',
        r'pinterest',
        r'redditbot',
        r'skypeuripreview',
        r'tumblr',
        r'vkshare',
        r'snapchat',
        r'instagrambot',
        r'embedly',
        r'quora link preview',
        r'outbrain',
        r'flipboard',
        r'applebot',
    ]

    # Monitoring and Uptime Services
    MONITORING = [
        r'uptimerobot',
        r'pingdom',
        r'statuscake',
        r'site24x7',
        r'monitis',
        r'updown\.io',
        r'freshping',
        r'montastic',
        r'nodeping',
        r'hetrixtools',
        r'uptime-kuma',
        r'newrelic',
        r'datadog',
        r'checkly',
        r'better uptime',
        r'oh dear',
        r'ohdear',
    ]

    # SEO and Analytics Crawlers
    SEO_ANALYTICS = [
        r'ahrefsbot',
        r'semrushbot',
        r'semrush',
        r'mj12bot',
        r'majestic12',
        r'dotbot',
        r'screaming frog',
        r'seobilitybot',
        r'serpstatbot',
        r'linkpadbot',
        r'seokicks',
        r'xovibot',
        r'searchmetricsbot',
        r'pr-cy\.ru',
        r'spbot',
        r'crawler4j',
        r'rogerbot',
        r'moz\.com',
        r'spyfu',
        r'cognitiveseo',
        r'cludo\.com',
        r'lumar',
        r'deepcrawl',
        r'oncrawlbot',
        r'botify',
        r'siteimprove',
    ]

    # Security Scanners and Research
    SECURITY = [
        r'shodan',
        r'censys',
        r'nmap scripting engine',
        r'masscan',
        r'zgrab',
        r'nuclei',
        r'acunetix',
        r'netsparker',
        r'qualys',
        r'rapid7',
        r'openvas',
        r'nikto',
        r'w3af',
        r'metis',
        r'burpcollaborator',
        r'nessus',
        r'security',
        r'pentest',
        r'scanner',
    ]

    # AI/LLM Crawlers
    AI_LLM = [
        r'gptbot',
        r'chatgpt',
        r'claude-web',
        r'claudebot',
        r'anthropic-ai',
        r'cohere-ai',
        r'perplexitybot',
        r'youbot',
        r'diffbot',
        r'omgili',
        r'omgilibot',
        r'ccbot',
        r'common crawl',
        r'iaskspider',
        r'petalsearch',
        r'bytespider',
    ]

    # Generic and Other Bots
    GENERIC_BOTS = [
        # Archiving
        r'archive\.org_bot',
        r'ia_archiver',
        r'wayback',
        r'wget',
        r'curl',
        r'httpie',
        r'python-requests',
        r'python-urllib',
        r'go-http-client',
        r'okhttp',
        r'axios',
        r'java/',
        r'jersey/',

        # Feed Readers
        r'feedfetcher',
        r'feedly',
        r'newsblur',
        r'inoreader',
        r'theoldreader',
        r'feedbin',
        r'rssowl',

        # Link Checkers
        r'w3c_validator',
        r'w3c_checklink',
        r'validator\.nu',
        r'deadlinkchecker',
        r'linkchecker',

        # WordPress
        r'jetpack',
        r'wordpress\.com',

        # Headless Browsers
        r'headlesschrome',
        r'chrome-lighthouse',
        r'phantomjs',
        r'selenium',
        r'puppeteer',
        r'playwright',

        # Generic indicators
        r'\bbot\b',
        r'\bcrawl',
        r'\bspider\b',
        r'\bscraper\b',
        r'http client',
        r'fetcher',
        r'checker',
        r'monitoring',
        r'scraping',
        r'indexer',
        r'aggregator',
        r'preview',
    ]

    def __init__(self):
        """Initialize the bot detector with compiled regex patterns."""
        self.patterns = {
            'Search Engine': [re.compile(pattern, re.IGNORECASE) for pattern in self.SEARCH_ENGINES],
            'Social Media': [re.compile(pattern, re.IGNORECASE) for pattern in self.SOCIAL_MEDIA],
            'Monitoring': [re.compile(pattern, re.IGNORECASE) for pattern in self.MONITORING],
            'SEO/Analytics': [re.compile(pattern, re.IGNORECASE) for pattern in self.SEO_ANALYTICS],
            'Security': [re.compile(pattern, re.IGNORECASE) for pattern in self.SECURITY],
            'AI/LLM': [re.compile(pattern, re.IGNORECASE) for pattern in self.AI_LLM],
            'Other Bot': [re.compile(pattern, re.IGNORECASE) for pattern in self.GENERIC_BOTS],
        }

    def detect(self, user_agent: str) -> Dict[str, Optional[str]]:
        """
        Detect if the User-Agent string represents a bot and classify it.

        Args:
            user_agent: The HTTP User-Agent header string

        Returns:
            Dictionary with keys:
                - is_bot: Boolean indicating if this is a bot
                - category: String category name if bot, None if human
                - matched_pattern: The specific pattern that matched, None if human

        Examples:
            >>> detector = BotDetector()
            >>> detector.detect("Mozilla/5.0 (compatible; Googlebot/2.1)")
            {'is_bot': True, 'category': 'Search Engine', 'matched_pattern': 'googlebot'}

            >>> detector.detect("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            {'is_bot': False, 'category': None, 'matched_pattern': None}
        """
        if not user_agent:
            return {'is_bot': False, 'category': None, 'matched_pattern': None}

        # Check each category in priority order
        # (More specific categories first, generic last)
        for category, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                match = pattern.search(user_agent)
                if match:
                    return {
                        'is_bot': True,
                        'category': category,
                        'matched_pattern': match.group(0).lower()
                    }

        # No match found - likely human
        return {'is_bot': False, 'category': None, 'matched_pattern': None}

    def is_bot(self, user_agent: str) -> bool:
        """
        Simple boolean check if User-Agent is a bot.

        Args:
            user_agent: The HTTP User-Agent header string

        Returns:
            True if bot detected, False if human
        """
        return self.detect(user_agent)['is_bot']

    def get_category(self, user_agent: str) -> Optional[str]:
        """
        Get the bot category for a User-Agent.

        Args:
            user_agent: The HTTP User-Agent header string

        Returns:
            Category string if bot detected, None if human
        """
        return self.detect(user_agent)['category']

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about available bot detection patterns.

        Returns:
            Dictionary with pattern counts per category
        """
        return {
            category: len(pattern_list)
            for category, pattern_list in self.patterns.items()
        }


# Module-level singleton for efficiency
_detector = BotDetector()


def detect_bot(user_agent: str) -> Dict[str, Optional[str]]:
    """
    Module-level convenience function for bot detection.

    Args:
        user_agent: The HTTP User-Agent header string

    Returns:
        Dictionary with is_bot, category, and matched_pattern keys
    """
    return _detector.detect(user_agent)


def is_bot(user_agent: str) -> bool:
    """
    Module-level convenience function for simple bot check.

    Args:
        user_agent: The HTTP User-Agent header string

    Returns:
        True if bot detected, False if human
    """
    return _detector.is_bot(user_agent)


def get_bot_category(user_agent: str) -> Optional[str]:
    """
    Module-level convenience function to get bot category.

    Args:
        user_agent: The HTTP User-Agent header string

    Returns:
        Category string if bot detected, None if human
    """
    return _detector.get_category(user_agent)
