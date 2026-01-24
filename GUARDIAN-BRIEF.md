# GSD Guardian Bot: Security Module Brief

## Executive Summary

Build a real-time Discord security bot ("GSD Guardian") that protects the GSD community from raids, scams, and automated attacks. The bot runs as a persistent process alongside the existing discord-mcp server, with all configuration controllable via Claude Code through new MCP tools.

## Why This Is Needed

The GSD Discord is associated with a meme coin, making it a high-value target for:
- **Raid attacks**: Mass bot joins flooding channels with spam/scams
- **Phishing scams**: Fake "free mint" / "airdrop" messages (one was manually banned today)
- **Account takeovers**: Compromised accounts posting malicious links
- **Impersonation**: Scammers mimicking admins/mods

Current protection is inadequate:
- Discord's native AutoMod catches some spam but has no account-age awareness
- No human verification gate (bots pass onboarding prompts)
- No raid detection (mass-join → lockdown)
- No real-time event monitoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Code                              │
│                         │                                    │
│                    MCP Protocol                              │
│                         │                                    │
│     ┌───────────────────┴───────────────────┐               │
│     ▼                                       ▼               │
│ ┌─────────────────┐                 ┌─────────────────┐     │
│ │  discord-mcp    │                 │  GSD Guardian   │     │
│ │  (REST API)     │◄───config.json──│  (Gateway)      │     │
│ │                 │                 │                 │     │
│ │ • Admin actions │                 │ • on_member_join│     │
│ │ • Channel mgmt  │                 │ • on_message    │     │
│ │ • Moderation    │                 │ • raid detection│     │
│ └────────┬────────┘                 └────────┬────────┘     │
│          │                                   │               │
│          └─────────────┬─────────────────────┘               │
│                        ▼                                     │
│                  Discord API                                 │
└─────────────────────────────────────────────────────────────┘
```

**Key insight**: The existing `discord-mcp` server handles REST API calls (admin actions on demand). The Guardian bot connects to Discord's Gateway (WebSocket) to receive real-time events. They share the same bot token but serve different purposes.

**Communication**: Guardian reads its config from a JSON file. The MCP server gets new tools (`guardian.*`) that write to this config file. Guardian watches the file for changes and hot-reloads.

## Core Features

### 1. Verification Gate

**Purpose**: Require new members to prove they're human before accessing the server.

**Flow**:
1. New member joins → assigned `@Unverified` role (can only see #verify channel)
2. Bot posts verification prompt in #verify with button
3. Member clicks button → presented with CAPTCHA or simple challenge
4. Pass → `@Unverified` removed, gains `@Member` role, sees all channels
5. Fail/timeout (configurable, default 10 min) → kicked with rejoin invite

**Implementation**:
- `on_member_join` event → assign unverified role, DM welcome + verify instructions
- Button interaction handler for verification
- CAPTCHA: simple image with distorted text, or math problem, or emoji selection
- Store pending verifications in memory with timeout tasks

**Config options** (controllable via MCP):
```json
{
  "verification": {
    "enabled": true,
    "channel_id": "123...",
    "unverified_role_id": "456...",
    "verified_role_id": "789...",
    "timeout_seconds": 600,
    "kick_on_timeout": true,
    "challenge_type": "button" | "captcha" | "math" | "emoji"
  }
}
```

### 2. Raid Detection & Response

**Purpose**: Detect mass-join attacks and automatically lock down the server.

**Detection signals**:
- X joins within Y seconds (default: 10 joins in 30 seconds)
- High % of joins from accounts < 7 days old
- Similar usernames/avatars in join wave

**Response actions** (configurable severity levels):
1. **Alert**: Post to mod channel, ping @Mods
2. **Slow**: Enable 60s slowmode on all public channels
3. **Lock**: Pause new joins (set verification to highest), lock channels
4. **Purge**: Auto-kick all unverified members who joined in last N minutes

**Auto-recovery**: After X minutes of no suspicious activity, gradually restore normal state.

**Config options**:
```json
{
  "raid_protection": {
    "enabled": true,
    "alert_channel_id": "123...",
    "join_threshold": 10,
    "join_window_seconds": 30,
    "new_account_days": 7,
    "new_account_threshold_percent": 50,
    "response_level": "alert" | "slow" | "lock" | "purge",
    "auto_recover_minutes": 15
  }
}
```

### 3. New Account Restrictions

**Purpose**: Limit what fresh Discord accounts can do until they've aged.

**Restrictions for accounts < X days old**:
- Cannot post links
- Cannot post attachments/images
- Cannot mention @everyone or roles
- Messages held for manual approval (optional)

**Config options**:
```json
{
  "new_account_filter": {
    "enabled": true,
    "min_age_days": 7,
    "block_links": true,
    "block_attachments": true,
    "block_mentions": true,
    "quarantine_channel_id": null,
    "exempt_roles": ["role_id_1", "role_id_2"]
  }
}
```

### 4. Anti-Scam Link Scanner

**Purpose**: Block known phishing domains and suspicious URLs in real-time.

**Implementation**:
- Maintain blocklist of known scam domains (updated regularly)
- Check all posted URLs against blocklist
- Heuristic detection: `vercel.app`, `netlify.app`, `github.io` domains with suspicious paths
- Check URL redirects (scammers use shorteners)

**Actions on detection**:
1. Delete message immediately
2. Timeout user (configurable duration)
3. Log to mod channel with context
4. Optionally auto-ban repeat offenders

**Config options**:
```json
{
  "link_scanner": {
    "enabled": true,
    "action": "delete" | "delete_timeout" | "delete_ban",
    "timeout_seconds": 3600,
    "log_channel_id": "123...",
    "custom_blocklist": ["scamdomain.com", "fakemint.xyz"],
    "suspicious_tlds": [".xyz", ".club", ".top"],
    "auto_ban_threshold": 2
  }
}
```

### 5. Logging & Audit Trail

**Purpose**: Record all security events for review.

**Events to log**:
- Member joins/leaves (with account age)
- Verification attempts (pass/fail)
- Raid alerts triggered
- Messages deleted by filters
- Moderation actions (kicks/bans/timeouts)
- Config changes

**Log format**: Embed messages to designated logging channel with timestamps, user info, action taken, and reason.

**Config options**:
```json
{
  "logging": {
    "enabled": true,
    "channel_id": "123...",
    "log_joins": true,
    "log_leaves": true,
    "log_verification": true,
    "log_moderation": true,
    "log_deleted_messages": true
  }
}
```

## MCP Tools to Add

Add these tools to `discord-mcp` for Claude Code control:

```python
# Configuration
guardian.get_config()           # Get current Guardian config
guardian.set_config(section, values)  # Update config section
guardian.reload()               # Force config reload

