"""SSRF-safe redirect resolver for link shorteners.

Rules (CLAUDE.md, security 4-5):
- Only HEAD requests (GET with at most a few KB when HEAD is not allowed). No JavaScript.
- At most 5 redirects, 3 second total timeout.
- Only http/https on ports 80 and 443.
- DNS is resolved at every hop; if any resolved address is private, loopback,
  link-local, multicast, reserved or otherwise non-global, the request is refused.
- The request goes to the verified IP itself (Host header and TLS SNI keep the original
  name), so a second DNS answer cannot rebind the connection to an internal address.

Nothing here logs URLs.
"""

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.scanner.hosts import normalize_host

MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 3.0
MAX_BODY_BYTES = 4096
ALLOWED_PORTS = {80, 443}
_DEFAULT_PORTS = {"http": 80, "https": 443}
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_HEAD_NOT_ALLOWED = {405, 501}
_NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")
_USER_AGENT = "Mozilla/5.0 (compatible; ScamShield-link-checker/1.0)"

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Resolver = Callable[[str, int], Awaitable[list[str]]]


class FetchError(StrEnum):
    BAD_SCHEME = "bad_scheme"
    BAD_PORT = "bad_port"
    BAD_HOST = "bad_host"
    DNS_FAILED = "dns_failed"
    BLOCKED_ADDRESS = "blocked_address"
    TOO_MANY_REDIRECTS = "too_many_redirects"
    TIMEOUT = "timeout"
    NETWORK = "network"


@dataclass
class FetchResult:
    final_url: str | None
    hops: list[str] = field(default_factory=list)
    error: FetchError | None = None

    @property
    def resolved(self) -> bool:
        return self.error is None and self.final_url is not None


class _Blocked(Exception):
    def __init__(self, reason: FetchError) -> None:
        self.reason = reason


async def system_resolver(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(
        host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )
    return list(dict.fromkeys(str(info[4][0]) for info in infos))


def _embedded_ipv4(address: ipaddress.IPv6Address) -> list[ipaddress.IPv4Address]:
    embedded = [address.ipv4_mapped, address.sixtofour]
    if address.teredo:
        embedded.extend(address.teredo)
    if address in _NAT64_PREFIX:
        embedded.append(ipaddress.IPv4Address(int(address) & 0xFFFFFFFF))
    return [ip for ip in embedded if ip is not None]


def is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    candidates: list[IPAddress] = [address]
    if isinstance(address, ipaddress.IPv6Address):
        candidates.extend(_embedded_ipv4(address))
    return all(
        ip.is_global and not ip.is_multicast and not ip.is_reserved and not ip.is_unspecified
        for ip in candidates
    )


@dataclass(frozen=True)
class _Target:
    scheme: str
    host: str
    port: int
    path: str


def _parse(url: str) -> _Target:
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise _Blocked(FetchError.BAD_HOST) from exc
    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        raise _Blocked(FetchError.BAD_SCHEME)
    port = port or _DEFAULT_PORTS[scheme]
    if port not in ALLOWED_PORTS:
        raise _Blocked(FetchError.BAD_PORT)
    host = normalize_host(parts.hostname or "")
    if host is None:
        raise _Blocked(FetchError.BAD_HOST)
    path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
    return _Target(scheme=scheme, host=host, port=port, path=path)


async def _verified_ip(target: _Target, resolver: Resolver) -> str:
    try:
        ipaddress.ip_address(target.host)
        addresses = [target.host]
    except ValueError:
        try:
            addresses = await resolver(target.host, target.port)
        except (OSError, UnicodeError) as exc:
            raise _Blocked(FetchError.DNS_FAILED) from exc
    if not addresses:
        raise _Blocked(FetchError.DNS_FAILED)
    if not all(is_public_address(address) for address in addresses):
        raise _Blocked(FetchError.BLOCKED_ADDRESS)
    return addresses[0]


def _ip_url(target: _Target, ip: str) -> str:
    literal = f"[{ip}]" if ":" in ip else ip
    return f"{target.scheme}://{literal}:{target.port}{target.path}"


def _host_header(target: _Target) -> str:
    if target.port == _DEFAULT_PORTS[target.scheme]:
        return target.host
    return f"{target.host}:{target.port}"


async def _request(client: httpx.AsyncClient, target: _Target, ip: str) -> httpx.Response:
    url = _ip_url(target, ip)
    headers = {"Host": _host_header(target), "User-Agent": _USER_AGENT}
    extensions = {"sni_hostname": target.host} if target.scheme == "https" else {}

    response = await client.head(url, headers=headers, extensions=extensions)
    if response.status_code not in _HEAD_NOT_ALLOWED:
        return response

    async with client.stream("GET", url, headers=headers, extensions=extensions) as response:
        received = 0
        async for chunk in response.aiter_raw():
            received += len(chunk)
            if received >= MAX_BODY_BYTES:
                break
    return response


async def _follow(
    url: str, client: httpx.AsyncClient, resolver: Resolver, result: FetchResult
) -> None:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        target = _parse(current)
        ip = await _verified_ip(target, resolver)
        response = await _request(client, target, ip)
        location = response.headers.get("location")
        if response.status_code not in _REDIRECT_STATUSES or not location:
            result.final_url = current
            return
        current = urljoin(current, location)
        result.hops.append(current)
    raise _Blocked(FetchError.TOO_MANY_REDIRECTS)


async def resolve_redirects(
    url: str,
    *,
    resolver: Resolver = system_resolver,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FetchResult:
    """Follows redirects safely. `hops` lists every redirect target in order."""
    result = FetchResult(final_url=None)
    client = httpx.AsyncClient(
        follow_redirects=False,
        timeout=TIMEOUT_SECONDS,
        trust_env=False,
        transport=transport,
    )
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS), client:
            await _follow(url, client, resolver, result)
    except _Blocked as blocked:
        result.error = blocked.reason
    except TimeoutError:
        result.error = FetchError.TIMEOUT
    except httpx.TimeoutException:
        result.error = FetchError.TIMEOUT
    except httpx.HTTPError:
        result.error = FetchError.NETWORK
    if result.error is not None:
        result.final_url = None
    return result
