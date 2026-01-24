"""Guardian Discord bot main entry point."""
import logging
import discord
from . import config
from . import infrastructure
from . import verification
from . import logging_utils
from . import verification_timeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure Discord intents
intents = discord.Intents.default()
intents.members = True  # Required for on_member_join event
intents.message_content = True  # Required for Phase 5 link scanning

# Create Discord client
client = discord.Client(intents=intents)


def is_moderator_or_higher(member: discord.Member) -> bool:
    """Check if member has moderator+ permissions.

    Returns True if member has administrator, moderate_members, or manage_guild permissions.
    Moderators bypass verification entirely.

    Args:
        member: Discord member to check

    Returns:
        True if member has moderator+ permissions, False otherwise
    """
    # Get highest role (excluding @everyone)
    highest_role = max(
        (r for r in member.roles if r.name != "@everyone"),
        key=lambda r: r.position,
        default=None
    )

    if highest_role is None:
        return False

    # Check for moderation permissions
    return (
        highest_role.permissions.administrator or
        highest_role.permissions.moderate_members or
        highest_role.permissions.manage_guild
    )


@client.event
async def on_ready():
    """Initialize Guardian infrastructure when bot is ready."""
    logger.info(f"Guardian bot logged in as {client.user}")

    # Initialize infrastructure for all guilds
    for guild in client.guilds:
        try:
            await infrastructure.initialize_infrastructure(guild)
        except Exception as e:
            logger.error(f"Failed to initialize infrastructure for {guild.name}: {e}")

    # Start verification timeout task
    verification_timeout.setup_timeout_task(client)
    logger.info("Verification timeout task started")

    logger.info(f"Guardian ready in {len(client.guilds)} guild(s)")


@client.event
async def on_member_join(member: discord.Member):
    """Assign @Unverified role to new members."""
    logger.info(f"New member joined: {member.name} in {member.guild.name}")

    # Bypass verification for moderators
    if is_moderator_or_higher(member):
        logger.info(f"Moderator {member.name} bypassed verification in {member.guild.name}")
        return

    try:
        # Get @Unverified role
        unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
        if not unverified_role:
            logger.error(f"@Unverified role not found in {member.guild.name}")
            return

        # Assign role to new member
        await member.add_roles(unverified_role, reason="New member verification")
        logger.info(f"Assigned @Unverified role to {member.name} in {member.guild.name}")

        # Get channels
        verify_channel = discord.utils.get(member.guild.channels, name="verify")
        security_logs_channel = discord.utils.get(member.guild.channels, name="security-logs")

        if not verify_channel or not security_logs_channel:
            logger.error(f"Required channels not found in {member.guild.name}")
            return

        # Log member join
        await logging_utils.log_member_join(security_logs_channel, member)

        # Get @Verified role for verification view
        verified_role = discord.utils.get(member.guild.roles, name="Verified")
        if not verified_role:
            logger.error(f"@Verified role not found in {member.guild.name}")
            return

        # Send verification challenge
        embed = discord.Embed(
            title="Welcome! Please verify you're human",
            description="Click the 🍕 emoji below to gain access to the server.",
            color=discord.Color.blue()
        )
        view = verification.VerificationView(
            guild=member.guild,
            member=member,
            verified_role=verified_role,
            unverified_role=unverified_role,
            security_logs_channel=security_logs_channel
        )
        await verify_channel.send(embed=embed, view=view)
        logger.info(f"Sent verification challenge to {member.name} in {member.guild.name}")

    except discord.Forbidden as e:
        logger.error(f"Permission denied: Cannot assign role to {member.name} in {member.guild.name} - {e}")
    except Exception as e:
        logger.error(f"Failed to assign role to {member.name} in {member.guild.name}: {e}")


@client.event
async def on_member_remove(member: discord.Member):
    """Log member leaves."""
    logger.info(f"Member left: {member.name} from {member.guild.name}")

    security_logs_channel = discord.utils.get(member.guild.channels, name="security-logs")
    if security_logs_channel:
        await logging_utils.log_member_leave(security_logs_channel, member)


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN)