# Verification
guardian.set_verification(enabled, channel_id, timeout, challenge_type)
guardian.list_pending()         # List users awaiting verification
guardian.verify_user(user_id)   # Manually verify a user
guardian.kick_unverified()      # Kick all unverified members

# Raid Protection
guardian.set_raid_protection(enabled, threshold, window, response)
guardian.trigger_lockdown()     # Manual lockdown
guardian.end_lockdown()         # Manual recovery
guardian.get_raid_status()      # Current raid detection state

# New Account Filter
guardian.set_account_filter(enabled, min_age, restrictions)
guardian.whitelist_user(user_id)  # Exempt specific user

# Link Scanner
guardian.add_blocked_domain(domain)
guardian.remove_blocked_domain(domain)
guardian.list_blocked_domains()
guardian.scan_message(content)  # Test scanner on text

# Logging
guardian.get_logs(limit, filter)  # Retrieve recent logs
guardian.export_logs(start, end)  # Export log range
```

## Technical Requirements

### Discord Bot Setup

**Required Gateway Intents** (must enable in Discord Developer Portal):
- `GUILDS` - basic guild info
- `GUILD_MEMBERS` (privileged) - member join/leave events
- `GUILD_MESSAGES` - message events
- `MESSAGE_CONTENT` (privileged) - read message content for scanning

**Required Permissions**:
- Manage Roles (assign verified/unverified)
- Kick Members
- Ban Members
- Manage Messages (delete)
- Moderate Members (timeout)
- View Channels
- Send Messages
- Embed Links

### Dependencies

```
discord.py >= 2.3.0   # Gateway client with interactions support
aiofiles              # Async file I/O for config
watchfiles            # File change detection for hot reload
aiohttp               # URL checking/redirects
Pillow                # CAPTCHA image generation (if using image captcha)
```

### File Structure

```
discord-mcp/
├── src/
│   ├── server.py           # Existing MCP server (add guardian.* tools)
│   ├── operations.json     # Existing operations schema
│   ├── guardian/
│   │   ├── __init__.py
│   │   ├── bot.py          # Main Guardian bot class
│   │   ├── cogs/
│   │   │   ├── verification.py
│   │   │   ├── raid_protection.py
│   │   │   ├── account_filter.py
│   │   │   ├── link_scanner.py
│   │   │   └── logging.py
│   │   ├── captcha.py      # CAPTCHA generation
│   │   ├── config.py       # Config management + hot reload
│   │   └── blocklist.py    # Scam domain list
├── guardian_config.json    # Runtime config (gitignored)
├── guardian_config.example.json
└── run_guardian.py         # Entry point to run Guardian bot
```

### Running

Guardian runs as a separate process from the MCP server:

```bash
# Terminal 1: MCP server (started by Claude Code automatically)
uv run python -m src.server

