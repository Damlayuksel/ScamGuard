"""Finds links in message text. Works only in memory; nothing here is stored or logged."""

import re
from dataclasses import dataclass

from app.scanner.hosts import normalize_host, registered_domain

MAX_LINKS = 10

# 1) explicit scheme, 2) www., 3) bare domain (validated against the public suffix list).
_LINK_PATTERN = re.compile(
    r"""
    (?:https?://[^\s<>"'`]+)
    | (?<![@\w.-])(?:www\.[^\s<>"'`]+)
    | (?<![@\w.-/])(?:[\w-]+\.)+[\w-]{2,}(?::\d{1,5})?(?:/[^\s<>"'`]*)?
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Also guillemet, typographic closing quotes and ellipsis (U+00BB, U+201D, U+2019, U+2026).
_TRAILING_PUNCTUATION = ".,;:!?)]}'\"" + "".join(map(chr, (0x00BB, 0x201D, 0x2019, 0x2026)))
_SCHEME = re.compile(r"^https?://", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractedLinks:
    urls: list[str]
    truncated: bool


def _clean(candidate: str) -> str:
    candidate = candidate.rstrip(_TRAILING_PUNCTUATION)
    # Keep a closing parenthesis only when it is balanced inside the URL.
    while candidate.endswith(")") and candidate.count("(") < candidate.count(")"):
        candidate = candidate[:-1]
    return candidate


def _host_of(url: str) -> str | None:
    rest = _SCHEME.sub("", url)
    authority = re.split(r"[/?#]", rest, maxsplit=1)[0]
    hostname = authority.rsplit("@", 1)[-1]
    if hostname.startswith("["):
        hostname = hostname.split("]", 1)[0] + "]"
    else:
        hostname = hostname.split(":", 1)[0]
    return normalize_host(hostname)


def extract_links(text: str) -> ExtractedLinks:
    urls: list[str] = []
    seen: set[str] = set()
    truncated = False
    for match in _LINK_PATTERN.finditer(text):
        candidate = _clean(match.group(0))
        has_scheme = bool(_SCHEME.match(candidate))
        host = _host_of(candidate)
        if host is None:
            continue
        # Bare words like "saat.14" are only links when they end in a real public suffix.
        if not has_scheme and registered_domain(host) is None:
            continue
        url = candidate if has_scheme else f"http://{candidate}"
        if url in seen:
            continue
        if len(urls) == MAX_LINKS:
            truncated = True
            break
        seen.add(url)
        urls.append(url)
    return ExtractedLinks(urls=urls, truncated=truncated)
