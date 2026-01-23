# Project Research Summary

**Project:** GSD Guardian (Discord Security Bot)
**Domain:** Real-time Discord security/moderation for crypto communities
**Researched:** 2026-01-23
**Confidence:** HIGH

## Executive Summary

GSD Guardian is a real-time Discord security bot protecting the GSD crypto community from raids, scams, and automated attacks. Experts build this using discord.py 2.6.4+ with a Cog-based architecture, where each security feature is an isolated module listening to Gateway events. The bot runs 24/7 on Railway as a worker process, connecting to Discord's Gateway WebSocket for real-time event streams.

The recommended approach starts with foundational defenses (verification gate + logging), then layers on active threat mitigation (raid detection + link scanning). Use Cogs for modularity, pydantic-settings for type-safe configuration, and loguru for structured logging. Deploy as a separate worker process alongside the existing discord-mcp REST server, sharing Python 3.12 and httpx but maintaining independent concerns.

Key risks center on rate limiting during actual raids, verification bypasses via automated tools, and link scanner evasion using URL shorteners. Mitigation requires lockdown-mode raid response (not mass-banning), CAPTCHA-level verification (not simple emoji clicks), and URL unfurling to check redirect destinations. The architecture must handle false positives gracefully with appeal mechanisms, avoid memory leaks from interaction collectors, and protect bot tokens from leakage.

## Key Findings

### Recommended Stack

Discord.py 2.6.4+ is the industry-standard Python framework for Gateway bots, handling WebSocket connections, rate limiting, and all Discord API operations. The 2.x series includes critical features: slash commands, buttons/modals, voice rewrite, and poll support. For GSD Guardian, the core stack is minimal and focused: discord.py for Discord integration, pydantic-settings for type-safe configuration, loguru for structured JSON logging, and httpx for external API calls (URL scanning via VirusTotal).

**Core technologies:**
- **discord.py 2.6.4+**: Gateway WebSocket, Discord API client — dominant library with 15.9k stars, active development, comprehensive feature set
- **pydantic-settings 2.x**: Type-safe configuration with validation — prevents runtime config errors, simpler than Dynaconf for straightforward needs
- **loguru 0.7+**: Structured logging with zero boilerplate — async-safe, JSON serialization for Railway logs, automatic exception capture
- **httpx 0.28.1+**: Async HTTP client for external APIs — already in discord-mcp, needed for URL scanning services
- **virustotal-python 1.0+**: VirusTotal v3 API wrapper — 70+ antivirus engines for phishing detection
- **pytest + pytest-asyncio + dpytest**: Testing stack — essential for async handlers, Discord-specific mocking without real API calls

### Expected Features

Discord security bots in crypto communities face constant threats: phishing links (50,000+ detected in 6 months), raid attacks, and compromised accounts. Table stakes include verification gates (blocks 90%+ of automated raiders), basic raid detection, link scanning with maintained blocklists, new account restrictions, and comprehensive activity logging. Missing any of these makes the product feel incomplete or untrustworthy.

**Must have (table stakes):**
- **Verification gate** — emoji selection method, simplest effective barrier against bot accounts
- **Basic raid detection** — 10+ joins in 30s triggers lockdown + CAPTCHA requirement
- **Link scanning** — 22,000+ domain blocklist with heuristic analysis, high false positive risk
- **New account restrictions** — accounts <7 days can't post links/attachments
- **Activity logging** — joins, leaves, bans, verification outcomes for forensics
- **Admin/mod immunity** — role-based exemptions prevent catastrophic false positives
- **Discord AutoMod integration** — complement, not conflict with native features

**Should have (competitive):**
- **Score-based anti-raid** — graduated responses (monitor → timeout → kick → ban) vs binary block
- **Selective verification** — auto-allow Discord accounts >30 days old, reduce friction
- **Link safety score** — risk levels (HIGH/MEDIUM/LOW) for manual moderator review
- **Raid simulation/testing** — generate fake join spike to validate thresholds before real attacks

