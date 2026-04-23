import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source
from app.sources.utils import get_with_backoff

logger = logging.getLogger(__name__)


class HackerTargetSource(Source):
    name = "hackertarget"
    display_name = "HackerTarget"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
        logger.info("hackertarget: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await get_with_backoff(client, url)
                if resp.status_code == 429:
                    logger.warning("hackertarget: daily limit reached (50 req/day free tier)")
                    return
                resp.raise_for_status()
                for line in resp.text.splitlines():
                    parts = line.strip().split(",")
                    if not parts:
                        continue
                    fqdn = parts[0].strip()
                    if fqdn and fqdn not in seen:
                        if fqdn.endswith(f".{domain}") or fqdn == domain:
                            seen.add(fqdn)
                            yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("hackertarget: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("hackertarget: error querying %s: %s", domain, e)

        logger.info("hackertarget: found %d subdomains for %s", len(seen), domain)
