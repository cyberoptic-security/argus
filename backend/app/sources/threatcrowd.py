import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)


class ThreatCrowdSource(Source):
    name = "threatcrowd"
    display_name = "ThreatCrowd"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        url = f"http://www.threatcrowd.org/searchApi/v1/domain/report/?domain={domain}"  # 1 req/10s
        logger.info("threatcrowd: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for fqdn in data.get("subdomains") or []:
                    fqdn = str(fqdn).strip()
                    if fqdn and fqdn not in seen:
                        if fqdn.endswith(f".{domain}") or fqdn == domain:
                            seen.add(fqdn)
                            yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("threatcrowd: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("threatcrowd: error querying %s: %s", domain, e)

        logger.info("threatcrowd: found %d subdomains for %s", len(seen), domain)
