import logging

import aiodns

logger = logging.getLogger(__name__)

_DEFAULT_NAMESERVERS = ["8.8.8.8", "1.1.1.1"]


class DnsResolver:
    def __init__(self, nameservers: list[str] | None = None):
        self._r = aiodns.DNSResolver(
            nameservers=nameservers or _DEFAULT_NAMESERVERS,
            timeout=5,
        )

    async def query_txt(self, name: str) -> list[str]:
        try:
            records = await self._r.query(name, "TXT")
            out: list[str] = []
            for r in records:
                text = r.text
                if isinstance(text, bytes):
                    out.append(text.decode("utf-8", errors="replace"))
                elif isinstance(text, (list, tuple)):
                    parts = [
                        p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p)
                        for p in text
                    ]
                    out.append("".join(parts))
                else:
                    out.append(str(text))
            return out
        except Exception as exc:
            logger.debug("TXT %s: %s", name, exc)
            return []

    async def query_mx(self, name: str) -> list[tuple[int, str]]:
        try:
            records = await self._r.query(name, "MX")
            return sorted((r.priority, r.host) for r in records)
        except Exception as exc:
            logger.debug("MX %s: %s", name, exc)
            return []
