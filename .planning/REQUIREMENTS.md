# Requirements: GSD Guardian

**Defined:** 2026-01-23
**Core Value:** New members must prove they're human before accessing the server, and scam links are blocked instantly.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: Guardian auto-creates #verify channel on first run
- [ ] **INFRA-02**: Guardian auto-creates #security-logs channel on first run
- [ ] **INFRA-03**: Guardian auto-creates @Unverified and @Verified roles on first run
- [ ] **INFRA-04**: Guardian runs as 24/7 worker process on Railway
- [ ] **INFRA-05**: Guardian provides slash commands for configuration (/guardian status, /guardian set-threshold, etc.)
- [ ] **INFRA-06**: Config changes apply without restart (hot-reload)

### Verification

- [ ] **VERIF-01**: New members assigned @Unverified role, can only see #verify
- [ ] **VERIF-02**: Verification uses emoji selection challenge ("click the pizza")
- [ ] **VERIF-03**: Unverified members auto-kicked after 10 minutes
- [ ] **VERIF-04**: Users with Moderator+ role bypass verification
- [ ] **VERIF-05**: /guardian verify @user manually passes a member

### Raid Detection

- [ ] **RAID-01**: Alert triggers when 10+ members join in 30 seconds
- [ ] **RAID-02**: Lockdown mode enables slow mode + pauses new verifications
- [ ] **RAID-03**: Alert if >50% of recent joins are accounts <7 days old
- [ ] **RAID-04**: Auto-recovery after 15 minutes of no suspicious activity

### Link Scanner

- [ ] **LINK-01**: Block messages containing known phishing domains (blocklist)
- [ ] **LINK-02**: Follow URL redirects to check final destination
- [ ] **LINK-03**: Delete scam link + 1hr timeout for poster
- [ ] **LINK-04**: Auto-ban on 2nd scam link offense

### Account Filter

- [ ] **ACCT-01**: Accounts <7 days old cannot post URLs
- [ ] **ACCT-02**: Accounts <7 days old cannot post attachments
- [ ] **ACCT-03**: Accounts <7 days old cannot @mention roles or @everyone
- [ ] **ACCT-04**: Specific roles can be exempted from restrictions

### Logging

- [ ] **LOG-01**: Log member joins/leaves with account age to #security-logs
- [ ] **LOG-02**: Log verification attempts (pass/fail/timeout)
- [ ] **LOG-03**: Log deleted scam links with message context
- [ ] **LOG-04**: Log all Guardian mod actions (kicks, bans, timeouts)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Enhanced Protection

- **SCORE-01**: Score-based anti-raid with graduated responses
- **SCORE-02**: Selective verification (auto-allow Discord accounts >30 days)
- **ALT-01**: Alt account detection using behavioral signals
- **DM-01**: DM spam detection and reporting

### Operational Tooling

- **OPS-01**: Raid simulation for testing thresholds
- **OPS-02**: Appeal channel for false positive recovery
- **OPS-03**: Dashboard for viewing security stats

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Admin account compromise detection | High false positive risk, behavioral anomaly detection immature |
| Real-time threat feed | Infrastructure complexity beyond single-bot scope |
| AI/ML smart detection | Opaque, unpredictable, hard to tune — use deterministic rules |
| External website verification | Privacy concerns, user friction, abandonment |
| Identity document storage | Privacy violation, liability risk |
| Administrator permission | Security risk if bot compromised — use minimal permissions |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| INFRA-04 | Phase 1 | Pending |
| INFRA-05 | Phase 3 | Pending |
| INFRA-06 | Phase 3 | Pending |
| VERIF-01 | Phase 2 | Pending |
| VERIF-02 | Phase 2 | Pending |
| VERIF-03 | Phase 2 | Pending |
| VERIF-04 | Phase 2 | Pending |
| VERIF-05 | Phase 3 | Pending |
| RAID-01 | Phase 4 | Complete |
| RAID-02 | Phase 4 | Complete |
| RAID-03 | Phase 4 | Complete |
| RAID-04 | Phase 4 | Complete |
| LINK-01 | Phase 5 | Pending |
| LINK-02 | Phase 5 | Pending |
| LINK-03 | Phase 5 | Pending |
| LINK-04 | Phase 5 | Pending |
| ACCT-01 | Phase 3 | Pending |
| ACCT-02 | Phase 3 | Pending |
| ACCT-03 | Phase 3 | Pending |
| ACCT-04 | Phase 3 | Pending |
| LOG-01 | Phase 2 | Pending |
| LOG-02 | Phase 2 | Pending |
| LOG-03 | Phase 5 | Pending |
| LOG-04 | Phase 4 | Complete |

**Coverage:**
- v1 requirements: 24 total
- Mapped to phases: 24
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-23*
*Last updated: 2026-01-23 after initial definition*
