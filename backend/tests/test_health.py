import httpx
import pytest

from app import cache


async def test_health_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "redis": "ok"}


async def test_health_degraded_when_redis_down(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def failing_check() -> bool:
        return False

    monkeypatch.setattr(cache, "check_redis", failing_check)

    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "ok", "redis": "error"}
