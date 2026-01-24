"""Guardian Discord bot main entry point."""
import logging
import discord
from discord import app_commands
from . import config
from . import infrastructure
from . import verification
from . import logging_utils
from . import verification_timeout
from . import account_restrictions
from . import config_manager
from . import slash_commands

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

# Create command tree and attach to client
client.tree = app_commands.CommandTree(client)

# Register Guardian command group
guardian_commands = slash_commands.GuardianCommands()
client.tree.add_command(guardian_commands)


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

    # Sync slash commands to all guilds
    for guild in client.guilds:
        try:
            await client.tree.sync(guild=guild)
            logger.info(f"Synced slash commands to {guild.name}")
        except Exception as e:
            logger.error(f"Failed to sync commands to {guild.name}: {e}")

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
            title=f"👋 Welcome, {member.display_name}!",
            description=(
                "To access the server, click the **pizza emoji** button below.\n\n"
                "🍕 = Verify me!\n"
                "🌮 🍔 = Wrong answer\n\n"
                "*This helps us keep bots out.*"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Having trouble? Contact a moderator.")
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


@client.event
async def on_message(message: discord.Message):
    """Filter messages from new accounts."""
    # Ignore bot messages
    if message.author.bot:
        return

    # Get guild and check for required infrastructure
    guild = message.guild
    if not guild:
        return  # DM, not a guild message

    # Load config
    config = config_manager.load_config(guild.id)

    # Check if account is exempt
    member = message.author
    if account_restrictions.is_account_exempt(member, config):
        return

    # Check account age
    account_age_days = account_restrictions.get_account_age_days(message.author)
    threshold = config.get("threshold_days", 7)

    if account_age_days >= threshold:
        return  # Account old enough, no restrictions

    # Check for content violations
    violations = account_restrictions.check_content_violations(message)
    if not violations:
        return  # No violations

    # Delete message silently
    try:
        await message.delete()
    except discord.Forbidden:
        logger.error(f"Cannot delete message in {guild.name}: Missing permissions")
        return
    except discord.NotFound:
        logger.warning(f"Message already deleted in {guild.name}")
        return

    # DM user explaining violation
    violation_text = ", ".join(violations)
    try:
        await message.author.send(
            f"Your message was deleted in **{guild.name}** because it contained: {violation_text}\n\n"
            f"Your account is new (created {account_age_days:.1f} days ago), so we restrict certain content "
            f"for the first {threshold} days. This helps protect the community from spam and scams.\n\n"
            f"You'll be able to post this content once your account is {threshold} days old."
        )
    except discord.Forbidden:
        logger.warning(f"Cannot DM {message.author.name}: DMs disabled")

    # Log violation to #security-logs
    security_logs = discord.utils.get(guild.channels, name="security-logs")
    if security_logs:
        embed = discord.Embed(
            title="Account Restriction Violation",
            color=discord.Color.red()
        )
        embed.add_field(name="User", value=f"{message.author.mention} ({account_age_days:.1f} days old)", inline=False)
        embed.add_field(name="Channel", value=message.channel.mention, inline=False)
        embed.add_field(name="Violations", value=violation_text, inline=False)
        await security_logs.send(embed=embed)

    logger.info(f"Deleted message from {message.author.name} in {guild.name}: {violation_text}")


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN)
