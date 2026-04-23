import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source
from app.sources.utils import get_with_backoff

logger = logging.getLogger(__name__)

_BASE = "https://urlscan.io/api/v1/search/"


class UrlScanSource(Source):
    name = "urlscan"
    display_name = "urlscan.io"
    requires_key = False

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        logger.info("urlscan: querying for %s", domain)
        seen: set[str] = set()
        params = {"q": f"domain.{domain}", "size": "100"}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                while True:
                    resp = await get_with_backoff(client, _BASE, params=params)
                    if resp.status_code == 429:
                        logger.warning("urlscan: rate limited after retries for %s", domain)
                        break
                    resp.raise_for_status()
                    data = resp.json()

                    for result in data.get("results", []):
                        fqdn = result.get("page", {}).get("domain", "").strip()
                        if fqdn and fqdn not in seen:
                            if fqdn.endswith(f".{domain}") or fqdn == domain:
                                seen.add(fqdn)
                                yield fqdn

                    if not data.get("has_more"):
                        break

                    results = data.get("results", [])
                    if not results:
                        break
                    sort = results[-1].get("sort")
                    if not sort:
                        break
                    params = {"q": f"domain.{domain}", "size": "100", "search_after": ",".join(str(x) for x in sort)}

        except httpx.HTTPStatusError as e:
            logger.error("urlscan: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("urlscan: error querying %s: %s", domain, e)

        logger.info("urlscan: found %d subdomains for %s", len(seen), domain)
