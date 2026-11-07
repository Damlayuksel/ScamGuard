import json
from datetime import UTC, datetime

import httpx
import respx

from app import cache
from app.scanner import rdap
from app.worker import jobs

BOOTSTRAP = {
    "services": [
        [["com", "net"], ["https://rdap.verisign.example/com/v1/"]],
        [["xyz"], ["http://insecure.example/", "https://rdap.centralnic.example/xyz"]],
    ]
}
NOW = datetime(2026, 10, 14, tzinfo=UTC)


def _rdap_domain(registered: str) -> dict[str, object]:
    return {"events": [{"eventAction": "registration", "eventDate": registered}]}


async def _store_bootstrap() -> None:
    await cache.get_redis().set(rdap.BOOTSTRAP_KEY, json.dumps(rdap.parse_bootstrap(BOOTSTRAP)))


def test_parse_bootstrap_prefers_https_and_adds_slash() -> None:
    assert rdap.parse_bootstrap(BOOTSTRAP) == {
        "com": "https://rdap.verisign.example/com/v1/",
        "net": "https://rdap.verisign.example/com/v1/",
        "xyz": "https://rdap.centralnic.example/xyz/",
    }


@respx.mock
async def test_bootstrap_job_stores_servers() -> None:
    respx.get(rdap.BOOTSTRAP_URL).mock(return_value=httpx.Response(200, json=BOOTSTRAP))

    assert await jobs.refresh_rdap_bootstrap() == 3
    assert "xyz" in json.loads(await cache.get_redis().get(rdap.BOOTSTRAP_KEY))


@respx.mock
async def test_new_domain_is_detected_and_cached() -> None:
    await _store_bootstrap()
    route = respx.get("https://rdap.centralnic.example/xyz/domain/fresh-scam.xyz").mock(
        return_value=httpx.Response(200, json=_rdap_domain("2026-10-01T10:00:00Z"))
    )

    assert await rdap.is_new_domain("fresh-scam.xyz", now=NOW)
    assert await rdap.is_new_domain("fresh-scam.xyz", now=NOW)
    assert route.call_count == 1
    assert route.calls.last.request.headers["Accept"] == "application/rdap+json"


@respx.mock
async def test_old_domain_is_not_new() -> None:
    await _store_bootstrap()
    respx.get("https://rdap.verisign.example/com/v1/domain/old-shop.com").mock(
        return_value=httpx.Response(200, json=_rdap_domain("2010-01-01T00:00:00Z"))
    )

    assert not await rdap.is_new_domain("old-shop.com", now=NOW)


async def test_tld_without_rdap_server_is_skipped() -> None:
    await _store_bootstrap()

    assert await rdap.registered_at("ornek.com.tr") is None
    assert not await rdap.is_new_domain("ornek.com.tr", now=NOW)


async def test_missing_bootstrap_skips_check() -> None:
    assert not await rdap.is_new_domain("anything.com", now=NOW)


@respx.mock
async def test_errors_are_cached_as_unknown() -> None:
    await _store_bootstrap()
    route = respx.get("https://rdap.verisign.example/com/v1/domain/broken.com").mock(
        side_effect=httpx.ConnectError("down")
    )

    assert await rdap.registered_at("broken.com") is None
    assert await rdap.registered_at("broken.com") is None
    assert route.call_count == 1
    assert await cache.get_redis().ttl(rdap.CACHE_PREFIX + "broken.com") > 0
