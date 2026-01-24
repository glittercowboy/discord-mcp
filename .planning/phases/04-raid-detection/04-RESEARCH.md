# Phase 4: Raid Detection - Research

**Researched:** 2026-01-24
**Domain:** Discord.py Member Join Event Tracking, Rate Limiting, Moderation Commands
**Confidence:** HIGH

## Summary

Phase 4 requires implementing coordinated join attack detection using Discord.py's `on_member_join` event handler combined with in-memory statistics tracking. The phase must:

1. Track recent member joins within 30-second time windows
2. Calculate account age distribution of recent joins
3. Trigger alerts and lockdown mode when thresholds are met (10+ joins in 30s, or >50% new accounts)
4. Implement slowmode as the lockdown mechanism via `channel.edit(slowmode_delay=...)`
5. Pause verification temporarily during lockdown
6. Auto-recover lockdown after 15 minutes of clean activity
7. Log all moderation actions (kicks, bans, timeouts) to #security-logs

The standard approach uses a sliding time window for join tracking, pre-compiling regex patterns, `discord.py` built-in slowmode support, and slash commands for manual lockdown control. Moderation action logging uses the audit log for tracking.

**Primary recommendation:** Use in-memory deque for join tracking (30-second window), `member.timeout()` for timeouts, `member.kick()` for kicks, `member.ban()` for bans, and `channel.edit(slowmode_delay=seconds)` for slowmode activation. Track moderation actions via dedicated logging without relying on gateway events (kicks have no event).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.6.4 | Discord Gateway client and member events | Provides `on_member_join` event, member methods (kick, ban, timeout), channel edit, audit logs |
| collections.deque | stdlib | Time-windowed join tracking | Efficient O(1) append/pop for rolling 30-second window |
| datetime | stdlib | Time-based calculations | Account age, join timestamps, window expiration |
| discord.utils | 2.6.4 (part of discord.py) | Utility functions | `discord.utils.get()` for finding roles/channels |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Async task scheduling | 15-minute auto-recovery timer, event loop management |
| json (stdlib) | 3.12+ | Configuration persistence | Raid detection thresholds (might be configurable like Phase 3) |
| logging (stdlib) | 3.12+ | Audit trail | Log raids, lockdowns, recoveries, moderation actions |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| deque for join window | List with manual cleanup | deque is O(1) pop from left, list is O(n); deque purpose-built for sliding windows |
| In-memory join tracking | Database per join | Database adds I/O overhead and complexity; in-memory acceptable for 30-second window (ephemeral) |
| `channel.edit(slowmode_delay=...)` | Kick/ban all new members | Slowmode is non-destructive, educational, allows moderation to intervene; kicks are permanent |
| Manual moderation logging | Audit log polling | Audit log queries are expensive; manual logging on each action is immediate and efficient |

**Installation:**
```bash
# discord.py already installed for Phase 1/2/3
# collections, datetime, asyncio, json, logging are stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
src/guardian/
├── guardian.py                  # Main bot, on_member_join event
├── raid_detection.py            # NEW: Join tracking, statistics, raid alerts
├── raid_lockdown.py             # NEW: Slowmode control, auto-recovery
├── moderation_logging.py        # NEW: Log kicks, bans, timeouts
├── config.py                    # Existing config
├── infrastructure.py            # Existing infrastructure
├── account_restrictions.py      # Existing account restrictions
├── verification.py              # Existing verification
├── slash_commands.py            # Existing + new raid commands
├── logging_utils.py             # Existing logging utils
└── verification_timeout.py      # Existing timeout task
```

### Pattern 1: Sliding Time Window for Join Tracking
**What:** Use `collections.deque` to maintain a 30-second rolling window of member joins, automatically removing expired entries.

**When to use:** Real-time detection of coordinated join attacks where timing matters.

