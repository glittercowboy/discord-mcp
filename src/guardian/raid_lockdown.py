"""Raid lockdown management with slowmode control and auto-recovery."""
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
import discord

logger = logging.getLogger(__name__)


async def enable_slowmode(channel: discord.TextChannel, delay_seconds: int) -> bool:
    """Enable slowmode on a channel.

    Args:
        channel: Discord text channel
        delay_seconds: Slowmode delay in seconds (max 21600)

    Returns:
        True if successful, False if permission error or other exception
    """
    try:
        await channel.edit(slowmode_delay=delay_seconds, reason="Raid lockdown activated")
        logger.info(f"Enabled {delay_seconds}s slowmode on #{channel.name}")
        return True
    except discord.Forbidden:
        logger.error(f"Missing permissions to edit #{channel.name}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Failed to enable slowmode on #{channel.name}: {e}")
        return False


async def disable_slowmode(channel: discord.TextChannel) -> bool:
    """Disable slowmode on a channel.

    Args:
        channel: Discord text channel

    Returns:
        True if successful, False if permission error or other exception
    """
    try:
        await channel.edit(slowmode_delay=0, reason="Raid lockdown deactivated")
        logger.info(f"Disabled slowmode on #{channel.name}")
        return True
    except discord.Forbidden:
        logger.error(f"Missing permissions to edit #{channel.name}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Failed to disable slowmode on #{channel.name}: {e}")
        return False


class RaidLockdownManager:
    """Manage raid lockdown state with slowmode control and auto-recovery.

    Tracks per-guild lockdown state including activation time and auto-recovery task.
    Lockdown applies 5-second slowmode to all channels except operational channels
    (verify, security-logs). Auto-recovery timer cancels properly on manual deactivation.
    """

    def __init__(self, client: discord.Client, recovery_seconds: int = 900):
        """Initialize lockdown manager.

        Args:
            client: Discord client instance for guild lookups
            recovery_seconds: Auto-recovery duration in seconds (default: 900 = 15 minutes)
        """
        self.client = client
        self.recovery_seconds = recovery_seconds
        # dict[guild_id] -> {"active": bool, "activated_at": datetime, "task": asyncio.Task}
        self.lockdown_state: Dict[int, Dict] = {}
        logger.info(f"RaidLockdownManager initialized with {recovery_seconds}s auto-recovery")

    async def activate_lockdown(
        self,
        guild: discord.Guild,
        alert_channel: discord.TextChannel
    ) -> bool:
        """Activate raid lockdown on a guild.

        Enables 5-second slowmode on all text channels except verify and security-logs.
        Sends alert embed to security-logs channel and starts auto-recovery timer.

        Args:
            guild: Discord guild to lock down
            alert_channel: Channel to send lockdown alert (typically #security-logs)

        Returns:
            True if lockdown activated, False if already locked
        """
        # Check if already locked
        if guild.id in self.lockdown_state and self.lockdown_state[guild.id]["active"]:
            logger.warning(f"Guild {guild.name} already in lockdown")
            return False

        logger.info(f"Activating raid lockdown for {guild.name}")

        # Enable slowmode on all channels except operational channels
        operational_channels = ["verify", "security-logs"]
        slowmode_count = 0

        for channel in guild.text_channels:
            # Skip operational channels
            if channel.name in operational_channels:
                logger.debug(f"Skipping slowmode on operational channel #{channel.name}")
                continue

            # Enable 5-second slowmode
            success = await enable_slowmode(channel, 5)
            if success:
                slowmode_count += 1

        # Send alert embed to security-logs
        embed = discord.Embed(
            title="🚨 Raid Detected - Lockdown Activated",
            description=(
                f"Slowmode enabled on {slowmode_count} channels.\n"
                f"Auto-recovery in {self.recovery_seconds // 60} minutes."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(
            name="Slowmode Duration",
            value="5 seconds",
            inline=True
        )
        embed.add_field(
            name="Channels Protected",
            value=f"{slowmode_count} channels",
            inline=True
        )
        embed.set_footer(text=guild.name)

        try:
            await alert_channel.send(embed=embed)
        except discord.Forbidden:
            logger.error(f"Cannot send alert to #{alert_channel.name}: missing permissions")

        # Create auto-recovery task
        recovery_task = asyncio.create_task(self._auto_recover(guild.id))

        # Store lockdown state
        self.lockdown_state[guild.id] = {
            "active": True,
            "activated_at": datetime.now(timezone.utc),
            "task": recovery_task
        }

        logger.info(f"Raid lockdown activated for {guild.name}, auto-recovery in {self.recovery_seconds}s")
        return True

    async def deactivate_lockdown(self, guild: discord.Guild) -> None:
        """Deactivate raid lockdown on a guild.

        Disables slowmode on all channels, cancels auto-recovery task if running,
        and sends recovery alert to security-logs.

        Args:
            guild: Discord guild to unlock
        """
        if guild.id not in self.lockdown_state:
            logger.warning(f"No lockdown state for {guild.name}")
            return

        logger.info(f"Deactivating raid lockdown for {guild.name}")

        # Cancel auto-recovery task if exists
        state = self.lockdown_state[guild.id]
        if "task" in state and state["task"] is not None:
            state["task"].cancel()
            logger.debug(f"Cancelled auto-recovery task for {guild.name}")

        # Disable slowmode on all channels
        slowmode_count = 0
        for channel in guild.text_channels:
            success = await disable_slowmode(channel)
            if success:
                slowmode_count += 1

        # Calculate lockdown duration
        activated_at = state.get("activated_at")
        if activated_at:
            duration = datetime.now(timezone.utc) - activated_at
            duration_minutes = int(duration.total_seconds() // 60)
            duration_seconds = int(duration.total_seconds() % 60)
            duration_str = f"{duration_minutes}m {duration_seconds}s"
        else:
            duration_str = "unknown"

        # Send recovery alert to security-logs
        security_logs = discord.utils.get(guild.channels, name="security-logs")
        if security_logs:
            embed = discord.Embed(
                title="✅ Lockdown Deactivated",
                description=(
                    f"Slowmode disabled on {slowmode_count} channels.\n"
                    f"Lockdown duration: {duration_str}"
                ),
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.set_footer(text=guild.name)

            try:
                await security_logs.send(embed=embed)
            except discord.Forbidden:
                logger.error(f"Cannot send recovery alert to #{security_logs.name}: missing permissions")

        # Delete lockdown state
        del self.lockdown_state[guild.id]

        logger.info(f"Raid lockdown deactivated for {guild.name} after {duration_str}")

    async def _auto_recover(self, guild_id: int) -> None:
        """Auto-recovery task that deactivates lockdown after timeout.

        Sleeps for recovery_seconds, then calls deactivate_lockdown.
        Task is cancelled if manual deactivation occurs.

        Args:
            guild_id: Discord guild ID
        """
        try:
            logger.debug(f"Auto-recovery timer started for guild {guild_id}, {self.recovery_seconds}s")
            await asyncio.sleep(self.recovery_seconds)

            # Get guild object from client
            guild = self.client.get_guild(guild_id)
            if guild is None:
                logger.error(f"Cannot auto-recover: guild {guild_id} not found")
                return

            logger.info(f"Auto-recovery triggered for guild {guild.name}, deactivating lockdown")
            await self.deactivate_lockdown(guild)

        except asyncio.CancelledError:
            logger.debug(f"Auto-recovery cancelled for guild {guild_id}")
            raise
