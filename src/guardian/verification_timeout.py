"""Background task for verification timeout enforcement."""
import logging
import discord
from discord.ext import tasks
from datetime import datetime, timedelta
from . import logging_utils

logger = logging.getLogger(__name__)


def setup_timeout_task(bot: discord.Client):
    """Set up and start the verification timeout background task.

    Args:
        bot: Discord client instance

    Returns:
        The running task loop instance
    """

    @tasks.loop(seconds=30)
    async def check_verification_timeout():
        """Check all guilds for unverified members past 10-minute deadline."""
        for guild in bot.guilds:
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if not unverified_role:
                continue

            now = datetime.utcnow()
            for member in guild.members:
                if unverified_role not in member.roles:
                    continue

                # Check if 10+ minutes since join
                time_since_join = now - member.joined_at
                if time_since_join > timedelta(minutes=10):
                    try:
                        await guild.kick(member, reason="Verification timeout (10 minutes)")
                        logger.info(f"Kicked {member.name} from {guild.name} (verification timeout)")

                        # Get security-logs channel
                        security_logs_channel = discord.utils.get(guild.channels, name="security-logs")
                        if security_logs_channel:
                            await logging_utils.log_timeout_kick(
                                security_logs_channel,
                                member,
                                time_since_join
                            )
                    except discord.Forbidden:
                        logger.error(f"Cannot kick {member.name}: missing permissions")
                    except discord.NotFound:
                        # Member already kicked/left, ignore
                        pass

    @check_verification_timeout.before_loop
    async def before_timeout_check():
        await bot.wait_until_ready()

    check_verification_timeout.start()
    return check_verification_timeout
