# Phase 1: Foundation - Research

**Researched:** 2026-01-23
**Domain:** Discord Gateway Bot Architecture & Railway Deployment
**Confidence:** HIGH

## Summary

Phase 1 requires building a Discord bot that maintains 24/7 uptime on Railway by connecting to Discord's Gateway (WebSocket), not the REST API. This is distinct from the existing discord-mcp MCP server which uses REST API calls on-demand.

The bot must auto-create infrastructure on startup (roles and channels) using idempotent patterns to prevent duplicates. Member verification requires handling the `on_member_join` event with proper intent configuration.

**Key architecture decision:** The Gateway bot runs as a separate long-lived process from the MCP server, both using the same bot token but serving different purposes (real-time events vs. on-demand admin actions).

**Primary recommendation:** Use discord.py 2.6.4 with Gateway intents for member events, idempotent initialization in `on_ready`, and explicit role hierarchy management to avoid permission failures.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.6.4 | Discord Gateway client library | Industry standard, actively maintained, async-ready, full intent support |
| python | 3.12+ | Runtime | Required by discord.py, async/await support |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-logging | stdlib | Structured logging | Catch errors and debug Gateway events |
| asyncio | stdlib | Async task management | Timeout handling for verification flows |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| discord.py | discord.js (TypeScript) | Lose Python ecosystem, MCP server already Python |
| discord.py | Pycord | Older, less maintained, discord.py is standard |
| Gateway bot | REST webhook polling | Lose real-time events, miss on_member_join |

**Installation:**
```bash
pip install discord.py>=2.6.4
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── guardian.py              # Main bot client and event handlers
├── config.py                # Config loading from JSON
├── infrastructure.py        # Idempotent channel/role creation
├── verification.py          # Member verification logic
└── logging_config.py        # Structured logging setup
```

### Pattern 1: Gateway Connection for 24/7 Uptime
**What:** Bot connects to Discord's WebSocket Gateway via `client.run()` which maintains persistent connection across events.

**When to use:** Any requirement for real-time events (member joins, messages, reactions). REST API (MCP) cannot receive these.

**Example:**
```python
import discord

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Bot logged in as {client.user}')

client.run(token)  # Maintains WebSocket connection indefinitely
```

**Key insight:** `client.run()` blocks forever, managing reconnection and heartbeat. This is why it runs as a separate Railway worker process.

### Pattern 2: Idempotent Infrastructure Initialization
**What:** Check if role/channel exists before creating to prevent duplicates on bot restart.

**When to use:** Auto-create infrastructure that must exist before handling events.

**Example:**
```python
async def ensure_role_exists(guild, role_name):
    """Idempotent role creation - safe to call multiple times."""
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        return role
    return await guild.create_role(name=role_name, reason="Guardian initialization")

async def ensure_channel_exists(guild, channel_name, category=None):
    """Idempotent channel creation with overwrites."""
    channel = discord.utils.get(guild.channels, name=channel_name)
    if channel:
        return channel

    # Create with permission overwrites already set
    unverified_role = discord.utils.get(guild.roles, name="Unverified")
    verified_role = discord.utils.get(guild.roles, name="Verified")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        unverified_role: discord.PermissionOverwrite(view_channel=True),  # For #verify only
        verified_role: discord.PermissionOverwrite(view_channel=True),
    }

    return await guild.create_text_channel(
        channel_name,
        category=category,
        overwrites=overwrites,
        reason="Guardian initialization"
    )

@client.event
async def on_ready():
    for guild in client.guilds:
        await ensure_role_exists(guild, "Unverified")
        await ensure_role_exists(guild, "Verified")
        await ensure_channel_exists(guild, "verify")
        await ensure_channel_exists(guild, "security-logs")
```

### Pattern 3: Member Join with Role Assignment
**What:** Use `on_member_join` event to assign Unverified role and lock to #verify channel.

**When to use:** Every new member, immediate action required.

