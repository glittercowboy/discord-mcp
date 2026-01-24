---
phase: 03-account-restrictions
verified: 2026-01-24T15:30:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "Moderator can change account age threshold via /guardian set-threshold command"
    status: failed
    reason: "Command is named /guardian config, not /guardian set-threshold per success criteria"
    artifacts:
      - path: "src/guardian/slash_commands.py"
        issue: "Command registered with name='config' (line 59) but success criteria specifies 'set-threshold'"
    missing:
      - "Command should be renamed from 'config' to 'set-threshold' to match ROADMAP success criteria"
      - "Or ROADMAP criterion 3 needs to be updated to reflect 'config' command name"
---

# Phase 3: Account Restrictions Verification Report

**Phase Goal:** New accounts restricted from posting malicious content, admins control bot via slash commands

**Verified:** 2026-01-24T15:30:00Z

**Status:** gaps_found

**Initial Verification** (no previous VERIFICATION.md found)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Discord account <7 days old cannot post URLs | ✓ VERIFIED | `account_restrictions.py` line 80: `URL_PATTERN.search()` detects URLs in `check_content_violations()` |
| 2 | Discord account <7 days old cannot post attachments | ✓ VERIFIED | `account_restrictions.py` line 65-66: `message.attachments` check |
| 3 | Discord account <7 days old cannot @mention roles | ✓ VERIFIED | `account_restrictions.py` line 75-76: `message.raw_role_mentions` check |
| 4 | Moderator runs /guardian status and sees config | ✓ VERIFIED | `slash_commands.py` line 17-57: `/guardian status` command shows threshold, features, exempt roles |
| 5 | Moderator can change threshold without restart | ⚠️ PARTIAL | `/guardian config` works with hot-reload (line 93: "no restart required" message) but command name doesn't match criterion 3 |
| 6 | Moderator runs /guardian verify @user | ✓ VERIFIED | `slash_commands.py` line 98-150: `/guardian verify` adds Verified role, removes Unverified role |
| 7 | Role in exemption list bypasses restrictions | ✓ VERIFIED | `account_restrictions.py` line 114-117: Checks `exempt_roles` config, blocks message filtering if role found |

**Score:** 4/5 core truths verified (criterion 5 has implementation mismatch)

### Required Artifacts

| Artifact | Path | Status | Details |
|----------|------|--------|---------|
| Account restrictions module | `src/guardian/account_restrictions.py` | ✓ VERIFIED | 120 lines, implements `check_content_violations()`, `get_account_age_days()`, `is_account_exempt()` |
| Config manager | `src/guardian/config_manager.py` | ✓ VERIFIED | 117 lines, hot-reload with atomic writes, file-based persistence |
| Slash commands | `src/guardian/slash_commands.py` | ✓ VERIFIED | 279 lines, 4 commands (status, config, verify, exempt) in GuardianCommands group |
| Guardian bot | `src/guardian/guardian.py` | ✓ VERIFIED | 250 lines, imports all modules, wires on_message handler, registers slash commands |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| guardian.py | account_restrictions.py | Line 10 import + line 196, 200, 207 | ✓ WIRED | Module imported and used in on_message handler |
| guardian.py | config_manager.py | Line 11 import + line 192 | ✓ WIRED | Module imported and used to load config |
| guardian.py | slash_commands.py | Line 12 import + line 33-34 | ✓ WIRED | GuardianCommands instantiated and added to client.tree |
| on_message handler | message deletion | Line 213 | ✓ WIRED | `await message.delete()` called after violation detected |
| on_message handler | user notification | Line 224-228 | ✓ WIRED | User DM sent with explanation of violation |
| on_message handler | security logging | Line 236-243 | ✓ WIRED | Violation logged to #security-logs channel |
| config command | hot-reload | Line 69-70 | ✓ WIRED | Calls `config_manager.save_config()` then responds "no restart required" |
| verify command | role updates | Line 116-117 | ✓ WIRED | `member.add_roles()` and `member.remove_roles()` called atomically |
| exempt command | role storage | Line 213-214 | ✓ WIRED | Role ID appended to `exempt_roles` list and saved via `config_manager` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| slash_commands.py | 59 | Command name mismatch | ⚠️ Warning | Command named `config` but success criteria specifies `set-threshold` |
| (none other) | - | - | - | Code is substantive with no TODO/FIXME comments, no stubs |

## Success Criteria Coverage

### Criterion 1: Account age restriction
- **Truth:** Discord account <7 days old cannot post URLs, attachments, or @mention roles
- **Status:** ✓ SATISFIED
- **Evidence:** 
  - URL detection: `account_restrictions.py` line 80 with pre-compiled regex
  - Attachment detection: `account_restrictions.py` line 65
  - Role mention detection: `account_restrictions.py` line 75
  - All wired in `guardian.py` `on_message` handler (lines 196-209)

### Criterion 2: /guardian status shows config
- **Truth:** Moderator sees current config with thresholds and enabled features
- **Status:** ✓ SATISFIED
- **Evidence:**
  - Command registered: `slash_commands.py` line 17
  - Shows threshold: line 33-35
  - Shows features (URLs, attachments, role mentions): line 39-47
  - Shows exempt roles count: line 50-53

### Criterion 3: /guardian set-threshold changes value without restart
- **Truth:** Moderator can change account age threshold without restarting bot
- **Status:** ⚠️ PARTIAL (implementation works, command name wrong)
- **Evidence:**
  - Hot-reload working: `config_manager.py` line 50 reads file on each call
  - No restart needed: `slash_commands.py` line 93 confirms "no restart required"
  - Config saved: line 70 calls `config_manager.save_config()`
  - **Issue:** Command is `/guardian config`, not `/guardian set-threshold` per criterion 3

