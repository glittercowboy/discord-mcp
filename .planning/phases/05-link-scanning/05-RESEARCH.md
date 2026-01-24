# Phase 5: Link Scanning - Research

**Researched:** 2026-01-24
**Domain:** Discord.py URL Detection, Redirect Following, Blocklist Matching, User Offense Tracking
**Confidence:** HIGH

## Summary

Phase 5 requires implementing URL-based phishing link detection using Discord.py's `on_message` event combined with HTTP redirect following to check final destinations. The implementation must:

1. Extract URLs from messages using regex pattern matching
2. Follow URL redirects using httpx to find final destination
3. Check extracted domains against known phishing blocklist
4. Delete violating messages silently with DM explanation
5. Track user offenses (1st: timeout, 2nd: auto-ban)
6. Log all deleted links to #security-logs with context

The standard approach uses httpx's async redirect following with domain extraction via tldextract for accurate TLD handling, pre-compiled URL regex for performance, and JSON-based offense tracking (similar to Phase 3 config patterns) for tracking per-user violations.

**Primary recommendation:** Use httpx AsyncClient with `follow_redirects=True` to resolve shortened URLs, tldextract for domain extraction, maintained community blocklists (Discord-AntiScam/scam-links), and JSON file persistence for per-user offense counts keyed by user ID.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| discord.py | 2.6.4 | Discord Gateway client and message events | Provides `on_message` event and member timeout/ban methods |
| httpx | 0.28.1+ | Async HTTP client for redirect following | Async-ready, follows redirects with history tracking, already in project dependencies |
| tldextract | Latest | Accurate domain/TLD extraction from URLs | Handles complex TLDs (e.g., co.uk), uses Mozilla Public Suffix List, prevents false positives |
| re (stdlib) | 3.12+ | URL pattern matching in message content | Pre-compiled for performance during high-volume message processing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json (stdlib) | 3.12+ | Offense tracking persistence | Store per-user offense counts, hot-reload on each access |
| pathlib (stdlib) | 3.12+ | Blocklist file paths | Cross-platform file handling for blocklist storage |
| datetime (stdlib) | 3.12+ | Timeout duration calculation | Account age, offense timestamps |
| asyncio (stdlib) | 3.12+ | Concurrent redirect resolution | Prevent blocking on slow HTTP requests during high message volume |
| logging (stdlib) | 3.12+ | Audit trail | Log link violations, offense tracking |

### Blocklist Source
| Source | Type | Purpose | Why Standard |
|--------|------|---------|--------------|
| Discord-AntiScam/scam-links | GitHub JSON | 24,000+ known scam/phishing domains | Community-maintained, regularly updated, comprehensive Discord-focused list |
| Discord-Phishing-Links (nikolaischunk) | GitHub JSON | 22,000+ phishing domains | Alternative/complement, actively maintained |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx async redirect following | requests library + requests.Session | requests is sync-only, requires thread pool or subprocess for async, httpx is native async |
| tldextract for domain extraction | urllib.parse + regex | urlparse handles basic domains, fails on complex TLDs (forums.bbc.co.uk → "co" not "bbc"), tldextract is purpose-built |
| Community blocklist | VirusTotal API or URLhaus API | External APIs add latency, require API keys, rate-limited; local blocklist is instant and offline-capable |
| JSON persistence | SQLite database | JSON is sufficient for offense tracking (limited data), simpler than SQL, matches Phase 3 pattern |
| `member.timeout()` for first offense | Role restriction or deletion | timeout is Discord's standard moderation action, visible to user with timer, clearer intent |
| Per-user offense tracking | Global offense flag | Per-user tracking required for "2nd offense = ban" requirement |

**Installation:**
```bash
# Add to project dependencies
pip install httpx>=0.28.1 tldextract

# Or via uv:
uv pip install httpx tldextract
```

## Architecture Patterns

