"""Idempotent infrastructure initialization for Guardian bot."""
import logging
import discord

logger = logging.getLogger(__name__)


async def ensure_role_exists(guild: discord.Guild, role_name: str) -> discord.Role:
    """Create role if it doesn't exist (idempotent).

    Args:
        guild: Discord guild to create role in
        role_name: Name of the role to create

    Returns:
        The role object (existing or newly created)
    """
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        logger.info(f"Role '{role_name}' already exists in {guild.name}")
        return role

    role = await guild.create_role(name=role_name, reason="Guardian initialization")
    logger.info(f"Created role '{role_name}' in {guild.name}")
    return role


async def ensure_channel_exists(
    guild: discord.Guild,
    channel_name: str,
    overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] | None = None
) -> discord.TextChannel:
    """Create text channel if it doesn't exist (idempotent).

    Args:
        guild: Discord guild to create channel in
        channel_name: Name of the channel to create
        overwrites: Optional permission overwrites for the channel

    Returns:
        The channel object (existing or newly created)
    """
    channel = discord.utils.get(guild.channels, name=channel_name)
    if channel:
        logger.info(f"Channel '#{channel_name}' already exists in {guild.name}")
        return channel

    channel = await guild.create_text_channel(
        channel_name,
        overwrites=overwrites,
        reason="Guardian initialization"
    )
    logger.info(f"Created channel '#{channel_name}' in {guild.name}")
    return channel


async def initialize_infrastructure(guild: discord.Guild) -> dict[str, discord.TextChannel]:
    """Initialize all required roles and channels for Guardian (idempotent).

    Creates:
    - @Unverified role
    - @Verified role
    - #verify channel (visible only to @Unverified)
    - #security-logs channel

    Args:
        guild: Discord guild to initialize

    Returns:
        Dictionary with channel references: {"verify": channel, "security_logs": channel}
    """
    logger.info(f"Initializing Guardian infrastructure for {guild.name}")

    # Create roles
    unverified_role = await ensure_role_exists(guild, "Unverified")
    verified_role = await ensure_role_exists(guild, "Verified")

    # Create #verify channel with permission overwrites
    # - @everyone: cannot see channel
    # - @Unverified: can see and send messages
    # - @Verified: cannot see channel (they've already verified)
    verify_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        unverified_role: discord.PermissionOverwrite(view_channel=True),
        verified_role: discord.PermissionOverwrite(view_channel=False),
    }
    verify_channel = await ensure_channel_exists(guild, "verify", overwrites=verify_overwrites)

    # Create #security-logs channel (no special permissions)
    security_logs_channel = await ensure_channel_exists(guild, "security-logs")

    logger.info(f"Guardian infrastructure initialized for {guild.name}")

    return {
        "verify": verify_channel,
        "security_logs": security_logs_channel,
    }
