"""Local blacklist lookups (layer 1).

Redis holds a hash `blacklist:hosts` (hostname -> comma separated sources) built by the
worker from the `blacklist_domains` table. When Redis is unreachable or the hash has not
been built yet, lookups fall back to Postgres.
"""

import logging
from dataclasses import dataclass

from redis.exceptions import RedisError
from sqlalchemy import select

from app import cache, db
from app.models import BlacklistDomain, BlacklistSource
from app.scanner.hosts import candidate_hosts

logger = logging.getLogger(__name__)

REDIS_KEY = "blacklist:hosts"


@dataclass(frozen=True)
class BlacklistHit:
    domain: str
    sources: tuple[BlacklistSource, ...]


def _parse_sources(raw: str) -> tuple[BlacklistSource, ...]:
    return tuple(sorted(BlacklistSource(value) for value in raw.split(",") if value))


async def _lookup_redis(candidates: list[str]) -> tuple[bool, BlacklistHit | None]:
    """Returns (answered, hit). `answered` is False when Redis cannot be trusted."""
    try:
        redis = cache.get_redis()
        async with redis.pipeline(transaction=False) as pipe:
            pipe.exists(REDIS_KEY)
            pipe.hmget(REDIS_KEY, candidates)
            exists, values = await pipe.execute()
    except RedisError:
        logger.warning("Redis unavailable; using database for blacklist lookup")
        return False, None
    if not exists:
        return False, None
    for candidate, value in zip(candidates, values, strict=True):
        if value:
            return True, BlacklistHit(domain=candidate, sources=_parse_sources(value))
    return True, None


async def _lookup_db(candidates: list[str]) -> BlacklistHit | None:
    async with db.get_sessionmaker()() as session:
        rows = (
            await session.execute(
                select(BlacklistDomain.domain, BlacklistDomain.source).where(
                    BlacklistDomain.domain.in_(candidates)
                )
            )
        ).all()
    found: dict[str, set[BlacklistSource]] = {}
    for domain, source in rows:
        found.setdefault(domain, set()).add(source)
    for candidate in candidates:
        if candidate in found:
            return BlacklistHit(domain=candidate, sources=tuple(sorted(found[candidate])))
    return None


async def lookup(host: str) -> BlacklistHit | None:
    """Checks the host and its parent domains (down to the registered domain)."""
    candidates = candidate_hosts(host)
    answered, hit = await _lookup_redis(candidates)
    if not answered:
        return await _lookup_db(candidates)
    return hit
