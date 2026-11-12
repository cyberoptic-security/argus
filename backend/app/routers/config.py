import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from datetime import datetime, timezone

from app.database import get_session
from app.models import ApiKey, Wordlist
from app.schemas import (
    ApiKeyExport,
    ApiKeyExportEntry,
    ApiKeyImportResult,
    ApiKeyResponse,
    ApiKeySet,
    WordlistResponse,
)
from app.sources.registry import SOURCES

router = APIRouter(prefix="/api/config", tags=["config"])
logger = logging.getLogger(__name__)


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ApiKey))
    keys = {k.source: k for k in result.scalars()}
    return [
        ApiKeyResponse(
            source=name,
            has_key=name in keys,
            has_secret=bool(keys[name].api_secret) if name in keys else False,
        )
        for name, src in SOURCES.items()
        if src.requires_key
    ]


@router.get("/api-keys/export", response_model=ApiKeyExport)
async def export_api_keys(session: AsyncSession = Depends(get_session)):
    """Export all stored API keys (plaintext) as JSON for backup/transfer."""
    result = await session.execute(select(ApiKey).order_by(ApiKey.source))
    keys = result.scalars().all()
    logger.info("exported %d api keys", len(keys))
    return ApiKeyExport(
        version=1,
        exported_at=datetime.now(timezone.utc),
        keys=[
            ApiKeyExportEntry(source=k.source, api_key=k.api_key, api_secret=k.api_secret)
            for k in keys
        ],
    )


@router.post("/api-keys/import", response_model=ApiKeyImportResult)
async def import_api_keys(
    body: ApiKeyExport, session: AsyncSession = Depends(get_session)
):
    """Import API keys from a previous export. Upserts known sources, skips unknown."""
    result = await session.execute(select(ApiKey))
    existing = {k.source: k for k in result.scalars()}

    imported: list[str] = []
    skipped: list[str] = []
    for entry in body.keys:
        if entry.source not in SOURCES or not entry.api_key:
            skipped.append(entry.source)
            continue
        key = existing.get(entry.source)
        if key:
            key.api_key = entry.api_key
            key.api_secret = entry.api_secret
        else:
            session.add(
                ApiKey(
                    source=entry.source,
                    api_key=entry.api_key,
                    api_secret=entry.api_secret,
                )
            )
        imported.append(entry.source)

    await session.commit()
    logger.info(
        "imported %d api keys (%d skipped)", len(imported), len(skipped)
    )
    return ApiKeyImportResult(imported=imported, skipped=skipped)


@router.put("/api-keys/{source}", response_model=ApiKeyResponse)
async def set_api_key(
    source: str, body: ApiKeySet, session: AsyncSession = Depends(get_session)
):
    if source not in SOURCES:
        raise HTTPException(status_code=404, detail="Unknown source")
    result = await session.execute(select(ApiKey).where(ApiKey.source == source))
    key = result.scalar_one_or_none()
    if key:
        key.api_key = body.api_key
        key.api_secret = body.api_secret
    else:
        key = ApiKey(source=source, api_key=body.api_key, api_secret=body.api_secret)
        session.add(key)
    await session.commit()
    logger.info("api key set for source %s", source)
    return ApiKeyResponse(source=source, has_key=True, has_secret=bool(body.api_secret))


@router.delete("/api-keys/{source}", status_code=204)
async def delete_api_key(source: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ApiKey).where(ApiKey.source == source))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    await session.delete(key)
    await session.commit()
    logger.info("api key deleted for source %s", source)


@router.get("/wordlists", response_model=list[WordlistResponse])
async def list_wordlists(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Wordlist).order_by(Wordlist.created_at.desc()))
    return result.scalars().all()


@router.post("/wordlists", response_model=WordlistResponse, status_code=201)
async def upload_wordlist(
    name: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    content = (await file.read()).decode("utf-8", errors="ignore")
    entries = [line.strip() for line in content.splitlines() if line.strip()]
    wordlist = Wordlist(name=name, entry_count=len(entries), content="\n".join(entries))
    session.add(wordlist)
    await session.commit()
    await session.refresh(wordlist)
    logger.info("wordlist '%s' uploaded with %d entries", name, len(entries))
    return wordlist


@router.delete("/wordlists/{wordlist_id}", status_code=204)
async def delete_wordlist(wordlist_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Wordlist).where(Wordlist.id == wordlist_id))
    wordlist = result.scalar_one_or_none()
    if not wordlist:
        raise HTTPException(status_code=404, detail="Wordlist not found")
    await session.delete(wordlist)
    await session.commit()
