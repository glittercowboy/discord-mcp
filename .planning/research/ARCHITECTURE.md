# Architecture Patterns: Discord Security Bot

**Domain:** Discord.py gateway-connected security bot
**Researched:** 2026-01-23
**Confidence:** HIGH (verified with official docs and community examples)

## Recommended Architecture

Guardian is a discord.py bot organized with **Cogs** (modular components) for feature separation, with shared configuration managed through a centralized Config service that reloads on change.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Guardian Bot                             │
│                      (discord.py Gateway)                        │
│                                                                  │
│  ┌──────────────┐   ┌─────────────────────────────────────┐     │
│  │  Bot Core    │   │         Cogs (Extensions)            │     │
│  │              │   │                                       │     │
│  │ • setup_hook │──▶│  ┌──────────────────────────────┐    │     │
│  │ • intents    │   │  │  VerificationCog             │    │     │
│  │ • event loop │   │  │  • on_member_join            │    │     │
│  │              │   │  │  • verify_button_callback    │    │     │
│  └──────┬───────┘   │  │  • kick_unverified_task      │    │     │
│         │           │  └──────────────────────────────┘    │     │
│         │           │                                       │     │
│         │           │  ┌──────────────────────────────┐    │     │
│         │           │  │  RaidProtectionCog           │    │     │
│         │           │  │  • on_member_join (listener) │    │     │
│         │           │  │  • analyze_join_pattern      │    │     │
│         │           │  │  • trigger_lockdown          │    │     │
│         │           │  └──────────────────────────────┘    │     │
│         │           │                                       │     │
│         │           │  ┌──────────────────────────────┐    │     │
│         │           │  │  LinkScannerCog              │    │     │
│         │           │  │  • on_message                │    │     │
│         │           │  │  • check_url_blocklist       │    │     │
│         │           │  │  • delete_and_timeout        │    │     │
│         │           │  └──────────────────────────────┘    │     │
│         │           │                                       │     │
│         │           │  ┌──────────────────────────────┐    │     │
│         │           │  │  AccountFilterCog            │    │     │
│         │           │  │  • on_message                │    │     │
│         │           │  │  • check_account_age         │    │     │
│         │           │  │  • filter_new_account_msg    │    │     │
│         │           │  └──────────────────────────────┘    │     │
│         │           │                                       │     │
│         │           │  ┌──────────────────────────────┐    │     │
│         │           │  │  LoggingCog                  │    │     │
│         │           │  │  • on_member_join            │    │     │
│         │           │  │  • on_member_remove          │    │     │
│         │           │  │  • log_to_channel            │    │     │
│         │           │  └──────────────────────────────┘    │     │
│         │           └─────────────────────────────────────┘     │
│         │                          │                            │
│         │                          │ bot.get_cog()              │
│         │                          ▼                            │
│         │           ┌─────────────────────────────────────┐     │
│         │           │    Shared Services                   │     │
│         │           │                                      │     │
│         │           │  ConfigService                       │     │
│         │           │  • load_config()                     │     │
│         │           │  • get(section, key)                 │     │
│         │           │  • reload_on_change()                │     │
│         │           │                                      │     │
│         │           │  ConvexClient (future)               │     │
│         │           │  • subscribe_to_config()             │     │
│         │           │  • log_event()                       │     │
│         │           └─────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ Discord Gateway (WebSocket)
                                  ▼
                          ┌───────────────┐
                          │  Discord API  │
                          └───────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Bot Core** | Setup, event routing, cog lifecycle | All Cogs (via load_extension) |
| **VerificationCog** | Member verification flow, captcha, role assignment | Discord API, ConfigService |
| **RaidProtectionCog** | Detect join patterns, trigger lockdown | Discord API, ConfigService, LoggingCog |
| **LinkScannerCog** | URL analysis, blocklist matching, message deletion | Discord API, ConfigService, LoggingCog |
| **AccountFilterCog** | Account age filtering, content restrictions | Discord API, ConfigService |
| **LoggingCog** | Centralized event logging to Discord channel | Discord API, ConfigService |
| **ConfigService** | Load/reload config, provide settings to cogs | File system (JSON), future: Convex |

### Data Flow

