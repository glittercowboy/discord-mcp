# Feature Landscape: Discord Security Bots

**Domain:** Discord security/protection bots for crypto/NFT communities
**Researched:** 2025-01-23
**Confidence:** MEDIUM (verified with multiple current sources, crypto-specific threats well-documented)

## Table Stakes

Features users expect from any Discord security bot. Missing these means the product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Verification gate** | Blocks 90%+ of automated raiders and bot accounts at entry | Medium | Multiple methods available (button, CAPTCHA, emoji pick, math). Emoji selection is simplest with decent effectiveness. |
| **Basic raid detection** | Communities expect protection from sudden influx attacks | Medium | Join rate monitoring (e.g., 10+ joins in 30s) is standard. Must trigger automated response (lockdown, CAPTCHA requirement). |
| **Link scanning** | Crypto/NFT communities face constant phishing attacks (50,000+ malicious links detected in 6 months on Discord) | High | Requires maintained blocklist (22,000+ known domains) + heuristic analysis. False positives are major UX risk. |
| **New account restrictions** | Prevents throwaway accounts from immediate malicious activity | Low | Standard: accounts <7 days old restricted from posting links/attachments. Simple age check. |
| **Activity logging** | Required for post-incident forensics and moderator accountability | Medium | Must log joins, leaves, bans, kicks, verification attempts, link blocks. Retention strategy needed. |
| **Admin/mod immunity** | Security bot must not block legitimate admin actions | Low | Critical: false positives on admins destroy trust. Role-based exemptions are table stakes. |
| **Discord AutoMod integration** | Users expect bots to complement, not conflict with, native Discord features | Medium | Must work alongside Discord's built-in AutoMod and raid protection without duplicate actions. |

## Differentiators

Features that set a security bot apart. Not expected, but highly valued when present.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Alt account detection** | Crypto/NFT communities face sophisticated attackers using multiple accounts | High | Advanced implementations use 20+ data points (IP, device fingerprint, cookies). Privacy concerns must be addressed. Resource-intensive. |
| **Score-based anti-raid** | More nuanced than binary block/allow - reduces false positives | High | Security Bot's approach: assign risk scores that reset at intervals. Allows graduated responses (monitor → timeout → kick → ban). |
| **Selective verification** | Better UX: only verify suspicious accounts, auto-allow established users | Medium | Wick's model: verify very new accounts, auto-allow long-standing Discord users. Balances security with friction. |
| **Admin account compromise detection** | Major threat: Bored Ape Yacht Club lost $360K when admin account was hacked | High | Behavioral anomaly detection (unusual permission changes, mass pings, non-standard announcement patterns). High false positive risk. |
| **DM spam detection** | Users report DM spam to mods; bot should track patterns | Medium | Requires user reporting mechanism + pattern analysis across reports. Privacy-sensitive feature. |
| **Link "safety score" (not just block/allow)** | Provides context for moderators on borderline links | High | Instead of binary block, show risk level. Allows manual review of MEDIUM-risk links. Reduces false positives. |
| **Raid simulation/testing** | Allows admins to test protection without real attack | Medium | Underutilized feature that builds confidence. Generate fake join spike to validate thresholds. |
| **Multi-layered protection** | Stacked approach: verification + raid detection + link scanning work together | Medium | Sources recommend "layered protection" - no single defense is sufficient for crypto communities. |
| **Real-time threat feed** | Share blocked domains across installations | High | If Bot A blocks new phishing domain, Bot B instances learn immediately. Requires central infrastructure. |

## Anti-Features

