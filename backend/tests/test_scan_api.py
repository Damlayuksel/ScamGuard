import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import cache
from app.core import ratelimit
from app.models import ScanLevel, ScanStat
from app.scanner import pipeline
from app.scanner.pipeline import level_for
from tests.scan_helpers import seed_blacklist, stub_shortener


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_shortener(monkeypatch, None)


async def _scan(client: httpx.AsyncClient, text: str) -> httpx.Response:
    return await client.post("/api/v1/scan", json={"text": text})


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0, ScanLevel.NO_KNOWN_THREAT),
        (29, ScanLevel.NO_KNOWN_THREAT),
        (30, ScanLevel.SUSPICIOUS),
        (69, ScanLevel.SUSPICIOUS),
        (70, ScanLevel.DANGEROUS),
        (100, ScanLevel.DANGEROUS),
    ],
)
def test_level_thresholds(score: int, level: ScanLevel) -> None:
    assert level_for(score) is level


async def test_response_shape(client: httpx.AsyncClient) -> None:
    response = await _scan(client, "Kargonuz teslim edilemedi: https://ptt-kargo-takip.xyz/a?b=1")

    body = response.json()
    assert set(body) == {"level", "label", "message", "score", "reasons", "links", "advice"}
    assert body["links"] == [
        {"domain": "ptt-kargo-takip.xyz", "score": 50, "reasons": body["links"][0]["reasons"]}
    ]
    assert "/a?b=1" not in response.text
    assert body["advice"]


async def test_blacklist_wins_over_official_link(client: httpx.AsyncClient) -> None:
    await seed_blacklist(["evil-site.com"])

    body = (
        await _scan(client, "Resmî: https://www.turkiye.gov.tr ve https://login.evil-site.com")
    ).json()

    assert body["score"] == 100
    assert body["level"] == "dangerous"
    assert "zararlı bağlantılar listesinde" in body["reasons"][0]


async def test_all_official_links_ignore_text(client: httpx.AsyncClient) -> None:
    text = "IBAN ve doğrulama kodunuzu gönderin, şifrenizi yazın: https://www.turkiye.gov.tr"

    body = (await _scan(client, text)).json()

    assert body["score"] == 0
    assert body["level"] == "no_known_threat"
    assert body["reasons"] == []


async def test_official_plus_unknown_link_uses_unknown_link(client: httpx.AsyncClient) -> None:
    text = "https://www.turkiye.gov.tr ve https://iade-basvuru.xyz"

    body = (await _scan(client, text)).json()

    assert body["score"] == 10
    assert [link["domain"] for link in body["links"]] == ["turkiye.gov.tr", "iade-basvuru.xyz"]


async def test_text_only_is_never_dangerous(client: httpx.AsyncClient) -> None:
    text = (
        "SON UYARI! Hesabınız askıya alınacak. Kart numaranızı, CVV, şifrenizi, "
        "doğrulama kodunu ve IBAN bilginizi hemen gönderin. Kazandınız!"
    )

    body = (await _scan(client, text)).json()

    assert body["score"] == 40
    assert body["level"] == "suspicious"


async def test_new_domain_adds_points(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def always_new(_domain: str, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(pipeline.rdap, "is_new_domain", always_new)

    body = (await _scan(client, "https://yeni-magaza.com")).json()

    assert body["score"] == 30
    assert any("çok yeni" in reason for reason in body["reasons"])


async def test_truncation_reason(client: httpx.AsyncClient) -> None:
    text = " ".join(f"https://site{i}.com" for i in range(12))

    body = (await _scan(client, text)).json()

    assert len(body["links"]) == 10
    assert "ilk 10 link" in body["reasons"][-1]


@pytest.mark.parametrize("text", ["", "a" * 5001])
async def test_text_length_limits(client: httpx.AsyncClient, text: str) -> None:
    response = await _scan(client, text)

    assert response.status_code == 422
    assert response.json()["detail"] == "Gönderilen bilgiler geçersiz."
    assert "a" * 100 not in response.text


async def test_scan_stats_store_only_domains(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _scan(client, "Bakın: https://ptt-kargo-takip.xyz/tr?id=55 https://www.ziraatbank.com.tr")

    rows = (await db_session.execute(select(ScanStat.domain, ScanStat.level))).all()
    assert sorted(rows) == [
        ("ptt-kargo-takip.xyz", ScanLevel.SUSPICIOUS),
        ("ziraatbank.com.tr", ScanLevel.SUSPICIOUS),
    ]


async def test_scan_stats_without_links(
    client: httpx.AsyncClient, db_session: AsyncSession
) -> None:
    await _scan(client, "Merhaba nasılsın?")

    rows = (await db_session.execute(select(ScanStat.domain, ScanStat.level))).all()
    assert rows == [(None, ScanLevel.NO_KNOWN_THREAT)]


async def test_rate_limit_per_ip(client: httpx.AsyncClient) -> None:
    for _ in range(ratelimit.SCAN_PER_IP.max_requests):
        assert (await _scan(client, "merhaba")).status_code == 200

    response = await _scan(client, "merhaba")

    assert response.status_code == 429
    assert response.json() == {"detail": ratelimit.RATE_LIMIT_MESSAGE}
    assert int(response.headers["Retry-After"]) > 0


async def test_rate_limit_key_has_no_plain_ip(client: httpx.AsyncClient) -> None:
    await _scan(client, "merhaba")

    keys = [key async for key in cache.get_redis().scan_iter("rl:*")]
    assert keys
    assert all("127.0.0.1" not in key for key in keys)


async def test_rate_limit_fails_open_without_redis(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from redis.exceptions import ConnectionError as RedisConnectionError

    class BrokenRedis:
        def pipeline(self, **_kwargs: object) -> object:
            raise RedisConnectionError("down")

        async def get(self, *_args: object) -> None:
            raise RedisConnectionError("down")

    monkeypatch.setattr(cache, "get_redis", lambda: BrokenRedis())

    response = await _scan(client, "merhaba https://ornek-site.com")

    assert response.status_code == 200
