# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-23)

**Core value:** New members must prove they're human before accessing the server, and scam links are blocked instantly.
**Current focus:** Phase 4 - Raid Detection

## Current Position

Phase: 4 of 5 (Raid Detection)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-01-24 — Completed 04-02-PLAN.md

Progress: [████████░░] 73%

## Performance Metrics

**Velocity:**
- Total plans completed: 11
- Average duration: 8 min
- Total execution time: 92 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | 20min | 10min |
| 02-verification-gate | 4 | 60min | 15min |
| 03-account-restrictions | 3 | 28min | 9min |
| 04-raid-detection | 2 | 4min | 2min |

**Recent Trend:**
- Last 5 plans: 03-02 (2min), 03-03 (24min debugging), 04-01 (3min), 04-02 (1min)
- Trend: Infrastructure plans execute quickly, integration plans require debugging

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Discord slash commands over Convex — Simpler architecture, works from phone, no external dependencies
- Emoji selection for verification — Stops commodity bots, better UX than CAPTCHA, adequate for threat model
- Guardian auto-creates infrastructure — Reduces manual setup, ensures correct permissions
- Separate Guardian bot from MCP server (01-01) — Different lifecycles: 24/7 Gateway vs on-demand REST
- Enable message_content intent now (01-01) — Avoid re-enabling for Phase 5 link scanning
- Idempotent infrastructure functions (01-01) — Safe to call multiple times on restart
- Worker deployment for Railway (01-02) — No health check endpoint because Guardian is Gateway WebSocket, not HTTP server
- 180s view timeout for ephemeral verification (02-01) — Acceptable state loss on restart, user can retry
- Permission-based moderator bypass (02-01) — administrator/moderate_members/manage_guild permissions
- Atomic role operations (02-01) — Sequential add_roles/remove_roles prevents race conditions
- Discord verification level 2 (02-04) — Email + 5min account age, Guardian handles the rest
- Grandfather existing members (02-04) — Bulk-assigned @Verified to 264 members to avoid disruption
- Channel permissions via role overwrites (02-04) — Deny @everyone, allow @Verified on categories
- #security-logs mod-only (02-04) — Contains sensitive info, restricted to Moderator role
- Pre-compile URL regex at module level (03-01) — Performance for high-volume message processing
- Atomic writes via temp file + rename (03-01) — Prevent config corruption during concurrent writes
- Hot-reload by reading file each access (03-01) — Runtime config updates without bot restart
- Guild ID as string in JSON (03-01) — JSON spec requires string keys
- app_commands.Group for slash commands (03-02) — Organized subcommand structure
- Ephemeral slash responses (03-02) — Privacy for admin commands
- Silent deletion + DM (03-02) — Reduce public friction, educate users
- CommandTree at client.tree (03-03) — Required for discord.py slash command registration
- Guild-only sync with clear_commands (03-03) — Prevents duplicate commands, instant propagation
- Deque-based sliding window (04-01) — O(1) append/popleft vs O(n) list operations for join tracking
- 5-second slowmode during lockdown (04-01) — Balance between rate limiting and usability
- Exclude verify/security-logs from slowmode (04-01) — Operational channels remain functional during raid
- 15-minute auto-recovery default (04-01) — Most raids conclude quickly, prevents indefinite lockdown
- Immediate moderation logging (04-01) — No audit log delay, complete data at call site
- RAID-03 runs independently of RAID-01 (04-02) — Separate alert even if join count <10, covers slow-drip raids
- Verification pause after role assignment (04-02) — Users get @Unverified but no UI during lockdown
- Moderator bypass preserved (04-02) — Joins tracked for metrics but verification skipped

### Pending Todos

- Consider moving Guardian code to separate repo (gsd/discord-guardian)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-24
Stopped at: Completed 04-02-PLAN.md
Resume file: None