#### Event Flow (Member Join)

```
1. Discord Gateway → Bot.on_member_join event
                 ↓
2. Event dispatched to ALL cogs with @commands.Cog.listener("on_member_join")
                 ↓
3. VerificationCog.on_member_join:
   - Assign @Unverified role
   - Send verification prompt
   - Start timeout task
                 ↓
4. RaidProtectionCog.on_member_join (SAME event, parallel):
   - Increment join counter
   - Check if join_threshold exceeded
   - If raid detected → trigger lockdown
                 ↓
5. LoggingCog.on_member_join (SAME event, parallel):
   - Log join event to #security-logs
   - Include account age, username
```

**Key insight:** Multiple cogs can listen to the same event. Discord.py dispatches events to ALL registered listeners.

#### Command Flow (Configuration Change via MCP)

```
1. Claude Code → discord-mcp (REST API)
               ↓
2. MCP tool guardian.set_config(section, values)
               ↓
3. Write to guardian_config.json
               ↓
4. Guardian ConfigService detects file change (watchfiles)
               ↓
5. ConfigService.reload()
               ↓
6. All cogs access new config via ConfigService.get()
```

#### Message Flow (Link Scanning)

```
1. Discord Gateway → Bot.on_message event
                 ↓
2. LinkScannerCog.on_message:
   - Extract URLs from message.content
   - Check against blocklist (ConfigService.get("link_scanner", "blocklist"))
   - If match:
     a. Delete message (await message.delete())
     b. Timeout user (await member.timeout(...))
     c. Notify LoggingCog → bot.get_cog("LoggingCog").log_action(...)
```

### File Structure

```
discord-mcp/
├── src/
│   ├── server.py                      # MCP server (existing, add guardian.* tools)
│   ├── guardian/
│   │   ├── __init__.py
│   │   ├── bot.py                     # Main bot instance, setup_hook
│   │   ├── config_service.py          # Config loading, watching, reload
│   │   ├── cogs/
│   │   │   ├── __init__.py
│   │   │   ├── verification.py        # VerificationCog
│   │   │   ├── raid_protection.py     # RaidProtectionCog
│   │   │   ├── link_scanner.py        # LinkScannerCog
│   │   │   ├── account_filter.py      # AccountFilterCog
│   │   │   └── logging.py             # LoggingCog
│   │   ├── utils/
│   │   │   ├── captcha.py             # CAPTCHA generation
│   │   │   └── blocklists.py          # Domain blocklist data
├── guardian_config.json               # Runtime config (gitignored)
├── guardian_config.example.json       # Template config
└── run_guardian.py                    # Entry point
```

## Patterns to Follow

### Pattern 1: Cog-Based Modularity

**What:** Each security feature is a separate `commands.Cog` subclass loaded as an extension.

**When:** Always. Cogs provide clean separation, hot-reloading, and isolated state.

**Example:**
```python
# src/guardian/cogs/verification.py
from discord.ext import commands
import discord

class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending_verifications = {}  # Cog-specific state

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = self.bot.config.get("verification")
        if not config.get("enabled"):
            return

        unverified_role = member.guild.get_role(config["unverified_role_id"])
        await member.add_roles(unverified_role)
        # ... send verification prompt

async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))
```

**Why:** Official discord.py pattern. Allows independent development/testing of features.

**Source:** [Cogs - Discord.py Documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)

### Pattern 2: Shared Config Service

**What:** Central `ConfigService` class loaded into `bot.config`, accessible by all cogs via `self.bot.config.get()`.

**When:** Any cog needs settings. Alternative to passing config to each cog's `__init__`.

**Example:**
```python
# src/guardian/config_service.py
import json
from pathlib import Path
from watchfiles import awatch

class ConfigService:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config = {}
        self.load()

    def load(self):
        with open(self.config_path) as f:
            self._config = json.load(f)

    def get(self, section: str, key: str = None):
        section_config = self._config.get(section, {})
        return section_config.get(key) if key else section_config

    async def watch_for_changes(self):
        """Background task to reload on file change."""
        async for _ in awatch(self.config_path):
            self.load()

# src/guardian/bot.py
from discord.ext import commands
from .config_service import ConfigService

class GuardianBot(commands.Bot):
    async def setup_hook(self):
        self.config = ConfigService(Path("guardian_config.json"))

        # Load all cogs
        for cog in ["verification", "raid_protection", "link_scanner",
                    "account_filter", "logging"]:
            await self.load_extension(f"guardian.cogs.{cog}")

        # Start config watcher
        self.loop.create_task(self.config.watch_for_changes())
```

