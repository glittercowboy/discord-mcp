# Phase 3: Account Restrictions - Research

**Researched:** 2026-01-24
**Domain:** Discord.py Message Filtering, Configuration Management, Slash Commands
**Confidence:** HIGH

## Summary

Phase 3 requires implementing content restrictions for new Discord accounts (<7 days old) using Discord.py's `on_message` event handler. The implementation must:

1. Detect URLs, attachments, and role mentions in messages
2. Delete violations silently and DM the user
3. Log all violations to #security-logs channel
4. Provide moderators with slash command configuration (`/guardian status`, `/guardian config`, `/guardian verify`, `/guardian exempt`)
5. Support hot-reloading of configuration without bot restart

The standard approach uses message content intent for real-time filtering, regex for URL detection, discord.py's built-in mention detection, and JSON-based configuration with in-memory caching. Slash commands are implemented via `app_commands.CommandTree` with group organization for `/guardian` subcommands.

**Primary recommendation:** Use discord.py's `on_message` event with `message_content` intent enabled (already done in Phase 1), regex for URL detection, `message.mention_everyone` and `message.raw_role_mentions` for mention detection, and `app_commands.Group` for slash command organization with JSON configuration file for hot-reload support.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.6.4 | Discord Gateway client and slash commands | Provides `on_message` event, message content intent, and `app_commands` for slash commands |
| app_commands | 2.6.4 (part of discord.py) | Slash command registration and routing | Standard pattern for application commands with group support |
| re (stdlib) | 3.12+ | URL pattern matching | Efficient, built-in, sufficient for Discord use case |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | 3.12+ | Configuration persistence | Read/write config files, human-readable format |
| pathlib (stdlib) | 3.12+ | Configuration file paths | Cross-platform file handling |
| datetime (stdlib) | 3.12+ | Account age calculation | Calculate days since `User.created_at` |
| logging (stdlib) | 3.12+ | Audit trail | Already in use, log violations and config changes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `on_message` event | Slash command prefix checks | Slower (requires command parsing), less real-time, requires @mention or prefix prefix |
| Regex for URLs | urlextract library | External dependency (not standard), more robust but overkill for this use case |
| JSON config | YAML, TOML, or database | YAML adds dependency, TOML adds dependency, database requires setup; JSON is built-in |
| `app_commands.Group` | Nested hybrid commands | Hybrid commands are legacy pattern, app_commands.Group is modern standard |

**Installation:**
```bash
# discord.py already installed for Phase 1/2
# re, json, pathlib, datetime are stdlib
```

## Architecture Patterns

### Recommended Project Structure
```
src/guardian/
├── guardian.py                # Main bot client and event handlers (includes on_message)
├── config.py                  # Config loading and validation
├── infrastructure.py          # Idempotent role/channel setup (existing)
├── account_restrictions.py    # NEW: Message filtering logic
├── slash_commands.py          # NEW: /guardian command group
├── verification.py            # Existing verification
└── logging_utils.py           # Existing logging
```

### Pattern 1: Message Event Filtering for New Accounts
**What:** Use `on_message` event to check account age and filter content before deletion.

**When to use:** Real-time filtering on message post, before content reaches the channel.

**Example:**
```python
import discord
import re
from datetime import datetime, timedelta

@client.event
async def on_message(message: discord.Message):
    """Filter messages from new accounts."""
    if message.author.bot:
        return

    # Get user account age
    created_at = message.author.created_at
    account_age = datetime.now(created_at.tzinfo) - created_at

    # Check if account is less than 7 days old
    if account_age < timedelta(days=7):
        violations = check_content_violations(message)
        if violations:
            # Delete message silently
            await message.delete()

            # DM user explaining why
            await message.author.send(
                f"Your message was deleted: {violations}\n"
                f"Your account is new, so we restrict certain content for the first 7 days."
            )

            # Log violation
            await log_violation(message, violations)
            return
```

**Key insight:** `message.created_at` is UTC-aware. Use `datetime.now(tzinfo=...)` to properly compare timezones. The `message_content` intent must be enabled (already configured in Phase 1).

