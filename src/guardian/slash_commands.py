"""Guardian slash command tree for bot configuration and control."""
import logging
import discord
from discord import app_commands
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
