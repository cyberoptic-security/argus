import asyncio
import csv
import io
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_session
from app.models import ApiKey, Scan, Subdomain, Wordlist
from app.schemas import ScanCreate, ScanListResponse, ScanResponse, SubdomainListResponse

router = APIRouter(prefix="/api/scans", tags=["scans"])
logger = logging.getLogger(__name__)


async def _run_scan(scan_id: str) -> None:
    scan_uuid = uuid.UUID(scan_id)

    async with async_session_factory() as session:
        result = await session.execute(select(Scan).where(Scan.id == scan_uuid))
        scan = result.scalar_one_or_none()
        if not scan:
            logger.error("scan %s not found in background task", scan_id)
            return

        domains = list(scan.domains)
        source_names = list(scan.sources)

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("scan %s: started for domains %s using sources %s", scan_id, domains, source_names)

        key_result = await session.execute(select(ApiKey))
        api_keys = {k.source: (k.api_key, k.api_secret) for k in key_result.scalars()}

        wordlist_content: str | None = None
        if "brute" in source_names:
            wordlist_id = scan.options.get("wordlist_id")
            if wordlist_id:
                wl_result = await session.execute(select(Wordlist).where(Wordlist.id == wordlist_id))
                wl = wl_result.scalar_one_or_none()
                wordlist_content = wl.content if wl else None

        brute_resolvers: list[str] = scan.options.get("dns_resolvers") or ["8.8.8.8", "1.1.1.1"]
        brute_concurrency: int = scan.options.get("brute_concurrency", 100)

    from app.sources.registry import SOURCES  # avoid circular import

    async def run_source(source_name: str) -> int:
        src = SOURCES.get(source_name)
        if not src:
            logger.warning("scan %s: unknown source %s, skipping", scan_id, source_name)
            return 0

        api_key, api_secret = api_keys.get(source_name, (None, None))
        logger.info("scan %s: source %s starting", scan_id, source_name)
        found = 0
        cancelled = False

        try:
            for domain in domains:
                if cancelled:
                    break
                async with async_session_factory() as s:
                    async for fqdn in src.run(domain, api_key, api_secret):
                        if found % 20 == 0:
                            status_result = await s.execute(
                                select(Scan.status).where(Scan.id == scan_uuid)
                            )
                            current_status = status_result.scalar_one_or_none()
                            if current_status in (None, "cancelled"):
                                logger.info("scan %s: stopping source %s (status=%s)", scan_id, source_name, current_status)
                                cancelled = True
                                break

                        existing = await s.execute(
                            select(Subdomain).where(
                                Subdomain.scan_id == scan_uuid,
                                Subdomain.fqdn == fqdn,
                            )
                        )
                        sub = existing.scalar_one_or_none()
                        if sub:
                            if source_name not in sub.sources:
                                sub.sources = sub.sources + [source_name]
                        else:
                            s.add(Subdomain(scan_id=scan_uuid, fqdn=fqdn, domain=domain, sources=[source_name]))
                        await s.commit()
                        found += 1
        except Exception as e:
            logger.error("scan %s: source %s error: %s", scan_id, source_name, e, exc_info=True)

        logger.info("scan %s: source %s finished, found %d subdomains", scan_id, source_name, found)
        return found

    async def run_brute_force() -> int:
        from app.brute.resolver import bruteforce
        from app.brute.wordlist import load_words

        words = load_words(wordlist_content)
        logger.info("scan %s: brute force starting with %d words", scan_id, len(words))
        found = 0
        cancelled = False

        for domain in domains:
            if cancelled:
                break
            async with async_session_factory() as s:
                async for fqdn, ips in bruteforce(domain, words, brute_resolvers, brute_concurrency):
                    if found % 20 == 0:
                        status_result = await s.execute(select(Scan.status).where(Scan.id == scan_uuid))
                        if status_result.scalar_one_or_none() in (None, "cancelled"):
                            logger.info("scan %s: cancellation detected in brute force", scan_id)
                            cancelled = True
                            break

                    existing = await s.execute(
                        select(Subdomain).where(Subdomain.scan_id == scan_uuid, Subdomain.fqdn == fqdn)
                    )
                    sub = existing.scalar_one_or_none()
                    if sub:
                        if "brute" not in sub.sources:
                            sub.sources = sub.sources + ["brute"]
                        if ips and not sub.ip_addresses:
                            sub.ip_addresses = ips
                    else:
                        s.add(Subdomain(scan_id=scan_uuid, fqdn=fqdn, domain=domain, sources=["brute"], ip_addresses=ips))
                    await s.commit()
                    found += 1

        logger.info("scan %s: brute force finished, found %d subdomains", scan_id, found)
        return found

    passive_tasks = [run_source(name) for name in source_names if name != "brute"]
    all_tasks = passive_tasks + ([run_brute_force()] if "brute" in source_names else [])
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
    total = sum(r for r in results if isinstance(r, int))

    async with async_session_factory() as session:
        result = await session.execute(select(Scan).where(Scan.id == scan_uuid))
        scan = result.scalar_one_or_none()
        if scan is None:
            logger.info("scan %s: row deleted before completion, discarding", scan_id)
            return
        if scan.status != "cancelled":
            scan.status = "completed"
        scan.completed_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("scan %s: %s, %d total subdomains discovered", scan_id, scan.status, total)


