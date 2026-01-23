---
phase: 01-foundation
plan: 01
subsystem: infra
tags: [discord.py, gateway, bot, roles, channels]

# Dependency graph
requires:
  - phase: None (initial phase)
    provides: N/A
provides:
  - Guardian bot with Discord Gateway connection
  - Idempotent infrastructure initialization (roles and channels)
  - Auto-role assignment on member join
affects: [02-verification, 03-slash-commands, 05-link-scanning]

# Tech tracking
tech-stack:
  added: [discord.py 2.6.4]
  patterns: [idempotent infrastructure creation, Gateway event handlers]

key-files:
  created:
    - src/guardian/__init__.py
    - src/guardian/config.py
    - src/guardian/guardian.py
    - src/guardian/infrastructure.py
  modified:
    - pyproject.toml

key-decisions:
  - "Separate Guardian bot code from MCP server (different lifecycles: 24/7 Gateway vs on-demand REST)"
  - "Enable message_content intent now for Phase 5 link scanning (avoid re-enabling later)"
  - "Idempotent infrastructure functions safe to call multiple times on restart"

patterns-established:
  - "Idempotent creation: check with discord.utils.get before creating"
  - "Permission overwrites for channel isolation (@Unverified only in #verify)"
  - "Comprehensive error handling with logging for all async operations"

# Metrics
duration: 5min
completed: 2026-01-23
---

# Phase 01 Plan 01: Guardian Gateway Bot Summary

**Discord.py Gateway bot with idempotent infrastructure initialization, auto-creating #verify, #security-logs channels and @Unverified/@Verified roles on startup**

## Performance

- **Duration:** 5 min
- **Started:** 2026-01-23T23:01:35Z
- **Completed:** 2026-01-23T23:06:35Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Guardian bot connects to Discord Gateway with members and message_content intents
- Idempotent infrastructure initialization creates required roles and channels safely on every restart
- #verify channel isolated with permission overwrites (@Unverified only)
- New members automatically assigned @Unverified role on join
- Foundation ready for Phase 2 emoji verification implementation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Guardian project structure with discord.py** - `8ade186` (feat)
2. **Task 2: Implement idempotent infrastructure initialization** - `fc83059` (feat)
3. **Task 3: Create Guardian bot client with Gateway connection** - `5aa1e76` (feat)

## Files Created/Modified
- `src/guardian/__init__.py` - Package initialization
- `src/guardian/config.py` - Loads DISCORD_BOT_TOKEN from environment
- `src/guardian/guardian.py` - Main bot client with on_ready and on_member_join handlers
- `src/guardian/infrastructure.py` - Idempotent role/channel creation functions
- `pyproject.toml` - Added discord.py>=2.6.4 dependency

## Decisions Made
- Separated Guardian bot code (src/guardian/) from MCP server (src/server.py) because they have different lifecycles: Guardian runs 24/7 Gateway connection, MCP runs as on-demand REST subprocess
- Enabled message_content intent now for future Phase 5 link scanning to avoid needing to re-enable later
- Used idempotent functions throughout (discord.utils.get checks before creation) to make infrastructure initialization safe on bot restarts

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

**Bot deployment requires environment configuration.** Next plan (01-02) will handle Railway deployment with DISCORD_BOT_TOKEN secret.

For local testing before deployment:
```bash
export DISCORD_BOT_TOKEN="your_bot_token_here"
python -m src.guardian.guardian
```

## Next Phase Readiness

- Guardian bot code complete and follows discord.py 2.6.4 Gateway patterns
- Infrastructure initialization is idempotent (safe to restart)
- Required intents enabled (members, message_content)
- #verify channel has correct permission isolation
- Ready for Railway deployment (Plan 01-02)
- Ready for emoji verification implementation (Phase 02)

---
*Phase: 01-foundation*
*Completed: 2026-01-23*
