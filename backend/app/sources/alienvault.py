import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)


class AlienVaultSource(Source):
    name = "alienvault"
    display_name = "AlienVault OTX"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
        logger.info("alienvault: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while url:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    for entry in data.get("passive_dns", []):
                        hostname = entry.get("hostname", "").strip()
                        if hostname and hostname not in seen:
                            if hostname.endswith(f".{domain}") or hostname == domain:
                                seen.add(hostname)
                                yield hostname
                    url = data.get("next")
        except httpx.HTTPStatusError as e:
            logger.error("alienvault: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("alienvault: error querying %s: %s", domain, e)

        logger.info("alienvault: found %d subdomains for %s", len(seen), domain)
