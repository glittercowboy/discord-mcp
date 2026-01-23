# Phase 2: Verification Gate - Research

**Researched:** 2026-01-23
**Domain:** Discord.py interactive verification system with timeouts and role management
**Confidence:** HIGH

## Summary

Phase 2 implements a emoji-based verification gate for new Discord members using discord.py 2.6.4. The implementation requires four primary technical components: interactive button views for the verification challenge, background task loops for timeout tracking and auto-kick, secure logging with embeds, and role hierarchy checks for moderator bypass.

The standard approach uses discord.py's `discord.ui.View` and `discord.ui.Button` for the interactive UI, `discord.ext.tasks.loop()` for background timeout tracking, `discord.Embed` for formatted security logs, and member role comparison operators for hierarchy checks. The existing infrastructure from Phase 1 (roles, channels, handlers) provides the foundation. The main pitfall is state persistence: button views lose in-memory tracking when the bot restarts, so the timeout system should use a simple tracking mechanism (per-guild dictionary keyed by member ID) that's rebuilt from the member list at startup.

**Primary recommendation:** Use discord.py's built-in View/Button system for the verification UI, discord.ext.tasks.loop for the timeout background task (checking unverified members every 30 seconds), and Member.add_roles/remove_roles for atomic role transitions. Avoid persistent view state—track verification timeouts in memory per guild, rebuilt on bot restart.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.6.4 | Discord bot framework with UI components | Official, production-ready for interactions |
| discord.ext.tasks | Included | Background task scheduling | Built-in, handles reconnection logic automatically |
| discord.ui.View | Included | Interactive component containers | Standard UI pattern in discord.py 2.0+ |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| discord.Embed | Included | Formatted message embeds for logs | Structured, readable security log output |
| asyncio | Python 3.8+ | Event loop and async patterns | Built into Python, used by discord.py |
| logging | Python 3.8+ | Application logging | Standard Python logging, already configured in Phase 1 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| discord.ui.View/Button | discord.Reaction and ReactionMenu | Reactions are legacy; View/Button provides better UX, persistence options, and is the modern standard |
| discord.ext.tasks.loop | Manual asyncio scheduling | tasks.loop handles reconnection and error handling automatically; manual scheduling adds complexity |
| Role-based channel permissions | Message filtering in handlers | Role permissions are native Discord, don't require message inspection; far simpler and more reliable |

**Installation:**
```bash
# discord.py 2.6.4 already specified in requirements.txt
pip install discord.py==2.6.4
```

## Architecture Patterns

### Recommended Project Structure
```
src/guardian/
├── guardian.py           # Main bot (existing, add verification handlers)
├── infrastructure.py     # Role/channel setup (existing)
├── verification.py       # NEW: Views, verification logic
├── verification_timeout.py # NEW: Background timeout task
└── config.py            # Configuration (existing)
```

### Pattern 1: Emoji Verification View with Multiple Buttons
**What:** A `discord.ui.View` subclass with multiple emoji buttons where only one is correct. The challenge asks "Click the pizza emoji" and users click from options like pizza, taco, burger.

**When to use:** Simple challenge with 3-5 options, displayed in a single message, requires no state beyond verification success/failure.

**Example:**
```python
# Source: discord.py documentation and Pycord v2.6.1
import discord

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)  # 3-minute timeout for view interaction
        self.verified = False

    @discord.ui.button(label="🍕", style=discord.ButtonStyle.primary, custom_id="pizza_button")
    async def pizza_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Correct answer
        self.verified = True
        await interaction.response.defer()

    @discord.ui.button(label="🌮", style=discord.ButtonStyle.secondary, custom_id="taco_button")
    async def taco_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Wrong answer
        await interaction.response.send_message("Wrong emoji! Try again.", ephemeral=True)

    @discord.ui.button(label="🍔", style=discord.ButtonStyle.secondary, custom_id="burger_button")
    async def burger_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Wrong answer
        await interaction.response.send_message("Wrong emoji! Try again.", ephemeral=True)
```

