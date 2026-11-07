"""Error responses and logs must never contain the submitted content (KVKK)."""

import logging
import uuid

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.errors import INTERNAL_ERROR_MESSAGE, VALIDATION_ERROR_MESSAGE
from app.core.logging import AccessLogPrivacyFilter, configure_logging, mask_path


class _Body(BaseModel):
    text: str = Field(max_length=10)


@pytest.fixture
def marker() -> str:
    return f"KVKK-MARKER-{uuid.uuid4()}"


@pytest.fixture
def app_with_probe_routes(app: FastAPI) -> FastAPI:
    @app.post("/probe/validate")
    async def validate(body: _Body) -> dict[str, str]:
        return {"ok": "yes"}

    @app.post("/probe/explode")
    async def explode(body: dict[str, str]) -> None:
        raise ValueError(f"failed while handling {body['text']}")

    return app


@pytest.fixture
async def probe_client(app_with_probe_routes: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app_with_probe_routes)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_validation_error_does_not_echo_input(
    probe_client: httpx.AsyncClient, marker: str, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)

    response = await probe_client.post("/probe/validate", json={"text": marker})

    assert response.status_code == 422
    assert response.json() == {
        "detail": VALIDATION_ERROR_MESSAGE,
        "errors": [{"field": "body.text", "message": "En fazla 10 karakter olabilir."}],
    }
    assert marker not in response.text
    assert marker not in caplog.text


async def test_invalid_json_does_not_echo_input(
    probe_client: httpx.AsyncClient, marker: str
) -> None:
    response = await probe_client.post(
        "/probe/validate",
        content=f'{{"text": "{marker}"',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert marker not in response.text


async def test_unhandled_error_hides_content(
    probe_client: httpx.AsyncClient,
    marker: str,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)

    response = await probe_client.post("/probe/explode", json={"text": marker})

    assert response.status_code == 500
    assert response.json() == {"detail": INTERNAL_ERROR_MESSAGE}
    assert "ValueError" in caplog.text
    assert marker not in caplog.text
    captured = capsys.readouterr()
    assert marker not in captured.out
    assert marker not in captured.err


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/numbers/+905321234567", "/api/v1/numbers/***"),
        ("/api/v1/numbers/05321234567/dispute", "/api/v1/numbers/***/dispute"),
        ("/api/v1/numbers/0532%20123%2045%2067?x=1", "/api/v1/numbers/***?x=1"),
        ("/api/v1/numbers/report", "/api/v1/numbers/report"),
        ("/api/v1/numbers?page=2", "/api/v1/numbers?page=2"),
        ("/api/v1/scan", "/api/v1/scan"),
    ],
)
def test_mask_path(path: str, expected: str) -> None:
    assert mask_path(path) == expected


def test_access_log_filter_hides_ip_and_number() -> None:
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("203.0.113.7:51234", "GET", "/api/v1/numbers/+905321234567", "1.1", 200),
        exc_info=None,
    )

    assert AccessLogPrivacyFilter().filter(record)
    message = record.getMessage()

    assert "203.0.113.7" not in message
    assert "905321234567" not in message
    assert "/api/v1/numbers/***" in message


def test_url_logging_libraries_are_quiet() -> None:
    configure_logging()

    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING


def _access_record(path: str, status: int) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:5000", "GET", path, "1.1", status),
        exc_info=None,
    )


def test_successful_health_checks_are_not_logged() -> None:
    log_filter = AccessLogPrivacyFilter()

    assert not log_filter.filter(_access_record("/api/v1/health", 200))
    assert log_filter.filter(_access_record("/api/v1/health", 503))
    assert log_filter.filter(_access_record("/api/v1/scan", 200))
