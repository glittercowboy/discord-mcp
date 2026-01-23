# Domain Pitfalls: Discord Security Bots

**Domain:** Discord security/moderation bots for crypto communities
**Researched:** 2025-01-23
**Confidence:** MEDIUM (WebSearch verified with technical documentation and community reports)

## Executive Summary

Discord security bots face unique challenges in high-threat environments like crypto communities. The three most critical failure modes are: (1) raid detection systems that fall behind during actual raids due to rate limiting, (2) verification systems with trivial bypasses that give false security, and (3) link scanning that fails against evasion techniques like URL shorteners and redirect chains.

This research focuses on pitfalls specific to your deployment: emoji verification with timeouts, raid detection via join rate monitoring, and link scanning with automatic moderation actions.

## Critical Pitfalls

### Pitfall 1: Rate Limiting During Active Raids

**What goes wrong:** When a raid actually happens, your bot's moderation actions get rate-limited by Discord's API, causing it to fall behind and become ineffective exactly when you need it most.

**Why it happens:** Discord enforces strict rate limits on moderation actions. During a raid (10+ joins in 30 seconds), your bot attempts to ban/timeout multiple users rapidly. The API throttles these requests, and your action queue grows faster than you can process it. Some bots hit the 2,000 nonmember ban limit and cannot ban further.

**Consequences:**
- Bot becomes useless during actual raids
- Attackers flood the server while bot is rate-limited
- Other integrations stop working due to shared rate limits
- No feedback to moderators about what's happening

**Prevention:**
- Implement exponential backoff with Discord's rate limit headers
- Queue moderation actions with priority (ban > timeout > kick)
- Switch to "lockdown mode" during raids (deny @everyone permissions) instead of trying to ban individuals
- Monitor rate limit status and alert moderators when approaching limits
- Consider using server-level verification features instead of bot actions during raids

**Detection (warning signs):**
- Bot responds slowly during test raids
- Audit log shows gaps between join time and ban time
- Rate limit errors in logs during peak activity
- Actions succeed for first 5-10 users, then fail

**Phase impact:** Phase 1 (raid detection). Design the system to survive mega-raids, not just detect them.

