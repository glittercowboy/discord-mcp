# GSD Guardian

## What This Is

A real-time Discord security bot that protects the GSD community from raids, scams, and automated attacks. Guardian runs as a 24/7 worker process on Railway, monitoring Discord Gateway events and enforcing security policies. It's controlled via Discord slash commands (`/guardian ...`) — no external infrastructure required.

## Core Value

New members must prove they're human before accessing the server, and scam links are blocked instantly.

## Requirements

### Validated

- MCP server for Discord admin operations (REST API) — existing
- 128 operations across 29 categories (messages, channels, members, moderation, etc.) — existing
- FastMCP framework with discover/schema/execute pattern — existing

### Active

- [ ] Verification gate with emoji selection challenge
- [ ] Raid detection with configurable thresholds
- [ ] Anti-scam link scanner with blocklist
- [ ] New account restrictions for accounts < 7 days old
- [ ] Full activity logging to #security-logs
- [ ] Discord slash commands for configuration
- [ ] Auto-create required channels/roles on first run
- [ ] Railway deployment as worker process

### Out of Scope

- Convex integration — Discord slash commands provide sufficient control without external dependencies
- MCP tools for Guardian control — Guardian is autonomous, not invoked by Claude Code
- Image CAPTCHA — emoji selection provides adequate bot detection with better UX
- Web dashboard — slash commands are sufficient for configuration

## Context

**Existing codebase:** discord-mcp is an MCP server that exposes Discord REST API operations to Claude Code. It runs locally as a subprocess, making on-demand API calls. It handles admin tasks but doesn't monitor real-time events.

**Guardian is different:** It connects to Discord's Gateway (WebSocket) to receive events as they happen — member joins, messages posted, raids starting. It runs 24/7 on Railway, independent of Claude Code.

**They share the bot token** but serve different purposes:
- discord-mcp: REST API, on-demand admin tasks, runs locally
- Guardian: Gateway connection, real-time monitoring, runs on Railway

**The GSD Discord** serves both developers using the GSD Claude Code workflow and holders of the $GSD token. Very active community, under 500 members. Has token-related channels alongside framework discussion channels.

**Recent threat context:** Had to manually ban a scammer posting fake mint links. Expect ongoing targeting due to crypto association.

## Constraints

- **Hosting**: Railway worker process (no HTTP port, just Gateway connection)
- **Control**: Discord slash commands only (no Convex, no external API)
- **Bot permissions**: Requires privileged intents (GUILD_MEMBERS, MESSAGE_CONTENT)
- **Python ecosystem**: Build with discord.py to match existing codebase patterns

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Discord slash commands over Convex | Simpler architecture, works from phone, no external dependencies | — Pending |
| Emoji selection for verification | Stops commodity bots, better UX than CAPTCHA, adequate for threat model | — Pending |
| 10 min verification timeout | Industry standard, balances user convenience with security | — Pending |
| Delete + 1hr timeout for scam links | Punishes without permanent ban, allows appeal for mistakes | — Pending |
| Auto-ban on 2nd scam offense | Zero tolerance for repeat offenders | — Pending |
| Guardian auto-creates infrastructure | Reduces manual setup, ensures correct permissions | — Pending |

---
*Last updated: 2026-01-23 after initialization*
