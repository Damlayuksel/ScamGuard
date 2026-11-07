from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.config import Settings, get_settings
from app.models import BlacklistDomain, BlacklistSource
from app.scanner import blacklist, rdap
from app.worker import blacklist_store, jobs, sources
from app.worker.main import build_scheduler
from app.worker.sources import FeedError, parse_entries

USOM_ENTRIES = [
    "evil-bank.com",
    "https://phish-site.net/login?user=1",
    "198.51.100.4",
    "https://drive.google.com/file/d/abc/view",
    "https://www.turkiye.gov.tr/giris",
    "sub.evil.github.io",
    "download1350.mediafire.com",
    "not a host",
]


def _usom_page(entries: list[str], page_count: int) -> dict[str, object]:
    return {
        "totalCount": len(entries),
        "count": len(entries),
        "models": [{"id": i, "url": url, "type": "domain"} for i, url in enumerate(entries)],
        "page": 0,
        "pageCount": page_count,
    }


@pytest.fixture(autouse=True)
def _no_page_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "USOM_PAGE_DELAY_SECONDS", 0)


@pytest.fixture
def usom_api() -> respx.MockRouter:
    with respx.mock(assert_all_called=False) as router:
        yield router


def _mock_usom(router: respx.MockRouter, pages: list[list[str]]) -> respx.Route:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(200, json=_usom_page(pages[page - 1], len(pages)))

    return router.get(get_settings().usom_api_url).mock(side_effect=handler)


async def _domains(session: AsyncSession) -> set[tuple[str, BlacklistSource]]:
    rows = (await session.execute(select(BlacklistDomain.domain, BlacklistDomain.source))).all()
    return {(domain, source) for domain, source in rows}


def test_parse_entries_skips_protected_and_invalid_hosts() -> None:
    hosts, skipped = parse_entries(USOM_ENTRIES)

    assert hosts == {"evil-bank.com", "phish-site.net", "198.51.100.4", "sub.evil.github.io"}
    assert skipped == 3


async def test_usom_full_sync_reads_every_page(
    usom_api: respx.MockRouter, db_session: AsyncSession
) -> None:
    route = _mock_usom(usom_api, [["one-evil.com", "two-evil.com"], ["three-evil.com"]])

    count = await jobs.update_usom()

    assert count == 3
    assert [call.request.url.params["page"] for call in route.calls] == ["1", "2"]
    assert "date_gte" not in route.calls[0].request.url.params
    assert ("three-evil.com", BlacklistSource.USOM) in await _domains(db_session)
    assert await cache.get_redis().hget(blacklist.REDIS_KEY, "one-evil.com") == "usom"


async def test_start_up_downloads_usom_only_when_empty(usom_api: respx.MockRouter) -> None:
    route = _mock_usom(usom_api, [["first-evil.com"]])

    assert await jobs.update_usom_if_empty() == 1
    assert route.call_count == 1

    # Data present: a restart or deploy must not download again.
    assert await jobs.update_usom_if_empty() == 0
    assert route.call_count == 1


@respx.mock
async def test_start_up_downloads_urlhaus_only_when_empty() -> None:
    route = respx.get(get_settings().urlhaus_url).mock(
        return_value=httpx.Response(200, text="http://malware-host.com/x.exe\n")
    )

    assert await jobs.update_urlhaus_if_empty() == 1
    assert await jobs.update_urlhaus_if_empty() == 0
    assert route.call_count == 1


@respx.mock
async def test_start_up_refreshes_rdap_bootstrap_only_when_missing() -> None:
    route = respx.get(rdap.BOOTSTRAP_URL).mock(
        return_value=httpx.Response(200, json={"services": [[["com"], ["https://rdap.x/"]]]})
    )

    assert await jobs.refresh_rdap_bootstrap_if_missing() == 1
    assert await jobs.refresh_rdap_bootstrap_if_missing() == 0
    assert route.call_count == 1


def test_downloads_are_scheduled_once_a_day() -> None:
    scheduler = build_scheduler()
    jobs_by_id = {job.id: job for job in scheduler.get_jobs()}

    for job_id in ("usom", "urlhaus", "rdap-bootstrap", "purge"):
        assert isinstance(jobs_by_id[job_id].trigger, CronTrigger), job_id
    for job_id in ("sync", "usom-if-empty", "urlhaus-if-empty", "rdap-if-missing"):
        assert isinstance(jobs_by_id[job_id].trigger, DateTrigger), job_id
    assert not any(isinstance(job.trigger, IntervalTrigger) for job in jobs_by_id.values())


async def test_update_refreshes_last_seen_without_duplicates(
    usom_api: respx.MockRouter, db_session: AsyncSession
) -> None:
    _mock_usom(usom_api, [USOM_ENTRIES])

    await jobs.update_usom()
    await jobs.update_usom()

    rows = (await db_session.scalars(select(BlacklistDomain))).all()
    assert len(rows) == 4


async def test_empty_feed_keeps_existing_entries(
    usom_api: respx.MockRouter, db_session: AsyncSession
) -> None:
    await blacklist_store.upsert_hosts(BlacklistSource.USOM, ["evil-site.com"])
    _mock_usom(usom_api, [[]])

    assert await jobs.update_usom() == 0
    assert await _domains(db_session) == {("evil-site.com", BlacklistSource.USOM)}


async def test_usom_http_error_raises_feed_error(usom_api: respx.MockRouter) -> None:
    usom_api.get(get_settings().usom_api_url).mock(return_value=httpx.Response(503))

    with pytest.raises(FeedError):
        await jobs.update_usom()


