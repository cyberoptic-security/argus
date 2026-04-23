import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.logging_config import configure_logging
from app.routers import config as config_router
from app.routers import scans as scans_router
from app.routers import sources as sources_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("Argus backend starting")
    yield
    await engine.dispose()
    logger.info("Argus backend shut down")


app = FastAPI(title="Argus", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_router.router)
app.include_router(scans_router.router)
app.include_router(sources_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
