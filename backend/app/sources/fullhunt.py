import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)

_BASE = "https://fullhunt.io/api/v1/domain/{domain}/subdomains"


class FullHuntSource(Source):
    name = "fullhunt"
    display_name = "FullHunt"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("fullhunt: no API key configured, skipping")
            return

        headers = {"X-API-KEY": api_key}
        url = _BASE.format(domain=domain)
        logger.info("fullhunt: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 429:
                    logger.warning("fullhunt: rate limited")
                    return
                resp.raise_for_status()
                data = resp.json()
                for fqdn in data.get("hosts", []):
                    fqdn = str(fqdn).strip()
                    if fqdn and fqdn not in seen:
                        if fqdn.endswith(f".{domain}") or fqdn == domain:
                            seen.add(fqdn)
                            yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("fullhunt: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("fullhunt: error querying %s: %s", domain, e)

        logger.info("fullhunt: found %d subdomains for %s", len(seen), domain)