**Why:** Single source of truth. Hot-reload without restart. Cogs don't manage config I/O.

**Source:** Community pattern from [discord.py cog state management](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)

### Pattern 3: Inter-Cog Communication via `bot.get_cog()`

**What:** Cogs retrieve other cogs by name to call methods or share data.

**When:** Cross-feature dependencies (e.g., LinkScanner tells Logging about deleted messages).

**Example:**
```python
# src/guardian/cogs/link_scanner.py
class LinkScannerCog(commands.Cog):
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self._is_scam_link(message.content):
            await message.delete()
            await message.author.timeout(timedelta(hours=1))

            # Notify logging cog
            logging_cog = self.bot.get_cog("LoggingCog")
            if logging_cog:
                await logging_cog.log_action(
                    event="scam_link_deleted",
                    user=message.author,
                    details={"url": self._extract_url(message.content)}
                )
```

**Why:** Official discord.py pattern for cog-to-cog data sharing without tight coupling.

**Source:** [Cogs - Discord.py Documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)

### Pattern 4: Multiple Listeners for Same Event

**What:** Multiple cogs register `@commands.Cog.listener()` for the same event (e.g., `on_member_join`).

**When:** Different features need to react to the same event independently.

**Example:**
```python
# VerificationCog
@commands.Cog.listener()
async def on_member_join(self, member):
    # Assign unverified role, send prompt
    ...

# RaidProtectionCog (SAME EVENT)
@commands.Cog.listener()
async def on_member_join(self, member):
    # Track join rate, trigger lockdown if needed
    ...

# LoggingCog (SAME EVENT)
@commands.Cog.listener()
async def on_member_join(self, member):
    # Log to #security-logs
    ...
```

**Why:** Discord.py dispatches events to ALL registered listeners. Each cog handles its concern independently.

