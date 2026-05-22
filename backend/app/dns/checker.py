import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import update

from app.database import async_session_factory
from app.dns.analyzers import (
    DKIM_COMMON_SELECTORS,
    Finding,
    analyze_dkim,
    analyze_dmarc,
    analyze_mx,
    analyze_spf,
)
from app.dns.records import DnsResolver
from app.models import DnsCheck, DnsCheckResult

logger = logging.getLogger(__name__)

_KNOWN_SLD_TLDS = {
    "co.uk", "org.uk", "me.uk", "net.uk", "ltd.uk", "plc.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.nz", "net.nz", "org.nz", "govt.nz",
    "co.jp", "or.jp", "ne.jp", "ac.jp",
    "com.br", "net.br", "org.br", "gov.br",
    "co.in", "net.in", "org.in", "gov.in",
    "co.za", "org.za", "net.za",
}


def _root_domain(fqdn: str) -> str:
    parts = fqdn.rstrip(".").split(".")
    if len(parts) <= 2:
        return fqdn
    if ".".join(parts[-2:]) in _KNOWN_SLD_TLDS and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


async def _check_one(
    fqdn: str,
    resolver: DnsResolver,
    root_dmarc_cache: dict[str, list[str]],
) -> list[Finding]:
    root = _root_domain(fqdn)
    is_root = fqdn == root

    # Launch all DNS queries in parallel
    txt_t = asyncio.create_task(resolver.query_txt(fqdn))
    mx_t = asyncio.create_task(resolver.query_mx(fqdn))
    own_dmarc_t = asyncio.create_task(resolver.query_txt(f"_dmarc.{fqdn}"))
    dkim_ts = [
        asyncio.create_task(resolver.query_txt(f"{sel}._domainkey.{fqdn}"))
        for sel in DKIM_COMMON_SELECTORS
    ]

    txt, mx, own_dmarc = await asyncio.gather(txt_t, mx_t, own_dmarc_t)
    dkim_results = await asyncio.gather(*dkim_ts, return_exceptions=True)

    found_selectors = [
        DKIM_COMMON_SELECTORS[i]
        for i, r in enumerate(dkim_results)
        if not isinstance(r, Exception)
        and any(x.lower().startswith("v=dkim1") for x in (r or []))
    ]

    root_dmarc = root_dmarc_cache.get(root, [])
    has_mx = bool(mx)

    findings: list[Finding] = []
    findings += analyze_spf(fqdn, txt, has_mx)
    findings += analyze_dmarc(fqdn, own_dmarc, root, root_dmarc, is_root)
    findings += analyze_mx(fqdn, mx)
    findings += analyze_dkim(fqdn, found_selectors)
    return findings


async def run_dns_check(check_id: uuid.UUID, fqdns: list[str]) -> None:
    logger.info("dns-check %s: starting for %d FQDNs", check_id, len(fqdns))
    resolver = DnsResolver()

    # Pre-fetch root DMARC for all unique root domains in one parallel batch
    root_domains = list({_root_domain(f) for f in fqdns})
    root_dmarc_raw = await asyncio.gather(
        *[resolver.query_txt(f"_dmarc.{rd}") for rd in root_domains]
    )
    root_dmarc_cache: dict[str, list[str]] = dict(zip(root_domains, root_dmarc_raw))

    async with async_session_factory() as db:
        await db.execute(
            update(DnsCheck).where(DnsCheck.id == check_id).values(status="running")
        )
        await db.commit()

    sem = asyncio.Semaphore(10)

    async def check_and_save(fqdn: str) -> list[Finding]:
        async with sem:
            try:
                found = await _check_one(fqdn, resolver, root_dmarc_cache)
                async with async_session_factory() as db:
                    db.add_all([
                        DnsCheckResult(
                            check_id=check_id,
                            fqdn=f.fqdn,
                            check_type=f.check_type,
                            status=f.status,
                            severity=f.severity,
                            title=f.title,
                            detail=f.detail,
                            raw_value=f.raw_value,
                            recommendation=f.recommendation,
                        )
                        for f in found
                    ])
                    await db.commit()
                logger.info("dns-check %s: %s — %d findings", check_id, fqdn, len(found))
                return found
            except Exception:
                logger.exception("dns-check %s: error checking %s", check_id, fqdn)
                return []

    try:
        all_results = await asyncio.gather(*[check_and_save(f) for f in fqdns])
        total = sum(len(r) for r in all_results)
        async with async_session_factory() as db:
            await db.execute(
                update(DnsCheck).where(DnsCheck.id == check_id).values(
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
        logger.info("dns-check %s: completed — %d total findings", check_id, total)
    except Exception:
        logger.exception("dns-check %s: fatal error", check_id)
        async with async_session_factory() as db:
            await db.execute(
                update(DnsCheck).where(DnsCheck.id == check_id).values(status="failed")
            )
            await db.commit()