@router.post("", response_model=ScanResponse, status_code=201)
async def create_scan(
    body: ScanCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    scan = Scan(
        name=body.name,
        domains=body.domains,
        sources=body.sources,
        options=body.options,
    )
    session.add(scan)
    await session.commit()
    await session.refresh(scan)
    background_tasks.add_task(_run_scan, str(scan.id))
    logger.info("scan %s: created", scan.id)
    return scan


@router.get("", response_model=ScanListResponse)
async def list_scans(
    offset: int = 0,
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session),
):
    total = (await session.execute(select(func.count()).select_from(Scan))).scalar_one()
    result = await session.execute(
        select(Scan).order_by(Scan.created_at.desc()).offset(offset).limit(limit)
    )
    return ScanListResponse(items=result.scalars().all(), total=total)


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(scan_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/{scan_id}/cancel", status_code=204)
async def cancel_scan(scan_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status not in ("pending", "running"):
        raise HTTPException(status_code=409, detail=f"Scan already {scan.status}")
    scan.status = "cancelled"
    await session.commit()
    logger.info("scan %s: cancellation requested", scan_id)


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(scan_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status in ("pending", "running"):  # background task checks status; delete handles commit
        scan.status = "cancelled"
    await session.delete(scan)
    await session.commit()
    logger.info("scan %s: deleted", scan_id)


@router.get("/{scan_id}/stream")
async def stream_scan(scan_id: uuid.UUID, request: Request):
    async def event_generator():
        last_id = 0
        while True:
            if await request.is_disconnected():
                async with async_session_factory() as s:
                    result = await s.execute(select(Scan).where(Scan.id == scan_id))
                    scan = result.scalar_one_or_none()
                    if scan and scan.status == "running":
                        scan.status = "cancelled"
                        await s.commit()
                        logger.info("scan %s: SSE client disconnected, scan cancelled", scan_id)
                return

            async with async_session_factory() as session:
                status_result = await session.execute(
                    select(Scan.status).where(Scan.id == scan_id)
                )
                status = status_result.scalar_one_or_none()

                if status is None:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'scan not found'})}\n\n"
                    return

                sub_result = await session.execute(
                    select(Subdomain)
                    .where(Subdomain.scan_id == scan_id, Subdomain.id > last_id)
                    .order_by(Subdomain.id)
                )
                for sub in sub_result.scalars():
                    last_id = sub.id
                    event = {
                        "type": "subdomain",
                        "fqdn": sub.fqdn,
                        "source": sub.sources[0] if sub.sources else None,
                        "sources": sub.sources,
                        "ips": sub.ip_addresses,
                        "ts": int(sub.created_at.timestamp()),
                    }
                    yield f"data: {json.dumps(event)}\n\n"

                if status in ("completed", "cancelled", "failed"):
                    count_result = await session.execute(
                        select(func.count())
                        .select_from(Subdomain)
                        .where(Subdomain.scan_id == scan_id)
                    )
                    total = count_result.scalar_one()
                    yield f"data: {json.dumps({'type': 'done', 'total': total, 'status': status})}\n\n"
                    return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{scan_id}/results", response_model=SubdomainListResponse)
async def get_scan_results(
    scan_id: uuid.UUID,
    offset: int = 0,
    limit: int = Query(default=100, le=1000),
    source: str | None = None,
    search: str | None = None,
    has_ip: bool | None = None,
    session: AsyncSession = Depends(get_session),
):
    base = select(Subdomain).where(Subdomain.scan_id == scan_id)
    count_base = select(func.count()).select_from(Subdomain).where(Subdomain.scan_id == scan_id)

    if source:
        base = base.where(Subdomain.sources.contains([source]))
        count_base = count_base.where(Subdomain.sources.contains([source]))
    if search:
        base = base.where(Subdomain.fqdn.ilike(f"%{search}%"))
        count_base = count_base.where(Subdomain.fqdn.ilike(f"%{search}%"))
    if has_ip is True:
        base = base.where(Subdomain.ip_addresses != None)  # noqa: E711
        count_base = count_base.where(Subdomain.ip_addresses != None)  # noqa: E711
    elif has_ip is False:
        base = base.where(Subdomain.ip_addresses == None)  # noqa: E711
        count_base = count_base.where(Subdomain.ip_addresses == None)  # noqa: E711

    total = (await session.execute(count_base)).scalar_one()
    result = await session.execute(base.order_by(Subdomain.domain, Subdomain.fqdn).offset(offset).limit(limit))
    return SubdomainListResponse(items=result.scalars().all(), total=total)


@router.get("/{scan_id}/export")
async def export_scan(
    scan_id: uuid.UUID,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Subdomain).where(Subdomain.scan_id == scan_id).order_by(Subdomain.domain, Subdomain.fqdn)
    )
    subs = result.scalars().all()

    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["domain", "fqdn", "ip_addresses", "sources"])
        for s in subs:
            writer.writerow([s.domain or "", s.fqdn, ",".join(s.ip_addresses or []), ",".join(s.sources)])
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.csv"},
        )

    data = [
        {"domain": s.domain, "fqdn": s.fqdn, "ip_addresses": s.ip_addresses, "sources": s.sources}
        for s in subs
    ]
    return StreamingResponse(
        iter([json.dumps(data, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=scan-{scan_id}.json"},
    )
