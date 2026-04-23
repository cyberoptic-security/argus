import asyncio
import logging
from typing import AsyncIterator

from app.sources.base import Source

logger = logging.getLogger(__name__)


class NetlasSource(Source):
    name = "netlas"
    display_name = "Netlas"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("netlas: no API key configured, skipping")
            return

        logger.info("netlas: querying for %s", domain)

        def _query() -> list[str]:
            import netlas
            api = netlas.Netlas(api_key=api_key)
            fqdns = []
            seen: set[str] = set()
            query = f"domain:*.{domain}"
            try:
                for page in api.query(query=query, datatype="domain", page=0):
                    for item in page.get("items", []):
                        name = item.get("data", {}).get("domain", "").strip()
                        if name and name not in seen:
                            if name.endswith(f".{domain}") or name == domain:
                                seen.add(name)
                                fqdns.append(name)
            except Exception as e:
                raise e
            return fqdns

        try:
            loop = asyncio.get_running_loop()
            fqdns = await loop.run_in_executor(None, _query)
            for fqdn in fqdns:
                yield fqdn
            logger.info("netlas: found %d subdomains for %s", len(fqdns), domain)
        except Exception as e:
            logger.error("netlas: error querying %s: %s", domain, e)