**Defer (v2+):**
- **Alt account detection** — too complex, privacy concerns, diminishing returns for 500-member community
- **Admin compromise detection** — behavioral anomaly detection has high false positive risk
- **Real-time threat feed** — requires infrastructure beyond single-bot scope
- **DM spam detection** — lower priority than public channel threats

### Architecture Approach

Guardian uses the Cog-based modularity pattern: each security feature is a `commands.Cog` subclass loaded as an extension, with isolated state and independent event handlers. Multiple cogs can listen to the same Gateway event (e.g., on_member_join fires for VerificationCog, RaidProtectionCog, and LoggingCog simultaneously). Configuration is centralized in a ConfigService accessible to all cogs via `self.bot.config.get()`, with file-watching for hot-reload without restart.

**Major components:**
1. **Bot Core** — setup_hook, intent configuration, cog lifecycle management
2. **VerificationCog** — member verification flow, emoji selection UI, role assignment, timeout tasks
3. **RaidProtectionCog** — join pattern analysis, lockdown trigger, graduated response system
4. **LinkScannerCog** — URL extraction, blocklist matching, redirect following, message deletion
5. **AccountFilterCog** — account age checks, content restrictions for new users
6. **LoggingCog** — centralized event logging to Discord channel, provides audit trail for forensics
7. **ConfigService** — shared configuration loader, file watcher, hot-reload on change

### Critical Pitfalls

1. **Rate limiting during active raids** — Bot's moderation actions get throttled by Discord API exactly when needed most. Prevention: implement lockdown mode (deny @everyone permissions) instead of mass-banning individuals. Queue moderation actions with priority (ban > timeout > kick), monitor rate limit headers, alert moderators when approaching limits.

2. **Verification system bypasses** — Automated tools pass simple emoji verification, making the gate worthless. Prevention: use CAPTCHA (image-based or puzzle) instead of buttons, or web-based OAuth2 flow which is "much harder for bots to bypass". Add additional checks: account age, avatar presence, username patterns. Monitor verification completion rate (>90% suggests too easy).

3. **Link scanner evasion** — Attackers use URL shorteners, multi-stage redirects, and Unicode homoglyphs to bypass regex-based scanning. Prevention: unfurl shorteners and check final destination, not just posted URL. Use maintained blocklists updated daily. Don't trust whitelist bypasses (even discord.gg can redirect to malicious servers via expired invite attack). Normalize Unicode before checking.

