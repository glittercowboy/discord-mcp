"""Message filtering logic for new Discord accounts.

Implements content violation detection (URLs, attachments, role mentions)
for accounts below configurable age threshold.
"""
import logging
import re
from datetime import datetime, timezone
import discord

logger = logging.getLogger(__name__)

# Pre-compile URL regex for performance during high message volume
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')


def get_account_age_days(user: discord.User) -> float:
    """Calculate account age in days from user creation timestamp.

    Uses timezone-aware datetime comparison to handle Discord's UTC timestamps.

    Args:
        user: Discord user to check

    Returns:
        Account age in days (fractional)

    Example:
        >>> user = discord.User(created_at=datetime(2026, 1, 17, tzinfo=timezone.utc))
        >>> get_account_age_days(user)  # On 2026-01-24
        7.0
    """
    now = datetime.now(timezone.utc)
    age_seconds = (now - user.created_at).total_seconds()
    age_days = age_seconds / 86400

    logger.debug(f"Account {user.name} age: {age_days:.2f} days")
    return age_days


def check_content_violations(message: discord.Message) -> list[str]:
    """Detect content violations in message.

    Checks for restricted content types:
    - URLs (http://, https://, www.)
    - Attachments (images, files, etc.)
    - @everyone or @here mentions
    - Role mentions

    Args:
        message: Discord message to check

    Returns:
        List of violation types found (e.g., ["URLs", "Attachments"])
        Empty list if no violations detected

    Example:
        >>> violations = check_content_violations(message)
        >>> if violations:
        ...     print(f"Violations: {', '.join(violations)}")
    """
    violations = []

    # Check for attachments
    if message.attachments:
        violations.append("Attachments")
        logger.debug(f"Message {message.id} contains {len(message.attachments)} attachment(s)")

    # Check for @everyone or @here
    if message.mention_everyone:
        violations.append("@everyone/@here")
        logger.debug(f"Message {message.id} contains @everyone/@here mention")

    # Check for role mentions
    if message.raw_role_mentions:
        violations.append("Role mentions")
        logger.debug(f"Message {message.id} contains {len(message.raw_role_mentions)} role mention(s)")

    # Check for URLs
    if URL_PATTERN.search(message.content):
        violations.append("URLs")
        logger.debug(f"Message {message.id} contains URL(s)")

    return violations


def is_account_exempt(member: discord.Member, config: dict) -> bool:
    """Check if account is exempt from restrictions.

    Accounts are exempt if:
    - Member has Nitro boost active (premium_since is set)
    - Member has any role ID in exempt_roles config list

    Args:
        member: Discord member to check
        config: Configuration dict with optional exempt_roles list

    Returns:
        True if member is exempt from restrictions, False otherwise

    Example:
        >>> config = {"exempt_roles": [123456789]}
        >>> is_exempt = is_account_exempt(member, config)
    """
    # Check Nitro booster status
    if member.premium_since is not None:
        logger.debug(f"Member {member.name} exempt: Nitro booster")
        return True

    # Check exempt roles
    exempt_role_ids = config.get("exempt_roles", [])
    member_role_ids = [role.id for role in member.roles]

    for role_id in exempt_role_ids:
        if role_id in member_role_ids:
            logger.debug(f"Member {member.name} exempt: has exempt role {role_id}")
            return True

    logger.debug(f"Member {member.name} not exempt")
    return False