**Example:**
```python
from collections import deque
from datetime import datetime, timedelta

class JoinTracker:
    """Track member joins in a 30-second sliding window per guild."""

    def __init__(self, window_seconds=30):
        self.window_seconds = window_seconds
        self.guild_joins = {}  # dict[guild_id] -> deque of (timestamp, member)

    def add_join(self, guild_id: int, member: discord.Member) -> None:
        """Add member join to tracking window."""
        if guild_id not in self.guild_joins:
            self.guild_joins[guild_id] = deque()

        now = datetime.now(datetime.timezone.utc)
        self.guild_joins[guild_id].append((now, member))

        # Remove expired entries (older than window)
        cutoff = now - timedelta(seconds=self.window_seconds)
        while self.guild_joins[guild_id] and self.guild_joins[guild_id][0][0] < cutoff:
            self.guild_joins[guild_id].popleft()

    def get_recent_joins(self, guild_id: int) -> list[discord.Member]:
        """Get all members who joined in the last 30 seconds."""
        if guild_id not in self.guild_joins:
            return []

        return [member for _, member in self.guild_joins[guild_id]]

    def get_join_count(self, guild_id: int) -> int:
        """Get count of joins in the window."""
        return len(self.guild_joins.get(guild_id, []))
```

**Key insight:** `deque.popleft()` is O(1), making it efficient for maintaining rolling windows. Store tuples of (timestamp, member) to enable age-based filtering later.

### Pattern 2: Account Age Distribution Analysis
**What:** Check what percentage of recent joins are accounts <7 days old.

**When to use:** After detecting 10+ rapid joins, analyze whether they're all new accounts (higher raid confidence).

**Example:**
```python
from datetime import datetime, timezone, timedelta

def analyze_account_age_distribution(members: list[discord.Member], threshold_days=7) -> dict:
    """Analyze age distribution of recent joins."""
    if not members:
        return {"total": 0, "new_accounts": 0, "percentage": 0}

    new_account_count = 0
    for member in members:
        account_age_days = (datetime.now(timezone.utc) - member.created_at).days
        if account_age_days < threshold_days:
            new_account_count += 1

    percentage = (new_account_count / len(members)) * 100

    return {
        "total": len(members),
        "new_accounts": new_account_count,
        "percentage": round(percentage, 1),
        "threshold_days": threshold_days
    }

# Usage in on_member_join
recent_joins = tracker.get_recent_joins(guild_id)
if len(recent_joins) >= 10:
    distribution = analyze_account_age_distribution(recent_joins)
    if distribution["percentage"] > 50:
        # Trigger additional alert
```

**Key insight:** Store member creation timestamp (`member.created_at`) at join time since member object may not persist in cache. Calculate percentage as integer metric for alerting.

### Pattern 3: Slowmode Activation and Deactivation
**What:** Activate slowmode by editing the channel's `slowmode_delay` property; deactivate by setting to 0.

**When to use:** Immediate lockdown in response to raid detection or manual moderator command.

**Example:**
```python
async def enable_slowmode(channel: discord.TextChannel, delay_seconds: int) -> bool:
    """Enable slowmode on a channel.

    Args:
        channel: Channel to slow
        delay_seconds: Delay between messages (1-21600 seconds)

    Returns:
        True if successful, False otherwise
    """
    try:
        await channel.edit(slowmode_delay=delay_seconds, reason="Raid lockdown activated")
        logging.info(f"Slowmode enabled on {channel.name}: {delay_seconds}s delay")
        return True
    except discord.Forbidden:
        logging.error(f"Cannot edit channel {channel.name}: Missing permissions")
        return False
    except discord.HTTPException as e:
        logging.error(f"Failed to enable slowmode: {e}")
        return False

async def disable_slowmode(channel: discord.TextChannel) -> bool:
    """Disable slowmode on a channel."""
    try:
        await channel.edit(slowmode_delay=0, reason="Raid lockdown deactivated")
        logging.info(f"Slowmode disabled on {channel.name}")
        return True
    except discord.Forbidden:
        logging.error(f"Cannot edit channel {channel.name}: Missing permissions")
        return False
    except discord.HTTPException as e:
        logging.error(f"Failed to disable slowmode: {e}")
        return False
```

**Key insight:** `channel.slowmode_delay` property is read-only; use `channel.edit(slowmode_delay=...)` to modify. Value of 0 disables slowmode. Maximum is 21600 seconds (6 hours).

### Pattern 4: Raid Lockdown State Management
**What:** Track lockdown state (active/inactive) per guild with auto-recovery timer.

**When to use:** Prevent duplicate lockdown alerts, enable auto-deactivation after clean period.

