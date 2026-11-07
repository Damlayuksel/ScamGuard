"""Hostname normalisation and registered-domain helpers.

Registered domains are always computed with tldextract, never with substring checks.
tldextract uses its bundled public suffix snapshot so it never downloads at runtime.
"""

import ipaddress
import re
from functools import lru_cache
from urllib.parse import urlsplit

import tldextract

from app.scanner.data import never_block_hosts, never_block_suffixes, official_domains

_extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

_HOST_CHARS = re.compile(r"^[a-z0-9._-]+$")
_MAX_HOST_LENGTH = 253
_MAX_LABEL_LENGTH = 63


def parse_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return None


def normalize_host(raw: str) -> str | None:
    """Lower-cases, strips the trailing dot and IDNA-encodes a hostname. None if invalid."""
    host = raw.strip().rstrip(".").lower()
    if not host:
        return None

    ip = parse_ip(host)
    if ip is not None:
        return ip.compressed

    if not host.isascii():
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError:
            return None

    if len(host) > _MAX_HOST_LENGTH or not _HOST_CHARS.match(host):
        return None
    labels = host.split(".")
    if any(not label or len(label) > _MAX_LABEL_LENGTH for label in labels):
        return None
    return host


def host_from_entry(entry: str) -> str | None:
    """Extracts the hostname from a blacklist entry that may be a domain, an IP or a URL."""
    entry = entry.strip()
    if not entry or entry.startswith("#"):
        return None
    if "://" not in entry:
        entry = "//" + entry
    try:
        hostname = urlsplit(entry).hostname
    except ValueError:
        return None
    return normalize_host(hostname) if hostname else None


@lru_cache(maxsize=4096)
def registered_domain(host: str) -> str | None:
    if parse_ip(host) is not None:
        return None
    return _extract(host).top_domain_under_public_suffix or None


@lru_cache(maxsize=4096)
def split_host(host: str) -> tuple[str, str, str]:
    """(subdomain, domain label, public suffix); IPs come back as ("", host, "")."""
    if parse_ip(host) is not None:
        return "", host, ""
    parts = _extract(host)
    return parts.subdomain, parts.domain, parts.suffix


def candidate_hosts(host: str) -> list[str]:
    """The host itself and each parent down to its registered domain.

    `a.b.evil.com` -> [`a.b.evil.com`, `b.evil.com`, `evil.com`]
    """
    registered = registered_domain(host)
    if registered is None or registered == host:
        return [host]
    labels = host.split(".")
    depth = registered.count(".") + 1
    return [".".join(labels[i:]) for i in range(len(labels) - depth + 1)]


def is_official(host: str) -> bool:
    official = official_domains()
    return host in official or registered_domain(host) in official


def _under_shared_suffix(host: str) -> bool:
    return any(host == s or host.endswith("." + s) for s in never_block_suffixes())


def is_protected(host: str) -> bool:
    """Hosts that must never be blacklisted: official domains and shared platforms."""
    return host in never_block_hosts() or _under_shared_suffix(host) or is_official(host)
