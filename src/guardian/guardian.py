"""Guardian Discord bot main entry point."""
import logging
import discord
from . import config
from . import infrastructure

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

    logger.info(f"Guardian ready in {len(client.guilds)} guild(s)")


@client.event
async def on_member_join(member: discord.Member):
    """Assign @Unverified role to new members."""
    logger.info(f"New member joined: {member.name} in {member.guild.name}")

    try:
        # Get @Unverified role
        unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
        if not unverified_role:
            logger.error(f"@Unverified role not found in {member.guild.name}")
            return

        # Assign role to new member
        await member.add_roles(unverified_role, reason="New member verification")
        logger.info(f"Assigned @Unverified role to {member.name} in {member.guild.name}")

    except discord.Forbidden as e:
        logger.error(f"Permission denied: Cannot assign role to {member.name} in {member.guild.name} - {e}")
    except Exception as e:
        logger.error(f"Failed to assign role to {member.name} in {member.guild.name}: {e}")


if __name__ == "__main__":
    client.run(config.DISCORD_BOT_TOKEN)
