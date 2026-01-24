"""Blocklist loading and domain matching for phishing detection.

Loads community-maintained phishing domain blocklist and provides
O(1) lookup with subdomain matching support.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BlocklistMatcher:
    """Load and match domains against phishing blocklist.

    Loads blocklist from JSON file into memory set for O(1) lookup.
    Supports both exact domain matches and subdomain matches
    (e.g., cdn.phishing.com matches if phishing.com is blocklisted).

    Attributes:
        blocklist_path: Path to blocklist JSON file
        domains: Set of lowercase blocklisted domains
    """

    def __init__(self, blocklist_path: Path):
        """Initialize blocklist matcher and load domains.

        Args:
            blocklist_path: Path to blocklist.json file
        """
        self.blocklist_path = blocklist_path
        self.domains: set[str] = set()
        self.load_blocklist()

    def load_blocklist(self) -> None:
        """Load blocklist from file into memory set.

        Handles two JSON formats:
        - Object with "domains" key: {"domains": ["example.com", ...]}
        - Flat array: ["example.com", "phishing.net", ...]

        Domains are stored as lowercase for case-insensitive matching.
        """
        try:
            if not self.blocklist_path.exists():
                logger.warning(f"Blocklist not found at {self.blocklist_path}")
                return

            with open(self.blocklist_path, 'r') as f:
                data = json.load(f)

            # Handle both object and array formats
            if isinstance(data, dict):
                domains = data.get("domains", [])
            elif isinstance(data, list):
                domains = data
            else:
                logger.error(f"Unexpected blocklist format: {type(data)}")
                return

            # Store as lowercase set for case-insensitive matching
            self.domains = set(d.lower() for d in domains if isinstance(d, str))
            logger.info(f"Loaded {len(self.domains)} domains from blocklist")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse blocklist JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to load blocklist: {e}")

    def is_blocklisted(self, domain: str) -> bool:
        """Check if domain is in blocklist.

        Checks both exact match and parent domain matches. For example:
        - "discord.com" matches if "discord.com" is blocklisted
        - "cdn.phishing.com" matches if "phishing.com" is blocklisted
        - "api.cdn.phishing.com" matches if "phishing.com" or "cdn.phishing.com" is blocklisted

        Args:
            domain: Domain to check (e.g., "discord-scam.com")

        Returns:
            True if domain or any parent domain is blocklisted, False otherwise

        Example:
            >>> matcher = BlocklistMatcher(Path("blocklist.json"))
            >>> matcher.is_blocklisted("phishing.com")
            True
            >>> matcher.is_blocklisted("cdn.phishing.com")
            True  # Matches parent domain
            >>> matcher.is_blocklisted("legitimate.com")
            False
        """
        if not domain:
            return False

        domain_lower = domain.lower()

        # Exact match check
        if domain_lower in self.domains:
            logger.debug(f"Domain {domain} matched exactly in blocklist")
            return True

        # Subdomain check: cdn.phishing.com should match phishing.com
        parts = domain_lower.split('.')
        for i in range(1, len(parts)):
            parent_domain = '.'.join(parts[i:])
            if parent_domain in self.domains:
                logger.debug(f"Domain {domain} matched by parent {parent_domain}")
                return True

        return False
