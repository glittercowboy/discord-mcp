---
phase: 04-raid-detection
plan: 03
subsystem: moderation
tags: [discord.py, slash-commands, moderation, lockdown]

# Dependency graph
requires:
  - phase: 04-01
    provides: raid_lockdown.py lockdown manager and logging_utils.log_moderation_action
provides:
  - Moderation slash commands (kick, ban, timeout) with permission checks
  - Manual lockdown controls (lockdown-on, lockdown-off) for proactive raid response
  - Moderation action logging to #security-logs
affects: [04-raid-detection (commands available for raid response), future-moderation-features]

# Tech tracking
tech-stack:
  added: []
  patterns: [slash-command-permission-checks, dynamic-module-import, ephemeral-moderation-responses]

key-files:
  created: []
  modified: [src/guardian/slash_commands.py]

key-decisions:
  - "Dynamic import of guardian module in lockdown commands to avoid circular import"
  - "Administrator permission for lockdown commands (higher than moderate_members)"
  - "Ephemeral responses for all moderation commands (privacy)"

patterns-established:
  - "Permission hierarchy: administrator > moderate_members > kick_members/ban_members"
  - "Dynamic import pattern: from . import guardian inside command function"
  - "Moderation action flow: execute → log → confirm (privacy-first)"

# Metrics
duration: 2min
completed: 2026-01-24
---

# Phase 04 Plan 03: Moderation Commands Summary

**Slash commands for moderator control: kick/ban/timeout actions with logging, manual lockdown on/off with auto-recovery**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-24T04:38:59Z
- **Completed:** 2026-01-24T04:40:51Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Five new slash commands under /guardian group for moderation control
- Permission-based access control (kick_members, ban_members, moderate_members, administrator)
- Complete moderation action logging to #security-logs with account age
- Manual lockdown controls for proactive raid response

## Task Commits

Each task was committed atomically:

1. **Task 1: Add moderation commands** - `eae1ce4` (feat)
   - /guardian kick with kick_members permission
   - /guardian ban with ban_members permission and message deletion
   - /guardian timeout with moderate_members permission
   - Logging to #security-logs via log_moderation_action
   - Ephemeral confirmations for privacy

2. **Task 2: Add manual lockdown controls** - `04288b7` (feat)
   - /guardian lockdown-on with administrator permission
   - /guardian lockdown-off with administrator permission
   - Dynamic import to avoid circular dependency
   - State validation and auto-recovery task cancellation

## Files Created/Modified
- `src/guardian/slash_commands.py` (+204 lines) - GuardianCommands class extended with 5 new commands

## Command Reference

### Moderation Commands

**`/guardian kick @user [reason]`**
- Permission: kick_members
- Bot permission: kick_members
- Logs: action, member info, account age, moderator, reason
- Response: ephemeral confirmation

**`/guardian ban @user [reason] [delete_days]`**
- Permission: ban_members
- Bot permission: ban_members
- Parameters: delete_days (0-7, default 1) for message deletion
- Logs: action, member info, account age, moderator, reason
- Response: ephemeral confirmation with deletion info

**`/guardian timeout @user [minutes] [reason]`**
- Permission: moderate_members
- Bot permission: moderate_members
- Parameters: minutes (1-40320, max 28 days, default 10)
- Logs: action, member info, account age, moderator, duration, reason
- Response: ephemeral confirmation with duration

### Lockdown Commands

**`/guardian lockdown-on`**
- Permission: administrator
- Effect: Activates lockdown mode (5s slowmode, pauses verification)
- Auto-recovery: 15 minutes
- Response: ephemeral confirmation with recovery time

**`/guardian lockdown-off`**
- Permission: administrator
- Effect: Deactivates lockdown (removes slowmode, resumes verification)
- Cancels: auto-recovery task
- Response: ephemeral confirmation

## Decisions Made

**Dynamic import pattern for lockdown commands:**
- Lockdown commands import `from . import guardian` inside function body
- Rationale: Avoids circular import (slash_commands ← guardian → slash_commands)
- Alternative considered: Pass lockdown_manager as parameter to GuardianCommands.__init__
- Chosen approach is simpler and follows discord.py patterns

**Administrator permission for lockdown:**
- Lockdown commands require administrator=True
- Rationale: Lockdown affects entire server (all channels), higher impact than single-member moderation
- Moderation commands use specific permissions (kick_members, ban_members, moderate_members)

**Ephemeral responses for privacy:**
- All moderation command confirmations use ephemeral=True
- Rationale: Prevents public exposure of moderation actions in channels
- Audit trail maintained in #security-logs (mod-only channel)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - commands follow established patterns from 03-02 (slash command structure) and 04-01 (logging utilities).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Complete for manual moderation:**
- Moderators can manually kick/ban/timeout members during raids
- Moderators can proactively enable lockdown for known events
- All actions logged to #security-logs with complete audit trail

**Ready for phase completion:**
- Plan 04-03 completes phase 4 moderation tooling
- Automated raid detection (join spike monitoring) remains for integration in guardian.py

---
*Phase: 04-raid-detection*
*Completed: 2026-01-24*