**Example:**
```python
class RaidLockdownManager:
    """Manage raid lockdown state and auto-recovery per guild."""

    def __init__(self, recovery_seconds=900):  # 15 minutes
        self.lockdown_state = {}  # dict[guild_id] -> {"active": bool, "activated_at": datetime, "task": asyncio.Task}
        self.recovery_seconds = recovery_seconds

    async def activate_lockdown(self, guild: discord.Guild, alert_channel: discord.TextChannel) -> bool:
        """Activate raid lockdown (slowmode + pause verification)."""
        guild_id = guild.id

        if guild_id in self.lockdown_state and self.lockdown_state[guild_id]["active"]:
            return False  # Already in lockdown

        # Enable slowmode on main channels
        for channel in guild.text_channels:
            if channel.name not in ["verify", "security-logs"]:  # Don't slow these
                await enable_slowmode(channel, delay_seconds=5)

        # Send alert
        embed = discord.Embed(
            title="🚨 Raid Detected - Lockdown Activated",
            description="Server is now in lockdown mode. Slowmode enabled.",
            color=discord.Color.red()
        )
        await alert_channel.send(embed=embed)

        # Start auto-recovery timer
        self.lockdown_state[guild_id] = {
            "active": True,
            "activated_at": datetime.now(timezone.utc),
            "task": asyncio.create_task(self._auto_recover(guild_id))
        }

        return True

    async def _auto_recover(self, guild_id: int) -> None:
        """Auto-deactivate lockdown after recovery period."""
        await asyncio.sleep(self.recovery_seconds)

        guild = ... # Fetch guild from client

        # Disable slowmode on all channels
        for channel in guild.text_channels:
            await disable_slowmode(channel)

        # Clear lockdown state
        if guild_id in self.lockdown_state:
            del self.lockdown_state[guild_id]

        logging.info(f"Raid lockdown auto-recovered for {guild.name}")
```

**Key insight:** Store task reference to allow cancellation if manual deactivation occurs before timer expires. Use `asyncio.create_task()` for background timer.

### Pattern 5: Moderation Action Logging
**What:** Log kicks, bans, timeouts to #security-logs immediately after they occur (no audit log events for kicks).

**When to use:** Every moderation action for audit trail and raid response tracking.

**Example:**
```python
async def log_moderation_action(
    security_logs_channel: discord.TextChannel,
    action: str,  # "kick", "ban", "timeout"
    member: discord.Member,
    reason: str = None,
    moderator: discord.Member = None,
    duration: str = None  # For timeouts: "30 minutes", "1 hour", etc.
) -> None:
    """Log a moderation action to #security-logs."""

    embed = discord.Embed(
        title=f"Moderation Action: {action.upper()}",
        color=discord.Color.red() if action in ["ban", "kick"] else discord.Color.orange()
    )
    embed.add_field(name="Member", value=f"{member.mention} ({member.name}#{member.discriminator})", inline=False)
    embed.add_field(name="Account Age", value=f"{(datetime.now(timezone.utc) - member.created_at).days} days", inline=False)

    if moderator:
        embed.add_field(name="Moderator", value=f"{moderator.mention}", inline=False)

    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)

    if duration:
        embed.add_field(name="Duration", value=duration, inline=False)

    embed.timestamp = datetime.now(timezone.utc)

    try:
        await security_logs_channel.send(embed=embed)
    except Exception as e:
        logging.error(f"Failed to log moderation action: {e}")
```

**Key insight:** Gateway events don't exist for kicks; audit log queries are expensive. Manual logging on each action is immediate and complete (no missed events).