Features to explicitly NOT build. Common mistakes in this domain that harm more than help.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Asking for Administrator permission** | Almost never needed; creates massive security risk if bot is compromised | Request only specific permissions needed (Manage Roles, Ban Members, etc.). Principle of least privilege. |
| **Overly aggressive auto-banning** | User reviews consistently complain: "bans moderators and bots" | Use graduated responses: monitor → warn → timeout → kick → ban. Start conservative, let admins tune. |
| **Blocking all shortened URLs** | High false positive rate; breaks legitimate use cases | Expand shortened URLs, then scan destination. Allow admins to whitelist trusted shorteners. |
| **Verification on every login** | UX nightmare; users abandon servers | Verify once at join, not on every session. Persist verified status. |
| **Exposing security settings to all members** | Attackers study defenses to bypass | Security dashboard should be admin-only. Don't announce raid thresholds publicly. |
| **Zero-tolerance for new accounts** | Legitimate new Discord users exist | Allow new accounts with restrictions (read-only until verified, no links/attachments), not outright bans. |
| **Requiring external website verification** | Privacy concerns, friction, abandonment | Keep verification in-Discord (button, emoji, CAPTCHA). Avoid redirecting users off-platform. |
| **Complex AI/ML "smart detection" as primary defense** | Opaque, unpredictable, hard to tune, high false positive risk | Use deterministic rules as primary layer (join rate, account age, blocklist). ML as supplementary signal only. |
| **Storing identity documents** | Privacy violation, liability risk | If age verification needed (not for security bot), use third-party service (e.g., k-ID) that deletes documents post-verification. |
| **Relying solely on Discord's native Audit Log** | Discord's audit log doesn't capture all events (message edits, joins/leaves in detail) | Implement extended logging that captures security-relevant events Discord omits. |

## Feature Dependencies

```
Verification Gate
  ↓
New Account Restrictions (requires account age detection from verification)
  ↓
Activity Logging (logs verification outcomes, restriction triggers)

Link Scanning
  ↓
Activity Logging (logs blocked links for analysis)
  ↓ (optional)
Real-time Threat Feed (shares newly discovered phishing domains)

Raid Detection
  ↓
Verification Gate (raid triggers CAPTCHA requirement)
  ↓
Activity Logging (logs raid events for forensics)

Admin/Mod Immunity
  ← Required by ALL features (prevents false positives on legitimate actions)
```

**Critical Path:** Admin/Mod Immunity → Verification Gate → Activity Logging → Raid Detection → Link Scanning

**Why this order:**
- **Admin immunity first**: Prevents catastrophic false positives during development
- **Verification gate early**: Stops 90% of threats at the door
- **Logging before detection**: Need audit trail as detection features roll out
- **Raid before links**: Raids are simpler to detect (join rate) than phishing (heuristics)

## MVP Recommendation

For GSD Guardian MVP protecting ~500 member crypto community, prioritize:

### Phase 1: Essential Protection (Must-Have)
1. **Verification gate** (emoji selection) - Simplest effective method
2. **Admin/mod immunity** - Role-based exemptions
3. **Activity logging** - Join, leave, verification outcomes, moderation actions
4. **New account restrictions** - <7 days: no links, no attachments

### Phase 2: Active Threat Mitigation (Should-Have)
5. **Raid detection** - 10 joins/30 seconds threshold triggers lockdown + CAPTCHA
6. **Link scanning** - Blocklist (22K+ domains) + basic heuristics (no ML)

### Phase 3: Enhanced Protection (Nice-to-Have)
7. **Score-based anti-raid** - Graduated responses instead of binary block
8. **Selective verification** - Auto-allow Discord accounts >30 days old

### Explicitly Defer to Post-MVP
- **Alt account detection** - Too complex, privacy concerns, diminishing returns for 500-member community
- **Admin compromise detection** - Behavioral anomaly detection is high false-positive risk
- **Real-time threat feed** - Requires infrastructure beyond single-bot scope
- **DM spam detection** - Lower priority than public channel threats

## Complexity Analysis

**Low Complexity (days):**
- New account restrictions (account creation date check)
- Admin/mod immunity (role permission check)
- Basic activity logging (event handlers → database)

**Medium Complexity (week):**
- Verification gate (UI flow, state management, timeout handling)
- Raid detection (sliding window join rate calculation, lockdown logic)
- Selective verification (account age heuristic, exemption rules)

