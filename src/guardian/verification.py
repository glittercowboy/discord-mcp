"""Discord UI verification view for emoji-based human verification."""
import logging
import discord

logger = logging.getLogger(__name__)


class VerificationView(discord.ui.View):
    """Interactive verification challenge with emoji buttons.

    Presents three emoji buttons to new members. Correct emoji selection
    triggers atomic role swap from @Unverified to @Verified.

    Attributes:
        guild: Discord guild where verification is occurring
        member: Member attempting verification
        verified_role: Role to assign on success
        unverified_role: Role to remove on success
        verified: Boolean flag indicating successful verification
    """

    def __init__(
        self,
        guild: discord.Guild,
        member: discord.Member,
        verified_role: discord.Role,
        unverified_role: discord.Role
    ):
        """Initialize verification view with 3-minute timeout.

        Args:
            guild: Discord guild for verification
            member: Member to verify
            verified_role: Role to grant on success
            unverified_role: Role to remove on success
        """
        super().__init__(timeout=180)  # 3-minute interaction window
        self.guild = guild
        self.member = member
        self.verified_role = verified_role
        self.unverified_role = unverified_role
        self.verified = False

    @discord.ui.button(label="🍕", style=discord.ButtonStyle.primary, custom_id="pizza_button")
    async def pizza_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle correct emoji selection (pizza).

        Atomically swaps roles (add @Verified, remove @Unverified),
        acknowledges interaction silently, and deletes verification message.

        Args:
            interaction: Discord button interaction
            button: Button that was clicked
        """
        try:
            # Atomic role swap: add verified, remove unverified
            await self.member.add_roles(self.verified_role, reason="Passed verification challenge")
            await self.member.remove_roles(self.unverified_role, reason="Passed verification challenge")

            self.verified = True
            logger.info(f"Member {self.member.name} verified successfully in {self.guild.name}")

            # Silent acknowledgment (no visible response)
            await interaction.response.defer()

            # Delete verification message after success
            await interaction.message.delete()

        except discord.Forbidden as e:
            logger.error(f"Permission denied: Cannot modify roles for {self.member.name} in {self.guild.name} - {e}")
            await interaction.response.send_message(
                "Verification failed: Bot lacks permissions. Contact a moderator.",
                ephemeral=True
            )
        except discord.NotFound as e:
            logger.error(f"Role or member not found during verification for {self.member.name} in {self.guild.name} - {e}")
            await interaction.response.send_message(
                "Verification failed: Role or member not found. Contact a moderator.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Unexpected error during verification for {self.member.name} in {self.guild.name}: {e}")
            await interaction.response.send_message(
                "Verification failed: Unexpected error. Contact a moderator.",
                ephemeral=True
            )

    @discord.ui.button(label="🌮", style=discord.ButtonStyle.secondary, custom_id="taco_button")
    async def taco_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle wrong emoji selection (taco).

        Sends ephemeral message prompting user to try again.

        Args:
            interaction: Discord button interaction
            button: Button that was clicked
        """
        logger.debug(f"Member {self.member.name} clicked wrong emoji (taco) in {self.guild.name}")
        await interaction.response.send_message("Wrong emoji! Try again.", ephemeral=True)

    @discord.ui.button(label="🍔", style=discord.ButtonStyle.secondary, custom_id="burger_button")
    async def burger_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle wrong emoji selection (burger).

        Sends ephemeral message prompting user to try again.

        Args:
            interaction: Discord button interaction
            button: Button that was clicked
        """
        logger.debug(f"Member {self.member.name} clicked wrong emoji (burger) in {self.guild.name}")
        await interaction.response.send_message("Wrong emoji! Try again.", ephemeral=True)
