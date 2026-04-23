import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source
from app.sources.utils import get_with_backoff

logger = logging.getLogger(__name__)

_BASE = "https://www.virustotal.com/api/v3/domains/{domain}/subdomains"


class VirusTotalSource(Source):
    name = "virustotal"
    display_name = "VirusTotal"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("virustotal: no API key configured, skipping")
            return

        headers = {"x-apikey": api_key}
        url = _BASE.format(domain=domain) + "?limit=40"
        seen: set[str] = set()
        logger.info("virustotal: querying for %s", domain)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while url:
                    resp = await get_with_backoff(client, url, headers=headers)
                    if resp.status_code == 429:
                        logger.warning("virustotal: rate limited after retries, stopping")
                        break
                    resp.raise_for_status()
                    data = resp.json()

                    for item in data.get("data", []):
                        fqdn = item.get("id", "").strip()
                        if fqdn and fqdn not in seen:
                            seen.add(fqdn)
                            yield fqdn

                    cursor = data.get("meta", {}).get("cursor")
                    url = (_BASE.format(domain=domain) + f"?limit=40&cursor={cursor}") if cursor else None

        except httpx.HTTPStatusError as e:
            logger.error("virustotal: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("virustotal: error querying %s: %s", domain, e)

        logger.info("virustotal: found %d subdomains for %s", len(seen), domain)
