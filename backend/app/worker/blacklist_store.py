"""Writes blacklist entries to Postgres and mirrors them into Redis."""

import logging
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta

from sqlalchemy import String, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app import cache, db
from app.models import BlacklistDomain, BlacklistSource
from app.scanner.blacklist import REDIS_KEY

logger = logging.getLogger(__name__)

_BATCH_SIZE = 5000
STALE_AFTER = timedelta(days=7)
FEED_ALIVE_WITHIN = timedelta(days=2)
_FEED_SOURCES = (BlacklistSource.USOM, BlacklistSource.URLHAUS)


def _batches(items: list[str], size: int = _BATCH_SIZE) -> Iterable[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def upsert_hosts(source: BlacklistSource, hosts: Iterable[str]) -> int:
    """Inserts new hosts and refreshes `last_seen` for known ones."""
    ordered = sorted(set(hosts))
    now = datetime.now(UTC)
    async with db.get_sessionmaker()() as session:
        for batch in _batches(ordered):
            stmt = insert(BlacklistDomain).values(
                [{"domain": host, "source": source, "last_seen": now} for host in batch]
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[BlacklistDomain.domain, BlacklistDomain.source],
                set_={"last_seen": stmt.excluded.last_seen},
            )
            await session.execute(stmt)
        await session.commit()
    return len(ordered)


async def has_source(source: BlacklistSource) -> bool:
    async with db.get_sessionmaker()() as session:
        found = await session.scalar(
            select(BlacklistDomain.id).where(BlacklistDomain.source == source).limit(1)
        )
    return found is not None


async def purge_stale(now: datetime | None = None) -> int:
    """Removes feed entries that have not been seen in the source list for 7 days.

    A feed that has not refreshed anything recently is skipped, so a feed outage
    never empties the blacklist.
    """
    now = now or datetime.now(UTC)
    cutoff = now - STALE_AFTER
    removed = 0
    async with db.get_sessionmaker()() as session:
        for source in _FEED_SOURCES:
            latest = await session.scalar(
                select(func.max(BlacklistDomain.last_seen)).where(BlacklistDomain.source == source)
            )
            if latest is None:
                continue
            if latest < now - FEED_ALIVE_WITHIN:
                logger.warning("%s feed has not refreshed recently; skipping purge", source)
                continue
            result = await session.execute(
                delete(BlacklistDomain).where(
                    BlacklistDomain.source == source,
                    BlacklistDomain.last_seen < cutoff,
                )
            )
            removed += result.rowcount or 0
        await session.commit()
    return removed


async def sync_redis() -> int:
    """Rebuilds the Redis hash from Postgres and swaps it in atomically."""
    async with db.get_sessionmaker()() as session:
        rows = (
            await session.execute(
                select(
                    BlacklistDomain.domain,
                    func.string_agg(BlacklistDomain.source, ",", type_=String).label("sources"),
                ).group_by(BlacklistDomain.domain)
            )
        ).all()

    redis = cache.get_redis()
    staging_key = f"{REDIS_KEY}:new"
    await redis.delete(staging_key)
    for start in range(0, len(rows), _BATCH_SIZE):
        chunk = rows[start : start + _BATCH_SIZE]
        await redis.hset(staging_key, mapping={domain: sources for domain, sources in chunk})

    if rows:
        await redis.rename(staging_key, REDIS_KEY)
    else:
        # An empty but existing marker tells lookups that the hash was built.
        async with redis.pipeline(transaction=True) as pipe:
            pipe.delete(REDIS_KEY)
            pipe.hset(REDIS_KEY, "__empty__", "")
            await pipe.execute()
    logger.info("Blacklist synced to Redis: %d host(s)", len(rows))
    return len(rows)


async def add_to_redis(domain: str, source: BlacklistSource) -> None:
    """Adds one host to the live Redis hash without a full rebuild.

    If the hash has not been built yet nothing is written: creating it with a single
    entry would make lookups trust an incomplete hash instead of falling back to Postgres.
    """
    redis = cache.get_redis()
    if not await redis.exists(REDIS_KEY):
        return
    current = await redis.hget(REDIS_KEY, domain)
    sources = set(filter(None, (current or "").split(","))) | {source.value}
    await redis.hset(REDIS_KEY, domain, ",".join(sorted(sources)))