**Example:**
```python
@client.event
async def on_member_join(member):
    """Assign unverified role on join."""
    unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
    if unverified_role:
        await member.add_roles(unverified_role, reason="New member verification")
```

### Anti-Patterns to Avoid
- **Using `on_ready` to create infrastructure indefinitely:** `on_ready` fires multiple times during reconnections. Always check existence first.
- **Not checking role hierarchy:** Bot role must be above Unverified/Verified in the role list, or permission assignments fail silently.
- **Enabling intents in code but not Developer Portal:** Code intent setup is required AND you must enable in Discord Developer Portal for privileged intents.
- **Forgetting permission overwrites on channel creation:** Setting view_channel=False on @everyone by default then allowing Unverified is essential for #verify isolation.
- **Running MCP server and Gateway bot in same process:** They have different lifecycle requirements (on-demand vs. persistent). Use separate processes.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connecting to Discord | WebSocket client from scratch | discord.py Client | discord.py handles gateway protocol, rate limiting, reconnection logic, heartbeat keepalive |
| Checking if member has role | Manual list iteration | discord.utils.get() | Handles comparison, returns None cleanly, idiomatic |
| Managing permission overwrites | Complex dict manipulation | PermissionOverwrite objects | Handles None vs False distinction, validation |
| Persisting configuration | Command-line args | JSON config file with file watchers | Allows hot-reload from MCP server changes without restart |
| Structured logging to channel | Manual message sends | discord logging handler or separate #security-logs sink | Prevents log spam, maintains audit trail |

**Key insight:** Discord.py abstracts away the Gateway protocol complexity. The library handles WebSocket reconnection, message fragmentation, heartbeat acknowledgment, and payload compression automatically. Building this from scratch would be dozens of lines of low-level asyncio code with failure modes.

## Common Pitfalls

### Pitfall 1: Role Hierarchy Permission Errors
**What goes wrong:** Bot cannot assign Unverified role to members. Error: "403 Forbidden - Missing permissions"

**Why it happens:** Bot's role is positioned below the Unverified role in the server's role hierarchy. Discord enforces strict hierarchy—bots can only manage roles below their own position.

**How to avoid:**
1. In Discord settings, drag the bot's role to the TOP of the hierarchy (above all managed roles)
2. Test role assignment in `on_member_join`
3. Log role positions: `print([(r.name, r.position) for r in guild.roles])`

**Warning signs:**
- 403 errors on first members joining
- Errors mention "role.position" or "hierarchy"
- Role was created but unassigned

### Pitfall 2: Missing Gateway Intents
**What goes wrong:** `on_member_join` event never fires. Bot is online but doesn't see new members.

**Why it happens:**
- Code doesn't enable members intent: `intents.members = True` missing
- Developer Portal doesn't have Members intent enabled (code-side is required AND portal-side)

**How to avoid:**
```python
intents = discord.Intents.default()  # Default intents
intents.members = True                # REQUIRED for on_member_join
intents.message_content = True        # REQUIRED for reading message text
client = discord.Client(intents=intents)
```

Then verify in Discord Developer Portal: Bot → Privileged Gateway Intents → enable "Server Members Intent"

**Warning signs:**
- `on_member_join` defined but never called
- Member list is empty even though members are in server
- Bot works but events don't fire

### Pitfall 3: on_ready Firing Multiple Times Creates Duplicate Infrastructure
**What goes wrong:** Bot restarts, on_ready fires, channels get recreated, existing configurations get overwritten.

**Why it happens:** `on_ready` is not "run once on startup". It fires every time the bot reconnects to the Gateway (normal operation, network hiccup, rate limit recovery). Discord recommends idempotent initialization.

**How to avoid:** Always check existence before creating:
```python
@client.event
async def on_ready():
    for guild in client.guilds:
        role = discord.utils.get(guild.roles, name="Unverified")
        if not role:
            await guild.create_role(name="Unverified")
```

**Warning signs:**
- Multiple #verify channels appear
- Bot logs show "created role Unverified" multiple times
- Infrastructure appears duplicated after network reconnection