### Recommended Project Structure
```
src/guardian/
├── guardian.py                  # Main bot client, on_message event
├── link_scanning.py             # NEW: URL detection, blocklist matching
├── link_resolver.py             # NEW: Async redirect following with httpx
├── offense_tracking.py          # NEW: Per-user offense counter persistence
├── config.py                    # Existing config (references blocklist path)
├── infrastructure.py            # Existing infrastructure
├── account_restrictions.py      # Existing account restrictions
├── verification.py              # Existing verification
├── slash_commands.py            # Existing slash commands
├── logging_utils.py             # Existing logging
└── data/
    └── blocklist.json           # NEW: Community blocklist (Discord-AntiScam)
```

### Pattern 1: URL Extraction and Pre-compilation
**What:** Extract all URLs from message content using pre-compiled regex, returning list of URLs to check.

**When to use:** On every on_message event to isolate URL checking from other message filtering.

**Example:**
```python
import re

# Pre-compile at module level for performance
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')

def extract_urls_from_message(message: discord.Message) -> list[str]:
    """Extract all URLs from message content.

    Args:
        message: Discord message to scan

    Returns:
        List of URL strings found in message, empty if none

    Example:
        >>> urls = extract_urls_from_message(message)
        >>> if urls:
        ...     # Check each URL
    """
    urls = URL_PATTERN.findall(message.content)
    return urls
```

**Key insight:** Pre-compile regex at module load time. Regex compilation is expensive; doing it on every message check is a performance bottleneck during raids or spam.

### Pattern 2: Domain Extraction from URL with tldextract
**What:** Extract the final domain from a URL (including TLD) using tldextract for accurate parsing.

**When to use:** After URL is extracted and resolved (after following redirects).

**Example:**
```python
import tldextract
from urllib.parse import urlparse

def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL, handling complex TLDs.

    Args:
        url: Full URL string

    Returns:
        Domain without subdomain (e.g., "discord.com" from "cdn.discord.com")

    Example:
        >>> extract_domain_from_url("https://forums.bbc.co.uk/path")
        "bbc.co.uk"
        >>> extract_domain_from_url("https://www.example.com")
        "example.com"
    """
    try:
        # Parse URL to get just the netloc (domain part)
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path.split('/')[0]

        # Extract domain using tldextract (handles complex TLDs)
        extracted = tldextract.extract(netloc)

        # Reconstruct domain.suffix (e.g., "discord.com" or "bbc.co.uk")
        if extracted.domain and extracted.suffix:
            return f"{extracted.domain}.{extracted.suffix}"
        elif extracted.domain:
            return extracted.domain
        else:
            # Fallback for IP addresses or unparseable URLs
            return netloc
    except Exception as e:
        logging.error(f"Failed to extract domain from {url}: {e}")
        return ""
```

**Key insight:** `urllib.parse.urlparse` alone is insufficient for TLDs like .co.uk, .com.au, or .github.io. tldextract uses Mozilla's Public Suffix List to correctly identify "bbc" as the domain in "forums.bbc.co.uk".

### Pattern 3: Async Redirect Following with httpx
**What:** Follow HTTP redirects asynchronously using httpx to resolve shortened URLs to their final destination.

**When to use:** For every URL extracted from message before checking blocklist (shortened URLs mask final destination).

**Example:**
```python
import httpx
import logging

logger = logging.getLogger(__name__)

async def resolve_url_destination(url: str, timeout_seconds: int = 5, max_redirects: int = 10) -> str:
    """Follow redirects to get final URL destination.

    Args:
        url: URL to resolve (may be shortened)
        timeout_seconds: Request timeout (shorter prevents hanging on slow servers)
        max_redirects: Maximum redirects to follow (prevents loops)

    Returns:
        Final URL after all redirects, or original URL if error/timeout

    Example:
        >>> final_url = await resolve_url_destination("https://bit.ly/example")
        >>> final_url
        "https://malicious-phishing-site.com/steal-nitro"
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            max_redirects=max_redirects
        ) as client:
            # Use HEAD request first (faster, gets headers only)
            # If HEAD fails, fall back to GET
            try:
                response = await client.head(url, follow_redirects=True)
            except (httpx.RequestError, httpx.HTTPError):
                # HEAD may fail on some servers, try GET
                response = await client.get(url, follow_redirects=True)

            # Return final URL after all redirects
            final_url = str(response.url)

            if response.history:
                logging.debug(f"URL redirect chain: {url} → {final_url} ({len(response.history)} redirects)")

            return final_url

    except httpx.TimeoutException:
        logging.warning(f"Timeout resolving {url} - treating as final URL")
        return url
    except Exception as e:
        logging.warning(f"Failed to resolve {url}: {e} - treating as final URL")
        return url
```