### Pattern 2: Background Task Loop for Timeout Tracking and Auto-Kick
**What:** A background task using `discord.ext.tasks.loop()` that periodically checks guild members with the @Unverified role and kicks those who joined more than 10 minutes ago.

**When to use:** Need periodic background work (timeout checks), want automatic reconnection handling and error recovery.

**Example:**
```python
# Source: discord.py documentation on discord.ext.tasks
from discord.ext import tasks
from datetime import datetime, timedelta

class VerificationTimeout(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_verification_timeout.start()

    @tasks.loop(seconds=30)  # Check every 30 seconds
    async def check_verification_timeout(self):
        """Auto-kick unverified members after 10 minutes."""
        for guild in self.bot.guilds:
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if not unverified_role:
                continue

            now = datetime.utcnow()
            for member in guild.members:
                if unverified_role in member.roles:
                    # Check if member joined more than 10 minutes ago
                    join_duration = now - member.joined_at
                    if join_duration > timedelta(minutes=10):
                        try:
                            await guild.kick(member, reason="Failed verification timeout")
                            # Log the kick
                        except discord.Forbidden:
                            logger.error(f"Cannot kick {member.name}: missing permissions")

    @check_verification_timeout.before_loop
    async def before_check(self):
        """Wait for bot to be ready before starting task."""
        await self.bot.wait_until_ready()
```

### Pattern 3: Security Logging with Embeds
**What:** Format verification events (join, verification success, timeout kick) as structured embeds sent to #security-logs.

**When to use:** Audit trails, security events, human-readable logging in Discord.

**Example:**
```python
# Source: discord.py Embed documentation
import discord
from datetime import datetime

async def log_member_join(channel: discord.TextChannel, member: discord.Member):
    """Log member join to security-logs channel."""
    embed = discord.Embed(
        title="Member Joined",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Member", value=f"{member.mention} ({member.id})")
    embed.add_field(name="Account Age", value=f"<t:{int(member.created_at.timestamp())}:R>")
    embed.set_footer(text=f"Guild: {member.guild.name}")

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
    """Log verification attempt (pass/fail/timeout)."""
    embed = discord.Embed(
        title="Verification Attempt",
        color=discord.Color.green() if success else discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Member", value=f"{member.mention} ({member.id})")
    embed.add_field(name="Status", value="PASSED" if success else "FAILED")
    if reason:
        embed.add_field(name="Reason", value=reason)

    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        logger.error(f"Cannot send to {channel.name}: missing permissions")
```

### Pattern 4: Role Hierarchy Check for Moderator Bypass
**What:** Check if a member's highest role is higher than the @Unverified role. If so, skip verification assignment.

**When to use:** Different member categories (moderators, admins) should bypass automated verification.

**Example:**
```python
# Source: discord.py documentation on role comparison
async def should_verify_member(member: discord.Member) -> bool:
    """Check if member should be assigned @Unverified role.

    Returns False if member has a role that's moderator+ (higher than Unverified).
    """
    unverified_role = discord.utils.get(member.guild.roles, name="Unverified")
    if not unverified_role:
        return True

    # Get member's highest role (excluding @everyone)
    highest_role = max(
        (r for r in member.roles if r.name != "@everyone"),
        key=lambda r: r.position,
        default=None
    )

    # If member has no roles or their highest is below Unverified, they need verification
    if highest_role is None:
        return True

    # If member's highest role >= Unverified, they're moderator+, skip verification
    return highest_role < unverified_role  # True = they need to verify
```