**Sources:**
- [Discord API Rate Limiting Issues](https://github.com/discord/discord-api-docs/issues/5002)
- [Raid Detection False Positives](https://erikmcclure.com/blog/discord-rise-of-bot-wars/)

---

### Pitfall 2: Verification System Bypasses

**What goes wrong:** Attackers bypass emoji verification using automated tools, making your verification gate worthless while you believe the server is protected.

**Why it happens:**
- Button/reaction-based verification is "user-friendly but slightly less secure than a full CAPTCHA"
- Bots can programmatically click buttons and add reactions
- Race conditions in verification timing allow users to post before role is assigned
- Missing @everyone permission checks let unverified users access channels

**Consequences:**
- Raider bots pass verification automatically
- False sense of security while server remains vulnerable
- Legitimate users frustrated by verification while attackers bypass it
- Phishing links posted during verification race condition window

**Prevention:**
- Implement CAPTCHA (image-based or puzzle) instead of simple emoji selection
- Use web-based verification flow (OAuth2) which is "much harder for bots to bypass"
- Verify @everyone permissions are correctly restricted before verification completes
- Add additional checks: account age, avatar presence, username patterns
- Monitor verification completion rate (>90% = probably too easy to bypass)
- Add verification timeout cleanup to remove stale verification attempts

**Detection (warning signs):**
- Verification completion rate approaches 100%
- New accounts pass verification instantly
- Accounts with default Discord avatars verify successfully
- Suspicious pattern in verification times (all exactly 2 seconds)

**Phase impact:** Phase 1 (verification system). Verification must actually stop bots, not just inconvenience humans.

**Sources:**
- [Discord Verification Bot Guide 2025](https://blog.communityone.io/best-discord-security-bot/)
- [Verification Bot Bypass Methods](https://github.com/0verp0wer/verifier-bypass)
- [Discord Security Best Practices 2025](https://friendify.net/blog/discord-bot-security-best-practices-2025.html)

---

### Pitfall 3: Link Scanner Evasion

**What goes wrong:** Attackers post malicious links that bypass your scanner using URL shorteners, redirects, and obfuscation techniques.

**Why it happens:**
- Simple regex-based scanning only checks the posted URL, not where it redirects
- URL shorteners (bit.ly, tinyurl) can't be blanket-banned (too many false positives)
- Attackers use multi-stage redirects: safe domain → shortener → phishing site
- Unicode homoglyphs make links look legitimate (discοrd.com with Greek omicron)
- Expired Discord invite links can be re-registered to point to malicious servers

**Consequences:**
- Phishing links reach users despite "link scanning enabled"
- Community loses trust in security measures
- Account takeovers occur from undetected phishing
- Ban on second offense never triggers because first offense wasn't detected

**Prevention:**
- **Unfurl shorteners:** Follow redirects and check final destination, not just posted URL
- **Check both ends:** Validate URLs before AND after following redirects
- **Use maintained blocklists:** Dogino's Discord-Phishing-URLs list (updated daily)
- **Implement retry logic:** Some shorteners require JavaScript, check multiple ways
- **Don't trust whitelist bypasses:** Even discord.gg can redirect to malicious servers (expired invite attack)
- **Normalize Unicode:** Convert lookalike characters to ASCII before checking
- **Time-based scanning:** Re-check links posted in the last hour (redirects can change)

**Detection (warning signs):**
- Users report phishing links that weren't deleted
- Links containing bit.ly/tinyurl/discord.gg getting through
- Phishing reports reference messages from the last week
- Multiple reports of "similar looking" Discord links

**Phase impact:** Phase 1 (link scanner). URL scanning is more complex than regex matching.

**Sources:**
- [Discord Phishing URL Evasion](https://research.checkpoint.com/2025/from-trust-to-threat-hijacked-discord-invites-used-for-multi-stage-malware-delivery/)
- [URL Shortener Issues](https://github.com/python-discord/bot/issues/863)
- [Discord Phishing URLs Database](https://github.com/Dogino/Discord-Phishing-URLs)
- [Bypassing Discord Link Filters](https://gist.github.com/Nickguitar/7c6bdfa8255b2ec7e0d6d4015550ce4c)

---

### Pitfall 4: False Positives Destroying Community Trust

**What goes wrong:** Over-aggressive detection settings ban/timeout legitimate users, especially during legitimate events like coordinated game launches or community meetups.

**Why it happens:**
- Raid thresholds trigger on legitimate mass joins (10 friends joining for game night)
- IP-based alt detection flags roommates, siblings, VPN users
- New account filters block legitimate new community members
- No appeal mechanism means false positives are permanent

**Consequences:**
- Community members get banned and leave permanently
- Word spreads that server is "ban-happy" or "broken"
- Moderators spend hours manually unbanning false positives
- Legitimate users learn to distrust security measures
- Server growth stalls because new users can't join

**Prevention:**
- **Dynamic thresholds:** Increase join-rate threshold during announced events
- **Whitelist mechanism:** Allow mods to whitelist users before events
- **Appeal channel required:** #verify-help for false positives
- **Manual review for edge cases:** Flag suspicious but don't auto-ban
- **Logging and transparency:** Show users WHY they were flagged
- **Relaxation options:** Disable strict IP matching for household users
- **Grace period:** Warn before banning on first offense

**Detection (warning signs):**
- Multiple users in #general asking "why was I banned?"
- Audit log shows ban/unban cycles for same user
- Moderators manually reversing bot actions frequently
- Complaints about "bot issues" in other Discord servers
- Drop in new member retention rate

**Phase impact:** Phase 1 (all features). Every automated action needs an appeal path.

**Sources:**
- [Discord Raid Detection False Positives](https://wiki.cakey.bot/en/moderation/anti-raid)
- [Alt Detection Issues](https://docs.doublecounter.gg/double-counter-en/legal)
- [Appeal System Implementation](https://github.com/sylveon/discord-ban-appeals)

---

### Pitfall 5: Missing Gateway Intents

**What goes wrong:** Your bot silently fails to detect events because required Gateway Intents aren't enabled in both code and Developer Portal.

**Why it happens:**
- `GuildMembers` privileged intent is required for raid detection (guildMemberAdd event)
- `MessageContent` privileged intent is required for link scanning
- Must be enabled in TWO places: code AND Discord Developer Portal
- Error messages are unclear ("event not firing" vs "intent missing")
- Bots over 100 servers require verification to use privileged intents

**Consequences:**
- Raid detection completely non-functional (guildMemberAdd never fires)
- Link scanner sees messages but can't read content (empty string)
- No errors logged, bot appears to work but doesn't
- Discovered only when actual attack happens

**Prevention:**
- **Enable in code:**
```javascript
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,     // For raid detection
    GatewayIntentBits.MessageContent,   // For link scanning
    GatewayIntentBits.GuildModeration   // For audit logs
  ]
});
```
- **Enable in Developer Portal:** Toggle privileged intents in Bot settings
- **Test with fresh accounts:** Don't just test with your own account
- **Monitor intent errors:** Log 4014 close codes (disallowed intents)
- **Plan for verification:** Bots >100 servers need Discord approval for privileged intents

**Detection (warning signs):**
- guildMemberAdd event never fires during test joins
- message.content is always empty string
- Bot connects successfully but features don't work
- WebSocket close code 4014 in logs

**Phase impact:** Phase 0 (initial setup). Must be configured before any features work.

**Sources:**
- [Discord Gateway Intents](https://discordjs.guide/popular-topics/intents)
- [Privileged Intents Requirements](https://support-dev.discord.com/hc/en-us/articles/6177533521047-Privileged-Intents-Best-Practices)
- [guildMemberAdd Not Working](https://github.com/discordjs/discord.js/discussions/9557)

---

## Moderate Pitfalls

### Pitfall 6: Sophisticated Raid Evasion

**What goes wrong:** Attackers evade simple "N joins in M seconds" detection by joining slowly, aging accounts, then unleashing coordinated spam later.

**Why it happens:**
- Simple threshold detection: "10 joins in 30 seconds"
- Sophisticated attackers: 1000 accounts join at 1/hour over weeks
- Accounts age to bypass "new account" filters
- Each account posts exactly 1 message (below spam threshold)
- Attack happens weeks after joins, no correlation in logs

**Prevention:**
- Track long-term join patterns (unusual sustained join rate)
- Monitor join sources (same invite link used 100 times)
- Implement "heat algorithm" with linear decay for spam detection
- Flag accounts that join and stay silent for weeks
- Cross-reference multiple signals: join time + first message time + content similarity

**Phase impact:** Phase 2+ (advanced raid detection). Simple detection handles simple raids.

**Sources:**
- [Pressure-Based Anti-Spam](https://erikmcclure.com/blog/pressure-based-anti-spam-for-discord-bots/)

---

### Pitfall 7: Account Takeover Detection Failure

**What goes wrong:** Legitimate accounts get compromised and post phishing links, bypassing new-account and verification checks.

**Why it happens:**
- Bot only checks account age and verification status
- Compromised accounts are old, verified, and trusted
- No behavioral analysis for sudden pattern changes
- Attackers use compromised accounts specifically to bypass security

**Prevention:**
- Monitor behavioral changes: account silent for months suddenly posts links
- Flag sudden permission changes (role additions)
- Detect unusual activity patterns (different timezone, device)
- Require re-verification for dormant accounts posting links
- Cross-check posted links against known phishing databases even for verified users

**Detection (warning signs):**
- Trusted member posts obvious phishing link
- Multiple reports of "X account got hacked"
- Link posted immediately after role change
- Account's first message in weeks is a suspicious link

**Phase impact:** Phase 2+ (behavioral detection). Beyond scope of basic filtering.

**Sources:**
- [Account Takeover via Discord Bots](https://learn.microsoft.com/en-us/answers/questions/5647402/my-microsoft-account-was-hacked-after-verifying-wi)

---

### Pitfall 8: Memory Leaks from Interaction Collectors

**What goes wrong:** Button collectors for emoji verification create memory leaks that crash your bot after 24-48 hours.

**Why it happens:**
- Interaction collectors attach event listeners that never get removed
- Each verification attempt creates a new collector
- No timeout specified, or timeout not properly cleaning up
- Collectors created inside event handlers without disposal

**Consequences:**
- Bot memory usage grows continuously
- Performance degrades over time
- Bot crashes requiring restart
- Verification breaks for pending users when bot restarts

**Prevention:**
- **Always set time limit:** `{ time: 600000 }` (10 minutes)
- **Set max interactions:** `{ max: 1 }` for single-click verification
- **Handle end event:** Explicitly clean up when collector ends
- **Don't create collectors in loops:** Use single collector with filter
- **Monitor memory:** Alert when memory usage exceeds threshold

**Code example:**
```javascript
// BAD: No timeout, no cleanup
const collector = message.createMessageComponentCollector({ filter });

// GOOD: Timeout + cleanup
const collector = message.createMessageComponentCollector({
  filter,
  time: 600000,  // 10 minutes
  max: 1         // Stop after one interaction
});

collector.on('end', () => {
  // Explicit cleanup
  collector.stop();
});
```

**Detection (warning signs):**
- Bot memory usage increases daily
- Bot crashes every 24-48 hours
- Slowdowns after handling many verifications
- Error: "Possible EventEmitter memory leak detected"

**Phase impact:** Phase 1 (verification system). Button collectors need lifecycle management.

**Sources:**
- [Interaction Collector Memory Leak](https://github.com/discordjs/discord.js/issues/6905)
- [Collector Timeout Issues](https://github.com/discordjs/discord.js/issues/4751)

---

### Pitfall 9: Bot Token Leaks

**What goes wrong:** Bot token gets committed to GitHub or leaked in logs, giving attackers full control of your bot.

**Why it happens:**
- Token hardcoded in source files instead of environment variables
- .env file accidentally committed to Git
- Token logged during debugging
- Token visible in Railway/deployment platform logs
- Compromised dependency steals environment variables

**Consequences:**
- Attackers gain full bot control
- Bot used to raid other servers (your bot gets banned)
- Server data accessed/leaked
- Must regenerate token, breaking existing deployment

**Prevention:**
- **Use .env files:** Never hardcode tokens
- **Gitignore .env:** Add to .gitignore before first commit
- **Railway environment variables:** Use Railway's built-in secrets, not .env in repo
- **Sanitize logs:** Never log full tokens (redact to first/last 4 chars)
- **Rotate tokens regularly:** Regenerate every 90 days
- **Monitor for leaks:** Services like GitGuardian scan for leaked tokens
- **Limit bot permissions:** Don't grant Administrator unnecessarily

**Detection (warning signs):**
- Bot performs actions you didn't trigger
- Unexpected API usage spikes
- Bot joins servers you don't recognize
- GitGuardian alerts

**Phase impact:** Phase 0 (initial setup). Security foundation must be solid.

**Sources:**
- [Discord Bot Token Security](https://vibecord.dev/blog/discord-bot-token-security-guide)
- [Token Leak Remediation](https://www.gitguardian.com/remediation/discord-bot-token)
- [CVE-2025-26604](https://cvefeed.io/vuln/detail/CVE-2025-26604)

---

### Pitfall 10: Timeout/Ban Action Edge Cases

**What goes wrong:** Moderation actions fail silently or have unexpected behavior due to Discord permission hierarchy and API limitations.

**Why it happens:**
- Can't timeout server owners (API silently fails)
- Can't timeout users with Administrator permission
- Can't timeout users with higher role than bot
- Timeout duration must be 60 seconds to 28 days (API rejects otherwise)
- Manual permission changes (removing speak permissions) aren't tracked as timeouts

**Consequences:**
- Raid leader (server owner alt) can't be timed out
- Moderators manually time out users, bot doesn't know to unban later
- Bot attempts action, gets 403, doesn't log failure
- Attackers give themselves high roles to bypass timeouts

**Prevention:**
- **Check hierarchy before action:** Verify bot's role is higher than target user's highest role
- **Handle permission errors:** Log and alert when moderation action fails
- **Validate timeout duration:** Ensure 60s ≤ duration ≤ 28 days before API call
- **Coordinate with manual actions:** Track manual timeouts via audit log
- **Fallback to ban:** If timeout fails due to permissions, escalate to ban

**Detection (warning signs):**
- Moderation actions "don't work" on certain users
- 403 Forbidden errors in bot logs
- Audit log shows bot attempted action but nothing happened
- Timeouts applied but user can still post

**Phase impact:** Phase 1 (all moderation actions). Permission checks before every action.

**Sources:**
- [Discord Moderation Best Practices](https://blog.communityone.io/best-discord-moderation-bots-2025/)
- [Timeout Limitations](https://www.qqtube.com/blog/how-to-untimeout-on-discord)

---

## Minor Pitfalls

### Pitfall 11: Missing Appeal System

**What goes wrong:** Users falsely flagged have no way to appeal, leading to permanent exodus and reputation damage.

**Prevention:** Implement #verify-help channel and manual review process from day one.

**Phase impact:** Phase 1 (must launch with verification).

---

### Pitfall 12: No Logging/Audit Trail

**What goes wrong:** When something breaks, you have no idea what happened or why.

**Prevention:** Log all moderation actions with timestamps, user IDs, reasons, and outcomes. Store in database, not just Discord channel.

**Phase impact:** Phase 1 (all features).

---

### Pitfall 13: Testing Only in Production

**What goes wrong:** First time you test raid detection is during an actual raid.

**Prevention:** Create test server, simulate raids with alt accounts, verify rate limiting behavior under load.

**Phase impact:** Phase 1 (before deployment).

---

### Pitfall 14: Ignoring GDPR/Privacy

**What goes wrong:** Storing IP addresses, device fingerprints, and user data without privacy policy or data retention limits.

**Prevention:**
- Create privacy policy documenting what data is collected and why
- Implement data retention limits (delete IP addresses after 24 months)
- Provide data deletion on request
- Don't collect more than necessary

**Phase impact:** Phase 1 (before collecting any user data).

**Sources:**
- [Discord GDPR Fine](https://dataprivacymanager.net/france-fines-discord-e800000-under-the-gdpr/)
- [Bot Privacy Policy Examples](https://docs.doublecounter.gg/double-counter-en/legal)

---

### Pitfall 15: Hardcoded Configuration

**What goes wrong:** Raid thresholds, timeout durations, and ban rules are hardcoded, requiring code changes and redeployment to adjust.

**Prevention:** Make all thresholds configurable via slash commands or config file.

**Phase impact:** Phase 1 (initial architecture).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Initial bot setup | Missing gateway intents (#5) | Enable privileged intents in code AND Developer Portal before testing |
| Verification system | Memory leaks from collectors (#8) | Set time/max limits on all interaction collectors |
| Raid detection | Rate limiting during raids (#1) | Implement lockdown mode instead of mass-banning |
| Link scanning | Shortener evasion (#3) | Unfurl URLs and check final destination |
| All automated actions | False positives (#4) | Build appeal system from day one |
| Deployment | Token leaks (#9) | Use Railway environment variables, never commit .env |
| Post-launch | No audit trail (#12) | Log everything to database from launch |

---

## Research Confidence Notes

### HIGH Confidence Areas
- Gateway intents requirements (official Discord documentation)
- Rate limiting behavior (Discord API specifications)
- Button collector memory leaks (confirmed GitHub issues)

### MEDIUM Confidence Areas
- Specific evasion techniques (community reports, security blogs)
- False positive rates (anecdotal from bot developers)
- Sophisticated raid patterns (security researcher articles)

### LOW Confidence Areas
- Exact rate limit thresholds (Discord doesn't publish specifics)
- CAPTCHA bypass rates (no authoritative data available)
- Account takeover detection accuracy (limited public research)

---

## Critical Takeaway

**The #1 mistake Discord security bots make:** Designing for the simple case (spam bot, obvious raid) and failing catastrophically against sophisticated attacks (slow raids, compromised accounts, evasion techniques).

Your roadmap must account for:
1. Rate limiting under load (not just detection, but action execution)
2. Evasion techniques (URL unfurling, not just regex)
3. False positives (appeal system is not optional)
4. Memory management (collectors must have timeouts)
5. Operational security (token protection from day zero)

Each feature should answer: "What happens when attackers specifically try to bypass this?"
