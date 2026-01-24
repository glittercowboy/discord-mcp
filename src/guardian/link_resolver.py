"""Async URL resolution and domain extraction for link scanning.

Provides functions to follow HTTP redirects and extract domains from URLs
with accurate TLD handling for blocklist matching.
"""
import httpx
import logging
import tldextract
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


async def resolve_url_destination(
    url: str,
    timeout_seconds: int = 5,
    max_redirects: int = 10
) -> str:
    """Follow HTTP redirects to get final URL destination.

    Attempts HEAD request first (faster, headers-only), falls back to GET
    if HEAD fails. Returns original URL on timeout/error (treats as safe
    to prevent blocking on slow servers).

    Args:
        url: URL to resolve (may be shortened)
        timeout_seconds: Request timeout (default 5s to prevent hanging)
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
            # Try HEAD request first (faster, gets headers only)
            try:
                response = await client.head(url, follow_redirects=True)
            except (httpx.RequestError, httpx.HTTPStatusError):
                # HEAD may fail on some servers, try GET
                response = await client.get(url, follow_redirects=True)

            # Return final URL after all redirects
            final_url = str(response.url)

            # Log redirect chain if redirects occurred
            if response.history:
                logger.debug(
                    f"URL redirect chain: {url} → {final_url} "
                    f"({len(response.history)} redirects)"
                )

            return final_url

    except httpx.TimeoutException:
        logger.warning(f"Timeout resolving {url} - treating as final URL")
        return url
    except Exception as e:
        logger.warning(f"Failed to resolve {url}: {e} - treating as final URL")
        return url


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL, handling complex TLDs.

    Uses tldextract with Mozilla Public Suffix List to correctly parse
    multi-level TLDs (e.g., co.uk, github.io). Returns domain.suffix
    format for blocklist matching.

    Args:
        url: Full URL string

    Returns:
        Domain without subdomain (e.g., "discord.com" from "cdn.discord.com")
        Empty string if domain extraction fails

    Example:
        >>> extract_domain_from_url("https://forums.bbc.co.uk/path")
        "bbc.co.uk"
        >>> extract_domain_from_url("https://cdn.discord.com/attachments")
        "discord.com"
        >>> extract_domain_from_url("https://www.example.com")
        "example.com"
    """
    try:
        # Parse URL to get netloc (domain part)
        parsed = urlparse(url)
        netloc = parsed.netloc or parsed.path.split('/')[0]

        if not netloc:
            logger.debug(f"No netloc found in URL: {url}")
            return ""

        # Extract domain using tldextract (handles complex TLDs)
        extracted = tldextract.extract(netloc)

        # Reconstruct domain.suffix (e.g., "discord.com" or "bbc.co.uk")
        if extracted.domain and extracted.suffix:
            domain = f"{extracted.domain}.{extracted.suffix}"
            logger.debug(f"Extracted domain from {url}: {domain}")
            return domain
        elif extracted.domain:
            # TLD-less domain (rare, possibly IP)
            logger.debug(f"Extracted domain without suffix from {url}: {extracted.domain}")
            return extracted.domain
        else:
            # Fallback for IP addresses or unparseable URLs
            logger.debug(f"Using netloc as fallback for {url}: {netloc}")
            return netloc

    except Exception as e:
        logger.error(f"Failed to extract domain from {url}: {e}")
        return ""
