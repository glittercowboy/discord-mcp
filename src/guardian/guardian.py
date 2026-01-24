"""Guardian Discord bot main entry point."""
import logging
import discord
from discord import app_commands
from datetime import datetime, timezone, timedelta
from pathlib import Path
from . import config
from . import infrastructure
from . import verification
from . import logging_utils
from . import verification_timeout
from . import account_restrictions
from . import config_manager
from . import slash_commands
from . import raid_detection
from . import raid_lockdown
from . import link_resolver
from . import blocklist_matcher
from . import offense_tracking
from .account_restrictions import URL_PATTERN

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

# Register Guardian command group at module level (before sync)
guardian_commands = slash_commands.GuardianCommands()
client.tree.add_command(guardian_commands)

# Raid detection and lockdown management
join_tracker = raid_detection.JoinTracker(window_seconds=30)
lockdown_manager = raid_lockdown.RaidLockdownManager(client=client, recovery_seconds=900)  # 15 minutes

# Link scanning infrastructure
blocklist = blocklist_matcher.BlocklistMatcher(Path(__file__).parent / "data" / "blocklist.json")
offense_tracker = offense_tracking.OffenseTracker(Path(__file__).parent / "data" / "offenses.json")


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

    # Log commands in tree before sync
    all_commands = client.tree.get_commands()
    logger.info(f"Commands in tree before sync: {[c.name for c in all_commands]}")

    # Sync to guilds only (not global) for instant propagation without duplicates
    for guild in client.guilds:
        try:
            # Clear existing guild commands first to avoid duplicates
            client.tree.clear_commands(guild=guild)
            # Copy our commands to this guild
            client.tree.copy_global_to(guild=guild)
            # Sync to Discord
            guild_synced = await client.tree.sync(guild=guild)
            logger.info(f"Synced {len(guild_synced)} commands to {guild.name}: {[c.name for c in guild_synced]}")
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

    # Add join to tracker
    join_tracker.add_join(member.guild.id, member)

    # Check for raid thresholds
    recent_joins = join_tracker.get_recent_joins(member.guild.id)
    join_count = len(recent_joins)

    # Get security-logs channel early (needed for alerts)
    security_logs_channel = discord.utils.get(member.guild.channels, name="security-logs")

    # Track if any raid condition triggered (for lockdown activation)
    raid_detected = False

    # RAID-01: 10+ joins in 30 seconds
    if join_count >= 10:
        raid_detected = True
        if security_logs_channel:
            embed = discord.Embed(
                title="⚠️ RAID-01: Rapid Join Spike",
                description=f"{join_count} members joined in 30 seconds",
                color=discord.Color.orange()
            )
            embed.add_field(name="Threshold", value="10+ joins", inline=False)
            embed.timestamp = datetime.now(timezone.utc)
            await security_logs_channel.send(embed=embed)

    # RAID-03: >50% new accounts (independent check)
    distribution = raid_detection.analyze_account_age_distribution(recent_joins, threshold_days=7)
    if distribution["percentage"] > 50:
        raid_detected = True
        if security_logs_channel:
            embed = discord.Embed(
                title="🚨 RAID-03: New Account Spike",
                description=f"{distribution['percentage']}% of recent joins are accounts <{distribution['threshold_days']} days old",
                color=discord.Color.red()
            )
            embed.add_field(name="Total Joins", value=f"{distribution['total']}", inline=True)
            embed.add_field(name="New Accounts", value=f"{distribution['new_accounts']}", inline=True)
            embed.timestamp = datetime.now(timezone.utc)
            await security_logs_channel.send(embed=embed)

    # Activate lockdown if any raid condition met
    if raid_detected:
        await lockdown_manager.activate_lockdown(member.guild, security_logs_channel)

    # Check lockdown BEFORE role assignment to avoid orphaned @Unverified roles
    if lockdown_manager.lockdown_state.get(member.guild.id, {}).get("active", False):
        logger.info(f"Verification paused for {member.name} during lockdown in {member.guild.name}")
        # Log join for audit trail but skip role assignment and verification UI
        if security_logs_channel:
            await logging_utils.log_member_join(security_logs_channel, member)
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
    """Filter messages from new accounts and scan all messages for scam links."""
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
        # Even exempt accounts get scam link scanning
        await scan_message_for_scam_links(message)
        return

    # Check account age
    account_age_days = account_restrictions.get_account_age_days(message.author)
    threshold = config.get("threshold_days", 7)

    if account_age_days >= threshold:
        # Account old enough, no restrictions - but still scan for scam links
        await scan_message_for_scam_links(message)
        return

    # Check for content violations
    violations = account_restrictions.check_content_violations(message)
    if not violations:
        # No account age violations, but still check for scam links
        await scan_message_for_scam_links(message)
        return

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

    # Note: Scam link scanning skipped here because account restriction already deleted the message
    # Link scanning happens on all other paths (exempt, old enough, no violations)