4. **False positives destroying trust** — Over-aggressive detection bans legitimate users during coordinated events (10 friends joining for game night). Prevention: dynamic thresholds during announced events, whitelist mechanism, appeal channel (#verify-help) required from day one, manual review for edge cases, grace period before ban.

5. **Missing Gateway intents** — Bot silently fails to detect events because privileged intents not enabled in both code AND Developer Portal. Prevention: enable GuildMembers (for raid detection) and MessageContent (for link scanning) intents in code, toggle privileged intents in Developer Portal, test with fresh accounts, log 4014 close codes.

## Implications for Roadmap

Based on research, suggested phase structure prioritizes foundational defenses before active threat mitigation, with dependency-based ordering to ensure each phase builds on proven components.

### Phase 1: Foundation + Core Security
**Rationale:** Bot infrastructure and logging must exist before any security features can function effectively. Admin immunity prevents catastrophic false positives during development. Verification gate addresses 90% of threats at entry.

**Delivers:** Working bot with Gateway connection, configuration system, comprehensive logging, admin role exemptions, emoji verification with timeout enforcement.

**Addresses:** Admin/mod immunity (table stakes), activity logging (table stakes), verification gate (table stakes), basic new account restrictions (table stakes).

**Avoids:** Missing Gateway intents (Pitfall 5 — must configure before features work), bot token leaks (Pitfall 9 — security foundation must be solid), no logging/audit trail (Pitfall 12).

**Research flags:** Standard patterns — Cog architecture, pydantic-settings, loguru all well-documented. Skip `/gsd:research-phase`.

### Phase 2: Active Threat Mitigation
**Rationale:** With foundation in place, add detection systems for active threats. Raid detection comes before link scanning because it's simpler (join rate threshold vs heuristic URL analysis) and more urgent (raids are immediate, phishing is persistent).

**Delivers:** Join rate monitoring with lockdown trigger, URL scanning with blocklist matching and redirect following, automated timeout/ban actions with rate limiting.

**Uses:** discord.py event listeners (on_member_join, on_message), httpx for URL expansion, virustotal-python for phishing checks, RateLimitedQueue for bulk actions.

**Implements:** RaidProtectionCog with lockdown mode, LinkScannerCog with URL unfurling, inter-cog communication via bot.get_cog().

**Addresses:** Raid detection (table stakes), link scanning (table stakes), Discord AutoMod integration (table stakes).

**Avoids:** Rate limiting during raids (Pitfall 1 — use lockdown mode), link scanner evasion (Pitfall 3 — unfurl URLs), sophisticated raid evasion (Pitfall 6).

**Research flags:** Needs research — `/gsd:research-phase` for URL scanning approaches (VirusTotal vs URLScan.io API differences, redirect handling libraries). Raid detection is straightforward.

### Phase 3: Enhanced Protection + Appeal System
**Rationale:** With active defenses working, refine to reduce false positives and add user appeal mechanisms. Score-based detection and selective verification improve UX without sacrificing security.

**Delivers:** Graduated response system (score-based anti-raid), automatic verification bypass for established accounts, appeal channel with manual review workflow, raid simulation testing tool.

**Addresses:** Score-based anti-raid (differentiator), selective verification (differentiator), missing appeal system (Pitfall 11).

**Avoids:** False positives destroying trust (Pitfall 4 — appeal system from day one), verification bypasses (Pitfall 2 — add account age checks).

**Research flags:** Standard patterns — Discord.py interaction collectors, role hierarchy checks. Skip `/gsd:research-phase`.

### Phase 4: MCP Integration + Operational Tooling
**Rationale:** With Guardian feature-complete, integrate control plane into discord-mcp for Claude Code access. Add operational tooling for monitoring and tuning.

**Delivers:** guardian.* tools in discord-mcp server (set_config, get_stats, trigger_lockdown), configuration hot-reload, memory monitoring, rate limit alerting.

**Uses:** FastMCP for tool definitions, watchfiles for config watching, Railway environment variables.

**Implements:** MCP tool handlers that read/write guardian_config.json, ConvexClient for future realtime config (migration path).

**Avoids:** Hardcoded configuration (Pitfall 15), memory leaks from collectors (Pitfall 8 — add monitoring).

**Research flags:** Standard patterns — FastMCP tool implementation follows discord-mcp patterns. Skip `/gsd:research-phase`.

### Phase Ordering Rationale

- **Foundation first:** Logging and config infrastructure must exist before any feature can log events or read settings. Building verification before raid detection provides immediate value (stops 90% of threats) and validates the Cog architecture before adding complexity.
- **Active threats before enhancements:** Raid detection and link scanning address critical table stakes features. Enhanced protection (score-based, selective verification) can wait because basic detection provides coverage.
- **Appeal system in Phase 3:** Must exist before full production use, but can wait until detection systems are proven. Building appeal workflow after false positives are observed (Phase 2 testing) yields better UX design.
- **MCP integration last:** Control plane is useful but not required for Guardian to function. Waiting until features are stable prevents churn in MCP tool schemas.

This ordering avoids Pitfall 13 (testing only in production) by validating each layer before building on it, and addresses the critical path identified in FEATURES.md: Admin immunity → Verification gate → Activity logging → Raid detection → Link scanning.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Link Scanning):** URL scanning approaches need API research. VirusTotal vs URLScan.io API differences, rate limit strategies, redirect handling libraries (httpx vs aiohttp follow patterns). Evasion techniques (homoglyphs, expired invite hijacking) need mitigation research.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Foundation):** Cog architecture extensively documented in discord.py official docs. Pydantic-settings and loguru have straightforward APIs. Gateway intent configuration is well-established pattern.
- **Phase 3 (Enhanced Protection):** Score-based systems are community-documented patterns. Interaction collectors have official discord.py examples. Appeal workflows are standard moderation patterns.
- **Phase 4 (MCP Integration):** FastMCP tool patterns already proven in discord-mcp codebase. Configuration watching via watchfiles is established pattern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | discord.py 2.6.4 verified via PyPI and official GitHub repo. Pydantic-settings is 2026 standard. Loguru widely adopted. All core dependencies have official documentation. |
| Features | MEDIUM | Table stakes verified with multiple current sources (2025-2026). Crypto/NFT threats well-documented. Complexity estimates from community bot examples. Anti-features identified from user reviews. |
| Architecture | HIGH | Cog-based modularity is official discord.py pattern. ConfigService approach verified in community examples. Inter-cog communication documented. Gateway intents requirements from official docs. |
| Pitfalls | MEDIUM | Rate limiting and intent issues verified via GitHub issues and official docs. Verification bypasses documented in security blogs. Link evasion techniques from security research. False positive patterns from community reports. |

