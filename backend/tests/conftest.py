import os
from collections.abc import AsyncIterator
from urllib.parse import urlsplit

# Point the app at the test database/redis before any app module reads settings.
os.environ["ENV"] = "test"
if "TEST_DATABASE_URL" in os.environ:
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
if "TEST_REDIS_URL" in os.environ:
    os.environ["REDIS_URL"] = os.environ["TEST_REDIS_URL"]
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production-use-0123456789")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8081")

_db_name = urlsplit(os.environ.get("DATABASE_URL", "")).path.lstrip("/")
if not _db_name.endswith("_test"):
    raise RuntimeError(
        f"Refusing to run tests against database {_db_name!r}; set TEST_DATABASE_URL "
        "to a database whose name ends with '_test'."
    )

import asyncio  # noqa: E402
from pathlib import Path  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from alembic import command  # noqa: E402
from app.cache import close_redis, get_redis  # noqa: E402
from app.db import dispose_engine, get_engine, get_sessionmaker  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return config


async def run_alembic(action: str, revision: str) -> None:
    # env.py calls asyncio.run(), so it must run outside the test event loop.
    await asyncio.to_thread(getattr(command, action), alembic_config(), revision)


@pytest.fixture(scope="session", autouse=True)
async def _migrated_database() -> None:
    await run_alembic("downgrade", "base")
    await run_alembic("upgrade", "head")


@pytest.fixture(autouse=True)
async def _clean_state(_migrated_database: None) -> AsyncIterator[None]:
    yield
    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    async with get_engine().begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await get_redis().flushdb()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with get_sessionmaker()() as session:
        yield session


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
async def _close_connections() -> AsyncIterator[None]:
    yield
    await dispose_engine()
    await close_redis()