# Terminal 2: Guardian bot (run manually or via systemd/pm2)
uv run python run_guardian.py
```

Or combine into single process if preferred (Guardian as background task within MCP server).

## Deployment (Railway)

Guardian runs as a persistent process on Railway.

**railway.json**:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python run_guardian.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Environment variables** (set in Railway dashboard):
- `DISCORD_BOT_TOKEN` - Bot token (same as discord-mcp uses)
- `DISCORD_GUILD_ID` - GSD server ID
- `CONVEX_URL` - Convex deployment URL

**Procfile** (alternative to railway.json):
```
worker: python run_guardian.py
```

Note: This is a **worker** process (no HTTP port), not a web service. Railway handles this fine.

## Configuration (Convex)

Config is stored in Convex for realtime sync. Guardian subscribes to config changes and applies them instantly without restart.

### Convex Schema

```typescript
// convex/schema.ts
import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  guardianConfig: defineTable({
    section: v.string(), // "verification", "raid_protection", etc.
    config: v.any(),     // JSON config for that section
    updatedAt: v.number(),
    updatedBy: v.string(), // "claude-code" or "dashboard"
  }).index("by_section", ["section"]),

  securityLogs: defineTable({
    event: v.string(),    // "member_join", "raid_detected", "scam_blocked", etc.
    userId: v.optional(v.string()),
    username: v.optional(v.string()),
    details: v.any(),
    timestamp: v.number(),
  }).index("by_event", ["event"])
    .index("by_timestamp", ["timestamp"]),

  blockedDomains: defineTable({
    domain: v.string(),
    reason: v.string(),
    addedAt: v.number(),
    addedBy: v.string(),
  }).index("by_domain", ["domain"]),
});
```

### Convex Functions

```typescript
// convex/guardian.ts
import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// Get all config (Guardian subscribes to this)
export const getConfig = query({
  handler: async (ctx) => {
    const configs = await ctx.db.query("guardianConfig").collect();
    return Object.fromEntries(configs.map(c => [c.section, c.config]));
  },
});

// Update a config section (called by MCP tools)
export const setConfig = mutation({
  args: { section: v.string(), config: v.any() },
  handler: async (ctx, { section, config }) => {
    const existing = await ctx.db
      .query("guardianConfig")
      .withIndex("by_section", q => q.eq("section", section))
      .first();

    if (existing) {
      await ctx.db.patch(existing._id, {
        config,
        updatedAt: Date.now(),
        updatedBy: "claude-code"
      });
    } else {
      await ctx.db.insert("guardianConfig", {
        section,
        config,
        updatedAt: Date.now(),
        updatedBy: "claude-code"
      });
    }
  },
});

// Log security event
export const logEvent = mutation({
  args: {
    event: v.string(),
    userId: v.optional(v.string()),
    username: v.optional(v.string()),
    details: v.any()
  },
  handler: async (ctx, args) => {
    await ctx.db.insert("securityLogs", {
      ...args,
      timestamp: Date.now(),
    });
  },
});

