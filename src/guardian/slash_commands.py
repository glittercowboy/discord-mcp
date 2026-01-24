"""Guardian slash command tree for bot configuration and control."""
import logging
import discord
from discord import app_commands
from datetime import timedelta
from . import config_manager
from . import logging_utils

logger = logging.getLogger(__name__)


class GuardianCommands(app_commands.Group):
    """Guardian slash command group."""

    def __init__(self):
        super().__init__(name="guardian", description="Guardian security bot configuration")

    @app_commands.command(name="status", description="View current Guardian config and bot state")
    @app_commands.default_permissions(administrator=True)
    async def status(self, interaction: discord.Interaction):
        """Show current Guardian configuration."""
        # Load config
        config = config_manager.load_config(interaction.guild_id)
        threshold = config.get("threshold_days", 7)
        features = config.get("features", {})
        exempt_roles = config.get("exempt_roles", [])

        # Build status embed
        embed = discord.Embed(
            title="Guardian Status",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Account Age Threshold",
            value=f"{threshold} days",
            inline=False
        )

        # Show feature status
        feature_status = []
        feature_status.append(f"URLs: {'✅ Blocked' if features.get('urls', True) else '❌ Allowed'}")
        feature_status.append(f"Attachments: {'✅ Blocked' if features.get('attachments', True) else '❌ Allowed'}")
        feature_status.append(f"Role mentions: {'✅ Blocked' if features.get('role_mentions', True) else '❌ Allowed'}")

        embed.add_field(
            name="Features",
            value="\n".join(feature_status),
            inline=False
        )

        embed.add_field(
            name="Exempt Roles",
            value=f"{len(exempt_roles)} role(s) exempt from restrictions",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Status command used by {interaction.user.name} in {interaction.guild.name}")

    @app_commands.command(name="config", description="Change account age threshold (in days)")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction, threshold: int):
        """Update account age threshold."""
        # Load current config
        config = config_manager.load_config(interaction.guild_id)

        # Update threshold
        config["threshold_days"] = threshold

        # Save config
        config_manager.save_config(interaction.guild_id, config)

        # Log to #security-logs
        security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
        if security_logs:
            embed = discord.Embed(
                title="Guardian Config Updated",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="Threshold Changed",
                value=f"Account age threshold set to **{threshold} days**",
                inline=False
            )
            embed.add_field(
                name="Updated By",
                value=interaction.user.mention,
                inline=False
            )
            await security_logs.send(embed=embed)

        # Respond to user
        await interaction.response.send_message(
            f"✅ Threshold updated to **{threshold} days** (no restart required)",
            ephemeral=True
        )
        logger.info(f"Config updated by {interaction.user.name} in {interaction.guild.name}: threshold={threshold}")

    @app_commands.command(name="verify", description="Manually verify a member (removes account restrictions)")
    @app_commands.default_permissions(moderate_members=True)
    async def verify(self, interaction: discord.Interaction, member: discord.Member):
        """Manually verify a member."""
        # Get roles
        verified_role = discord.utils.get(interaction.guild.roles, name="Verified")
        unverified_role = discord.utils.get(interaction.guild.roles, name="Unverified")

        if not verified_role or not unverified_role:
            await interaction.response.send_message(
                "❌ Required roles (@Verified, @Unverified) not found",
                ephemeral=True
            )
            logger.error(f"Manual verify failed: roles not found in {interaction.guild.name}")
            return

        # Add @Verified, remove @Unverified atomically
        try:
            await member.add_roles(verified_role, reason=f"Manual verification by {interaction.user.name}")
            await member.remove_roles(unverified_role, reason=f"Manual verification by {interaction.user.name}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Missing permissions to modify member roles",
                ephemeral=True
            )
            logger.error(f"Manual verify failed: permission denied for {member.name} in {interaction.guild.name}")
            return

        # Log to #security-logs
        security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
        if security_logs:
            embed = discord.Embed(
                title="Manual Verification",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Member Verified",
                value=member.mention,
                inline=False
            )
            embed.add_field(
                name="Verified By",
                value=interaction.user.mention,
                inline=False
            )
            await security_logs.send(embed=embed)

        # Respond to user
        await interaction.response.send_message(
            f"✅ {member.mention} manually verified",
            ephemeral=True
        )
        logger.info(f"Manual verification: {member.name} verified by {interaction.user.name} in {interaction.guild.name}")

    @app_commands.command(name="exempt", description="Manage role exemptions from account restrictions")
    @app_commands.default_permissions(administrator=True)
    @app_commands.choices(action=[
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove")
    ])
    async def exempt(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        role: discord.Role = None
    ):
        """Manage exempt roles."""
        # Load config
        config = config_manager.load_config(interaction.guild_id)
        exempt_roles = config.get("exempt_roles", [])

        # Handle list action
        if action.value == "list":
            if not exempt_roles:
                await interaction.response.send_message(
                    "No exempt roles configured",
                    ephemeral=True
                )
                return

            # Build list of exempt role names
            role_names = []
            for role_id in exempt_roles:
                role_obj = interaction.guild.get_role(role_id)
                if role_obj:
                    role_names.append(role_obj.mention)
                else:
                    role_names.append(f"Unknown role ({role_id})")

            embed = discord.Embed(
                title="Exempt Roles",
                description="\n".join(role_names),
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Require role parameter for add/remove actions
        if role is None:
            await interaction.response.send_message(
                "❌ Role parameter required for add/remove actions",
                ephemeral=True
            )
            return

        # Handle add action
        if action.value == "add":
            if role.id in exempt_roles:
                await interaction.response.send_message(
                    f"⚠️ {role.mention} is already exempt",
                    ephemeral=True
                )
                return

            exempt_roles.append(role.id)
            config["exempt_roles"] = exempt_roles
            config_manager.save_config(interaction.guild_id, config)

            # Log to #security-logs
            security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
            if security_logs:
                embed = discord.Embed(
                    title="Exempt Role Added",
                    color=discord.Color.green()
                )
                embed.add_field(
                    name="Role",
                    value=role.mention,
                    inline=False
                )
                embed.add_field(
                    name="Added By",
                    value=interaction.user.mention,
                    inline=False
                )
                await security_logs.send(embed=embed)

            await interaction.response.send_message(
                f"✅ {role.mention} added to exempt roles",
                ephemeral=True
            )
            logger.info(f"Exempt role added: {role.name} by {interaction.user.name} in {interaction.guild.name}")

        # Handle remove action
        elif action.value == "remove":
            if role.id not in exempt_roles:
                await interaction.response.send_message(
                    f"⚠️ {role.mention} is not in exempt roles",
                    ephemeral=True
                )
                return

            exempt_roles.remove(role.id)
            config["exempt_roles"] = exempt_roles
            config_manager.save_config(interaction.guild_id, config)

            # Log to #security-logs
            security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
            if security_logs:
                embed = discord.Embed(
                    title="Exempt Role Removed",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Role",
                    value=role.mention,
                    inline=False
                )
                embed.add_field(
                    name="Removed By",
                    value=interaction.user.mention,
                    inline=False
                )
                await security_logs.send(embed=embed)

            await interaction.response.send_message(
                f"✅ {role.mention} removed from exempt roles",
                ephemeral=True
            )
            logger.info(f"Exempt role removed: {role.name} by {interaction.user.name} in {interaction.guild.name}")

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def kick_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        """Kick a member with logging.

        Args:
            interaction: Slash command interaction
            member: Member to kick
            reason: Optional reason for kick
        """
        try:
            # Kick member
            await member.kick(reason=reason or "Manual kick via /guardian")

            # Log to #security-logs
            security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
            if security_logs:
                await logging_utils.log_moderation_action(
                    security_logs_channel=security_logs,
                    action="kick",
                    member=member,
                    reason=reason or "Manual kick",
                    moderator=interaction.user
                )

            # Confirm to moderator
            embed = discord.Embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked",
                color=discord.Color.red()
            )
            if reason:
                embed.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("Cannot kick this member (permission denied or hierarchy issue).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to kick member: {e}", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def ban_command(self, interaction: discord.Interaction, member: discord.Member, reason: str = None, delete_days: int = 1):
        """Ban a member with message deletion and logging.

        Args:
            interaction: Slash command interaction
            member: Member to ban
            reason: Optional reason for ban
            delete_days: Days of messages to delete (0-7, default 1)
        """
        # Validate delete_days
        if not (0 <= delete_days <= 7):
            await interaction.response.send_message("delete_days must be 0-7.", ephemeral=True)
            return

        try:
            # Ban member (delete_message_seconds is days * 86400)
            await member.ban(
                reason=reason or "Manual ban via /guardian",
                delete_message_seconds=delete_days * 86400
            )

            # Log to #security-logs
            security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
            if security_logs:
                await logging_utils.log_moderation_action(
                    security_logs_channel=security_logs,
                    action="ban",
                    member=member,
                    reason=reason or "Manual ban",
                    moderator=interaction.user
                )

            # Confirm to moderator
            embed = discord.Embed(
                title="Member Banned",
                description=f"{member.mention} has been banned",
                color=discord.Color.red()
            )
            if reason:
                embed.add_field(name="Reason", value=reason)
            embed.add_field(name="Messages Deleted", value=f"Last {delete_days} day(s)")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("Cannot ban this member (permission denied or hierarchy issue).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to ban member: {e}", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member for specified duration")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    async def timeout_command(self, interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = None):
        """Timeout a member with logging.

        Args:
            interaction: Slash command interaction
            member: Member to timeout
            minutes: Timeout duration in minutes (1-40320, max 28 days)
            reason: Optional reason for timeout
        """
        # Validate duration (Discord max is 28 days = 40320 minutes)
        if not (1 <= minutes <= 40320):
            await interaction.response.send_message("Minutes must be 1-40320 (max 28 days).", ephemeral=True)
            return

        try:
            # Timeout member
            duration = timedelta(minutes=minutes)
            await member.timeout(duration, reason=reason or "Manual timeout via /guardian")

            # Format duration for logging
            hours, mins = divmod(minutes, 60)
            duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"

            # Log to #security-logs
            security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")
            if security_logs:
                await logging_utils.log_moderation_action(
                    security_logs_channel=security_logs,
                    action="timeout",
                    member=member,
                    reason=reason or "Manual timeout",
                    moderator=interaction.user,
                    duration=duration_str
                )

            # Confirm to moderator
            embed = discord.Embed(
                title="Member Timed Out",
                description=f"{member.mention} timed out for {duration_str}",
                color=discord.Color.orange()
            )
            if reason:
                embed.add_field(name="Reason", value=reason)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("Cannot timeout this member (permission denied or hierarchy issue).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to timeout member: {e}", ephemeral=True)

    @app_commands.command(name="lockdown-on", description="Manually activate raid lockdown")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown_on_command(self, interaction: discord.Interaction):
        """Manually activate lockdown mode.

        Enables slowmode on all channels (except verify/security-logs) and pauses new verifications.
        Auto-deactivates after 15 minutes unless manually deactivated.
        """
        # Import guardian module to access lockdown_manager
        from . import guardian

        security_logs = discord.utils.get(interaction.guild.channels, name="security-logs")

        # Activate lockdown
        activated = await guardian.lockdown_manager.activate_lockdown(
            guild=interaction.guild,
            alert_channel=security_logs
        )

        if activated:
            embed = discord.Embed(
                title="Lockdown Activated",
                description="Manual lockdown enabled. Slowmode active, verifications paused.",
                color=discord.Color.red()
            )
            embed.add_field(name="Auto-Recovery", value="15 minutes", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Lockdown already active.", ephemeral=True)

    @app_commands.command(name="lockdown-off", description="Manually deactivate raid lockdown")
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown_off_command(self, interaction: discord.Interaction):
        """Manually deactivate lockdown mode.

        Disables slowmode on all channels and cancels auto-recovery timer.
        """
        # Import guardian module to access lockdown_manager
        from . import guardian

        guild_id = interaction.guild.id

        # Check if lockdown is active
        if guild_id not in guardian.lockdown_manager.lockdown_state or \
           not guardian.lockdown_manager.lockdown_state[guild_id].get("active", False):
            await interaction.response.send_message("Lockdown is not active.", ephemeral=True)
            return

        # Deactivate lockdown
        await guardian.lockdown_manager.deactivate_lockdown(interaction.guild)

        embed = discord.Embed(
            title="Lockdown Deactivated",
            description="Manual lockdown disabled. Slowmode removed, verifications resumed.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reload-blocklist", description="Reload phishing link blocklist from disk")
    @app_commands.default_permissions(administrator=True)
    async def reload_blocklist(self, interaction: discord.Interaction):
        """Reload blocklist from file (admin only).

        Manually reload the blocklist.json file without restarting the bot.
        Useful after updating the blocklist with new phishing domains.
        """
        # Import guardian module to access global blocklist instance
        from . import guardian

        # Reload blocklist
        guardian.blocklist.load_blocklist()

        # Count domains loaded
        domain_count = len(guardian.blocklist.domains)

        await interaction.response.send_message(
            f"✅ Blocklist reloaded: {domain_count:,} domains",
            ephemeral=True
        )