### Anti-Patterns to Avoid
- **Storing view state in discord.Member attributes:** Views are ephemeral until bot restart. Use guild-level tracking dictionaries that are rebuilt at startup.
- **Calling member.edit(roles=[...]) multiple times in succession:** Use atomic add_roles/remove_roles. Multiple edit() calls can race and lose earlier changes.
- **Checking permission flags directly on member:** Use role hierarchy comparison operators (role1 > role2) instead; they're more reliable.
- **Ignoring on_guild_join:** Phase 1 has on_ready for initial setup, but bot infrastructure must also run when bot is added to a new guild.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interactive buttons/reactions | Custom reaction tracking with DB | discord.ui.View and discord.ui.Button | Views handle interaction detection, timeouts, and message recovery automatically |
| Periodic timeout checks | Manual sleep loops with reconnection logic | discord.ext.tasks.loop | tasks.loop provides automatic reconnection with exponential backoff, error handling, graceful shutdown |
| Audit trail logging | Write to files or webhook URLs | discord.Embed sent to channel | Channel-based logging is queryable in Discord history, timestamped, and supports message embeds for structure |
| Role hierarchy checking | Manual role position comparison | Role comparison operators (>) | Built-in operators handle edge cases like @everyone and bot role limitations |

**Key insight:** Discord.py abstracts away complex Discord API patterns (interaction routing, task reconnection, role hierarchy) that would be fragile if hand-rolled. The library is the standard solution for these problems in the Python Discord bot community.

## Common Pitfalls

### Pitfall 1: View State Lost on Bot Restart
**What goes wrong:** A View is instantiated in memory, button interactions are tracked as instance variables. Bot crashes or restarts. View instance is gone; buttons no longer work even though the message still shows them.

**Why it happens:** Views are in-memory objects. When Python process restarts, all in-memory state is lost. Discord API doesn't know which Python instance should handle button clicks.

**How to avoid:**
- For ephemeral views (temporary verification flow): Acceptable to lose state on restart; message will show stale buttons.
- For persistent views (verification buttons across bot restarts): Set `timeout=None`, assign `custom_id` to all buttons, use `bot.add_view()` at startup to register which message IDs use which View class. Store member verification state in a persistent way (database or per-guild dict rebuilt from member list).

**Warning signs:** After bot restart, users see "This interaction failed" when clicking buttons. Or verification challenges are lost.

### Pitfall 2: Race Condition in Role Assignment
**What goes wrong:** Two operations modify member.roles simultaneously (e.g., bot assigns @Unverified while infrastructure assigns another role). The second request overwrites the first, resulting in member having only one role instead of both.

**Why it happens:** Discord API processes role modification requests sequentially. If two requests are sent in quick succession, the second request operates on a stale view of the member's role list and overwrites changes from the first.

**How to avoid:**
- Use `member.add_roles(role1, role2)` to add multiple roles atomically (single API request).
- Never call `member.edit(roles=[...])` multiple times in succession; use add_roles/remove_roles instead.
- If checking "which roles does member have?" before making changes, re-fetch member object immediately before modifying: `await member.guild.fetch_member(member.id)`.

**Warning signs:** Member verification succeeds but @Verified role isn't applied. Or old @Unverified role remains when it should be removed.

### Pitfall 3: Missing Intent for on_member_join
**What goes wrong:** `on_member_join` event never fires. New members join but bot doesn't assign roles.

**Why it happens:** on_member_join requires `members` intent. If intent is not enabled in code OR in Discord Developer Portal settings, Discord doesn't send the event to bot.

**How to avoid:**
- Set intent in code: `intents = discord.Intents.default(); intents.members = True`
- Verify intent is enabled in Discord Developer Portal > Application > Bot > Intents
- Log when on_ready fires to confirm bot is fully initialized before relying on events

**Warning signs:** on_member_join handler is defined but never called. Check bot logs for "Gateway event" messages.

### Pitfall 4: Blocking Operations in Event Handlers
**What goes wrong:** on_member_join calls a slow operation (database query, external API) without await. Handler blocks, bot becomes unresponsive to other events.

**Why it happens:** Discord.py runs on single event loop. If handler does sync I/O or doesn't await async operations, event queue stalls.

**How to avoid:**
- Always use `await` for async operations in event handlers.
- Offload slow work to background tasks (use `discord.ext.tasks.loop` or `asyncio.create_task`).
- Wrap long operations: `asyncio.create_task(slow_operation(member))` allows handler to return quickly.

