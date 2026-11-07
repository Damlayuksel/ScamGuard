import httpx
import pytest

from app.config import Settings, get_settings
from app.main import create_app

ALLOWED_ORIGIN = "http://localhost:8081"


def _settings(**overrides: object) -> Settings:
    base = get_settings().model_dump()
    base.update(overrides)
    return Settings(**base)


async def _get(app_settings: Settings, path: str, **kwargs: object) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app(app_settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path, **kwargs)


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
async def test_docs_disabled_in_prod(path: str) -> None:
    settings = _settings(env="prod", secret_key="x" * 64)

    response = await _get(settings, path)

    assert response.status_code == 404


async def test_docs_enabled_in_dev() -> None:
    response = await _get(_settings(env="dev"), "/docs")

    assert response.status_code == 200


def test_prod_rejects_placeholder_secret() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        _settings(env="prod", secret_key="change-me")


def test_comma_separated_lists_are_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("TRUSTED_PROXIES", "10.0.0.1,10.0.0.2")

    settings = Settings()

    assert settings.cors_origins == ["https://a.example", "https://b.example"]
    assert settings.trusted_proxies == ["10.0.0.1", "10.0.0.2"]


async def test_cors_allows_configured_origin(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


async def test_cors_rejects_unknown_origin(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


async def test_not_found_message_is_turkish(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Aradığınız sayfa bulunamadı."}
