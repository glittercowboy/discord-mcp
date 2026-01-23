# Roadmap: GSD Guardian

## Overview

GSD Guardian protects the GSD Discord community through layered security: verification gates stop automated raiders at entry, account filters restrict new users from posting malicious content, raid detection triggers lockdown during coordinated attacks, and link scanning blocks phishing attempts. The roadmap progresses from foundational infrastructure through defensive capabilities, ending with active threat mitigation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation** - Bot infrastructure and auto-provisioning
- [ ] **Phase 2: Verification Gate** - Human verification with emoji challenge
- [ ] **Phase 3: Account Restrictions** - New account filtering and control plane
- [ ] **Phase 4: Raid Detection** - Join rate monitoring with lockdown
- [ ] **Phase 5: Link Scanning** - Phishing link detection and blocking

## Phase Details

### Phase 1: Foundation
**Goal**: Bot runs 24/7 on Railway with required channels, roles, and logging infrastructure
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. Bot connects to Discord Gateway and maintains 24/7 uptime on Railway
  2. #verify channel exists with correct permissions (Unverified can view, Verified cannot)
  3. #security-logs channel exists and receives test events
  4. @Unverified and @Verified roles exist with correct permission hierarchy
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — Gateway bot with idempotent infrastructure
- [ ] 01-02-PLAN.md — Railway deployment and verification

### Phase 2: Verification Gate
**Goal**: New members must complete emoji challenge to access server
**Depends on**: Phase 1
**Requirements**: VERIF-01, VERIF-02, VERIF-03, VERIF-04, LOG-01, LOG-02
**Success Criteria** (what must be TRUE):
  1. New member joins and receives @Unverified role, can only see #verify channel
  2. Member clicks correct emoji button and gains @Verified role, loses @Unverified
  3. Member who doesn't verify within 10 minutes is auto-kicked
  4. Moderator+ role members bypass verification entirely (never assigned @Unverified)
  5. All member joins, leaves, verification attempts log to #security-logs with timestamps
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 3: Account Restrictions
**Goal**: New accounts restricted from posting malicious content, admins control bot via slash commands
**Depends on**: Phase 2
**Requirements**: ACCT-01, ACCT-02, ACCT-03, ACCT-04, INFRA-05, INFRA-06, VERIF-05
**Success Criteria** (what must be TRUE):
  1. Discord account <7 days old cannot post URLs, attachments, or @mention roles
  2. Moderator runs /guardian status and sees current config (thresholds, enabled features)
  3. Moderator runs /guardian set-threshold and changes raid detection value without restart
  4. Moderator runs /guardian verify @user and manually passes a stuck member
  5. Role added to exemption list bypasses new account restrictions
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 4: Raid Detection
**Goal**: Bot detects coordinated join attacks and triggers lockdown to prevent spam
**Depends on**: Phase 3
**Requirements**: RAID-01, RAID-02, RAID-03, RAID-04, LOG-04
**Success Criteria** (what must be TRUE):
  1. 10+ members join within 30 seconds, alert posts to #security-logs
  2. Lockdown mode activates (slow mode enabled, new verifications paused), alert sent
  3. >50% of recent joins are accounts <7 days old, additional alert fires
  4. 15 minutes pass with no suspicious activity, lockdown auto-deactivates
  5. All Guardian mod actions (kicks, bans, timeouts) log to #security-logs
**Plans**: TBD

Plans:
- [ ] TBD during planning

### Phase 5: Link Scanning
**Goal**: Messages with known phishing links are deleted and poster punished
**Depends on**: Phase 4
**Requirements**: LINK-01, LINK-02, LINK-03, LINK-04, LOG-03
**Success Criteria** (what must be TRUE):
  1. Message containing blocklisted domain is deleted within seconds
  2. URL shortener expands to final destination, final destination checked against blocklist
  3. First offense: message deleted, poster receives 1hr timeout, action logged
  4. Second offense: poster auto-banned, ban logged with evidence
  5. All deleted scam links logged to #security-logs with message context and poster info
**Plans**: TBD

Plans:
- [ ] TBD during planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/2 | Planning complete | - |
| 2. Verification Gate | 0/0 | Not started | - |
| 3. Account Restrictions | 0/0 | Not started | - |
| 4. Raid Detection | 0/0 | Not started | - |
| 5. Link Scanning | 0/0 | Not started | - |