**Source:** [Event Reference - Pycord Documentation](https://docs.pycord.dev/en/v2.6.1/api/events.html)

### Pattern 5: Gateway Intents Configuration

**What:** Explicitly enable privileged intents required for security bot functionality.

**When:** Bot creation. Must match settings in Discord Developer Portal.

**Example:**
```python
# run_guardian.py
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.members = True           # Privileged: required for on_member_join/remove
intents.message_content = True   # Privileged: required to read message.content

bot = GuardianBot(
    command_prefix="!",
    intents=intents
)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
```

**Why:** Discord requires explicit intent declaration. Bots in >100 guilds need verification for privileged intents.

**Source:** [A Primer to Gateway Intents - Discord.py](https://discordpy.readthedocs.io/en/stable/intents.html)

### Pattern 6: Queue-Based Rate Limiting for Bulk Actions

**What:** Place bulk operations (e.g., welcome DMs to 200 new members) in a queue that throttles execution.

**When:** Any operation that might hit Discord's 50 req/sec rate limit.

**Example:**
```python
import asyncio
from collections import deque

class RateLimitedQueue:
    def __init__(self, rate_per_second: int = 40):
        self.queue = deque()
        self.rate = rate_per_second
        self.interval = 1.0 / rate_per_second

    async def add(self, coro):
        self.queue.append(coro)

    async def process(self):
        while True:
            if self.queue:
                coro = self.queue.popleft()
                await coro
                await asyncio.sleep(self.interval)
            else:
                await asyncio.sleep(0.1)

# Usage in VerificationCog
class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dm_queue = RateLimitedQueue(rate_per_second=40)
        bot.loop.create_task(self.dm_queue.process())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.dm_queue.add(member.send("Welcome! Please verify..."))
```

**Why:** Discord enforces 50 req/sec global limit. Queueing prevents 429 errors during raid scenarios.

**Source:** [Discord Rate Limit Handling Patterns (2025)](https://friendify.net/blog/discord-rate-limit-handling-patterns-2025.html)

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic bot.py File

**What:** All commands, listeners, and logic in a single `bot.py` or `main.py` file.

**Why bad:** Unmanageable beyond ~500 lines. No hot-reloading. Tight coupling. Difficult testing.

**Instead:** Use cogs (one per feature). Guardian has 5+ features → 5+ cogs.

**Example:** The existing `discord-mcp/src/server.py` is 2500+ lines of handler functions. Guardian should NOT follow this pattern.

### Anti-Pattern 2: Polling Config File

**What:** Using `@tasks.loop(seconds=5)` to repeatedly check if config file changed.

**Why bad:** Wastes CPU. 5-second delay before changes apply. Clutters logs.

**Instead:** Use `watchfiles` to get notified on filesystem events immediately.

```python
# BAD
@tasks.loop(seconds=5)
async def reload_config_task(self):
    new_mtime = os.path.getmtime("config.json")
    if new_mtime > self.last_mtime:
        self.load_config()

# GOOD
from watchfiles import awatch

async def watch_config(self):
    async for changes in awatch(self.config_path):
        self.load()
```

### Anti-Pattern 3: Synchronous Blocking Operations

**What:** Using `requests.get()` instead of `aiohttp` for URL checks, or `open()` instead of `aiofiles`.

**Why bad:** Blocks the event loop, freezing the entire bot. Discord.py is async-first.

**Instead:** Use async libraries (`aiohttp`, `aiofiles`).

```python
# BAD
import requests

def check_url(self, url: str):
    resp = requests.get(url)  # BLOCKS EVENT LOOP
    return resp.status_code == 200

# GOOD
import aiohttp

async def check_url(self, url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return resp.status == 200
```

**Source:** Standard async/await best practice in Python

### Anti-Pattern 4: Storing State in Global Variables

**What:** Using module-level globals to track pending verifications, raid counters, etc.

**Why bad:** Breaks when bot runs multiple instances (sharding). Not accessible to other cogs. Hard to test.

**Instead:** Store state in cog instance attributes (`self.pending_verifications`).

```python
# BAD
pending_verifications = {}  # Module global

class VerificationCog(commands.Cog):
    async def on_member_join(self, member):
        pending_verifications[member.id] = ...  # Global mutation

# GOOD
class VerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_verifications = {}  # Instance attribute

    async def on_member_join(self, member):
        self.pending_verifications[member.id] = ...
```

### Anti-Pattern 5: Ignoring Privileged Intents in Developer Portal

**What:** Setting `intents.members = True` in code but forgetting to enable in Discord Developer Portal.

**Why bad:** Bot silently fails to receive `on_member_join` events. No error, just no events.

**Instead:** Enable in BOTH places:
1. Code: `intents.members = True`
2. Portal: Bot → Privileged Gateway Intents → Server Members Intent → ON

**Source:** [A Primer to Gateway Intents - Discord.py](https://discordpy.readthedocs.io/en/stable/intents.html)

### Anti-Pattern 6: No Error Handling in Event Listeners

**What:** Event listeners that raise unhandled exceptions.

**Why bad:** Discord.py logs the error but continues. Silent failures. User sees nothing.

**Instead:** Wrap listener logic in try/except, log errors, notify mods.

```python
# BAD
@commands.Cog.listener()
async def on_message(self, message):
    urls = self.extract_urls(message.content)  # Could raise
    if self.is_blocked(urls[0]):  # Could IndexError
        await message.delete()

# GOOD
@commands.Cog.listener()
async def on_message(self, message):
    try:
        urls = self.extract_urls(message.content)
        if urls and self.is_blocked(urls[0]):
            await message.delete()
    except Exception as e:
        logger.error(f"Link scanner error: {e}", exc_info=True)
        # Optionally notify mods in logging channel
```

## Build Order (Dependency-Based)

Based on component dependencies, recommended build order:

### Phase 1: Foundation (No dependencies)
1. **Bot Core + ConfigService** - Setup bot instance, intents, config loading
2. **LoggingCog** - Depends only on config. Needed by other cogs for audit trail

### Phase 2: Core Security (Depends on Foundation)
3. **VerificationCog** - Depends on: LoggingCog (optional, for logging verification events)
4. **RaidProtectionCog** - Depends on: LoggingCog (alerts), VerificationCog (lockdown may change verification behavior)

### Phase 3: Content Filtering (Depends on Logging)
5. **LinkScannerCog** - Depends on: LoggingCog
6. **AccountFilterCog** - Depends on: LoggingCog

### Phase 4: MCP Integration (Depends on All Cogs)
7. **MCP Tools** - Add `guardian.*` tools to `discord-mcp/src/server.py` that read/write `guardian_config.json`

**Rationale:**
- **Logging first** because multiple cogs call it
- **Verification before RaidProtection** because raid lockdown might tighten verification rules
- **Content filters last** because they're independent (can be built in parallel)
- **MCP tools last** because they need all cogs to exist to be useful

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 100K users |
|---------|--------------|--------------|---------------|
| **Member joins** | Handle inline | Rate-limit DMs (40/sec queue) | Sharding required (split guilds across bot instances) |
| **Message scanning** | Check every message | Cache blocklist in memory | Add bloom filter for fast negative checks |
| **Config storage** | JSON file works | JSON file works | Move to Convex for realtime multi-instance sync |
| **Raid detection** | In-memory counter | In-memory with TTL cleanup | Redis for distributed state across shards |
| **Logging volume** | Discord channel | Discord channel + file logs | External service (Sentry, Datadog) |

**Current architecture supports up to ~10K members** without modification. Beyond that, need:
- **Sharding** (discord.py built-in: `AutoShardedBot`)
- **Distributed state** (Redis or Convex)
- **Database** for audit logs (PostgreSQL)

## Convex Integration (Future Phase)

Guardian will eventually use Convex for config and logging instead of JSON files.

**Benefits:**
- Realtime config updates (no file watching)
- Multi-instance support (if sharding)
- Built-in audit trail (updatedAt, updatedBy)
- Query logs from web dashboard
- Type-safe schema validation

**Migration path:**
1. **Phase 1:** JSON file (good for MVP)
2. **Phase 2:** Add Convex alongside JSON (write to both)
3. **Phase 3:** Remove JSON, read/write only Convex

**Architecture impact:**
- Replace `ConfigService.load()` with `ConvexClient.query("guardian:getConfig")`
- Replace `ConfigService.watch_for_changes()` with `ConvexClient.subscribe("guardian:getConfig", callback)`
- Replace `LoggingCog.log_to_channel()` with `ConvexClient.mutation("guardian:logEvent", ...)`

See GUARDIAN-BRIEF.md section "Configuration (Convex)" for schema and functions.

## Sources

### Official Documentation (HIGH confidence)
- [Cogs - Discord.py Documentation](https://discordpy.readthedocs.io/en/stable/ext/commands/cogs.html)
- [A Primer to Gateway Intents - Discord.py](https://discordpy.readthedocs.io/en/stable/intents.html)
- [Event Reference - Pycord Documentation](https://docs.pycord.dev/en/v2.6.1/api/events.html)

### Community Examples (MEDIUM confidence)
- [Discord.py Cogs Example - GitHub Gist](https://gist.github.com/EvieePy/d78c061a4798ae81be9825468fe146be)
- [Modular Discord Bots in Python: A Guide to Using Cogs - Medium](https://medium.com/@ajiboyetolu1/modular-discord-bots-in-python-a-guide-to-using-cogs-d89da141c4b9)
- [Discord Rate Limit Handling Patterns (2025)](https://friendify.net/blog/discord-rate-limit-handling-patterns-2025.html)

### Reference Implementations (MEDIUM confidence, deprecated but instructive)
- [Raid-Protect-Discord-Bot - GitHub](https://github.com/Darkempire78/Raid-Protect-Discord-Bot) (deprecated, but shows cog structure)

### Best Practices Guides (MEDIUM confidence)
- [Project Structure - create-discord-bot](https://create-discord-bot.github.io/docs/basics/project-structure/)
- [Managing bot configuration files - StudyRaid](https://app.studyraid.com/en/read/7183/176811/managing-bot-configuration-files)
