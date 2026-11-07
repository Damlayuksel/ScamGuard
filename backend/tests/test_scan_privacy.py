"""KVKK: the scanned message must not reach any persistent store (CLAUDE.md, security 1-3).

A unique marker is placed in the message text and in the URL path. After scanning, every
table, every Redis key and value, all captured logs/stdout/stderr and recently written
temporary files are searched for it.
"""

import logging
import os
import tempfile
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.models import Base
from app.scanner import pipeline
from tests.scan_helpers import seed_blacklist, stub_shortener

_MAX_FILE_BYTES = 1024 * 1024


@pytest.fixture
def marker() -> str:
    # Lower-case and ASCII so normalisation inside the scanner cannot disguise it.
    return f"kvkkmarker{uuid.uuid4().hex}"


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_shortener(monkeypatch, None)


async def _database_dump(session: AsyncSession) -> str:
    parts: list[str] = []
    for table in Base.metadata.sorted_tables:
        rows = (await session.execute(select(table))).all()
        parts.extend(repr(tuple(row)) for row in rows)
    return "\n".join(parts).lower()


async def _redis_dump() -> str:
    redis = cache.get_redis()
    parts: list[str] = []
    async for key in redis.scan_iter("*"):
        parts.append(key)
        kind = await redis.type(key)
        if kind == "string":
            parts.append(str(await redis.get(key)))
        elif kind == "hash":
            parts.append(repr(await redis.hgetall(key)))
        elif kind == "set":
            parts.append(repr(await redis.smembers(key)))
        elif kind == "list":
            parts.append(repr(await redis.lrange(key, 0, -1)))
        elif kind == "zset":
            parts.append(repr(await redis.zrange(key, 0, -1)))
    return "\n".join(parts).lower()


def _recent_files(since: float) -> Iterator[Path]:
    for root in {tempfile.gettempdir(), os.getcwd()}:
        for dirpath, _dirnames, filenames in os.walk(root):
            for name in filenames:
                path = Path(dirpath) / name
                try:
                    if path.stat().st_mtime >= since and path.stat().st_size <= _MAX_FILE_BYTES:
                        yield path
                except OSError:
                    continue


def _assert_not_in_files(marker: str, since: float) -> None:
    for path in _recent_files(since):
        try:
            content = path.read_bytes().lower()
        except OSError:
            continue
        assert marker.encode() not in content, f"message content found in {path}"


async def _assert_nowhere(
    marker: str,
    db_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    since: float,
) -> None:
    assert marker not in await _database_dump(db_session)
    assert marker not in await _redis_dump()
    assert marker not in caplog.text.lower()
    captured = capsys.readouterr()
    assert marker not in captured.out.lower()
    assert marker not in captured.err.lower()
    _assert_not_in_files(marker, since)


async def test_scanned_message_is_not_persisted(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    marker: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    await seed_blacklist([])
    since = time.time() - 1
    text = (
        f"Sayın müşterimiz {marker}, kargonuz teslim edilemedi. IBAN ve doğrulama kodunuzu "
        f"girin: https://ptt-kargo-takip.xyz/{marker}?ref={marker} ve https://bit.ly/{marker}"
    )

    response = await client.post("/api/v1/scan", json={"text": text})

    assert response.status_code == 200
    assert marker not in response.text
    await _assert_nowhere(marker, db_session, caplog, capsys, since)
    # Sanity check: the scan did write its (domain-only) statistics.
    assert "ptt-kargo-takip.xyz" in await _database_dump(db_session)


async def test_rejected_message_is_not_persisted(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    marker: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    since = time.time() - 1

    response = await client.post("/api/v1/scan", json={"text": marker * 200})

    assert response.status_code == 422
    assert marker not in response.text
    await _assert_nowhere(marker, db_session, caplog, capsys, since)


async def test_failed_scan_does_not_leak_message(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    marker: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caplog.set_level(logging.DEBUG)
    since = time.time() - 1

    async def broken_scan(text: str) -> None:
        raise ValueError(f"could not scan {text}")

    monkeypatch.setattr("app.api.scan.scan", broken_scan)

    response = await client.post("/api/v1/scan", json={"text": f"mesaj {marker}"})

    assert response.status_code == 500
    assert marker not in response.text
    assert "ValueError" in caplog.text
    await _assert_nowhere(marker, db_session, caplog, capsys, since)


def test_pipeline_module_has_no_logging_of_text() -> None:
    source = Path(pipeline.__file__).read_text(encoding="utf-8")

    assert "logger" not in source
    assert "print(" not in source
