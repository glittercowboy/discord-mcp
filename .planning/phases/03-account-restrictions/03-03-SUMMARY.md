---
phase: 03-account-restrictions
plan: 03
subsystem: deployment
tags: [discord.py, slash-commands, command-registration, discord-api]

# Dependency graph
requires:
  - phase: 03-02
    provides: GuardianCommands slash command group
provides:
  - Discord slash command registration via CommandTree.sync()
  - Guild-specific command deployment pattern
  - Working /guardian command interface in Discord
affects: [future-discord-features, deployment-processes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CommandTree attached to client.tree for proper discord.py integration"
    - "Module-level command registration before sync"
    - "Guild-only sync pattern (clear_commands + copy_global_to)"
    - "Per-guild sync loop in on_ready"

key-files:
  created: []
  modified:
    - src/guardian/guardian.py

key-decisions:
  - "Attach CommandTree to client.tree (required by discord.py architecture)"
  - "Register commands at module level before sync (order matters)"
  - "Use guild-only sync to avoid duplicate commands in UI"
  - "Clear guild commands before copy_global_to for clean state"

patterns-established:
  - "Command sync: clear_commands(guild) + copy_global_to(guild) after infrastructure setup"
  - "Debug logging: log tree contents and synced command names for troubleshooting"
  - "Per-guild error handling: try/except around sync to continue on failure"

# Metrics
duration: 24min
completed: 2026-01-24
---

# Phase 3 Plan 3: Command Registration & Verification Summary

**Discord slash commands successfully registered via CommandTree.sync() with guild-only deployment pattern**

## Performance

- **Duration:** 24 min
- **Started:** 2026-01-24T05:15:10Z
- **Completed:** 2026-01-24T05:39:13Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- CommandTree integration with proper client.tree attribute attachment
- Module-level command registration for discord.py compatibility
- Guild-only sync pattern to prevent duplicate commands
- Working slash commands verified in Discord (/guardian status, config, verify, exempt)

## Task Commits

Each task was committed atomically:

1. **Task 1: Register slash commands in on_ready event** - `450aa2c` (feat)
   - Debugging iterations:
     - `0cd1fb5` (fix) - Attach CommandTree to client.tree attribute
     - `3d9b270` (fix) - Register commands in on_ready, log synced command names
     - `36ca117` (fix) - Register commands at module level, log tree contents
     - `f584f75` (fix) - Use global sync then copy_global_to for guild sync
     - `f408e3c` (fix) - Clear global commands to remove duplicates, guild-only sync
     - `1521d19` (fix) - Clear guild commands before copy_global_to, skip global sync

2. **Task 2: Human verification checkpoint** - APPROVED

## Files Created/Modified
- `src/guardian/guardian.py` - Added CommandTree initialization and guild sync in on_ready
- `.planning/debug/guardian-commands-not-visible.md` - Debugging notes for command visibility issue (not production code)

## Decisions Made
- **CommandTree attachment:** Attached to `client.tree` instead of standalone variable (required by discord.py architecture for proper command routing)
- **Module-level registration:** Moved `tree.add_command()` call to module level before on_ready (discord.py requires commands registered before sync)
- **Guild-only sync:** Changed from global sync to guild-only (`clear_commands(guild=guild)` + `copy_global_to(guild=guild)`) to prevent duplicate commands appearing in Discord UI
- **Sync timing:** Sync commands after infrastructure initialization (ensures channels exist for logging)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CommandTree not attached to client.tree attribute**
- **Found during:** Task 1 (initial slash command registration)
- **Issue:** Commands registered but not appearing in Discord - discord.py requires CommandTree attached to `client.tree` attribute for proper routing
- **Fix:** Changed from standalone `tree` variable to `client.tree = app_commands.CommandTree(client)`
- **Files modified:** src/guardian/guardian.py
- **Verification:** Checked discord.py documentation, verified attribute attachment pattern
- **Committed in:** 0cd1fb5 (fix commit)

**2. [Rule 1 - Bug] Commands registered in wrong order**
- **Found during:** Task 1 (debugging command visibility)
- **Issue:** `tree.add_command()` called inside on_ready after sync - discord.py requires commands registered at module level before sync
- **Fix:** Moved command registration to module level (after CommandTree creation, before on_ready)
- **Files modified:** src/guardian/guardian.py
- **Verification:** Logged tree contents before sync, confirmed commands present
- **Committed in:** 36ca117 (fix commit)

**3. [Rule 1 - Bug] Duplicate commands from global sync**
- **Found during:** Task 1 (commands appearing twice in Discord UI)
- **Issue:** Global sync + guild sync caused duplicate command entries in slash command autocomplete
- **Fix:** Changed to guild-only sync pattern: `clear_commands(guild=guild)` + `copy_global_to(guild=guild)` without global sync
- **Files modified:** src/guardian/guardian.py
- **Verification:** Tested in Discord, commands appear once
- **Committed in:** f408e3c, 1521d19 (fix commits - iterative refinement)

---

**Total deviations:** 3 auto-fixed (3 bugs - discord.py integration issues)
**Impact on plan:** All auto-fixes required for correct command registration. Discord.py slash command architecture has specific requirements not fully captured in initial plan. Debugging was necessary discovery work.

## Issues Encountered

**Discord slash command visibility debugging (24 minutes):**
- Initial implementation followed basic pattern from RESEARCH.md but commands didn't appear
- Root causes discovered through iterative debugging:
  1. CommandTree must be attached to `client.tree` (not documented in research)
  2. Commands must be registered at module level (timing requirement)
  3. Global sync creates duplicates (guild-only sync required)
- Resolution: Applied fixes iteratively with verification after each change
- Captured debugging process in `.planning/debug/guardian-commands-not-visible.md` for future reference

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 3 account restrictions fully complete and verified:
- ✓ Slash commands registered and visible in Discord
- ✓ /guardian status shows current configuration
- ✓ /guardian config updates threshold with hot-reload
- ✓ /guardian verify manually passes members
- ✓ /guardian exempt manages role exemptions
- ✓ Message filtering enforces restrictions on new accounts
- ✓ Violations logged to #security-logs

All 5 roadmap success criteria validated:
1. Discord account <7 days old cannot post URLs, attachments, or @mention roles ✓
2. Moderator runs /guardian status and sees current config ✓
3. Moderator runs /guardian config and changes settings without restart ✓
4. Moderator runs /guardian verify @user and manually passes a stuck member ✓
5. Role added to exemption list bypasses new account restrictions ✓

Phase 3 complete. Ready for next phase planning.

No blockers or concerns.

---
*Phase: 03-account-restrictions*
*Completed: 2026-01-24*