### Pattern 2: Content Violation Detection
**What:** Detect URLs, attachments, and role mentions using built-in Discord.py properties and regex.

**When to use:** For each message that passes the age check.

**Example:**
```python
import re

def check_content_violations(message: discord.Message) -> list[str]:
    """Check message for restricted content."""
    violations = []

    # Check for attachments
    if message.attachments:
        violations.append("Attachments")

    # Check for @everyone or @here mentions
    if message.mention_everyone:
        violations.append("@everyone/@here mentions")

    # Check for role mentions
    if message.raw_role_mentions:
        violations.append("Role mentions")

    # Check for URLs (http://, https://, www.)
    url_pattern = r'https?://\S+|www\.\S+'
    if re.search(url_pattern, message.content):
        violations.append("URLs")

    return violations
```

**Key insight:** Discord.py provides `message.mention_everyone`, `message.raw_role_mentions`, and `message.attachments` as built-in properties—no custom parsing needed. Only URLs require regex.

### Pattern 3: Slash Command Group Organization
**What:** Use `app_commands.Group` to organize `/guardian` subcommands.

**When to use:** For moderator configuration and verification commands.

**Example:**
```python
import discord
from discord import app_commands

@app_commands.command(name="guardian", description="Guardian configuration")
@app_commands.default_permissions(administrator=True)
async def guardian_group(interaction: discord.Interaction):
    """Fallback for /guardian (shouldn't be called directly)."""
    await interaction.response.send_message("Use `/guardian status`, `/guardian config`, etc.", ephemeral=True)

# Define status subcommand
@app_commands.command(name="status", description="View current Guardian config", parent=guardian_group)
async def guardian_status(interaction: discord.Interaction):
    """View current configuration."""
    config = load_config(interaction.guild_id)
    embed = discord.Embed(title="Guardian Status", description=f"Threshold: {config['threshold']} days")
    await interaction.response.send_message(embed=embed, ephemeral=True)
```

**Key insight:** In discord.py 2.6+, use `@app_commands.command` with `parent` parameter for subcommands. No need for `hybrid_group` or old-style group decorators. The `parent` parameter links subcommands to their parent group.

### Pattern 4: Configuration File Hot-Reload
**What:** Load config from JSON file each time it's needed, enabling changes without restart.

**When to use:** For moderator-changeable settings (threshold, enabled features, exempt roles).

**Example:**
```python
import json
import logging
from pathlib import Path

CONFIG_FILE = Path("config/guardian.json")
DEFAULT_CONFIG = {
    "threshold_days": 7,
    "features": {"urls": True, "attachments": True, "role_mentions": True},
    "exempt_roles": []
}

def load_config(guild_id: int) -> dict:
    """Load config from JSON file (supports hot-reload)."""
    if not CONFIG_FILE.exists():
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE) as f:
            all_config = json.load(f)
        return all_config.get(str(guild_id), DEFAULT_CONFIG.copy())
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse config: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(guild_id: int, config: dict) -> None:
    """Save config to JSON file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Load existing config for other guilds
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                all_config = json.load(f)
        else:
            all_config = {}

        # Update this guild's config
        all_config[str(guild_id)] = config

        # Write back
        with open(CONFIG_FILE, "w") as f:
            json.dump(all_config, f, indent=2)
        logging.info(f"Config saved for guild {guild_id}")
    except IOError as e:
        logging.error(f"Failed to save config: {e}")
```

**Key insight:** Reading from file on each command (vs. in-memory cache) automatically supports hot-reload. Trade-off is minor I/O overhead, but acceptable for occasional `/guardian config` commands. Always validate JSON gracefully.

### Pattern 5: Exempt Roles Check
**What:** Check if member has exempt role before applying restrictions.

**When to use:** For Nitro boosters and moderators (already exempted via `is_moderator_or_higher`).

**Example:**
```python
async def is_account_exempt(member: discord.Member, config: dict) -> bool:
    """Check if member is exempt from account restrictions."""
    # Check if Nitro booster (using is_premium_subscriber from role tags)
    if member.premium_since is not None:
        return True

    # Check if has exempt role
    exempt_role_ids = config.get("exempt_roles", [])
    for role in member.roles:
        if role.id in exempt_role_ids:
            return True

    return False
```

