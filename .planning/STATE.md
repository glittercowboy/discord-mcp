# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-23)

**Core value:** New members must prove they're human before accessing the server, and scam links are blocked instantly.
**Current focus:** Phase 3 - Account Restrictions

## Current Position

Phase: 3 of 5 (Account Restrictions)
Plan: 0 of 0 in current phase (not yet planned)
Status: Ready to plan
Last activity: 2026-01-24 — Phase 2 complete

Progress: [████░░░░░░] 40%

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 10 min
- Total execution time: 1 hour

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2 | 20min | 10min |
| 02-verification-gate | 4 | 60min | 15min |

**Recent Trend:**
- Last 5 plans: 02-01 (2min), 02-02 (5min), 02-03 (5min), 02-04 (45min manual testing)
- Trend: Manual testing/verification takes longer than automated execution

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

### Pending Todos

- Consider moving Guardian code to separate repo (gsd/discord-guardian)
- Add slash commands for admin control (/kick, /verify, etc.)

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-24
Stopped at: Phase 2 complete, verification gate working in production
Resume file: None