**Key insight:** HEAD requests are faster (headers only), but some servers block HEAD. Fallback to GET. Set timeout low (5 seconds) to prevent blocking on slow/malicious servers that intentionally delay. Max redirects prevents infinite loops.

### Pattern 4: Blocklist Loading and Matching
**What:** Load blocklist from JSON file into set for O(1) lookup performance, check extracted domains against set.

**When to use:** Once per message containing URLs, after domain extraction.

**Example:**
```python
import json
from pathlib import Path

class BlocklistMatcher:
    """Load and match domains against phishing blocklist."""

    def __init__(self, blocklist_path: Path):
        """Load blocklist from JSON file.

        Args:
            blocklist_path: Path to blocklist.json file
        """
        self.blocklist_path = blocklist_path
        self.domains = set()
        self.load_blocklist()

    def load_blocklist(self) -> None:
        """Load blocklist from file into memory set."""
        try:
            if not self.blocklist_path.exists():
                logging.warning(f"Blocklist not found at {self.blocklist_path}")
                return

            with open(self.blocklist_path, 'r') as f:
                data = json.load(f)

            # Blocklist format: {"domains": ["example.com", "phishing.net"]}
            # Or flat list of domains
            if isinstance(data, dict):
                domains = data.get("domains", [])
            elif isinstance(data, list):
                domains = data
            else:
                logging.error(f"Unexpected blocklist format: {type(data)}")
                return

            # Store as lowercase for case-insensitive matching
            self.domains = set(d.lower() for d in domains)
            logging.info(f"Loaded {len(self.domains)} domains from blocklist")

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse blocklist JSON: {e}")
        except Exception as e:
            logging.error(f"Failed to load blocklist: {e}")

    def is_blocklisted(self, domain: str) -> bool:
        """Check if domain is in blocklist.

        Args:
            domain: Domain to check (e.g., "discord-scam.com")

        Returns:
            True if domain is blocklisted, False otherwise
        """
        if not domain:
            return False

        domain_lower = domain.lower()

        # Exact match
        if domain_lower in self.domains:
            return True

        # Subdomain match (e.g., "cdn.phishing.com" matches "phishing.com")
        parts = domain_lower.split('.')
        for i in range(1, len(parts)):
            parent_domain = '.'.join(parts[i:])
            if parent_domain in self.domains:
                logging.debug(f"Domain {domain} matched by parent {parent_domain}")
                return True

        return False
```

**Key insight:** Set lookup is O(1), enabling instant blocklist checking even with 24,000+ domains. Reload blocklist on startup (not hot-reload like Phase 3, since blocklist is infrequently updated). Check subdomains too (cdn.phishing.com should match phishing.com).

### Pattern 5: Per-User Offense Tracking with JSON
**What:** Track number of violations per user ID in JSON file, increment on each violation, auto-ban on 2nd offense.

**When to use:** After detecting scam link in message, before applying timeout.

