import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)

_BASE = "https://leakix.net/api/subdomains/{domain}"


class LeakIXSource(Source):
    name = "leakix"
    display_name = "LeakIX"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("leakix: no API key configured, skipping")
            return

        headers = {"api-key": api_key, "Accept": "application/json"}
        url = _BASE.format(domain=domain)
        logger.info("leakix: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 429:
                    logger.warning("leakix: rate limited")
                    return
                resp.raise_for_status()
                data = resp.json()
                for entry in data if isinstance(data, list) else []:
                    fqdn = entry.get("subdomain", "").strip()
                    if fqdn and fqdn not in seen:
                        if fqdn.endswith(f".{domain}") or fqdn == domain:
                            seen.add(fqdn)
                            yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("leakix: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("leakix: error querying %s: %s", domain, e)

        logger.info("leakix: found %d subdomains for %s", len(seen), domain)