// Get recent logs
export const getLogs = query({
  args: { limit: v.optional(v.number()), event: v.optional(v.string()) },
  handler: async (ctx, { limit = 100, event }) => {
    let query = ctx.db.query("securityLogs").withIndex("by_timestamp");
    if (event) {
      query = ctx.db.query("securityLogs").withIndex("by_event", q => q.eq("event", event));
    }
    return await query.order("desc").take(limit);
  },
});

// Blocked domains
export const getBlockedDomains = query({
  handler: async (ctx) => {
    return await ctx.db.query("blockedDomains").collect();
  },
});

export const addBlockedDomain = mutation({
  args: { domain: v.string(), reason: v.string() },
  handler: async (ctx, { domain, reason }) => {
    await ctx.db.insert("blockedDomains", {
      domain: domain.toLowerCase(),
      reason,
      addedAt: Date.now(),
      addedBy: "claude-code",
    });
  },
});
```

### Guardian Python Client

```python
# src/guardian/convex_client.py
from convex import ConvexClient
import asyncio
import os

class GuardianConfig:
    def __init__(self):
        self.client = ConvexClient(os.environ["CONVEX_URL"])
        self._config = {}
        self._callbacks = []

    async def start(self):
        """Subscribe to config changes."""
        # Initial fetch
        self._config = await self.client.query("guardian:getConfig")

        # Subscribe to realtime updates
        self.client.subscribe("guardian:getConfig", self._on_config_change)

    def _on_config_change(self, new_config):
        """Called when config changes in Convex."""
        self._config = new_config
        for callback in self._callbacks:
            callback(new_config)

    def on_change(self, callback):
        """Register callback for config changes."""
        self._callbacks.append(callback)

    def get(self, section: str, default=None):
        return self._config.get(section, default)

    async def log_event(self, event: str, user_id: str = None,
                        username: str = None, details: dict = None):
        await self.client.mutation("guardian:logEvent", {
            "event": event,
            "userId": user_id,
            "username": username,
            "details": details or {},
        })
```

### Why Convex

1. **Instant config updates** - Guardian subscribes to queries, changes propagate immediately
2. **No polling/websocket code** - Convex handles the realtime plumbing
3. **Type safety** - Schema validates config structure
4. **Built-in audit trail** - `updatedAt`, `updatedBy` on every config change
5. **Logs in same place** - Security events stored alongside config
6. **Future dashboard** - Convex functions double as API for web dashboard later

## Server Setup Required

Before running Guardian, Lex needs to create:

1. **#verify channel** - Where new members complete verification
2. **#security-logs channel** - Where Guardian posts audit logs
3. **@Unverified role** - Assigned to new members, can only see #verify
4. **@Member role** - Granted after verification, sees all channels

Channel permissions:
- #verify: @Unverified can view + send, @everyone cannot view
- All other channels: @Unverified cannot view

## Implementation Priority

1. **Verification gate** - Most critical, stops automated bots
2. **Raid detection** - Prevents mass attacks
3. **Link scanner** - Catches scam posts
4. **New account filter** - Reduces manual spam
5. **Logging** - Nice to have for auditing

## Success Criteria

- New members must pass verification to access channels
- Mass-join events (10+ in 30s) trigger automatic alerts
- Known scam links are deleted within 1 second of posting
- All security events logged to #security-logs
- All config changes possible via Claude Code (no Discord UI needed)

## References

- [Discord.py Gateway Intents](https://discordpy.readthedocs.io/en/latest/intents.html)
- [Discord.py API Reference](https://discordpy.readthedocs.io/en/latest/api.html)
- [Discord Raid Protection Guide](https://support.discord.com/hc/en-us/articles/10989121220631-How-to-Protect-Your-Server-from-Raids-101)
- [Raid-Protect-Discord-Bot (reference implementation)](https://github.com/Darkempire78/Raid-Protect-Discord-Bot)
- [RaidProtect Bot](https://raidprotect.bot/en)
- [SecurityBot Web3](https://securitybot.info/)
