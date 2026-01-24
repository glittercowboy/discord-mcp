---
phase: 04-raid-detection
plan: 02
subsystem: security
tags: [discord.py, raid-detection, event-handlers, anti-raid]

# Dependency graph
requires:
  - phase: 04-01
    provides: raid_detection.py, raid_lockdown.py, logging_utils.py modules
provides:
  - Live raid detection on member joins with 30-second sliding window
  - RAID-01 alert (10+ joins in 30 seconds)
  - RAID-03 alert (>50% new accounts)
  - Automatic lockdown activation on raid detection
  - Verification pause during active lockdown
affects: [04-03, manual-raid-response]

# Tech tracking
tech-stack:
  added: []
  patterns: [event-driven-raid-detection, lockdown-state-management]

key-files:
  created: []
  modified: [src/guardian/guardian.py]

key-decisions:
  - "RAID-03 runs independently of RAID-01 (separate alert even if join count <10)"
  - "Verification pause happens after role assignment (users get @Unverified but no UI)"
  - "Moderator bypass preserved (joins tracked but verification skipped)"

patterns-established:
  - "Event flow: moderator bypass → add join → raid check → role assignment → lockdown check → verification UI"
  - "Alert pattern: Check threshold, build embed, send to security-logs, trigger lockdown if raid_detected"

# Metrics
duration: 1min
completed: 2026-01-24
---

# Phase 4 Plan 2: Raid Detection Integration Summary

**Live raid detection wired into on_member_join event with RAID-01/RAID-03 alerts, automatic lockdown activation, and verification pause during active raids**

## Performance

- **Duration:** 1 min
- **Started:** 2026-01-24T06:38:59Z
- **Completed:** 2026-01-24T06:40:52Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Join tracking integrated into on_member_join event (30-second sliding window)
- RAID-01 alert fires when 10+ members join in 30 seconds
- RAID-03 alert fires when >50% of recent joins are new accounts (<7 days old)
- Lockdown activates automatically on any raid condition
- New verifications pause during active lockdown (users get @Unverified but no UI)

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire raid detection into on_member_join event** - `2afa113` (feat)

## Files Created/Modified
- `src/guardian/guardian.py` - Added raid detection imports, join_tracker/lockdown_manager instances, raid threshold checks in on_member_join event, verification pause logic during lockdown

## Decisions Made

**RAID-03 independence:**
- RAID-03 analysis runs on every join regardless of join count
- Can fire when join_count < 10 if >50% are new accounts
- Provides coverage for slow-drip raids (not just rapid spikes)

**Verification pause timing:**
- Pause check happens AFTER role assignment (so @Unverified is applied)
- But BEFORE verification UI sent
- Result: Users are logged and visible in member list, but no verification button appears
- Preserves audit trail while preventing spam during raid

**Moderator bypass preserved:**
- Moderators bypass verification entirely (existing behavior)
- Their joins ARE tracked in join_tracker (for accurate raid metrics)
- But they don't trigger verification UI or lockdown pause logic

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for manual raid response (04-03):**
- Lockdown state accessible via `lockdown_manager.lockdown_state`
- Manual deactivation command can call `lockdown_manager.deactivate_lockdown()`
- Recovery timer cancellation already implemented

**Testing recommendations:**
1. Manual join simulation (10+ accounts in 30 seconds → RAID-01)
2. New account spike test (create accounts <7 days old → RAID-03)
3. Verify lockdown activates (slowmode enabled, alert sent)
4. Verify verification UI pauses (no buttons appear in #verify)
5. Verify auto-recovery after 15 minutes

**Event flow verified:**
```
on_member_join
  ↓
moderator bypass check
  ↓
add_join to tracker
  ↓
get recent_joins
  ↓
check RAID-01 (join_count >= 10)
  ↓
check RAID-03 (>50% new accounts)
  ↓
activate_lockdown if raid_detected
  ↓
assign @Unverified role
  ↓
log member join
  ↓
check lockdown state
  ↓
pause verification if active lockdown
  OR
send verification UI if no lockdown
```

---
*Phase: 04-raid-detection*
*Completed: 2026-01-24*