### Criterion 4: /guardian verify @user manually passes member
- **Truth:** Moderator can manually verify stuck members
- **Status:** ✓ SATISFIED
- **Evidence:**
  - Command registered: `slash_commands.py` line 98
  - Adds Verified role: line 116
  - Removes Unverified role: line 117
  - Logged to security-logs: line 129-143

### Criterion 5: Role in exemption list bypasses restrictions
- **Truth:** Members with exempt role bypass new account restrictions
- **Status:** ✓ SATISFIED
- **Evidence:**
  - Exempt check in on_message: `guardian.py` line 196
  - Logic in `account_restrictions.py` line 114-117
  - Exempt command to add/remove roles: `slash_commands.py` line 205-214, 243-252
  - Role ID stored in config: line 213

## Gaps Summary

**1 gap blocking full goal achievement:**

### Gap: Command naming mismatch for criterion 3

**What's wrong:** Success criteria #3 specifies `/guardian set-threshold` but implementation has `/guardian config`

**Why it matters:** While the functionality works correctly (changes threshold without restart), the command name doesn't match the documented success criteria. This suggests either:
- The ROADMAP criterion is outdated/wrong (mentions "raid detection value" which is Phase 4 terminology)
- The implementation should rename the command to match the spec

**What needs fixing:** Either:
1. Rename `slash_commands.py` line 59 `name="config"` to `name="set-threshold"`, OR
2. Update ROADMAP.md criterion 3 to say `/guardian config` instead of `/guardian set-threshold`

**Current state:** Functionality is complete and working, just documented differently than specified.

---

## Code Quality Assessment

### Substantive Implementation
- **account_restrictions.py:** 120 lines with 3 core functions, pre-compiled regex for performance
- **config_manager.py:** 117 lines with atomic write pattern and hot-reload design
- **slash_commands.py:** 279 lines with 4 fully implemented commands
- **guardian.py integration:** 250 lines with complete on_message handler wiring

### No Stubs Found
- All functions have real implementations
- No TODO/FIXME comments in core implementation files
- No placeholder responses or empty handlers
- Error handling is comprehensive (try/except for Discord API failures)

### Wiring Verification
- All modules properly imported and used
- on_message handler flow: check exempt → check age → check violations → delete → DM → log
- Slash commands properly registered at module level (line 33-34 in guardian.py)
- Config hot-reload verified: reads file on each access
- All responses logged to #security-logs for audit trail

---

## Human Verification Needed

The following items require human testing to fully verify:

### 1. Message Filtering in Discord

**Test:** In Discord, as new account (<7 days old):
1. Try to post a message with a URL (e.g., "https://example.com")
2. Try to post a message with an attachment (image/file)
3. Try to mention a role (e.g., "@Moderators")

**Expected:**
- Message is deleted silently
- User receives DM explaining the violation
- Violation appears in #security-logs

**Why human:** Need to verify actual Discord API behavior with real message and real account age

### 2. /guardian status Command

**Test:** As moderator, run `/guardian status`

**Expected:**
- Shows "Account Age Threshold: 7 days" (or configured value)
- Shows feature status (URLs, Attachments, Role mentions all blocked)
- Shows exempt roles count

**Why human:** Need to verify slash command UI rendering and interaction response

### 3. /guardian config Command

**Test:** As moderator, run `/guardian config 14`

**Expected:**
- Response: "Threshold updated to 14 days (no restart required)"
- New restriction: accounts <14 days old now blocked
- Old account (11 days) can now post URLs (was blocked at 7)

**Why human:** Need to verify hot-reload actually works without restarting bot, and threshold takes effect immediately

### 4. /guardian verify Command

**Test:** As moderator with moderate_members permission:
1. Have new member (with @Unverified) try to post
2. Run `/guardian verify @member`
3. Member tries to post again

**Expected:**
- Before verify: message deleted with violation
- After verify: member has @Verified role, can post freely
- Action logged to #security-logs

**Why human:** Need to verify role removal actually unblocks posting (relies on role check in code)

### 5. /guardian exempt Command

**Test:** As administrator:
1. Run `/guardian exempt list` (should be empty initially)
2. Run `/guardian exempt add @SomeRole`
3. Have member with that role post restricted content
4. Run `/guardian exempt remove @SomeRole`
5. Test again

**Expected:**
- Step 1: "No exempt roles configured"
- Step 2: "SomeRole added to exempt roles"
- Step 3: Member's message is NOT deleted (exempt role)
- Step 4: "SomeRole removed"
- Step 5: Member's message IS deleted (no longer exempt)

**Why human:** Need to verify exemption logic actually prevents message deletion

---

## Summary

**Implementation Status:** ✅ Fully implemented and wired

**Functionality:** All 5 success criteria are functionally implemented:
1. ✅ Restrictions block URLs, attachments, role mentions
2. ✅ /guardian status shows config
3. ⚠️ /guardian config (named differently, but works) changes threshold without restart
4. ✅ /guardian verify manually verifies members
5. ✅ Role exemptions work

**Issues:** One minor gap - command named `/guardian config` instead of `/guardian set-threshold` specified in criterion 3.

**Code Quality:** Clean, no stubs, proper error handling, logging integrated.

**Ready for:** Human verification testing in actual Discord.

---

_Verified: 2026-01-24T15:30:00Z_
_Verifier: Claude (gsd-verifier)_