### Pitfall 4: Railway Free Tier Doesn't Support 24/7 Bots
**What goes wrong:** Bot runs for first month on free trial, then stops when $5 credit runs out.

**Why it happens:** Railway provides $5 one-time trial credit expiring in 30 days. After that, services stop unless on paid plan ($5/month Hobby minimum).

**How to avoid:**
- Plan for paid Railway ($5+/month) or use alternative host (Render, Replit, VPS)
- Set up deployment early to catch billing issues
- Monitor Railway usage dashboard

**Warning signs:**
- Deployment log says "Deployment succeeded" but bot isn't online
- Railway dashboard shows "Suspended" or service has no running instance
- Month boundary approaches

### Pitfall 5: Channel Permission Overwrites Default to View Channel Allowed
**What goes wrong:** #verify channel visible to @everyone instead of just Unverified role.

**Why it happens:** If you don't explicitly set `view_channel=False` on @everyone, default is allow. PermissionOverwrite doesn't create denies by default.

**How to avoid:**
```python
overwrites = {
    guild.default_role: discord.PermissionOverwrite(view_channel=False),      # DENY for @everyone
    unverified_role: discord.PermissionOverwrite(view_channel=True),          # ALLOW for Unverified
}
await guild.create_text_channel("verify", overwrites=overwrites)
```

**Warning signs:**
- Verified members can see #verify (shouldn't be able to)
- Unverified members can see channels other than #verify

## Code Examples

Verified patterns from official sources:

### Initialize Roles and Channels on Startup
```python
# Source: discord.py documentation + idempotent pattern
import discord
import logging

logger = logging.getLogger(__name__)

async def initialize_infrastructure(guild):
    """Idempotent infrastructure setup on first ready event."""

    # Ensure roles exist
    unverified = discord.utils.get(guild.roles, name="Unverified")
    if not unverified:
        unverified = await guild.create_role(
            name="Unverified",
            reason="Guardian verification role"
        )
        logger.info(f"Created Unverified role in {guild.name}")

    verified = discord.utils.get(guild.roles, name="Verified")
    if not verified:
        verified = await guild.create_role(
            name="Verified",
            reason="Guardian verified members role"
        )
        logger.info(f"Created Verified role in {guild.name}")

    # Ensure channels exist with correct permissions
    verify_channel = discord.utils.get(guild.channels, name="verify")
    if not verify_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            unverified: discord.PermissionOverwrite(view_channel=True),
            verified: discord.PermissionOverwrite(view_channel=False),
        }
        verify_channel = await guild.create_text_channel(
            "verify",
            overwrites=overwrites,
            reason="Guardian verification channel"
        )
        logger.info(f"Created #verify channel in {guild.name}")

    security_logs = discord.utils.get(guild.channels, name="security-logs")
    if not security_logs:
        security_logs = await guild.create_text_channel(
            "security-logs",
            reason="Guardian security log channel"
        )
        logger.info(f"Created #security-logs channel in {guild.name}")

    return {"verify": verify_channel, "security_logs": security_logs}

@client.event
async def on_ready():
    """Called when bot connects to Discord."""
    for guild in client.guilds:
        await initialize_infrastructure(guild)
    logger.info(f"Guardian ready in {len(client.guilds)} guilds")
```

### Assign Unverified Role on Member Join
```python
# Source: discord.py documentation
@client.event
async def on_member_join(member):
    """Assign unverified role when member joins."""
    unverified = discord.utils.get(member.guild.roles, name="Unverified")
    if unverified:
        try:
            await member.add_roles(unverified, reason="New member verification")
            logger.info(f"Assigned Unverified role to {member} in {member.guild.name}")
        except discord.Forbidden:
            logger.error(f"Cannot assign Unverified role in {member.guild.name} - check role hierarchy")
        except discord.HTTPException as e:
            logger.error(f"Failed to assign role to {member}: {e}")
```

