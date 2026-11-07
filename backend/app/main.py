from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.cache import close_redis
from app.config import Settings, get_settings
from app.core.errors import SafeErrorMiddleware, register_exception_handlers
from app.core.logging import configure_logging
from app.db import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()
    await close_redis()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    app = FastAPI(
        title="ScamShield API",
        version="0.1.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    # Middleware added last runs first: CORS wraps the error middleware so 500s keep CORS headers.
    app.add_middleware(SafeErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Device-Id"],
        allow_credentials=False,
    )

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