**Example:**
```python
import json
from pathlib import Path
from datetime import datetime, timezone

class OffenseTracker:
    """Track per-user link scanning offenses for escalating punishment."""

    def __init__(self, tracking_file: Path):
        """Initialize offense tracker.

        Args:
            tracking_file: Path to offenses.json file
        """
        self.tracking_file = tracking_file
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

    def get_offense_count(self, user_id: int) -> int:
        """Get number of offenses for user.

        Args:
            user_id: Discord user ID

        Returns:
            Number of prior offenses (0 if no prior offenses)
        """
        try:
            if not self.tracking_file.exists():
                return 0

            with open(self.tracking_file, 'r') as f:
                data = json.load(f)

            user_key = str(user_id)
            if user_key in data:
                return data[user_key].get("count", 0)
            return 0

        except json.JSONDecodeError:
            logging.warning("Offense tracking file corrupted, resetting")
            return 0
        except Exception as e:
            logging.error(f"Failed to get offense count: {e}")
            return 0

    def record_offense(self, user_id: int, message_id: int, domain: str) -> int:
        """Record a link scanning violation for user.

        Args:
            user_id: Discord user ID
            message_id: Discord message ID that violated
            domain: Blocklisted domain found

        Returns:
            Total offense count after recording (1 or 2)
        """
        try:
            # Load existing data
            if self.tracking_file.exists():
                with open(self.tracking_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}

            user_key = str(user_id)
            if user_key not in data:
                data[user_key] = {"count": 0, "offenses": []}

            # Increment count
            data[user_key]["count"] += 1
            current_count = data[user_key]["count"]

            # Record offense details
            data[user_key]["offenses"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": message_id,
                "domain": domain
            })

            # Keep only last 10 offenses per user to prevent unbounded growth
            if len(data[user_key]["offenses"]) > 10:
                data[user_key]["offenses"] = data[user_key]["offenses"][-10:]

            # Write atomically (temp file then rename)
            temp_file = self.tracking_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.tracking_file)

            logging.info(f"Recorded offense {current_count} for user {user_id}")
            return current_count

        except Exception as e:
            logging.error(f"Failed to record offense: {e}")
            return 0
```

**Key insight:** Use atomic writes (temp + rename) to prevent corruption if bot crashes mid-write. Store offense history for mod review and evidence. Increment on each violation (required for 2nd offense auto-ban).