async def test_usom_unexpected_shape_raises_feed_error(usom_api: respx.MockRouter) -> None:
    usom_api.get(get_settings().usom_api_url).mock(
        return_value=httpx.Response(200, json={"error": "x"})
    )

    with pytest.raises(FeedError):
        await jobs.update_usom()


@respx.mock
async def test_urlhaus_stores_hosts_and_sends_auth_key_when_set() -> None:
    settings = Settings(**{**get_settings().model_dump(), "urlhaus_auth_key": "test-key"})
    route = respx.get(settings.urlhaus_url).mock(
        return_value=httpx.Response(
            200, text="http://malware-host.com/x.exe\r\nhttps://download1.mediafire.com/a\r\n"
        )
    )

    assert await jobs.update_urlhaus(settings=settings) == 1
    assert route.calls.last.request.headers["Auth-Key"] == "test-key"


@respx.mock
async def test_urlhaus_works_without_auth_key() -> None:
    route = respx.get(get_settings().urlhaus_url).mock(
        return_value=httpx.Response(200, text="http://malware-host.com/x.exe\n")
    )

    assert await jobs.update_urlhaus() == 1
    assert "Auth-Key" not in route.calls.last.request.headers


async def _age(session: AsyncSession, domains: list[str], days: int) -> None:
    await session.execute(
        update(BlacklistDomain)
        .where(BlacklistDomain.domain.in_(domains))
        .values(last_seen=datetime.now(UTC) - timedelta(days=days))
    )
    await session.commit()


async def test_purge_removes_only_stale_feed_entries(db_session: AsyncSession) -> None:
    await blacklist_store.upsert_hosts(BlacklistSource.USOM, ["old-site.com", "fresh-site.com"])
    db_session.add(BlacklistDomain(domain="community-site.com", source=BlacklistSource.COMMUNITY))
    await db_session.commit()
    await _age(db_session, ["old-site.com", "community-site.com"], days=8)

    removed = await jobs.purge_stale_entries()

    assert removed == 1
    assert {d for d, _ in await _domains(db_session)} == {"fresh-site.com", "community-site.com"}


async def test_purge_skips_feed_that_stopped_updating(db_session: AsyncSession) -> None:
    await blacklist_store.upsert_hosts(BlacklistSource.USOM, ["a-site.com", "b-site.com"])
    await _age(db_session, ["a-site.com", "b-site.com"], days=8)

    assert await jobs.purge_stale_entries() == 0
    assert len(await _domains(db_session)) == 2


async def test_lookup_matches_parent_domains_via_redis() -> None:
    await blacklist_store.upsert_hosts(BlacklistSource.USOM, ["evil-site.com"])
    await blacklist_store.upsert_hosts(BlacklistSource.URLHAUS, ["evil-site.com"])
    await blacklist_store.sync_redis()

    hit = await blacklist.lookup("login.secure.evil-site.com")

    assert hit == blacklist.BlacklistHit(
        domain="evil-site.com", sources=(BlacklistSource.URLHAUS, BlacklistSource.USOM)
    )
    assert await blacklist.lookup("good-site.com") is None


async def test_lookup_falls_back_to_db_when_redis_not_built() -> None:
    await blacklist_store.upsert_hosts(BlacklistSource.USOM, ["evil-site.com"])

    hit = await blacklist.lookup("www.evil-site.com")

    assert hit is not None
    assert hit.domain == "evil-site.com"


async def test_lookup_falls_back_to_db_when_redis_down(monkeypatch: pytest.MonkeyPatch) -> None:
    await blacklist_store.upsert_hosts(BlacklistSource.USOM, ["evil-site.com"])
    await blacklist_store.sync_redis()

    class BrokenRedis:
        def pipeline(self, **_kwargs: object) -> object:
            raise RedisConnectionError("down")

    monkeypatch.setattr(cache, "get_redis", lambda: BrokenRedis())

    hit = await blacklist.lookup("evil-site.com")

    assert hit is not None
    assert hit.sources == (BlacklistSource.USOM,)


async def test_empty_sync_marks_hash_as_built() -> None:
    await blacklist_store.sync_redis()

    assert await cache.get_redis().exists(blacklist.REDIS_KEY)
    assert await blacklist.lookup("anything.com") is None


async def test_run_job_swallows_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def boom() -> int:
        raise RuntimeError("https://secret.example/token")

    monkeypatch.setitem(jobs.JOBS, "urlhaus", boom)

    await jobs.run_job("urlhaus")

    assert "RuntimeError" in caplog.text
    assert "secret.example" not in caplog.text


async def test_usom_logs_progress(
    usom_api: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level("INFO")
    _mock_usom(usom_api, [[f"evil-{i}.com"] for i in range(12)])

    await jobs.update_usom()

    assert "usom: 10/12 page(s) downloaded" in caplog.text
    assert "usom: 12/12 page(s) downloaded" in caplog.text
    assert "usom: storing 12 host(s)" in caplog.text


async def test_usom_download_has_overall_timeout(
    usom_api: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import timedelta

    monkeypatch.setattr(jobs, "USOM_FETCH_TIMEOUT", timedelta(milliseconds=50))
    monkeypatch.setattr(sources, "USOM_PAGE_DELAY_SECONDS", 0.2)
    _mock_usom(usom_api, [["a-evil.com"], ["b-evil.com"], ["c-evil.com"]])

    with pytest.raises(TimeoutError):
        await jobs.update_usom()
