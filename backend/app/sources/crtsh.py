import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)


class CrtShSource(Source):
    name = "crtsh"
    display_name = "crt.sh"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        logger.info("crt.sh: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                for entry in resp.json():
                    for name_value in entry.get("name_value", "").splitlines():
                        fqdn = name_value.strip().lstrip("*.")
                        if fqdn and (fqdn.endswith(f".{domain}") or fqdn == domain):
                            if fqdn not in seen:
                                seen.add(fqdn)
                                yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("crt.sh: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("crt.sh: error querying %s: %s", domain, e)

        logger.info("crt.sh: found %d unique subdomains for %s", len(seen), domain)
