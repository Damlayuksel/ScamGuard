"""Domain age via RDAP (layer 2: +30 when the domain is younger than 30 days).

- The IANA bootstrap file (TLD -> RDAP server) is refreshed daily by the worker and kept
  in Redis. Without it, or for TLDs without an RDAP server (e.g. .tr), the check is skipped.
- Only the registered domain is sent to the RDAP server, never a URL.
- Results are cached per domain in Redis for 24 hours, including "unknown".
"""

import json
import logging
from datetime import UTC, datetime, timedelta

import httpx
from redis.exceptions import RedisError

from app import cache

logger = logging.getLogger(__name__)

BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
BOOTSTRAP_KEY = "rdap:bootstrap"
CACHE_PREFIX = "rdap:registered:"
CACHE_TTL_SECONDS = 24 * 60 * 60
NEW_DOMAIN_AGE = timedelta(days=30)
LOOKUP_TIMEOUT_SECONDS = 3.0
_UNKNOWN = "unknown"


def parse_bootstrap(payload: dict) -> dict[str, str]:
    servers: dict[str, str] = {}
    for tlds, urls in payload.get("services", []):
        https_urls = [url for url in urls if url.startswith("https://")]
        if not https_urls:
            continue
        base = https_urls[0] if https_urls[0].endswith("/") else https_urls[0] + "/"
        for tld in tlds:
            servers[tld.lower()] = base
    return servers


async def refresh_bootstrap(client: httpx.AsyncClient) -> int:
    response = await client.get(BOOTSTRAP_URL)
    response.raise_for_status()
    servers = parse_bootstrap(response.json())
    if servers:
        await cache.get_redis().set(BOOTSTRAP_KEY, json.dumps(servers))
    return len(servers)


def registration_date(payload: dict) -> datetime | None:
    for event in payload.get("events", []):
        if event.get("eventAction") == "registration" and event.get("eventDate"):
            try:
                value = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
            except ValueError:
                return None
            return value if value.tzinfo else value.replace(tzinfo=UTC)
    return None


async def _server_for(domain: str) -> str | None:
    raw = await cache.get_redis().get(BOOTSTRAP_KEY)
    if not raw:
        return None
    return json.loads(raw).get(domain.rsplit(".", 1)[-1])


async def _query(server: str, domain: str, transport: httpx.AsyncBaseTransport | None) -> str:
    async with httpx.AsyncClient(
        timeout=LOOKUP_TIMEOUT_SECONDS, follow_redirects=True, transport=transport
    ) as client:
        response = await client.get(
            f"{server}domain/{domain}", headers={"Accept": "application/rdap+json"}
        )
    if response.status_code != 200:
        return _UNKNOWN
    registered = registration_date(response.json())
    return registered.isoformat() if registered else _UNKNOWN


async def registered_at(
    domain: str, transport: httpx.AsyncBaseTransport | None = None
) -> datetime | None:
    """Registration time of a registered domain, or None when it cannot be determined."""
    redis = cache.get_redis()
    try:
        cached = await redis.get(CACHE_PREFIX + domain)
        if cached is None:
            server = await _server_for(domain)
            if server is None:
                return None
            try:
                cached = await _query(server, domain, transport)
            except (httpx.HTTPError, ValueError):
                cached = _UNKNOWN
            await redis.set(CACHE_PREFIX + domain, cached, ex=CACHE_TTL_SECONDS)
    except RedisError:
        logger.warning("Redis unavailable; skipping domain age check")
        return None
    return None if cached == _UNKNOWN else datetime.fromisoformat(cached)


async def is_new_domain(
    domain: str,
    now: datetime | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> bool:
    registered = await registered_at(domain, transport=transport)
    if registered is None:
        return False
    return (now or datetime.now(UTC)) - registered < NEW_DOMAIN_AGE