**Key insight:** `Member.premium_since` is a datetime if member is nitro booster, `None` otherwise. For exempt roles, store role IDs (not names) in config to avoid issues with renamed roles.

### Anti-Patterns to Avoid
- **Deleting message synchronously in on_message:** Always `await message.delete()`, never block the event handler.
- **Not handling timezone-aware datetime comparison:** `message.author.created_at` is UTC. Use `datetime.now(timezone.utc)` for proper comparison.
- **Storing role names instead of IDs in exemption list:** Roles can be renamed; IDs are stable.
- **Not validating config JSON:** Malformed JSON can crash on_message. Always use try/except and default to safe config.
- **Checking account age only once per session:** Re-check on every message because threshold is time-based (account gets older).
- **Sending DM without error handling:** Some users disable DMs. Wrap in try/except and log the failure.
- **Forgetting to check `message.author.bot`:** Bot messages would also be filtered unnecessarily.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Extracting URLs from text | Custom regex | `re.search(r'https?://\S+\|www\.\S+', text)` | Simple pattern is sufficient, more complex patterns create false positives |
| Detecting @everyone/@here mentions | Parse message.content | `message.mention_everyone` property | Built into discord.py, handles edge cases |
| Detecting role mentions | Parse message.content | `message.raw_role_mentions` property | Built into discord.py, returns list of role IDs |
| Checking if member is Nitro booster | Query Discord API | `member.premium_since` property | Built-in attribute, no extra API call |
| Managing configuration | In-memory dict | JSON file with hot-reload | Simple I/O, supports multi-restart scenarios, moderator-friendly |
| Validating slash command permissions | Custom role checks | `@app_commands.default_permissions()` decorator | Built-in validation, handles permission inheritance |

**Key insight:** Discord.py provides mention detection as first-class properties. Using regex or string parsing is error-prone compared to built-in APIs.

## Common Pitfalls

### Pitfall 1: Timezone Awareness in Account Age Calculation
**What goes wrong:** Comparing `message.author.created_at` (UTC) with `datetime.now()` (local time) results in incorrect age calculations, especially for users in different timezones.

**Why it happens:** Python's `datetime.now()` returns local time (naive), while Discord timestamps are always UTC-aware.

**How to avoid:** Always use timezone-aware datetime:
```python
from datetime import datetime, timezone

created_at = message.author.created_at  # UTC-aware
now = datetime.now(timezone.utc)  # UTC-aware
age = now - created_at
```

**Warning signs:** Age calculations are off by hours or the comparison always returns False.

### Pitfall 2: Configuration File Corruption During Hot-Reload
**What goes wrong:** If `/guardian config` command is called while another process is writing the JSON file, partial writes or race conditions can corrupt the config.

**Why it happens:** JSON writes are not atomic. Multiple simultaneous writes can interleave.

**How to avoid:**
1. Write to temporary file first, then rename (atomic operation)
2. Use file locking library if multiple processes access the file
3. Validate config after every load

```python
def save_config(guild_id: int, config: dict) -> None:
    """Save config atomically using temp file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = CONFIG_FILE.with_suffix(".tmp")

    try:
        # Load existing config
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                all_config = json.load(f)
        else:
            all_config = {}

        # Update and write to temp
        all_config[str(guild_id)] = config
        with open(temp_file, "w") as f:
            json.dump(all_config, f, indent=2)

        # Atomic rename
        temp_file.replace(CONFIG_FILE)
    except Exception as e:
        temp_file.unlink(missing_ok=True)
        raise
```

**Warning signs:** Config becomes empty, becomes unreadable JSON, or settings randomly reset.

### Pitfall 3: DM Fails Silently, Looks Like a Bug
**What goes wrong:** `await message.author.send()` can fail if user has DMs disabled or the bot lacks permissions, but the error is easy to miss in logs.

**Why it happens:** Discord allows users to disable DMs from bots and servers.

