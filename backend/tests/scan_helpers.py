"""Shared helpers for scan tests: no test ever reaches the real network."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.models import BlacklistSource
from app.scanner import pipeline
from app.scanner.safe_fetch import FetchError, FetchResult
from app.worker import blacklist_store

FIXTURES = Path(__file__).parent / "fixtures" / "messages"


def load_messages(name: str) -> list[dict[str, Any]]:
    with (FIXTURES / name).open(encoding="utf-8") as fh:
        return json.load(fh)["messages"]


def stub_shortener(monkeypatch: pytest.MonkeyPatch, final_url: str | None) -> None:
    """Makes every shortener resolve to `final_url` (None = cannot be resolved)."""

    async def fake_resolve(_url: str, **_kwargs: object) -> FetchResult:
        if final_url is None:
            return FetchResult(final_url=None, error=FetchError.NETWORK)
        return FetchResult(final_url=final_url, hops=[final_url])

    monkeypatch.setattr(pipeline, "resolve_redirects", fake_resolve)


async def seed_blacklist(hosts: list[str]) -> None:
    if hosts:
        await blacklist_store.upsert_hosts(BlacklistSource.USOM, hosts)
    await blacklist_store.sync_redis()
