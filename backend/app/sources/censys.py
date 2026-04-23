import logging
from typing import AsyncIterator

import httpx

from app.sources.base import Source

logger = logging.getLogger(__name__)

_CERTS_URL = "https://search.censys.io/api/v2/certificates/search"


class CensysSource(Source):
    name = "censys"
    display_name = "Censys"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key or not api_secret:
            logger.warning("censys: API ID and secret both required, skipping")
            return

        logger.info("censys: querying certificates for %s", domain)
        seen: set[str] = set()
        auth = (api_key, api_secret)

        try:
            async with httpx.AsyncClient(timeout=30, auth=auth) as client:
                cursor = None
                pages = 0
                while pages < 5:  # cap at 5 pages to stay within free quota
                    params: dict = {"q": f"parsed.names: {domain}", "per_page": 100, "fields": "parsed.names"}
                    if cursor:
                        params["cursor"] = cursor

                    resp = await client.get(_CERTS_URL, params=params)
                    if resp.status_code == 429:
                        logger.warning("censys: rate limited (250 queries/month on free tier)")
                        break
                    resp.raise_for_status()
                    data = resp.json()

                    for hit in data.get("result", {}).get("hits", []):
                        for name in hit.get("parsed", {}).get("names", []):
                            name = name.strip().lstrip("*.")
                            if name and name not in seen:
                                if name.endswith(f".{domain}") or name == domain:
                                    seen.add(name)
                                    yield name

                    links = data.get("result", {}).get("links", {})
                    cursor = links.get("next")
                    if not cursor:
                        break
                    pages += 1

        except httpx.HTTPStatusError as e:
            logger.error("censys: HTTP %s for %s", e.response.status_code, domain)
        except Exception as e:
            logger.error("censys: error querying %s: %s", domain, e)

        logger.info("censys: found %d subdomains for %s", len(seen), domain)