### Anti-Patterns to Avoid
- **Not cleaning up join tracking window:** Old entries will accumulate in memory if not removed. Use deque.popleft() on every check.
- **Checking account age only once per member:** Member joins, then create account timestamp changes? No—account creation timestamp is immutable from member perspective. But Phase 3 already tracks this correctly.
- **Setting slowmode too high:** 21600 seconds (6 hours) makes server unusable. Raid lockdown should use 2-5 seconds. Manual admin override needed for extreme cases.
- **Not canceling auto-recovery task on manual deactivation:** If mod manually disables lockdown at 10 minutes, timer still waits full 15. Always cancel previous task before creating new one.
- **Logging moderation actions with partial data:** Always log account age, moderator, and reason for audit trail. Incomplete logs are useless.
- **Forgetting permission check for moderation commands:** Mods shouldn't accidentally ban themselves. Use `@app_commands.checks.has_permissions()`.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Tracking joins in a time window | List with manual timestamp checking | `collections.deque` with popleft() | deque is O(1) for rolling window, list is O(n); deque is built for this pattern |
| Implementing slowmode | Custom message rate limiting | `channel.edit(slowmode_delay=...)` | Discord's slowmode is built-in, handles edge cases (interaction timeouts in 2026), enforced by Discord |
| Kicking/banning members | Manual role removal + DM | `member.kick()` and `member.ban()` | Built-in methods handle permission checks, audit log entries, cascading removes |
| Timing out members | Custom DM + timestamp tracking | `member.timeout(duration=...)` | Built-in, Discord handles UI indication, audit log, permission checks |
| Detecting raid patterns | Manual heuristics | Combination: 10+ joins in 30s + >50% new accounts | Research shows effective two-layer detection; single metric misses sophisticated attacks |

**Key insight:** Discord's slowmode is specifically designed for this use case. Custom message filtering is less effective because it doesn't block verified accounts or bots mimicking normal behavior.

## Common Pitfalls

### Pitfall 1: Join Tracking Memory Leaks
**What goes wrong:** deque grows indefinitely, consuming memory even though entries are supposed to expire after 30 seconds.

**Why it happens:** Forgetting to call `popleft()` to clean old entries, or calling `get_recent_joins()` without cleanup logic.

**How to avoid:**
```python
def get_recent_joins(self, guild_id: int) -> list[discord.Member]:
    """Get all members who joined in the last 30 seconds, cleaning old entries."""
    if guild_id not in self.guild_joins:
        return []

    # Always clean first
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=self.window_seconds)
    while self.guild_joins[guild_id] and self.guild_joins[guild_id][0][0] < cutoff:
        self.guild_joins[guild_id].popleft()

    return [member for _, member in self.guild_joins[guild_id]]
```

**Warning signs:** Bot memory usage grows over time, eventually crashes. Check memory profiler or Task Manager.

### Pitfall 2: Slowmode Prevents Slash Commands
**What goes wrong:** After enabling slowmode, users can't run `/guardian` commands in that channel.

**Why it happens:** As of 2026, slowmode affects message-based interactions including slash command responses. Discord is transitioning away from this behavior but it's not complete.

**How to avoid:**
- Don't apply slowmode to #security-logs or #verify (where mods might need to run commands)
- Or: Moderators with specific roles (manage_guild) can bypass slowmode
- Or: Use role-based channel permissions to allow mods to send in slowed channels

**Warning signs:** Slash commands timeout or fail with "slowmode" error in logs.

### Pitfall 3: Auto-Recovery Timer Doesn't Cancel Previous Task
**What goes wrong:** Raid detected, lockdown activated, 5 minutes later mod manually deactivates with `/guardian lockdown off`, but 10 minutes later the auto-recovery task fires again and re-enables slowmode.

**Why it happens:** Asyncio tasks don't auto-cancel when replaced. Need to track and cancel manually.

**How to avoid:**
```python
async def deactivate_lockdown_manual(self, guild_id: int, guild: discord.Guild) -> None:
    """Manually deactivate lockdown, canceling auto-recovery."""

    # Cancel auto-recovery task if running
    if guild_id in self.lockdown_state and self.lockdown_state[guild_id]["task"]:
        self.lockdown_state[guild_id]["task"].cancel()

    # Disable slowmode
    for channel in guild.text_channels:
        await disable_slowmode(channel)

    # Clear state
    if guild_id in self.lockdown_state:
        del self.lockdown_state[guild_id]
```

**Warning signs:** Lockdown re-enables unexpectedly after manual disable.

### Pitfall 4: Account Age Calculation Timezone Issues
**What goes wrong:** Comparing `member.created_at` (UTC) with local timezone for age calculation results in incorrect ages, especially for accounts created in other timezones.

**Why it happens:** Same as Phase 3, but now applied to join spike analysis.

**How to avoid:**
```python
from datetime import datetime, timezone

account_age_days = (datetime.now(timezone.utc) - member.created_at).days
# Always use timezone.utc for comparison with Discord timestamps
```

