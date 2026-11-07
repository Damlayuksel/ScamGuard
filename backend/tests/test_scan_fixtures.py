"""Phase 1 acceptance: scam examples are Tehlikeli/Şüpheli, official ones Bilinen tehdit yok."""

from typing import Any

import httpx
import pytest

from tests.scan_helpers import load_messages, seed_blacklist, stub_shortener

SCAM = load_messages("scam.json")
LEGIT = load_messages("legit.json")


def _shortener_target(message: dict[str, Any]) -> str | None:
    target = message.get("shortener", "unresolved")
    return None if target == "unresolved" else target


async def _scan(client: httpx.AsyncClient, message: dict[str, Any], monkeypatch) -> dict:
    stub_shortener(monkeypatch, _shortener_target(message))
    await seed_blacklist(message.get("blacklist", []))
    response = await client.post("/api/v1/scan", json={"text": message["text"]})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("message", SCAM, ids=[m["note"] for m in SCAM])
async def test_scam_messages(
    client: httpx.AsyncClient, message: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    body = await _scan(client, message, monkeypatch)

    assert body["level"] == message["expected_level"], body
    assert body["reasons"]


@pytest.mark.parametrize("message", LEGIT, ids=[m["note"] for m in LEGIT])
async def test_legit_messages(
    client: httpx.AsyncClient, message: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    body = await _scan(client, message, monkeypatch)

    assert body["level"] == "no_known_threat", body
    assert body["message"] == "Bilinen bir tehdit bulunamadı, yine de dikkatli olun."


def test_fixture_counts() -> None:
    assert len(SCAM) >= 15
    assert len(LEGIT) >= 10
