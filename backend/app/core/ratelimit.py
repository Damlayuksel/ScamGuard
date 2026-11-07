"""Fixed-window rate limits in Redis. Keys contain only HMAC hashes, never raw IPs or ids.

If Redis is unreachable the limiter fails open (CLAUDE.md), so scanning keeps working.
"""

import logging
from dataclasses import dataclass

from fastapi import HTTPException
from redis.exceptions import RedisError

from app import cache
from app.core.hashing import hmac_sha256

logger = logging.getLogger(__name__)

RATE_LIMIT_MESSAGE = "Çok fazla istek gönderdiniz. Lütfen biraz bekleyip tekrar deneyin."


@dataclass(frozen=True)
class Limit:
    name: str
    max_requests: int
    window_seconds: int


SCAN_PER_IP = Limit("scan:ip", 20, 60)
DOMAIN_REPORT_PER_DEVICE = Limit("domain-report:device", 10, 3600)


async def check(limit: Limit, identity: str) -> None:
    """Counts one request for `identity`; raises HTTP 429 once the window is full."""
    key = f"rl:{limit.name}:{hmac_sha256(identity)}"
    try:
        redis = cache.get_redis()
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, limit.window_seconds, nx=True)
            pipe.ttl(key)
            count, _, ttl = await pipe.execute()
    except RedisError:
        logger.warning("Redis unavailable; rate limit %s not enforced", limit.name)
        return
    if count > limit.max_requests:
        retry_after = ttl if isinstance(ttl, int) and ttl > 0 else limit.window_seconds
        raise HTTPException(
            status_code=429,
            detail=RATE_LIMIT_MESSAGE,
            headers={"Retry-After": str(retry_after)},
        )
