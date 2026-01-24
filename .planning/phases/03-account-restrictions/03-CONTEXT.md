# Phase 3: Account Restrictions - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

New Discord accounts (<7 days old) are restricted from posting potentially malicious content. Moderators control Guardian via slash commands. Raid detection and link scanning are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Content Restrictions
- Block: URLs, attachments, and @role mentions (covers phishing, malware, @everyone spam)
- Violation action: Delete silently, DM user explaining why
- No proactive warning — DM on violation is sufficient
- All violations logged to #security-logs (helps mods spot patterns)

### Account Age Threshold
- Default 7 days, configurable via `/guardian config`
- Only Discord account age matters (not server membership duration)
- Re-evaluate on each message (no persistent timers per user)
- Nitro boosters auto-exempt (paid users = low scam risk)

### Slash Command Design
- Structure: `/guardian <subcommand>` (single namespace)
- Commands: `status`, `config`, `verify`, `exempt`
  - `status` — View current config and bot state
  - `config` — Change settings (threshold, enabled features)
  - `verify` — Manually pass a stuck user through verification
  - `exempt` — Manage role exemptions (list/add/remove)
- Permissions: Moderator+ (administrator OR manage_guild OR moderate_members)
- Visibility: Ephemeral by default, `--public` flag for transparency when needed

### Exemption System
- Auto-exempt: @Moderator role, Nitro boosters
- Blanket exemptions only (no per-restriction granularity)
- Storage: In-memory config persisted to JSON file (reads on startup)
- `/guardian exempt` subcommands: `list`, `add @role`, `remove @role`

### Claude's Discretion
- Config file format and location
- DM message wording for violations
- Exact slash command option names and descriptions
- Error handling for edge cases (DMs disabled, etc.)

</decisions>

<specifics>
## Specific Ideas

- Violation DM should be friendly, not accusatory ("Your account is new, so we restrict certain content for the first 7 days")
- `/guardian status` should show at-a-glance: restrictions enabled/disabled, current threshold, exempt roles count

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-account-restrictions*
*Context gathered: 2026-01-24*
