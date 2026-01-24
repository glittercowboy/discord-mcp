---
phase: 03-account-restrictions
plan: 01
subsystem: security
tags: [discord.py, message-filtering, configuration, json]

# Dependency graph
requires:
  - phase: 02-verification-gate
    provides: Guardian bot foundation with verification system
provides:
  - Message content violation detection (URLs, attachments, role mentions)
  - Account age calculation with timezone-aware datetime
  - Exemption system (Nitro boosters, role-based)
  - Configuration persistence with hot-reload and atomic writes
affects: [03-02-on_message-handler, 03-03-slash-commands]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pre-compiled regex at module level for performance"
    - "Atomic file writes via temp file + rename pattern"
    - "Hot-reload configuration by reading file on each access"

key-files:
  created:
    - src/guardian/account_restrictions.py
    - src/guardian/config_manager.py
  modified: []

key-decisions:
  - "Pre-compile URL regex at module level for high-volume message processing performance"
  - "Use temp file + rename pattern for atomic config writes to prevent corruption"
  - "Implement hot-reload by reading config file on each access (no in-memory cache)"
  - "Store guild_id as string in JSON (JSON keys must be strings)"

patterns-established:
  - "Module-level regex compilation: URL_PATTERN compiled once at import"
  - "Timezone-aware datetime: Use datetime.now(timezone.utc) for Discord timestamps"
  - "Atomic writes: temp_file.write() → temp_file.replace(CONFIG_FILE)"
  - "Graceful config fallback: Return DEFAULT_CONFIG.copy() on file errors"

# Metrics
duration: 2min
completed: 2026-01-24
---

# Phase 3 Plan 1: Core Modules Summary

**Standalone message filtering and configuration modules with hot-reload support for Discord account restrictions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-01-24T05:03:31Z
- **Completed:** 2026-01-24T05:05:46Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created account_restrictions.py with 3 core functions for message violation detection
- Created config_manager.py with hot-reload configuration persistence
- Implemented pre-compiled regex for URL detection performance
- Implemented atomic writes via temp file pattern to prevent config corruption

## Task Commits

Each task was committed atomically:

1. **Task 1: Create account_restrictions.py with filtering logic** - `4ef8c50` (feat)
2. **Task 2: Create config_manager.py with hot-reload support** - `bcac509` (feat)

## Files Created/Modified
- `src/guardian/account_restrictions.py` - Message content violation detection (URLs, attachments, @everyone/@here, role mentions), account age calculation, exemption checking
- `src/guardian/config_manager.py` - JSON-based configuration with hot-reload and atomic writes

## Decisions Made
- **Pre-compiled URL regex:** Compiled `URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')` at module level for performance during high message volume
- **Atomic write pattern:** Use temp file + rename (`temp_file.replace(CONFIG_FILE)`) to prevent corruption during concurrent writes
- **Hot-reload design:** Read config file on each `load_config()` call instead of caching for runtime updates without restart
- **Guild ID as string:** Store guild_id as string in JSON (JSON spec requires string keys)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both modules created and verified:
- account_restrictions.py (120 lines, 3+ functions, pre-compiled regex)
- config_manager.py (117 lines, 2+ functions, atomic writes)

Ready for integration into on_message handler (plan 03-02).

No blockers or concerns.

---
*Phase: 03-account-restrictions*
*Completed: 2026-01-24*
