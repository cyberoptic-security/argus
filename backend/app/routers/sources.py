from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ApiKey
from app.schemas import SourceStatus
from app.sources.registry import SOURCES

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceStatus])
async def list_sources(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ApiKey))
    keys = {k.source for k in result.scalars()}
    return [
        SourceStatus(
            name=src.name,
            display_name=src.display_name,
            requires_key=src.requires_key,
            enabled=not src.requires_key or src.name in keys,
        )
        for src in SOURCES.values()
    ]
