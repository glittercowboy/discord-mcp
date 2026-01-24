"""Configuration persistence with hot-reload support.

Implements JSON-based configuration storage with atomic writes and
file-based hot-reload for account restrictions.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration file location
CONFIG_FILE = Path("config/guardian.json")

# Default configuration for new guilds
DEFAULT_CONFIG = {
    "threshold_days": 7,
    "features": {
        "urls": True,
        "attachments": True,
        "role_mentions": True
    },
    "exempt_roles": []
}


def load_config(guild_id: int) -> dict:
    """Load configuration for guild with hot-reload support.

    Reads configuration from disk on each call to support runtime
    updates without bot restart. Returns default config if file
    doesn't exist or guild not found.

    Args:
        guild_id: Discord guild ID to load config for

    Returns:
        Configuration dict with threshold_days, features, exempt_roles

    Example:
        >>> config = load_config(123456789)
        >>> threshold = config["threshold_days"]  # 7
    """
    # Return default if config file doesn't exist
    if not CONFIG_FILE.exists():
        logger.debug(f"Config file not found, using defaults for guild {guild_id}")
        return DEFAULT_CONFIG.copy()

    try:
        # Read config from file (hot-reload: reads every time)
        with CONFIG_FILE.open("r") as f:
            all_config = json.load(f)

        # Return guild-specific config or default
        guild_key = str(guild_id)
        if guild_key in all_config:
            logger.debug(f"Loaded config for guild {guild_id}")
            return all_config[guild_key]
        else:
            logger.debug(f"Guild {guild_id} not in config, using defaults")
            return DEFAULT_CONFIG.copy()

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config file: {e}")
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Unexpected error loading config for guild {guild_id}: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(guild_id: int, config: dict) -> None:
    """Save configuration for guild with atomic write.

    Uses temp file + rename pattern to prevent corruption during write.
    Creates config directory if it doesn't exist.

    Args:
        guild_id: Discord guild ID to save config for
        config: Configuration dict to persist

    Raises:
        Exception: If write fails (logged but not re-raised)

    Example:
        >>> config = {"threshold_days": 14, "features": {...}, "exempt_roles": [...]}
        >>> save_config(123456789, config)
    """
    temp_file = CONFIG_FILE.with_suffix(".tmp")

    try:
        # Create config directory if needed
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config for all guilds
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open("r") as f:
                all_config = json.load(f)
        else:
            all_config = {}

        # Update config for this guild
        all_config[str(guild_id)] = config

        # Atomic write: write to temp file, then rename
        with temp_file.open("w") as f:
            json.dump(all_config, f, indent=2)

        # Atomic rename (overwrites existing file)
        temp_file.replace(CONFIG_FILE)

        logger.info(f"Saved config for guild {guild_id}")

    except Exception as e:
        logger.error(f"Failed to save config for guild {guild_id}: {e}")
        # Clean up temp file on error
        temp_file.unlink(missing_ok=True)
        raise