async def scan_message_for_scam_links(message: discord.Message):
    """Scan message for blocklisted links and apply punishment escalation.

    Checks message content for URLs, follows redirects to final destination,
    checks against blocklist, and applies escalating punishment:
    - First offense: 1hr timeout + DM + log
    - Second offense: auto-ban + DM attempt + log

    Args:
        message: Discord message to scan
    """
    guild = message.guild
    if not guild:
        return

    # Extract URLs from message content
    urls = URL_PATTERN.findall(message.content)
    if not urls:
        return  # No URLs to check

    # Get security-logs channel early (needed for logging)
    security_logs = discord.utils.get(guild.channels, name="security-logs")

    # Check each URL
    for url in urls:
        # Resolve URL to final destination (follows redirects)
        final_url = await link_resolver.resolve_url_destination(url)

        # Extract domain for blocklist matching
        domain = link_resolver.extract_domain_from_url(final_url)

        if not domain:
            continue  # Skip if domain extraction failed

        # Check if domain is blocklisted
        if blocklist.is_blocklisted(domain):
            logger.info(f"Blocklisted domain detected: {domain} in message from {message.author.name}")

            # Get current offense count
            current_offense_count = offense_tracker.get_offense_count(message.author.id)

            # Delete message silently
            try:
                await message.delete()
            except discord.NotFound:
                logger.warning(f"Message already deleted in {guild.name}")
            except discord.Forbidden:
                logger.error(f"Cannot delete message in {guild.name}: Missing permissions")
                # Continue to punishment even if deletion fails (message may already be deleted)

            # Record offense (increments count)
            new_count = offense_tracker.record_offense(message.author.id, message.id, domain)

            # Escalating punishment
            action_taken = ""

            if new_count == 1:
                # First offense: 1hr timeout
                try:
                    await message.author.timeout(timedelta(hours=1), reason=f"Scam link posted: {domain}")
                    action_taken = "1hr timeout"
                    logger.info(f"Applied 1hr timeout to {message.author.name} for scam link (first offense)")

                    # DM user explaining timeout
                    try:
                        await message.author.send(
                            f"**Warning: Scam Link Detected**\n\n"
                            f"Your message in **{guild.name}** was deleted because it contained a known scam link: `{domain}`\n\n"
                            f"You have been timed out for **1 hour** as a first-time warning. "
                            f"Posting scam links again will result in an automatic ban.\n\n"
                            f"If you believe this was a mistake, please contact a moderator."
                        )
                    except discord.Forbidden:
                        logger.warning(f"Cannot DM {message.author.name}: DMs disabled")

                except discord.Forbidden:
                    logger.error(f"Cannot timeout {message.author.name}: Missing permissions")
                    action_taken = "Timeout failed (permissions)"

            elif new_count >= 2:
                # Second+ offense: auto-ban
                try:
                    # Try to DM before banning (will fail after ban)
                    try:
                        await message.author.send(
                            f"**Account Banned: Scam Link Violation**\n\n"
                            f"You have been automatically banned from **{guild.name}** for posting scam links multiple times.\n\n"
                            f"This is your **offense #{new_count}**. Latest domain: `{domain}`\n\n"
                            f"If you believe this was a mistake, contact server staff through another channel."
                        )
                    except discord.Forbidden:
                        logger.warning(f"Cannot DM {message.author.name}: DMs disabled")

                    # Ban user
                    await message.author.ban(reason=f"Scam link offense #{new_count}: {domain}")
                    action_taken = f"Auto-ban (offense #{new_count})"
                    logger.info(f"Auto-banned {message.author.name} for scam link (offense #{new_count})")

                except discord.Forbidden:
                    logger.error(f"Cannot ban {message.author.name}: Missing permissions")
                    action_taken = "Ban failed (permissions)"

            # Log to #security-logs
            if security_logs:
                embed = discord.Embed(
                    title="🚨 Scam Link Deleted",
                    color=discord.Color.red()
                )
                embed.add_field(name="User", value=message.author.mention, inline=False)
                embed.add_field(name="Channel", value=message.channel.mention, inline=False)
                embed.add_field(name="Domain", value=f"`{domain}`", inline=False)
                embed.add_field(name="URL", value=f"`{url[:100]}...`" if len(url) > 100 else f"`{url}`", inline=False)
                embed.add_field(name="Offense Count", value=str(new_count), inline=True)
                embed.add_field(name="Action Taken", value=action_taken, inline=True)

                # Include message preview (first 100 chars)
                message_preview = message.content[:100] + "..." if len(message.content) > 100 else message.content
                embed.add_field(name="Message Content", value=f"`{message_preview}`", inline=False)

                embed.timestamp = datetime.now(timezone.utc)
                await security_logs.send(embed=embed)

            # Only process first blocklisted link found
            return


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN)
