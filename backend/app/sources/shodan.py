import asyncio
import logging
from typing import AsyncIterator

from app.sources.base import Source

logger = logging.getLogger(__name__)


class ShodanSource(Source):
    name = "shodan"
    display_name = "Shodan"
    requires_key = True

    async def run(
        self,
        domain: str,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> AsyncIterator[str]:
        if not api_key:
            logger.warning("shodan: no API key configured, skipping")
            return

        logger.info("shodan: querying for %s", domain)

        def _query() -> list[str]:
            import shodan as shodan_lib
            api = shodan_lib.Shodan(api_key)
            result = api.dns.domain_info(domain, type="A", page=1)
            fqdns = []
            for sub in result.get("subdomains", []):
                fqdns.append(f"{sub}.{domain}")
            seen = set(fqdns)
            for record in result.get("data", []):
                sub = record.get("subdomain", "")
                if sub:
                    fqdn = f"{sub}.{domain}"
                    if fqdn not in seen:
                        seen.add(fqdn)
                        fqdns.append(fqdn)
            return fqdns

        try:
            loop = asyncio.get_running_loop()
            fqdns = await loop.run_in_executor(None, _query)
            for fqdn in fqdns:
                yield fqdn
            logger.info("shodan: found %d subdomains for %s", len(fqdns), domain)
        except Exception as e:
            logger.error("shodan: error querying %s: %s", domain, e)