**Overall confidence:** HIGH

Research covers all critical areas with multiple sources. Stack recommendations verified with official documentation. Feature landscape validated against 2025-2026 sources. Architecture patterns proven in production bots. Pitfall identification draws from both official docs (intents, rate limits) and community experience (false positives, evasion).

### Gaps to Address

**VirusTotal API specifics:** virustotal-python version number and rate limit behavior need PyPI verification during Phase 2 planning. Alternative: URLScan.io may have better rate limits for single-bot deployment.

**Convex integration timeline:** GUARDIAN-BRIEF.md mentions Convex for configuration, but research recommends JSON files for MVP. Need to validate Convex migration path and decide when to switch (Phase 4 vs post-launch).

**Sharding requirements:** Architecture research notes sharding needed beyond 10K members. GSD community is ~500 members, so this is deferred. If growth accelerates, need to research discord.py AutoShardedBot and distributed state (Redis or Convex).

**CAPTCHA vs emoji verification trade-off:** Research shows emoji selection is "user-friendly but slightly less secure than a full CAPTCHA". For Phase 1, emoji is acceptable. Phase 3 can upgrade to CAPTCHA if bot bypass rates exceed 10%.

**Testing infrastructure:** Pitfall 13 warns against testing only in production. Need to validate dpytest capabilities during Phase 1 to ensure raid simulations work before deployment.

## Sources

### Primary (HIGH confidence)
- [discord.py PyPI](https://pypi.org/project/discord.py/) — Version 2.6.4 verification, API features
- [discord.py GitHub](https://github.com/Rapptz/discord.py) — Active development status, contributor count
- [discord.py Official Docs](https://discordpy.readthedocs.io/en/stable/) — Cogs, Gateway intents, event reference
- [Pydantic Settings Docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — Type-safe configuration patterns
- [Discord Developer Portal](https://discord.com/developers/docs) — Privileged intents requirements, rate limiting

### Secondary (MEDIUM confidence)
- [Top Discord Security Bots 2025](https://nitronomics.com/blog/top-discord-security-bots-2025) — Feature landscape, table stakes identification
- [Discord Verification Bot Guide 2025](https://blog.communityone.io/best-discord-security-bot/) — Verification methods comparison
- [Discord Raid Protection Guide](https://support.discord.com/hc/en-us/articles/10989121220631) — Official Discord raid mitigation strategies
- [Discord-Phishing-URLs GitHub](https://github.com/nikolaischunk/discord-phishing-links) — 22,000+ malicious domain blocklist
- [Discord Security Best Practices 2025](https://friendify.net/blog/discord-bot-security-best-practices-2025.html) — Common pitfalls, anti-patterns
- [Pressure-Based Anti-Spam](https://erikmcclure.com/blog/pressure-based-anti-spam-for-discord-bots/) — Score-based raid detection algorithms
- [Discord Rate Limit Handling 2025](https://friendify.net/blog/discord-rate-limit-handling-patterns-2025.html) — Queue-based bulk action patterns

### Tertiary (LOW confidence, needs validation)
- virustotal-python version number (PyPI check needed during Phase 2)
- dpytest version 0.7+ (official docs verification during Phase 1)
- CAPTCHA bypass rates (no authoritative data, monitoring needed)

---
*Research completed: 2026-01-23*
*Ready for roadmap: yes*