**How to avoid:** Always catch and log DM failures explicitly:
```python
try:
    await message.author.send("Your message was deleted because...")
except discord.Forbidden:
    logging.warning(f"Cannot DM {message.author.name}: DMs disabled or bot blocked")
    # Fallback: send to security-logs instead
    await security_logs_channel.send(f"**DM Failed for {message.author.name}** - DMs disabled")
except discord.NotFound:
    logging.warning(f"Cannot DM {message.author.name}: User not found")
```

**Warning signs:** Users report violations weren't explained, but logs show no errors.

### Pitfall 4: Regex Performance Issues with Message Spam
**What goes wrong:** Running complex regex on every message in a high-traffic guild becomes a CPU bottleneck.

**Why it happens:** Regex is compiled on each invocation. Complex patterns (backtracking) scale poorly.

**How to avoid:** Pre-compile regex patterns at module load:
```python
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')

def check_content_violations(message: discord.Message) -> list[str]:
    violations = []
    if message.attachments:
        violations.append("Attachments")
    if message.mention_everyone or message.raw_role_mentions:
        violations.append("Mentions")
    if URL_PATTERN.search(message.content):
        violations.append("URLs")
    return violations
```

**Warning signs:** High CPU usage spikes when messages spike, bot becomes unresponsive during raids.

### Pitfall 5: Role Permissions Check Missing for /guardian Commands
**What goes wrong:** Moderators expect only admins/mods can run `/guardian config`, but commands are accessible to everyone.

**Why it happens:** Forgetting to add permission checks to slash commands.

**How to avoid:** Use `@app_commands.default_permissions()` and `@app_commands.checks.has_permissions()`:
```python
@app_commands.command(name="config", description="Change settings")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True, manage_guild=True, moderate_members=True)
async def guardian_config(interaction: discord.Interaction, threshold: int):
    """Only users with admin/mod permissions can use this."""
    await interaction.response.send_message(f"Threshold set to {threshold} days", ephemeral=True)
```

**Warning signs:** Regular members can change Guardian settings, security bypassed.

## Code Examples

Verified patterns from official discord.py documentation:

### Account Age Calculation
```python
# Source: https://discordpy.readthedocs.io/en/stable/api (User.created_at)
from datetime import datetime, timezone, timedelta

def get_account_age_days(user: discord.User) -> float:
    """Get account age in days."""
    now = datetime.now(timezone.utc)
    return (now - user.created_at).total_seconds() / 86400

# Check if account is less than 7 days old
if get_account_age_days(message.author) < 7:
    # Apply restrictions
```

### Message Mention Detection
```python
# Source: https://discordpy.readthedocs.io/en/stable/api (Message properties)
def has_restricted_content(message: discord.Message) -> bool:
    """Check if message contains restricted content."""
    # Check @everyone/@here
    if message.mention_everyone:
        return True

    # Check role mentions
    if message.raw_role_mentions:
        return True

    # Check attachments
    if message.attachments:
        return True

    # Check URLs
    if re.search(r'https?://\S+|www\.\S+', message.content):
        return True

    return False
```

### Ephemeral Slash Command Response
```python
# Source: https://discordpy.readthedocs.io/en/stable/interactions/api (InteractionResponse)
@app_commands.command(name="status", description="View Guardian status")
async def status_command(interaction: discord.Interaction):
    """Send ephemeral response (only visible to user)."""
    config = load_config(interaction.guild_id)
    embed = discord.Embed(
        title="Guardian Status",
        description=f"Threshold: {config['threshold_days']} days"
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
```