**Warning signs:** Bot stops responding after certain members join. Discord reports "bot unresponsive" or events are delayed.

### Pitfall 5: Auto-Kick Using Exact Timestamp Comparison
**What goes wrong:** Timeout task kicks a member at exactly 10:00:05 after they joined, then checks again at 10:00:35 and tries to kick an already-kicked member.

**Why it happens:** No guard against double-kick. Logic is "if joined_at < now - 10 minutes, kick", which remains true forever unless member is removed.

**How to avoid:**
- Use try-except around kick: `try: await guild.kick(...) except discord.NotFound: pass` (member already gone)
- Or track which members have been kicked in a set, and don't kick twice.
- Simple solution: kick is idempotent if error is handled; just let NotFound pass silently.

**Warning signs:** Error logs show "User not found" after first kick attempt succeeds.

## Code Examples

Verified patterns from official sources:

### Creating and Sending a Verification View
```python
# Source: Pycord v2.6.1 documentation
import discord

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.verified = False

    @discord.ui.button(label="🍕", style=discord.ButtonStyle.primary)
    async def pizza_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.verified = True
        await interaction.response.defer()  # Silent acknowledgment

# Send verification message with view
embed = discord.Embed(title="Click the pizza emoji to verify", description="Choose wisely!")
view = VerificationView()
message = await channel.send(embed=embed, view=view)

# Wait for button interaction or timeout
await view.wait()
if view.verified:
    # Process verification
    pass
```

### Background Task for Timeout Checking
```python
# Source: discord.py documentation on discord.ext.tasks
from discord.ext import tasks
from datetime import datetime, timedelta
import discord

class VerificationTimeoutTask(discord.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verification_timeout_task.start()

    @tasks.loop(seconds=30)
    async def verification_timeout_task(self):
        """Check and kick unverified members after 10 minutes."""
        for guild in self.bot.guilds:
            unverified_role = discord.utils.get(guild.roles, name="Unverified")
            if not unverified_role:
                continue

            now = datetime.utcnow()
            for member in guild.members:
                if unverified_role not in member.roles:
                    continue

                time_since_join = now - member.joined_at
                if time_since_join > timedelta(minutes=10):
                    try:
                        await guild.kick(member, reason="Failed verification timeout")
                    except (discord.Forbidden, discord.NotFound) as e:
                        logger.error(f"Failed to kick {member}: {e}")

    @verification_timeout_task.before_loop
    async def before_verification_timeout_task(self):
        await self.bot.wait_until_ready()
```

### Security Log Entry with Embed
```python
# Source: discord.py Embed documentation
import discord
from datetime import datetime

async def log_verification_success(security_logs_channel: discord.TextChannel, member: discord.Member):
    embed = discord.Embed(
        title="Member Verified",
        description=f"Member passed emoji challenge",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Member", value=f"{member.mention}", inline=True)
    embed.add_field(name="ID", value=f"{member.id}", inline=True)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=False)
    embed.set_footer(text=f"Guild: {member.guild.name}")

    try:
        await security_logs_channel.send(embed=embed)
    except discord.Forbidden:
        logger.error(f"No permission to send to {security_logs_channel.name}")
```

