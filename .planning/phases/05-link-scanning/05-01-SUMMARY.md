---
phase: 05-link-scanning
plan: 01
subsystem: security
tags: [phishing-detection, url-resolution, httpx, tldextract, blocklist, offense-tracking]

# Dependency graph
requires:
  - phase: 03-account-restrictions
    provides: Atomic write pattern (config_manager.py) and pre-compiled regex pattern
provides:
  - URL redirect resolution with httpx async client
  - Domain extraction with tldextract for accurate TLD handling
  - Blocklist matcher with O(1) lookup and subdomain support
  - Offense tracking with JSON persistence and atomic writes
  - Discord-AntiScam blocklist with 24,000+ phishing domains
affects: [05-link-scanning-integration, security-automation, anti-spam]

# Tech tracking
tech-stack:
  added: [tldextract>=5.1.2, Discord-AntiScam/scam-links blocklist]
  patterns:
    - "Async HTTP redirect following with timeout guards"
    - "Domain extraction with Mozilla Public Suffix List"
    - "Subdomain matching for blocklist bypass prevention"
    - "Atomic JSON writes for offense tracking (Phase 3 pattern)"

key-files:
  created:
    - src/guardian/link_resolver.py
    - src/guardian/blocklist_matcher.py
    - src/guardian/offense_tracking.py
    - src/guardian/data/blocklist.json
  modified:
    - pyproject.toml

key-decisions:
  - "Use httpx over requests for async-native redirect following"
  - "Use tldextract for accurate TLD parsing (handles co.uk, github.io)"
  - "Implement subdomain matching in blocklist (cdn.phishing.com matches phishing.com)"
  - "Keep last 10 offenses per user to prevent unbounded JSON growth"
  - "Return original URL on timeout (treat as safe, prevent DoS from slow servers)"

patterns-established:
  - "Pattern 1: Async redirect following with HEAD fallback to GET"
  - "Pattern 2: 5-second timeout prevents hanging on malicious servers"
  - "Pattern 3: Parent domain iteration for subdomain blocking"
  - "Pattern 4: Atomic write pattern (temp + rename) for concurrent safety"

# Metrics
duration: 3min
completed: 2026-01-24
---

# Phase 5 Plan 1: Link Scanning Infrastructure Summary

**Async URL resolver with redirect following, blocklist matcher with 24,000+ phishing domains, and per-user offense tracker with JSON persistence**

## Performance

- **Duration:** 3 min
- **Started:** 2026-01-24T14:40:33Z
- **Completed:** 2026-01-24T14:43:42Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- URL resolution infrastructure resolves shortened URLs to final destination with 5-second timeout
- Blocklist matcher supports exact and subdomain matching with O(1) lookup performance
- Offense tracker persists per-user violation counts across restarts with atomic writes
- Downloaded Discord-AntiScam community blocklist with 36,751 lines (24,000+ domains)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add tldextract dependency and download blocklist** - `093d730` (chore)
2. **Task 2: Create link_resolver.py with async redirect following** - `2c085d0` (feat)
3. **Task 3: Create blocklist_matcher.py and offense_tracking.py** - `780e6dc` (feat)

## Files Created/Modified
- `pyproject.toml` - Added tldextract>=5.1.2 dependency
- `src/guardian/data/blocklist.json` - Discord-AntiScam phishing domain blocklist (36,751 lines)
- `src/guardian/link_resolver.py` - Async URL redirect following and domain extraction (121 lines)
- `src/guardian/blocklist_matcher.py` - Blocklist loading and matching with subdomain support (111 lines)
- `src/guardian/offense_tracking.py` - Per-user offense tracking with JSON persistence (135 lines)

## Decisions Made

**1. httpx over requests for redirect following**
- httpx is async-native (no thread pool needed), already in project dependencies
- requests is sync-only, would require thread pool or subprocess for async

**2. tldextract for domain extraction**
- Handles complex TLDs (bbc.co.uk, github.io) using Mozilla Public Suffix List
- Simple urlparse or regex fails on multi-level TLDs

**3. Subdomain matching in blocklist**
- Check parent domains to prevent bypass (cdn.phishing.com matches if phishing.com is blocklisted)
- Iterate domain parts and check each parent domain against set

**4. Keep last 10 offenses per user**
- Prevents unbounded JSON growth while maintaining evidence for review
- 10 offenses sufficient for audit trail without excessive storage

**5. Return original URL on timeout**
- Treat timeout as "safe" (don't block) to prevent DoS from slow servers
- 5-second timeout prevents hanging on malicious servers
- Log warning for manual review

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Python environment mismatch (system Python 3.11 vs venv Python 3.12)**
- **Problem:** Import verification failed because system Python didn't have tldextract
- **Solution:** Used `source .venv/bin/activate` for verification commands
- **Resolution:** No code changes needed, verification pattern adjusted

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

**Ready for link scanning integration:**
- link_resolver.py exports resolve_url_destination and extract_domain_from_url
- blocklist_matcher.py exports BlocklistMatcher with subdomain checking
- offense_tracking.py exports OffenseTracker with atomic writes
- All modules importable without errors
- Blocklist loaded with 24,000+ phishing domains

**Next steps:**
- Integrate link scanning into on_message event (05-02)
- Wire up offense tracking to timeout/ban logic
- Add URL extraction with pre-compiled regex
- Implement message deletion and DM notification

---
*Phase: 05-link-scanning*
*Completed: 2026-01-24*