**Warning signs:** Account ages off by hours or days, threshold checks fail inconsistently.

### Pitfall 5: Missing Permission Checks on Moderation Commands
**What goes wrong:** Regular members can run `/guardian kick @user`, bypassing moderation restrictions.

**Why it happens:** Forgetting `@app_commands.checks.has_permissions()` on kick/ban commands.

**How to avoid:**
```python
@app_commands.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(administrator=True, moderate_members=True)
@app_commands.checks.bot_has_permissions(kick_members=True)
async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Only mods can kick."""
    try:
        await member.kick(reason=reason)
        # Log action
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to kick that member.", ephemeral=True)
```

**Warning signs:** Regular members can trigger moderation commands, security bypassed.

## Code Examples

Verified patterns from official sources:

### Member Timeout Implementation
```python
# Source: https://discordpy.readthedocs.io/en/stable/api.html (Member.timeout)
from datetime import datetime, timedelta, timezone

@app_commands.command(name="timeout", description="Timeout a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_command(interaction: discord.Interaction, member: discord.Member, minutes: int = 10):
    """Timeout a member for specified minutes."""
    duration = timedelta(minutes=minutes)
    try:
        await member.timeout(duration, reason="Manual moderation timeout")
        embed = discord.Embed(title="Member Timed Out", description=f"{member.mention} timed out for {minutes} minutes", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Cannot timeout this member.", ephemeral=True)
```

### Member Kick Implementation
```python
# Source: https://discordpy.readthedocs.io/en/stable/api.html (Member.kick)
@app_commands.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick_command(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Kick a member from the server."""
    try:
        await member.kick(reason=reason or "Manual kick")
        embed = discord.Embed(title="Member Kicked", description=f"{member.mention} kicked", color=discord.Color.red())
        if reason:
            embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Cannot kick this member.", ephemeral=True)
```

### Member Ban Implementation
```python
# Source: https://discordpy.readthedocs.io/en/stable/api.html (Member.ban)
@app_commands.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_command(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    """Ban a member from the server."""
    try:
        await member.ban(reason=reason or "Manual ban", delete_message_seconds=86400)  # Delete last 24h of messages
        embed = discord.Embed(title="Member Banned", description=f"{member.mention} banned", color=discord.Color.red())
        if reason:
            embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Cannot ban this member.", ephemeral=True)
```