### Deferring Slash Commands for Slow Operations
```python
# Source: https://discordpy.readthedocs.io/en/stable/interactions/api (defer)
@app_commands.command(name="verify", description="Manually verify a member")
async def verify_command(interaction: discord.Interaction, member: discord.Member):
    """Defer while performing async operations."""
    # Acknowledge immediately (Discord requires response within 3 seconds)
    await interaction.response.defer(ephemeral=True)

    # Perform long operation
    await asyncio.sleep(2)  # Simulate long operation

    # Send followup
    await interaction.followup.send("Verification complete!", ephemeral=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hybrid commands with prefix | App commands (slash commands) only | Discord.py 2.0+ | Slash commands are Discord standard, better UX, no prefix parsing needed |
| Role name storage in config | Role ID storage | Always | Role IDs are stable; names can change and break config |
| On-demand role checking | Pre-loaded member roles | Always | discord.py provides `member.roles` cached, no extra API call |
| Message regex for @mentions | `message.mention_everyone` and `message.raw_role_mentions` | Always | Built-in properties handle edge cases, no parsing errors |
| Blocking on message delete | Async delete with exception handling | discord.py 1.0+ | Non-blocking prevents event handler hangs |

**Deprecated/outdated:**
- Prefix-based moderation commands: Use slash commands instead (modern UX, no parsing)
- In-memory-only config: Persist to file for multi-restart support (Phase 3 requires hot-reload)
- No error handling on DM sends: Always wrap in try/except (users can disable DMs)

## Open Questions

1. **What should happen if `/guardian verify @user` is called but the user is already verified?**
   - What we know: Verify command manually passes a member through verification (removes restrictions)
   - What's unclear: Should it be idempotent (no error) or should it reject already-verified users?
   - Recommendation: Make it idempotent (always works, logs the action). Moderators may manually re-verify suspicious users.

2. **Should the 7-day threshold be global (all guilds) or per-guild?**
   - What we know: Config design supports per-guild storage (guild_id key in JSON)
   - What's unclear: Does CONTEXT.md intend global threshold or per-guild flexibility?
   - Recommendation: Implement per-guild (config file structure already supports it). Safer for multi-guild deployments.

3. **How should the bot handle message.content being empty (embeds-only messages)?**
   - What we know: `message_content` intent doesn't apply to embed-only messages
   - What's unclear: Should empty content messages be flagged as violations?
   - Recommendation: Treat empty content as "no URL restriction violated." Check only attachments and mentions.

4. **Should role exemptions in config include the bot's own role?**
   - What we know: Role-based exemption system is designed for role management
   - What's unclear: Should admin-created exempt roles automatically exclude Guardian's bot role?
   - Recommendation: No. Explicitly list exempt roles in config (Guardian shouldn't need exemption if bot role is below Unverified).

## Sources

### Primary (HIGH confidence)
- [discord.py Documentation: User.created_at](https://discordpy.readthedocs.io/en/stable/api) - Account creation timestamp (UTC)
- [discord.py Documentation: Message properties](https://discordpy.readthedocs.io/en/stable/api) - `mention_everyone`, `raw_role_mentions`, `attachments`
- [discord.py Documentation: on_message event](https://discordpy.readthedocs.io/en/stable/intro) - Real-time message handling with message_content intent
- [discord.py Documentation: InteractionResponse](https://discordpy.readthedocs.io/en/stable/interactions/api) - Slash command responses (ephemeral, defer)
- [discord.py Documentation: app_commands.Group](https://discordpy.readthedocs.io/en/stable/interactions/api) - Subcommand organization

### Secondary (MEDIUM confidence - WebSearch verified with official docs)
- [URL Regex Patterns](https://uibakery.io/regex-library/url-regex-python) - Simple `https?://\S+|www\.\S+` pattern verified sufficient for Discord use case
- [Python JSON Configuration Best Practices](https://configu.com/blog/working-with-python-configuration-files-tutorial-best-practices/) - JSON file format with schema validation, hot-reload via re-reading on each access

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - discord.py is documented, tested, community-standard
- Message filtering patterns: HIGH - discord.py provides built-in detection for mentions/attachments
- Slash command organization: HIGH - app_commands.Group is official pattern
- Configuration hot-reload: MEDIUM - JSON re-read pattern is standard, but thread safety concerns require verification during implementation
- URL regex: MEDIUM - Simple pattern works, but more complex patterns exist (research suggested urlextract library); simple pattern chosen per CONTEXT.md constraints

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days for stable library, earlier if discord.py updates message filtering APIs)
