from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from app.db import get_engine
from app.models import Base
from tests.conftest import run_alembic

PHASE1_TABLES = {"blacklist_domains", "domain_reports", "scan_stats"}


def _table_names(connection: Connection) -> set[str]:
    return set(inspect(connection).get_table_names())


def _schema_diff(connection: Connection) -> list[object]:
    return compare_metadata(MigrationContext.configure(connection), Base.metadata)


async def test_downgrade_and_upgrade_roundtrip() -> None:
    await run_alembic("downgrade", "base")
    async with get_engine().connect() as conn:
        assert not PHASE1_TABLES & await conn.run_sync(_table_names)

    await run_alembic("upgrade", "head")
    async with get_engine().connect() as conn:
        assert PHASE1_TABLES <= await conn.run_sync(_table_names)


async def test_models_match_migrations() -> None:
    async with get_engine().connect() as conn:
        assert await conn.run_sync(_schema_diff) == []
