# External Integrations

**Analysis Date:** 2026-01-23

## APIs & External Services

**Discord REST API:**
- Service: Discord
- Purpose: Complete server administration including messages, moderation, roles, channels, events, webhooks, and 128+ operations
- SDK/Client: httpx (raw HTTP client)
- Base URL: `https://discord.com/api/v10`
- Auth: Bot token via `Authorization: Bot {DISCORD_BOT_TOKEN}` header
- Rate Limiting: Global limit 50 req/sec, per-route limits vary; automatic handling by implementation

## Data Storage

**Databases:**
- None - Stateless server with no persistent data storage

**File Storage:**
- None - All state is transient

**Caching:**
- None - All requests hit Discord API directly

## Authentication & Identity

**Auth Provider:**
- Discord Bot Token - Custom bot authentication
- Implementation: Token provided via environment variable `DISCORD_BOT_TOKEN`
- Token used in Authorization header for all Discord API requests in `src/server.py` via `get_headers()` function
- Scopes required: `bot`, `applications.commands`
- Required bot permissions: Administrator (or granular permissions for specific operations)

**Privileged Intents Required:**
- Server Members Intent - For member listing and role management operations
- Message Content Intent - For reading message content (not just metadata)

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Console output only via httpx debug logs
- No structured logging framework

## CI/CD & Deployment

**Hosting:**
- Local machine or development environment
- Executed on-demand via Claude Desktop/Code when tools are invoked
- No dedicated server required

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- `DISCORD_BOT_TOKEN` - Bot authentication token (must never be exposed/committed)
- `DISCORD_GUILD_ID` - Target Discord server ID for operations

**Secrets location:**
- Environment variables passed via MCP server configuration in:
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - Claude Code: `.claude/settings.json`

## Webhooks & Callbacks

**Incoming:**
- None - Server receives no inbound webhooks

**Outgoing:**
- Webhook creation/management operations available via `webhooks.create` and `webhooks.send` operations in `src/operations.json`
- Allows Claude to programmatically create and send messages through Discord webhooks
- Not receiving webhook callbacks from Discord

## Operation Categories

**128 total operations organized in `src/operations.json`:**
- messages (9) - Send, read, edit, delete, pin messages
- reactions (5) - Add, remove, list reactions
- threads (10) - Create, manage, archive threads
- channels (7) - Create, edit, delete channels
- members (6) - List, search, edit members
- moderation (7) - Kick, ban, timeout members with audit log support
- roles (5) - Create, edit, delete roles with permissions
- invites (4) - Create, list, delete invites
- events (6) - Scheduled event management
- polls (2) - Create and end polls
- guild (4) - Server settings and info
- audit_log (1) - View audit log
- automod (5) - Auto-moderation rule configuration
- webhooks (7) - Webhook management
- voice (2) - Voice channel member control
- emojis (5) - Custom emoji management
- stickers (3) - Sticker management
- forum (5) - Forum posts and tags
- stage (6) - Stage channel instances
- onboarding (3) - New member onboarding
- welcome_screen (2) - Welcome screen settings
- soundboard (5) - Soundboard sounds
- commands (5) - Slash command management
- integrations (2) - Server integrations
- widget (3) - Server widget
- vanity (2) - Vanity URL
- templates (6) - Server templates
- dm (1) - Direct messages
- bulk_ban (1) - Bulk ban users

---

*Integration audit: 2026-01-23*
