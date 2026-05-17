from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import duplicates, health, logs, pipeline, queue, tracks, ws
from app.api import settings as settings_routes
from app.config import get_settings
from app.db.session import create_tables, get_engine, init_engine
from app.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_engine(settings.database_url)
    create_tables()
    get_engine()
    get_logger("API").info("application_started", env=settings.env)
    yield
    get_logger("API").info("application_stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="DJ Library Pipeline", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(settings_routes.router, prefix="/settings", tags=["settings"])
    app.include_router(queue.router, prefix="/queue", tags=["queue"])
    app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
    app.include_router(ws.router, tags=["websocket"])
    app.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
    app.include_router(duplicates.router, prefix="/duplicates", tags=["duplicates"])
    app.include_router(logs.router, prefix="/logs", tags=["logs"])
    return app


app = create_app()
