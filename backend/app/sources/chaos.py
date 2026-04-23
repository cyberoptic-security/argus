import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)

_BASE = "https://dns.projectdiscovery.io/dns/{domain}/public-recon-data"


class ChaosSource(Source):
    name = "chaos"
    display_name = "Chaos (ProjectDiscovery)"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("chaos: no API key configured, skipping")
            return

        headers = {"CHAOS_API_KEY": api_key}
        url = _BASE.format(domain=domain)
        logger.info("chaos: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 404:
                    logger.info("chaos: domain %s not in dataset (public/bug-bounty only)", domain)
                    return
                if resp.status_code == 429:
                    logger.warning("chaos: rate limited")
                    return
                resp.raise_for_status()
                data = resp.json()
                for sub in data.get("subdomains", []):
                    fqdn = f"{sub}.{domain}".strip()
                    if fqdn and fqdn not in seen:
                        seen.add(fqdn)
                        yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("chaos: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("chaos: error querying %s: %s", domain, e)

        logger.info("chaos: found %d subdomains for %s", len(seen), domain)
