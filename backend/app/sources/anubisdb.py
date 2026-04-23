import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)


class AnubisDBSource(Source):
    name = "anubisdb"
    display_name = "AnubisDB"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        url = f"https://anubisdb.com/anubis/subdomains/{domain}"
        logger.info("anubisdb: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                subdomains = resp.json()
                if not isinstance(subdomains, list):
                    logger.warning("anubisdb: unexpected response format for %s", domain)
                    return
                for fqdn in subdomains:
                    fqdn = str(fqdn).strip()
                    if fqdn and fqdn not in seen:
                        if fqdn.endswith(f".{domain}") or fqdn == domain:
                            seen.add(fqdn)
                            yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("anubisdb: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("anubisdb: error querying %s: %s", domain, e)

        logger.info("anubisdb: found %d subdomains for %s", len(seen), domain)
