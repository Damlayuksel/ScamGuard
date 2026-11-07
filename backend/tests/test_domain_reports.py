import uuid

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.core import ratelimit
from app.core.device import INVALID_DEVICE_MESSAGE
from app.models import BlacklistDomain, BlacklistSource, DomainReport
from app.scanner import blacklist
from app.services.domain_reports import COMMUNITY_THRESHOLD
from app.worker import blacklist_store
from tests.scan_helpers import stub_shortener

URL = "/api/v1/domains/report"


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_shortener(monkeypatch, None)


async def _report(
    client: httpx.AsyncClient, domain: str, device: str | None = None
) -> httpx.Response:
    headers = {"X-Device-Id": device or str(uuid.uuid4())}
    return await client.post(URL, json={"domain": domain}, headers=headers)


async def _community(session: AsyncSession) -> list[str]:
    rows = await session.scalars(
        select(BlacklistDomain.domain).where(BlacklistDomain.source == BlacklistSource.COMMUNITY)
    )
    return list(rows)


async def test_report_is_accepted(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    response = await _report(client, "https://www.Sahte-Kargo.com/takip?id=1")

    assert response.status_code == 200
    assert response.json() == {"message": "Bildiriminiz alındı. Teşekkür ederiz."}
    assert list(await db_session.scalars(select(DomainReport.domain))) == ["www.sahte-kargo.com"]


async def test_device_id_is_stored_hashed(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    device = str(uuid.uuid4())

    await _report(client, "sahte-kargo.com", device)

    stored = await db_session.scalar(select(DomainReport.device_hash))
    assert stored is not None
    assert device not in stored
    assert len(stored) == 64


async def test_threshold_promotes_to_community_blacklist(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await blacklist_store.sync_redis()
    for _ in range(COMMUNITY_THRESHOLD - 1):
        await _report(client, "sahte-kargo.com")

    assert await _community(db_session) == []
    assert await blacklist.lookup("sahte-kargo.com") is None

    await _report(client, "sahte-kargo.com")

    assert await _community(db_session) == ["sahte-kargo.com"]
    hit = await blacklist.lookup("sahte-kargo.com")
    assert hit is not None
    assert hit.sources == (BlacklistSource.COMMUNITY,)

    scan = await client.post("/api/v1/scan", json={"text": "https://sahte-kargo.com/odeme"})
    assert scan.json()["level"] == "dangerous"
    assert "kullanıcı bildirimleri" in scan.json()["reasons"][0]


async def test_same_device_counts_once(client: httpx.AsyncClient, db_session: AsyncSession) -> None:
    device = str(uuid.uuid4())
    for _ in range(COMMUNITY_THRESHOLD):
        response = await _report(client, "sahte-kargo.com", device)
        assert response.status_code == 200

    assert len(list(await db_session.scalars(select(DomainReport)))) == 1
    assert await _community(db_session) == []


async def test_promotion_without_built_redis_hash_does_not_create_partial_hash(
    client: httpx.AsyncClient,
) -> None:
    for _ in range(COMMUNITY_THRESHOLD):
        await _report(client, "sahte-kargo.com")

    assert not await cache.get_redis().exists(blacklist.REDIS_KEY)
    assert await blacklist.lookup("sahte-kargo.com") is not None


@pytest.mark.parametrize("device", [None, "", "not-a-uuid", "123"])
async def test_missing_or_invalid_device_id(client: httpx.AsyncClient, device: str | None) -> None:
    headers = {} if device is None else {"X-Device-Id": device}

    response = await client.post(URL, json={"domain": "sahte-kargo.com"}, headers=headers)

    assert response.status_code == 400
    assert response.json() == {"detail": INVALID_DEVICE_MESSAGE}


@pytest.mark.parametrize(
    "domain",
    ["https://www.turkiye.gov.tr", "ziraatbank.com.tr", "github.com", "drive.google.com"],
)
async def test_protected_domains_cannot_be_reported(client: httpx.AsyncClient, domain: str) -> None:
    response = await _report(client, domain)

    assert response.status_code == 400
    assert "bildirilemez" in response.json()["detail"]


@pytest.mark.parametrize("domain", ["localhost", "bir kelime", "http://", "..."])
async def test_invalid_domains_are_rejected(client: httpx.AsyncClient, domain: str) -> None:
    response = await _report(client, domain)

    assert response.status_code == 400
    assert "geçerli bir site adresi" in response.json()["detail"]


async def test_rate_limit_per_device(client: httpx.AsyncClient) -> None:
    device = str(uuid.uuid4())
    for i in range(ratelimit.DOMAIN_REPORT_PER_DEVICE.max_requests):
        assert (await _report(client, f"site-{i}.com", device)).status_code == 200

    response = await _report(client, "one-more.com", device)

    assert response.status_code == 429
    assert (await _report(client, "one-more.com")).status_code == 200
