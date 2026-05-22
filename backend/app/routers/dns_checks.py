import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory, get_session
from app.dns.checker import run_dns_check
from app.models import DnsCheck, DnsCheckResult
from app.schemas import DnsCheckCreate

router = APIRouter(prefix="/api/dns-checks", tags=["dns-checks"])
logger = logging.getLogger(__name__)


def _result_dict(r: DnsCheckResult) -> dict:
    return {
        "id": r.id,
        "check_id": str(r.check_id),
        "fqdn": r.fqdn,
        "check_type": r.check_type,
        "status": r.status,
        "severity": r.severity,
        "title": r.title,
        "detail": r.detail,
        "raw_value": r.raw_value,
        "recommendation": r.recommendation,
        "created_at": r.created_at.isoformat(),
    }


def _check_dict(check: DnsCheck, results: list[DnsCheckResult]) -> dict:
    return {
        "id": str(check.id),
        "scan_id": str(check.scan_id) if check.scan_id else None,
        "fqdns": check.fqdns,
        "status": check.status,
        "created_at": check.created_at.isoformat(),
        "completed_at": check.completed_at.isoformat() if check.completed_at else None,
        "results": [_result_dict(r) for r in results],
    }


@router.post("")
async def create_dns_check(
    body: DnsCheckCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
):
    if not body.fqdns:
        raise HTTPException(400, "fqdns must not be empty")
    check = DnsCheck(scan_id=body.scan_id, fqdns=body.fqdns, status="pending")
    db.add(check)
    await db.commit()
    await db.refresh(check)
    background_tasks.add_task(run_dns_check, check.id, list(body.fqdns))
    return _check_dict(check, [])


@router.get("/by-scan/{scan_id}")
async def get_check_by_scan(scan_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    q = await db.execute(
        select(DnsCheck)
        .where(DnsCheck.scan_id == scan_id)
        .order_by(DnsCheck.created_at.desc())
        .limit(1)
    )
    check = q.scalar_one_or_none()
    if not check:
        raise HTTPException(404, "No DNS check found for this scan")
    rq = await db.execute(
        select(DnsCheckResult)
        .where(DnsCheckResult.check_id == check.id)
        .order_by(DnsCheckResult.id)
    )
    return _check_dict(check, list(rq.scalars()))


@router.get("/{check_id}/stream")
async def stream_dns_check(check_id: uuid.UUID):
    async def gen():
        last_id = 0
        while True:
            async with async_session_factory() as db:
                check = await db.get(DnsCheck, check_id)
                if check is None:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'not found'})}\n\n"
                    return
                rq = await db.execute(
                    select(DnsCheckResult)
                    .where(
                        DnsCheckResult.check_id == check_id,
                        DnsCheckResult.id > last_id,
                    )
                    .order_by(DnsCheckResult.id)
                )
                for r in rq.scalars():
                    last_id = r.id
                    yield f"data: {json.dumps({'type': 'result', **_result_dict(r)})}\n\n"
                if check.status in ("completed", "failed"):
                    yield f"data: {json.dumps({'type': 'done', 'status': check.status})}\n\n"
                    return
            await asyncio.sleep(1)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{check_id}")
async def get_dns_check(check_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    check = await db.get(DnsCheck, check_id)
    if not check:
        raise HTTPException(404, "DNS check not found")
    rq = await db.execute(
        select(DnsCheckResult)
        .where(DnsCheckResult.check_id == check_id)
        .order_by(DnsCheckResult.id)
    )
    return _check_dict(check, list(rq.scalars()))
