import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)


class BufferOverSource(Source):
    name = "bufferover"
    display_name = "BufferOver TLS"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        url = f"https://tls.bufferover.run/dns?q=.{domain}"
        logger.info("bufferover: querying for %s", domain)
        seen: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for entry in data.get("Results") or []:
                    parts = entry.split(",")
                    if len(parts) < 4:
                        continue
                    fqdn = parts[3].strip()
                    if fqdn and fqdn not in seen:
                        if fqdn.endswith(f".{domain}") or fqdn == domain:
                            seen.add(fqdn)
                            yield fqdn
        except httpx.HTTPStatusError as e:
            logger.error("bufferover: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("bufferover: error querying %s: %s", domain, e)

        logger.info("bufferover: found %d subdomains for %s", len(seen), domain)
