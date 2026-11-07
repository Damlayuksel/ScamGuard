"""Downloads public blacklist feeds and extracts hostnames from them.

- USOM (T.C. Siber Güvenlik Başkanlığı): paginated JSON API. Pages start at 1.
- URLhaus (abuse.ch): plain-text dump of online malware URLs, one per line.
"""

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

import httpx

from app.config import Settings
from app.scanner.hosts import host_from_entry, is_protected

logger = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
_MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
_USER_AGENT = "ScamShield-blacklist-updater/1.0"

USOM_PAGE_SIZE = 9999  # API maximum
USOM_MAX_PAGES = 500  # safety cap (~5M entries)
USOM_PAGE_DELAY_SECONDS = 0.5  # be polite to the public API
USOM_PROGRESS_EVERY = 10  # log progress every N pages


class FeedError(Exception):
    pass


def parse_entries(entries: Iterable[str]) -> tuple[set[str], int]:
    """Returns (blacklistable hosts, number of skipped protected hosts)."""
    hosts: set[str] = set()
    skipped = 0
    for entry in entries:
        host = host_from_entry(entry)
        if host is None:
            continue
        if is_protected(host):
            skipped += 1
            continue
        hosts.add(host)
    return hosts, skipped


def http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=_DOWNLOAD_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    )


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, str]) -> Any:
    response = await client.get(url, params=params)
    if response.status_code != 200:
        raise FeedError(f"usom API returned HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise FeedError("usom API returned invalid JSON") from exc


def _usom_page_entries(payload: Any) -> tuple[list[str], int]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise FeedError("usom API response has an unexpected shape")
    entries = [
        model["url"]
        for model in payload["models"]
        if isinstance(model, dict) and isinstance(model.get("url"), str)
    ]
    page_count = payload.get("pageCount")
    return entries, page_count if isinstance(page_count, int) else 1


async def fetch_usom(client: httpx.AsyncClient, settings: Settings) -> list[str]:
    """Fetches all USOM entries."""
    params = {"per-page": str(USOM_PAGE_SIZE)}

    entries: list[str] = []
    page = 1
    page_count = 1
    while page <= min(page_count, USOM_MAX_PAGES):
        payload = await _get_json(client, settings.usom_api_url, {**params, "page": str(page)})
        page_entries, page_count = _usom_page_entries(payload)
        entries.extend(page_entries)
        if page % USOM_PROGRESS_EVERY == 0 or page == page_count:
            logger.info("usom: %d/%d page(s) downloaded", page, page_count)
        page += 1
        if page <= page_count:
            await asyncio.sleep(USOM_PAGE_DELAY_SECONDS)
    return entries


async def fetch_urlhaus(client: httpx.AsyncClient, settings: Settings) -> list[str]:
    headers = {}
    auth_key = settings.urlhaus_auth_key.get_secret_value()
    if auth_key:
        headers["Auth-Key"] = auth_key

    chunks: list[bytes] = []
    size = 0
    async with client.stream("GET", settings.urlhaus_url, headers=headers) as response:
        if response.status_code != 200:
            raise FeedError(f"urlhaus feed returned HTTP {response.status_code}")
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > _MAX_DOWNLOAD_BYTES:
                raise FeedError("urlhaus feed is larger than the download limit")
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace").splitlines()
