"""Raid detection infrastructure for tracking join patterns and account age distribution."""
import logging
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
import discord

logger = logging.getLogger(__name__)


class JoinTracker:
    """Track member joins within a sliding time window using deque for O(1) operations.

    Uses collections.deque for O(1) append/popleft operations. Stores (timestamp, member)
    tuples to enable time-based filtering and automatic cleanup of expired entries.
    """

    def __init__(self, window_seconds: int = 30):
        """Initialize join tracker with configurable time window.

        Args:
            window_seconds: Length of sliding window in seconds (default: 30)
        """
        self.window_seconds = window_seconds
        # dict[guild_id] -> deque of (timestamp, member) tuples
        self.guild_joins: Dict[int, deque] = {}
        logger.info(f"JoinTracker initialized with {window_seconds}s window")

    def add_join(self, guild_id: int, member: discord.Member) -> None:
        """Add a member join to the tracking window.

        Automatically cleans up expired entries to prevent memory leak.

        Args:
            guild_id: Discord guild ID
            member: Member who joined
        """
        now = datetime.now(timezone.utc)

        # Initialize deque for this guild if not exists
        if guild_id not in self.guild_joins:
            self.guild_joins[guild_id] = deque()

        # Add join to deque
        self.guild_joins[guild_id].append((now, member))

        # Clean up expired entries
        self._cleanup_expired(guild_id)

        logger.debug(f"Tracked join for {member.name} in guild {guild_id}")

    def get_recent_joins(self, guild_id: int) -> List[discord.Member]:
        """Get list of members who joined within the time window.

        Cleans expired entries before returning results.

        Args:
            guild_id: Discord guild ID

        Returns:
            List of members who joined within window
        """
        if guild_id not in self.guild_joins:
            return []

        # Clean up expired entries first
        self._cleanup_expired(guild_id)

        # Return member list (second element of each tuple)
        return [member for _, member in self.guild_joins[guild_id]]

    def get_join_count(self, guild_id: int) -> int:
        """Get count of joins within the time window.

        Args:
            guild_id: Discord guild ID

        Returns:
            Number of joins in window
        """
        if guild_id not in self.guild_joins:
            return 0

        # Clean up expired entries first
        self._cleanup_expired(guild_id)

        return len(self.guild_joins[guild_id])

    def _cleanup_expired(self, guild_id: int) -> None:
        """Remove entries older than the cutoff time using popleft() for O(1) operation.

        Uses deque.popleft() to efficiently remove old entries from the front
        of the deque. This prevents memory leak from accumulating stale join records.

        Args:
            guild_id: Discord guild ID to clean up
        """
        if guild_id not in self.guild_joins:
            return

        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.window_seconds)
        join_deque = self.guild_joins[guild_id]

        # Remove expired entries from front of deque
        # Deque is ordered by time, so we only need to pop from left until we hit valid entry
        while join_deque and join_deque[0][0] < cutoff_time:
            join_deque.popleft()

        # Remove guild entry if deque is now empty (memory cleanup)
        if not join_deque:
            del self.guild_joins[guild_id]


def analyze_account_age_distribution(
    members: List[discord.Member],
    threshold_days: int = 7
) -> Dict[str, any]:
    """Analyze account age distribution for a list of members.

    Calculates the percentage of accounts created within the threshold period.
    Uses timezone.utc for all datetime comparisons to avoid timezone issues.

    Args:
        members: List of Discord members to analyze
        threshold_days: Age threshold in days (default: 7)

    Returns:
        Dict with keys:
            - total: Total number of members analyzed
            - new_accounts: Count of accounts under threshold
            - percentage: Percentage of new accounts (0-100)
            - threshold_days: Threshold used for analysis
    """
    if not members:
        return {
            "total": 0,
            "new_accounts": 0,
            "percentage": 0.0,
            "threshold_days": threshold_days
        }

    now = datetime.now(timezone.utc)
    new_account_count = 0

    for member in members:
        # Calculate account age in days
        account_age_days = (now - member.created_at).days

        if account_age_days < threshold_days:
            new_account_count += 1

    total = len(members)
    percentage = (new_account_count / total) * 100 if total > 0 else 0.0

    result = {
        "total": total,
        "new_accounts": new_account_count,
        "percentage": percentage,
        "threshold_days": threshold_days
    }

    logger.debug(f"Account age analysis: {new_account_count}/{total} ({percentage:.1f}%) under {threshold_days} days")

    return result
