import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)

_BASE = "https://api.securitytrails.com/v1/domain/{domain}/subdomains"


class SecurityTrailsSource(Source):
    name = "securitytrails"
    display_name = "SecurityTrails"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("securitytrails: no API key configured, skipping")
            return

        headers = {"APIKEY": api_key}
        url = _BASE.format(domain=domain)
        logger.info("securitytrails: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 429:
                    logger.warning("securitytrails: rate limited")
                    return
                resp.raise_for_status()
                data = resp.json()
                for sub in data.get("subdomains", []):
                    fqdn = f"{sub}.{domain}".strip()
                    if fqdn and fqdn not in seen:
                        seen.add(fqdn)
                        yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("securitytrails: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("securitytrails: error querying %s: %s", domain, e)

        logger.info("securitytrails: found %d subdomains for %s", len(seen), domain)