### Anti-Patterns to Avoid
- **Checking blocklist without following redirects:** Shortened URLs hide final destination. Always resolve first.
- **Synchronous HTTP requests in on_message:** Will block event handler, causing message lag during raids. Always use `async with httpx.AsyncClient()`.
- **Not handling HTTP timeouts gracefully:** Slow/malicious servers can stall the bot. Set timeout to 5 seconds max, treat timeouts as "pass" (don't delete).
- **Case-sensitive domain matching:** Domains are case-insensitive (DISCORD.COM = discord.com). Always lowercase before checking.
- **Checking only direct domain, not subdomains:** cdn.malicious.com won't match malicious.com in blocklist. Check parent domains.
- **Not tracking offense count across bot restarts:** JSON persistence required so offense count survives restarts.
- **Deleting message without DM:** Users won't know why message was deleted. Always DM explanation (with try/except for DM failures).
- **Not logging to #security-logs:** Audit trail required for trust and dispute resolution.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Following URL redirects | Manual redirect loop with requests | httpx with `follow_redirects=True` | httpx handles redirect loops, encoding issues, HEAD fallback; manual loop is error-prone |
| Extracting domain from complex TLDs | Regex or string split on "." | tldextract with Public Suffix List | Handles forums.bbc.co.uk (naive split fails), github.io, co.uk, etc. |
| Managing phishing blocklist | Build own list or scrape | Discord-AntiScam/scam-links community list | 24,000+ domains, actively maintained, Discord-focused, tested |
| HTTP timeout handling | No timeout or very long timeout | httpx with timeout=5 | Long timeout hangs on slow malicious servers; 5s is standard |
| Persistent offense tracking | Memory-only counter | JSON file with atomic writes | Survives bot restarts, prevents circumventing 2nd offense ban |
| Checking subdomains | Only check exact domain | Check parent domains in blocklist | cdn.phishing.com should block even if only phishing.com is listed |

**Key insight:** URL redirect following looks simple (just fetch the URL) but has edge cases: slow servers, redirects to invalid URLs, encoding issues, infinite loops. httpx handles all of these. Domain extraction with TLDs is surprisingly complex (cc.uk is TLD, co.uk is TLD, but .uk alone is not in many contexts). tldextract uses Mozilla's curated list.

## Common Pitfalls

### Pitfall 1: HTTP Request Blocks on_message Event Handler
**What goes wrong:** Message arrives, bot tries to resolve URL, server is slow (or intentionally stalls), bot stops processing messages in that channel for 10+ seconds.

**Why it happens:** Using synchronous requests (requests library) or not setting timeout on httpx.

**How to avoid:**
```python
# WRONG - blocks event handler
response = requests.get(url)  # No timeout, synchronous

# RIGHT - async with timeout
async with httpx.AsyncClient(timeout=5) as client:
    response = await client.get(url, follow_redirects=True)
```

**Warning signs:** Bot messages lag after malicious URL is posted, other messages queue up, event handler appears frozen.

### Pitfall 2: Shortened URL Bypasses Blocklist Check
**What goes wrong:** User posts bit.ly/xyz which redirects to discord-scam.com, bot checks bit.ly (not blocklisted), approves message.

**Why it happens:** Not following redirects before domain extraction.

**How to avoid:** Always resolve URL to final destination before checking blocklist:
```python
urls = extract_urls_from_message(message)
for url in urls:
    final_url = await resolve_url_destination(url)  # Follow redirects
    domain = extract_domain_from_url(final_url)     # Extract from FINAL url
    if blocklist.is_blocklisted(domain):
        # Delete message
```

**Warning signs:** Malicious users report shortened URLs passing through, users accidentally click scam links through shortened form.

### Pitfall 3: Case Sensitivity in Domain Matching
**What goes wrong:** Blocklist contains "discord.com" (lowercase), user posts link to "DISCORD-PHISHING.COM" (uppercase), bot doesn't detect match.

**Why it happens:** Forgetting that domain names are case-insensitive by RFC 3986.

**How to avoid:**
```python
def is_blocklisted(self, domain: str) -> bool:
    domain_lower = domain.lower()  # Always lowercase before checking
    return domain_lower in self.domains
```

**Warning signs:** Same phishing links sometimes get caught, sometimes don't (depends on letter case in message).

### Pitfall 4: Subdomain Bypass
**What goes wrong:** Blocklist has "phishing.com", user posts "cdn.phishing.com", bot checks "cdn.phishing.com" against exact list only, doesn't match.

**Why it happens:** Not checking parent domains when doing blocklist lookup.

**How to avoid:**
```python
def is_blocklisted(self, domain: str) -> bool:
    domain_lower = domain.lower()

    # Check exact match
    if domain_lower in self.domains:
        return True

    # Check parent domains
    parts = domain_lower.split('.')
    for i in range(1, len(parts)):
        parent = '.'.join(parts[i:])
        if parent in self.domains:
            return True

    return False
```

**Warning signs:** Malicious users bypass filters by using subdomains (api.phishing.com, cdn.phishing.com, etc.).

### Pitfall 5: Race Condition - Offense Count Lost If Two Messages Arrive Simultaneously
**What goes wrong:** User sends two scam links in rapid succession, both detected before first offense is recorded, only recorded once instead of twice. Second message doesn't trigger auto-ban.

**Why it happens:** JSON writes are not atomic; concurrent reads/writes can interleave.

**How to avoid:**
```python
def record_offense(self, user_id: int, message_id: int, domain: str) -> int:
    try:
        # Load existing data
        with open(self.tracking_file, 'r') as f:
            data = json.load(f)

        # Increment
        data[str(user_id)]["count"] += 1

        # Write atomically: write to temp, then rename
        temp_file = self.tracking_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f)
        temp_file.replace(self.tracking_file)  # Atomic on POSIX

        return data[str(user_id)]["count"]
```

**Warning signs:** Auto-ban logic triggers inconsistently, offense count sometimes appears to reset.

### Pitfall 6: Timeout Duration Exceeds Discord's 28-Day Maximum
**What goes wrong:** Auto-ban requirement uses 28+ day timeout, Discord API rejects with error.

**Why it happens:** Misunderstanding that `member.timeout()` has maximum 28-day duration; auto-ban must use `member.ban()` instead.

**How to avoid:**
```python
# First offense: timeout for 1 hour (within 28-day limit)
await member.timeout(timedelta(hours=1), reason="Scam link posted")

# Second offense: permanent ban (not timeout)
await member.ban(reason="Scam link offense #2", delete_message_seconds=0)
```

**Warning signs:** Timeout API returns "Invalid timeout duration" or 400 Bad Request.

### Pitfall 7: Message Already Deleted When Trying to Delete
**What goes wrong:** Two checks detect same scam link, both try to delete message, second call throws discord.NotFound exception.

**Why it happens:** No idempotency check before delete.

**How to avoid:**
```python
try:
    await message.delete()
except discord.NotFound:
    logging.info(f"Message {message.id} already deleted")
except discord.Forbidden:
    logging.error(f"Cannot delete message {message.id} - missing permissions")
```

**Warning signs:** Exceptions logged when deleting already-deleted messages.

## Code Examples

Verified patterns from official sources and community practice:

### Extract URLs from Message
```python
# Source: Phase 3 URL_PATTERN pre-compiled pattern, adapted
import re

URL_PATTERN = re.compile(r'https?://\S+|www\.\S+')

def extract_urls(message: discord.Message) -> list[str]:
    """Extract all URLs from message content."""
    return URL_PATTERN.findall(message.content)
```

### Resolve URL with Redirect Following
```python
# Source: HTTPX official documentation
import httpx

async def resolve_url(url: str) -> str:
    """Follow redirects to final destination."""
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            response = await client.head(url)
            return str(response.url)
    except:
        return url
```

### Extract Domain from URL
```python
# Source: tldextract documentation
import tldextract
from urllib.parse import urlparse

def extract_domain(url: str) -> str:
    """Extract domain from URL (handles complex TLDs)."""
    parsed = urlparse(url)
    netloc = parsed.netloc
    extracted = tldextract.extract(netloc)
    return f"{extracted.domain}.{extracted.suffix}" if extracted.suffix else extracted.domain
```

### Member Timeout for First Offense
```python
# Source: discord.py documentation
from datetime import timedelta

async def apply_first_offense(member: discord.Member, reason: str):
    """Apply 1-hour timeout for first scam link offense."""
    try:
        await member.timeout(timedelta(hours=1), reason=reason)
    except discord.Forbidden:
        logging.error(f"Cannot timeout {member.name} - check permissions")
```

### Member Ban for Second Offense
```python
# Source: discord.py documentation
async def apply_second_offense(member: discord.Member, reason: str):
    """Auto-ban for second offense."""
    try:
        await member.ban(reason=reason)
    except discord.Forbidden:
        logging.error(f"Cannot ban {member.name} - check permissions")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual request library with thread pool | httpx async redirect following | 2020+ | Native async prevents thread overhead, cleaner code |
| Simple regex domain extraction | tldextract with Public Suffix List | Always | Handles complex TLDs, prevents false negatives |
| No redirect following (check original URL) | Follow redirects to final destination | Always | URL shorteners mask phishing sites, must resolve |
| Global blocklist flag | Per-user offense tracking | This project | Enables 1st timeout → 2nd ban escalation required by spec |
| In-memory offense tracking | JSON persistent file | This project | Survives restarts, prevents circumventing 2nd offense |
| Block only exact domain match | Check subdomains and parent domains | Best practice | cdn.phishing.com should block even if only phishing.com listed |

**Deprecated/outdated:**
- Manual URL parsing with string methods: Use tldextract (handles all edge cases)
- No timeout on HTTP requests: Always set timeout (prevents stalling)
- Synchronous HTTP in on_message: Use async/await (prevents blocking)

## Open Questions

1. **Should bot actively update blocklist or use static list?**
   - What we know: Phase 5 requirement is to check against blocklist, source not specified
   - What's unclear: Should bot download latest blocklist from Discord-AntiScam GitHub daily, or use static JSON checked in?
   - Recommendation: Start with static JSON checked in (simpler, reliable). Add scheduled download as future enhancement. Version control the blocklist snapshot.

2. **What should happen if HTTP request times out?**
   - What we know: Some servers are slow, malicious servers intentionally stall
   - What's unclear: Should timeout be treated as "safe URL" (pass) or "suspicious URL" (delete)?
   - Recommendation: Treat timeout as "pass" (safer for UX, prevents DoS where malicious servers stall bot). Log timeout as warning for manual review.

3. **Should subdomain subdomains be blocklisted separately?**
   - What we know: Can check parent domains in blocklist matching
   - What's unclear: If blocklist contains "example.com", should we also block "a.b.example.com" (6 levels deep)?
   - Recommendation: Check all parent domains up to the TLD. Most legitimate use cases won't go deeper than 2-3 levels.

4. **Should users be able to appeal bans for false positives?**
   - What we know: Phase 5 requires auto-ban on 2nd offense
   - What's unclear: Is there a manual review/appeal process, or is auto-ban final?
   - Recommendation: Defer to Phase 2 or later. Store offense details in log for manual review, but auto-ban is final in Phase 5.

5. **How often should the bot re-check the blocklist for updates?**
   - What we know: Community blocklists are maintained and updated
   - What's unclear: Should bot reload blocklist hourly, daily, or on startup only?
   - Recommendation: Reload blocklist on startup only (or via manual `/guardian reload-blocklist` command in Phase 3). Community lists are updated daily but reloading too often adds overhead.

6. **What domains should be excluded from URL checking?**
   - What we know: All URLs in messages should be checked
   - What's unclear: Should Discord-owned domains (cdn.discordapp.com) be exempt? GitHub links?
   - Recommendation: No exemptions by default. Discord itself can detect Discord phishing. All external links should be checked.

## Sources

### Primary (HIGH confidence)
- [HTTPX Official Documentation - API](https://www.python-httpx.org/api/) - follow_redirects parameter, AsyncClient, response.url and response.history
- [HTTPX Official Documentation - Quickstart](https://www.python-httpx.org/quickstart/) - Redirect following examples
- [tldextract PyPI](https://pypi.org/project/tldextract/) - Domain extraction with Public Suffix List
- [tldextract GitHub](https://github.com/john-kurkowski/tldextract) - Motivation for accurate TLD handling
- [discord.py Documentation: Member.timeout()](https://discordpy.readthedocs.io/en/stable/api.html) - Timeout API with duration limits
- [discord.py Documentation: Member.ban()](https://discordpy.readthedocs.io/en/stable/api.html) - Ban API for second offense
- [Discord Support: Time Out FAQ](https://support.discord.com/hc/en-us/articles/4413305239191-Time-Out-FAQ) - 28-day maximum timeout duration

### Secondary (MEDIUM confidence - WebSearch verified with official sources)
- [GitHub: Discord-AntiScam/scam-links](https://github.com/Discord-AntiScam/scam-links) - Community blocklist with 24,000+ domains, actively maintained
- [GitHub: nikolaischunk/discord-phishing-links](https://github.com/nikolaischunk/discord-phishing-links) - Alternative blocklist with 22,000+ domains
- [Discord: Protecting Against Scams on Discord](https://discord.com/safety/protecting-users-from-scams-on-discord) - Official guidance on phishing detection
- [Coding the Shield: Discord Anti-Phishing Bot](https://dev.to/ctnkaan/coding-the-shield-a-deep-dive-into-the-development-of-the-discord-bot-that-blocked-1000+-phishing-attacks-agl) - Community implementation patterns
- [Python Discord Guide: Why JSON is unsuitable as database](https://www.pythondiscord.com/pages/guides/python-guides/why-not-json-as-database/) - Context on JSON persistence (acceptable for small data like offense tracking)

### Tertiary (LOW confidence - WebSearch only, marked for validation)
- WebSearch results on discord.py rate limiting and on_message event performance (unverified for Phase 5 link scanning specifics)

## Metadata

**Confidence breakdown:**
- Standard stack (httpx, tldextract): HIGH - Official docs and community consensus
- Redirect following patterns: HIGH - HTTPX documentation is authoritative
- Domain extraction: HIGH - tldextract is purpose-built, tested library
- Blocklist approach: MEDIUM - Community lists are actively maintained but third-party sources
- Offense tracking: MEDIUM - JSON approach matches Phase 3 patterns but unverified for concurrent writes edge case
- Timeout/ban moderation: HIGH - discord.py API is documented and stable

**Research date:** 2026-01-24
**Valid until:** 2026-02-24 (30 days for stable domains; earlier if httpx or discord.py update timeout handling)

**Gaps that need validation during implementation:**
- Concurrent message handling and race conditions in offense tracking (test with rapid fire messages)
- HTTP timeout behavior on actual malicious servers (may need field testing)
- Blocklist update strategy (manual vs. automatic download)
