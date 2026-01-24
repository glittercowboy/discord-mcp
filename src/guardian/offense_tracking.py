"""Per-user offense tracking for link scanning violations.

Tracks number of violations per user with JSON persistence and atomic
writes for escalating punishment (1st offense: timeout, 2nd: ban).
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class OffenseTracker:
    """Track per-user link scanning offenses for escalating punishment.

    Persists offense counts and violation history to JSON file with
    atomic writes. Survives bot restarts to enable proper 2nd offense
    auto-ban enforcement.

    Attributes:
        tracking_file: Path to offenses.json file
    """

    def __init__(self, tracking_file: Path):
        """Initialize offense tracker.

        Creates parent directory if it doesn't exist.

        Args:
            tracking_file: Path to offenses.json file
        """
        self.tracking_file = tracking_file
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

    def get_offense_count(self, user_id: int) -> int:
        """Get number of offenses for user.

        Args:
            user_id: Discord user ID

        Returns:
            Number of prior offenses (0 if no prior offenses or file doesn't exist)

        Example:
            >>> tracker = OffenseTracker(Path("offenses.json"))
            >>> count = tracker.get_offense_count(123456789)
            >>> count
            0  # First time offender
        """
        try:
            if not self.tracking_file.exists():
                return 0

            with open(self.tracking_file, 'r') as f:
                data = json.load(f)

            user_key = str(user_id)
            if user_key in data:
                return data[user_key].get("count", 0)
            return 0

        except json.JSONDecodeError:
            logger.warning("Offense tracking file corrupted, resetting")
            return 0
        except Exception as e:
            logger.error(f"Failed to get offense count: {e}")
            return 0

    def record_offense(
        self,
        user_id: int,
        message_id: int,
        domain: str
    ) -> int:
        """Record a link scanning violation for user.

        Increments offense count, stores violation details (timestamp,
        message_id, domain), and writes atomically to prevent corruption.
        Keeps last 10 offenses per user to prevent unbounded growth.

        Args:
            user_id: Discord user ID
            message_id: Discord message ID that violated
            domain: Blocklisted domain found

        Returns:
            Total offense count after recording (1 for first offense, 2 for second, etc.)

        Example:
            >>> tracker = OffenseTracker(Path("offenses.json"))
            >>> count = tracker.record_offense(123456789, 987654321, "phishing.com")
            >>> count
            1  # First offense
        """
        try:
            # Load existing data
            if self.tracking_file.exists():
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}

            user_key = str(user_id)
            if user_key not in data:
                data[user_key] = {"count": 0, "offenses": []}

            # Increment count
            data[user_key]["count"] += 1
            current_count = data[user_key]["count"]

            # Record offense details for evidence and audit trail
            data[user_key]["offenses"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": message_id,
                "domain": domain
            })

            # Keep only last 10 offenses per user to prevent unbounded growth
            if len(data[user_key]["offenses"]) > 10:
                data[user_key]["offenses"] = data[user_key]["offenses"][-10:]

            # Atomic write: write to temp file, then rename
            # (Matches config_manager.py pattern from Phase 3)
            temp_file = self.tracking_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.tracking_file)

            logger.info(f"Recorded offense {current_count} for user {user_id} (domain: {domain})")
            return current_count

        except Exception as e:
            logger.error(f"Failed to record offense: {e}")
            return 0
