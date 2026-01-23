"""Security logging utilities for Discord events."""
import logging
import discord
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def log_member_join(channel: discord.TextChannel, member: discord.Member):
    """Log member join event to security logs channel.

    Args:
        channel: Security logs channel to send embed to
        member: Member who joined
    """
    embed = discord.Embed(
        title="Member Joined",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Member",
        value=f"{member.mention} (ID: {member.id})",
        inline=False
    )
    embed.add_field(
        name="Account Age",
        value=f"<t:{int(member.created_at.timestamp())}:R>",
        inline=False
    )
    embed.set_footer(text=member.guild.name)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        logger.error(f"Cannot send to {channel.name}: missing permissions")


async def log_member_leave(channel: discord.TextChannel, member: discord.Member):
    """Log member leave event to security logs channel.

    Args:
        channel: Security logs channel to send embed to
        member: Member who left
    """
    time_in_server = datetime.utcnow() - member.joined_at
    days = time_in_server.days
    hours, remainder = divmod(time_in_server.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    duration_str = ""
    if days > 0:
        duration_str += f"{days}d "
    if hours > 0:
        duration_str += f"{hours}h "
    duration_str += f"{minutes}m"

    embed = discord.Embed(
        title="Member Left",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Member",
        value=f"{member.mention} (ID: {member.id})",
        inline=False
    )
    embed.add_field(
        name="Time in Server",
        value=duration_str,
        inline=False
    )
    embed.set_footer(text=member.guild.name)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        logger.error(f"Cannot send to {channel.name}: missing permissions")


async def log_verification_attempt(
    channel: discord.TextChannel,
    member: discord.Member,
    success: bool,
    reason: str = ""
):
    """Log verification attempt to security logs channel.

    Args:
        channel: Security logs channel to send embed to
        member: Member who attempted verification
        success: Whether verification passed or failed
        reason: Optional reason for the result
    """
    embed = discord.Embed(
        title="Verification Attempt",
        color=discord.Color.green() if success else discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Member",
        value=f"{member.mention} (ID: {member.id})",
        inline=False
    )
    embed.add_field(
        name="Status",
        value="PASSED" if success else "FAILED",
        inline=False
    )
    if reason:
        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )
    embed.set_footer(text=member.guild.name)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        logger.error(f"Cannot send to {channel.name}: missing permissions")


async def log_timeout_kick(
    channel: discord.TextChannel,
    member: discord.Member,
    time_since_join: timedelta
):
    """Log timeout kick event to security logs channel.

    Args:
        channel: Security logs channel to send embed to
        member: Member who was kicked for timeout
        time_since_join: Duration since member joined
    """
    minutes = int(time_since_join.total_seconds() // 60)
    seconds = int(time_since_join.total_seconds() % 60)

    embed = discord.Embed(
        title="Timeout Kick",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="Member",
        value=f"{member.mention} (ID: {member.id})",
        inline=False
    )
    embed.add_field(
        name="Time Elapsed",
        value=f"{minutes}m {seconds}s",
        inline=False
    )
    embed.add_field(
        name="Reason",
        value="Verification timeout",
        inline=False
    )
    embed.set_footer(text=member.guild.name)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        logger.error(f"Cannot send to {channel.name}: missing permissions")