**High Complexity (weeks):**
- Link scanning (blocklist maintenance, URL expansion, heuristic analysis, false positive management)
- Score-based anti-raid (scoring algorithm, decay logic, threshold tuning)
- Alt account detection (fingerprinting, multi-factor correlation, privacy controls)

## Threat-Specific Features

Based on crypto/NFT community threat landscape:

### Top Threats (High Priority)
1. **Fake minting announcements** → Link scanning with crypto-specific heuristics
2. **Admin account hijacking** → Activity logging (unusual permission changes) + manual review
3. **Social engineering raids** → Verification gate + new account restrictions
4. **Phishing DMs from compromised accounts** → New account restrictions + link scanning

### Lower Priority for 500-Member Community
1. **Sophisticated multi-account raids** → Alt account detection (defer)
2. **Zero-day phishing domains** → Real-time threat feed (defer)
3. **Insider threats** → Audit trail exists via activity logging (sufficient)

## Feature Validation Criteria

How to know if a feature is working:

| Feature | Success Metric | Acceptable False Positive Rate |
|---------|----------------|-------------------------------|
| Verification gate | 95%+ completion rate | <5% legitimate users fail |
| Raid detection | Detect within 30s, lockdown within 60s | <1 false alarm per month |
| Link scanning | Block known phishing, 0 successful attacks | <3% legitimate links blocked |
| New account restrictions | 0 spam from <7 day accounts | 0% (this is restriction, not block) |
| Activity logging | 100% event capture | N/A (passive feature) |

## Sources

**General Discord Security (2025):**
- [Top 7 Discord Bots for Server Security in 2025](https://nitronomics.com/blog/top-discord-security-bots-2025)
- [Discord Verification Bot Guide: Secure Your Server 2025](https://blog.communityone.io/best-discord-security-bot/)
- [How to Protect Your Server from Raids 101 – Discord](https://support.discord.com/hc/en-us/articles/10989121220631-How-to-Protect-Your-Server-from-Raids-101)
- [Security Bot](https://securitybot.gg/)
- [RaidProtect](https://raidprotect.bot/en)

**Crypto/NFT Specific Threats:**
- [Discord malware campaign targets crypto and NFT communities](https://www.bleepingcomputer.com/news/security/discord-malware-campaign-targets-crypto-and-nft-communities/)
- [The Rising Threat of NFT Scams on Discord](https://immunebytes.com/blog/the-rising-threat-of-nft-scams-on-discord/)
- [Discord Malware Hijacks Expired Invite Links to Steal Crypto Wallets in 2025](https://www.secureblink.com/cyber-security-news/discord-malware-hijacks-expired-invite-links-to-steal-crypto-wallets-in-2025)

**Link Scanning & Phishing:**
- [Discord Phishing Risk Increases with 50,000+ Malicious Links Detected in 6 Months](https://www.spamtitan.com/blog/discord-phishing-risk-increases-with-50000-malicious-links-detected-in-6-months/)
- [discord-phishing-links GitHub (22,000+ malicious domains)](https://github.com/nikolaischunk/discord-phishing-links)
- [Discord Invite Link Hijacking Delivers AsyncRAT and Skuld Stealer](https://thehackernews.com/2025/06/discord-invite-link-hijacking-delivers.html)

**Activity Logging:**
- [Discord Audit Logs with MEE6](https://help.mee6.xyz/support/solutions/articles/101000475709-how-to-use-audit-logs-to-track-your-members-actions)
- [Audit Logger Discord Bot](https://top.gg/bot/1026735525501087815)

**Best Practices & Anti-Patterns:**
- [Security Guide for Discord Bots using discord.py](https://gist.github.com/apple502j/d1330461e7e8ad6532cb62a670d06a5a)
- [Discord Bot Security Best Practices 2025](https://friendify.net/blog/discord-bot-security-best-practices-2025.html)
- [The 10 Most Common Discord Security Risks](https://www.keywordsstudios.com/en/about-us/news-events/news/the-10-most-common-discord-security-risks-and-how-to-avoid-them/)
