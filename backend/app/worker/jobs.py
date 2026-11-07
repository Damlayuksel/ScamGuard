"""Worker jobs. Each job logs only counts and exception types, never URLs or content.

External feeds are downloaded once a day (decided 2026-10-15). On worker start a feed is
downloaded only when its data is missing (first install, wiped database or Redis), so
deploys and restarts do not cause extra downloads.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx

from app import cache
from app.config import Settings, get_settings
from app.models import BlacklistSource
from app.scanner import rdap
from app.worker import blacklist_store
from app.worker.sources import fetch_urlhaus, fetch_usom, http_client, parse_entries

logger = logging.getLogger(__name__)

# A full download is ~50 pages of ~10 s each on the production server.
USOM_FETCH_TIMEOUT = timedelta(minutes=30)


@asynccontextmanager
async def _client(client: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if client is not None:
        yield client
        return
    async with http_client() as owned:
        yield owned


async def _store(source: BlacklistSource, entries: list[str]) -> int:
    hosts, skipped = parse_entries(entries)
    if not hosts:
        logger.warning("%s returned no hosts; keeping existing entries", source)
        return 0
    logger.info("%s: storing %d host(s)", source, len(hosts))
    count = await blacklist_store.upsert_hosts(source, hosts)
    await blacklist_store.sync_redis()
    logger.info("%s updated: %d host(s), %d protected host(s) skipped", source, count, skipped)
    return count


async def update_usom(
    settings: Settings | None = None, client: httpx.AsyncClient | None = None
) -> int:
    """Downloads the whole USOM list."""
    settings = settings or get_settings()
    # Each request has its own timeout; this bounds the whole download so a slow or
    # stalled API ends in a logged failure instead of a job that never finishes.
    async with asyncio.timeout(USOM_FETCH_TIMEOUT.total_seconds()), _client(client) as http:
        entries = await fetch_usom(http, settings)
    return await _store(BlacklistSource.USOM, entries)


async def update_urlhaus(
    settings: Settings | None = None, client: httpx.AsyncClient | None = None
) -> int:
    settings = settings or get_settings()
    async with _client(client) as http:
        entries = await fetch_urlhaus(http, settings)
    return await _store(BlacklistSource.URLHAUS, entries)


async def _if_empty(source: BlacklistSource, update: Callable[[], Awaitable[int]]) -> int:
    if await blacklist_store.has_source(source):
        logger.info("%s: entries present, next download in the daily run", source)
        return 0
    return await update()


async def update_usom_if_empty() -> int:
    return await _if_empty(BlacklistSource.USOM, update_usom)


async def update_urlhaus_if_empty() -> int:
    return await _if_empty(BlacklistSource.URLHAUS, update_urlhaus)


async def purge_stale_entries() -> int:
    removed = await blacklist_store.purge_stale()
    await blacklist_store.sync_redis()
    logger.info("Removed %d stale blacklist entries", removed)
    return removed


async def sync_blacklist() -> int:
    return await blacklist_store.sync_redis()


async def refresh_rdap_bootstrap(client: httpx.AsyncClient | None = None) -> int:
    async with _client(client) as http:
        count = await rdap.refresh_bootstrap(http)
    logger.info("RDAP bootstrap refreshed: %d TLD(s)", count)
    return count


async def refresh_rdap_bootstrap_if_missing() -> int:
    # Redis is not persistent, so the bootstrap can be gone after a Redis restart.
    if await cache.get_redis().exists(rdap.BOOTSTRAP_KEY):
        logger.info("RDAP bootstrap present, next refresh in the daily run")
        return 0
    return await refresh_rdap_bootstrap()


JOBS: dict[str, Callable[[], Awaitable[int]]] = {
    "usom": update_usom,
    "urlhaus": update_urlhaus,
    "rdap-bootstrap": refresh_rdap_bootstrap,
    "purge": purge_stale_entries,
    "sync": sync_blacklist,
    "usom-if-empty": update_usom_if_empty,
    "urlhaus-if-empty": update_urlhaus_if_empty,
    "rdap-if-missing": refresh_rdap_bootstrap_if_missing,
}


async def run_job(name: str) -> None:
    """Scheduler entry point: one failing job must not stop the worker."""
    try:
        await JOBS[name]()
    except Exception as exc:
        logger.error("Job %s failed: %s", name, type(exc).__qualname__)