### Role Hierarchy Check for Moderator Bypass
```python
# Source: discord.py documentation on role comparison
def is_moderator_or_higher(member: discord.Member) -> bool:
    """Check if member has moderator+ role."""
    # Get member's highest role
    highest_role = max(
        (r for r in member.roles if r.name != "@everyone"),
        key=lambda r: r.position,
        default=None
    )

    if highest_role is None:
        return False  # No roles

    # Check if role has moderation permissions
    return highest_role.permissions.administrator or \
           highest_role.permissions.moderate_members or \
           highest_role.permissions.manage_guild
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Reaction role bots | discord.ui.Button based verification | discord.py 2.0+ (2021) | Better UX, interaction tokens, automatic timeout handling |
| Manual event loop scheduling | discord.ext.tasks.loop | discord.py 1.0 (included throughout) | Automatic reconnection, error handling, graceful shutdown |
| Direct role position checking | Role comparison operators (role1 > role2) | discord.py 2.0+ | More reliable, handles @everyone edge cases |

**Deprecated/outdated:**
- Reaction-based verification: While still supported, Views + Buttons are the modern standard and provide better UX.
- discord.Client without Intents: Discord.py 1.x used default intents; 2.0+ requires explicit intent configuration.

## Open Questions

1. **Should verification buttons be persistent across bot restarts?**
   - What we know: Phase 2 spec requires challenge sent to #verify channel when member joins. No mention of persistent verification buttons across restarts.
   - What's unclear: Should stale buttons in #verify (from before a restart) still be clickable? Or is it acceptable for users to see "This interaction failed"?
   - Recommendation: Implement as ephemeral (non-persistent for now). Use 180-second view timeout. If needed in future phases, add persistent view registration at startup.

2. **What data should security logs capture?**
   - What we know: Phase 2 spec mentions logging joins/leaves with timestamps and verification attempts (pass/fail/timeout).
   - What's unclear: Should logs include IP address, browser info, or other metadata? Discord Member API doesn't provide this.
   - Recommendation: Log member ID, mention, account creation time, join/leave timestamps, verification result. Keep it within Discord API capabilities.

3. **How to handle verification race conditions?**
   - What we know: Member must transition from @Unverified to @Verified atomically.
   - What's unclear: What if member clicks button while bot is processing role assignment?
   - Recommendation: Use a per-member lock (asyncio.Lock) or simple dict to prevent double-processing of the same verification attempt.

## Sources

### Primary (HIGH confidence)
- **Pycord v2.6.1 Documentation** - discord.ui.View, discord.ui.Button API, interaction handling
  - https://docs.pycord.dev/en/v2.6.1/api/ui_kit.html
- **discord.py Official Documentation** - discord.ext.tasks module for background tasks
  - https://discordpy.readthedocs.io/en/latest/ext/tasks/index.html
- **discord.py Official Repository** - discord.Member API, role management
  - https://github.com/Rapptz/discord.py/blob/master/discord/member.py

### Secondary (MEDIUM confidence)
- **Discord.py Guide** - Buttons and UI Components
  - https://guide.pycord.dev/interactions/ui-components/buttons
- **Real Python** - How to Make a Discord Bot in Python (2026)
  - https://realpython.com/how-to-make-a-discord-bot-python/
- **GitHub Discussions** - Role assignment patterns and timing issues
  - Various threads on Rapptz/discord.py repository discussing race conditions and solutions

### Tertiary (LOW confidence)
- **WebSearch results** - Community patterns for verification systems (verified with official docs where noted)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - discord.py 2.6.4 with Views/Tasks is production standard; verified via official docs
- Architecture patterns: HIGH - Patterns come directly from Pycord and discord.py official documentation
- Common pitfalls: MEDIUM - Pitfalls #1-3 from official docs and GitHub discussions; #4-5 from community experience and testing patterns
- Code examples: HIGH - All examples either directly from official documentation or closely follow documented patterns

**Research date:** 2026-01-23
**Valid until:** 2026-02-23 (30 days for stable library, discord.py is slow-moving)

---

## Research Notes

**Key decisions locked in from context:**
- Emoji selection verification (not CAPTCHA, not email)
- Separate Guardian bot (not MCP integration)
- discord.py 2.6.4 (already in use)

**Trade-offs considered:**
- Views vs. Reactions: Views chosen (modern, better interaction handling)
- tasks.loop vs. manual asyncio: tasks.loop chosen (error handling, reconnection)
- Database persistence vs. in-memory: In-memory chosen for Phase 2 simplicity (can add DB in Phase 3)

**Not researched (deferred):**
- Phase 5 integration (link scanning)
- Multi-language support
- Custom emoji handling beyond built-in Discord emoji