### Setup Logging for Production
```python
# Source: discord.py logging documentation
import logging
import logging.handlers

def setup_logging():
    """Configure structured logging for production."""
    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)

    # File handler with rotation
    handler = logging.handlers.RotatingFileHandler(
        filename="guardian.log",
        maxBytes=5_242_880,  # 5 MB
        backupCount=5
    )
    handler.setFormatter(
        logging.Formatter(
            fmt='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    )
    logger.addHandler(handler)

    # Also log to stdout for Railway console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()
```

### Create Client with Required Intents
```python
# Source: discord.py documentation
import discord
import os

intents = discord.Intents.default()
intents.members = True              # Required for on_member_join
intents.message_content = True      # Required for reading message text

client = discord.Client(intents=intents)

# For use with Railways environment variables
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

if __name__ == "__main__":
    client.run(TOKEN)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| discord.py 1.x async pattern | discord.py 2.x with native async/await | 2021 | Code cleaner, full async support, better type hints |
| Intents opt-in without enforcement | Intents required, some privileged | 2020 | Bots must explicitly enable, Discord controls access for 100+ guilds |
| webhook polling for events | Gateway WebSocket persistent connection | Always built-in | Real-time events, proper event ordering, lower latency |
| REST API only (MCP) | MCP + Gateway bot dual-process | This project | REST for on-demand admin, Gateway for real-time events |

**Deprecated/outdated:**
- discord.py 1.x: Still works but no new features, use 2.x
- `on_error` global handler: Use per-command error handlers with logging instead
- Storing state in memory only: Use persistent config for infrastructure decisions

## Open Questions

1. **Exact Discord server ID**
   - What we know: Phase 1 success criteria require auto-creating infrastructure, which requires bot to be in the guild
   - What's unclear: Is the GSD Discord already set up? Will bot be invited before Phase 1 execution?
   - Recommendation: Assume bot will be invited with admin permissions before Phase 1 tasks run. Test infrastructure creation in controlled guild first.

2. **Permission scope for initial deployment**
   - What we know: Bot needs to create roles and channels (requires Admin or specific perms)
   - What's unclear: Should bot request minimal permissions or full Administrator?
   - Recommendation: Use minimal permissions set (Manage Channels, Manage Roles, Send Messages) for security. Administrator is dangerous but simplifies development.

3. **Hot-reload from MCP config changes**
   - What we know: MCP server will write config.json updates
   - What's unclear: Should Guardian watch config.json for changes and reload, or require manual restart?
   - Recommendation: Implement file watcher (watchdog library) for hot-reload to avoid "restart bot to apply settings" UX.

4. **Verification flow implementation detail**
   - What we know: Decision is "emoji selection" over CAPTCHA
   - What's unclear: Which emojis, how many choices, timeout duration?
   - Recommendation: Defer to Phase 2 (verification module). Phase 1 only needs infrastructure ready.

## Sources

### Primary (HIGH confidence)
- discord.py 2.6.4 documentation - Gateway connection, on_ready event, intents, role/channel creation, permission overwrites
- Discord API documentation - Role hierarchy enforcement, privileged intents
- Railway documentation - Start command configuration, environment variables

### Secondary (MEDIUM confidence)
- WebSearch (verified with official Discord docs): on_member_join event pattern
- WebSearch (verified with official Discord docs): Idempotent initialization pattern
- WebSearch (verified with official docs): Gateway logging best practices

### Tertiary (LOW confidence - for context only)
- WebSearch: Railway free tier limits (unverified, may change)
- Community discussions: Common permission pitfalls (consensus from multiple sources)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - discord.py is official library, version confirmed via PyPI
- Architecture: HIGH - Based on official discord.py patterns and Discord API docs
- Pitfalls: HIGH - Drawn from official docs and consistent community reports
- Railway specifics: MEDIUM - Deployment practice verified but may have changes

**Research date:** 2026-01-23
**Valid until:** 2026-02-23 (stable domain, check for discord.py updates and Railway pricing changes)