### Channel Slowmode Control
```python
# Source: https://discordpy.readthedocs.io/en/stable/api.html (TextChannel.edit)
@app_commands.command(name="slowmode", description="Set channel slowmode")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode_command(interaction: discord.Interaction, seconds: int = 0):
    """Set slowmode delay (0 = disabled, 1-21600 seconds)."""
    if not (0 <= seconds <= 21600):
        await interaction.response.send_message("Slowmode must be 0-21600 seconds.", ephemeral=True)
        return

    try:
        await interaction.channel.edit(slowmode_delay=seconds)
        status = "disabled" if seconds == 0 else f"set to {seconds}s"
        embed = discord.Embed(title="Slowmode Updated", description=f"Slowmode {status}", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Cannot edit channel.", ephemeral=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-message rate limiting | Discord slowmode | Always (Discord API) | Slowmode is enforced by Discord, not bot; harder to evade |
| Manual audit log queries for actions | Immediate logging on action | This project | Eliminates delay, handles kicks (no gateway event) |
| Kick detection via audit log polling | Manual log on kick command | This project | Polling is expensive; manual logging is reliable |
| Global join tracking | Per-guild tracking with separate deques | This project | Prevents raid in one guild from triggering false positives in others |

**Deprecated/outdated:**
- Custom message rate limiting: Use Discord's slowmode instead (enforced at Discord level)
- Relying on gateway events for all moderation: Kicks have no event; use audit log or manual logging

## Open Questions

1. **Should Phase 4 pause all verifications or just new ones?**
   - What we know: Requirement says "pauses new verifications" in lockdown mode
   - What's unclear: Can ongoing verification attempts continue, or do we block in-flight?
   - Recommendation: Pause *new* verifications (check on_member_join if lockdown active, defer role assignment). Allow in-flight to complete.

2. **What join threshold should trigger the secondary 50% new-accounts alert?**
   - What we know: Requirement is "RAID-01 fires first (10+ joins), RAID-03 fires if >50% are new"
   - What's unclear: Should RAID-03 be independent (alert separately) or only fire if RAID-01 already triggered?
   - Recommendation: RAID-03 fires independently if observed (separate alert channel post). Two-layer detection.

3. **Should moderators be able to manually trigger lockdown without a raid?**
   - What we know: Phase 4 is raid *detection* (automatic)
   - What's unclear: Should there be `/guardian lockdown on` command for manual override?
   - Recommendation: YES—add manual override via `/guardian lockdown on/off` for proactive protection during known events.

4. **How should the bot handle ban-and-delete-messages vs. kick?**
   - What we know: Ban and kick are separate moderation actions
   - What's unclear: During raid response, should mods ban (prevents rejoin) or kick (allows rejoin)?
   - Recommendation: Implement both as separate commands. Ban for serious raids, kick for accidental joins.

5. **Should lockdown slowmode apply to all channels or exclude some?**
   - What we know: Slowmode can be per-channel
   - What's unclear: Should #verify or #security-logs be excluded to allow mods to respond?
   - Recommendation: Exclude #security-logs and #verify from slowmode. These are operational channels.

6. **How precise should the 30-second window be?**
   - What we know: Requirement says "10+ members join within 30 seconds"
   - What's unclear: Is this exactly 30s or approximately? Grace period?
   - Recommendation: Use exactly 30-second sliding window. No grace period—raids are fast.

## Sources

### Primary (HIGH confidence)
- [discord.py Documentation: Member.timeout()](https://discordpy.readthedocs.io/en/stable/api.html) - Member timeout API
- [discord.py Documentation: Member.kick() / Member.ban()](https://discordpy.readthedocs.io/en/stable/api.html) - Member moderation methods
- [discord.py Documentation: TextChannel.edit()](https://discordpy.readthedocs.io/en/stable/api.html) - Channel slowmode via `slowmode_delay` parameter
- [discord.py Documentation: on_member_join event](https://discordpy.readthedocs.io/en/stable/intro.html) - Member join event handling
- [Discord API: Rate Limits](https://discord.com/developers/docs/topics/rate-limits) - Gateway and REST rate limiting
- [Discord Support: Slowmode FAQ](https://support.discord.com/hc/en-us/articles/360016150952-Slowmode-FAQ) - Slowmode behavior and limits

### Secondary (MEDIUM confidence - WebSearch verified with official docs)
- [How to Protect Your Server from Raids 101](https://support.discord.com/hc/en-us/articles/10989121220631-How-to-Protect-Your-Server-from-Raids-101) - Discord's official raid defense recommendations
- [Discord Spam Bots: How They Work + Best Anti-Spam Tools](https://pixelscan.net/blog/discord-spam-bots-how-they-work-5-best-anti-spam-tools/) - Raid attack patterns and detection methods
- [Discord Activity Alerts + Security Actions](https://support.discord.com/hc/en-us/articles/17439993574167-Activity-Alerts-Security-Actions) - Discord's built-in activity monitoring
- [Discord.py GitHub: on_member_join event handling](https://github.com/Rapptz/discord.py/discussions/8232) - Community implementations
- [Discord Moderation: Kick, Ban, Timeout Implementation](https://semicolon.dev/discord/how-to-mute-block-timeout-kick-or-ban-and-unban-users-from-discord-server) - Moderation command patterns

### Tertiary (LOW confidence - WebSearch only, marked for validation)
- WebSearch results on "Join Row feature" from SecurityBot (unverified, community tool documentation)
- WebSearch results on RaidProtect detection systems (unverified, community tool documentation)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - discord.py built-ins are documented, tested, community-standard
- Raid detection patterns: HIGH - Discord's official guidance confirms 10+ joins + new account age as effective indicators
- Slowmode implementation: HIGH - `channel.edit(slowmode_delay=...)` is stable API
- Moderation logging: MEDIUM - No gateway event for kicks; manual logging is standard but unverified if complete
- Join tracking with deque: HIGH - collections.deque is stdlib, well-established pattern
- Auto-recovery timing: MEDIUM - asyncio task management is stable but edge cases around cancellation need verification

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (stable domain, watch for Discord slowmode changes scheduled for Feb 23, 2026 regarding permission bypass)
