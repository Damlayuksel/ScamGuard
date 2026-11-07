import asyncio

import httpx
import pytest
import respx

from app.scanner.safe_fetch import (
    MAX_REDIRECTS,
    FetchError,
    is_public_address,
    resolve_redirects,
)

PUBLIC_IP = "93.184.216.34"
OTHER_PUBLIC_IP = "93.184.216.35"


def resolver_for(table: dict[str, list[str]]):
    calls: list[str] = []

    async def resolve(host: str, _port: int) -> list[str]:
        calls.append(host)
        if host not in table:
            raise OSError("no such host")
        return table[host]

    resolve.calls = calls  # type: ignore[attr-defined]
    return resolve


@pytest.mark.parametrize(
    ("address", "public"),
    [
        ("8.8.8.8", True),
        ("2606:4700:4700::1111", True),
        ("127.0.0.1", False),
        ("10.1.2.3", False),
        ("172.16.0.1", False),
        ("192.168.1.1", False),
        ("169.254.169.254", False),
        ("100.64.0.1", False),
        ("0.0.0.0", False),  # noqa: S104 - checking that it is refused
        ("224.0.0.1", False),
        ("233.252.0.1", False),
        ("240.0.0.1", False),
        ("::1", False),
        ("fe80::1", False),
        ("fc00::1", False),
        ("::ffff:127.0.0.1", False),
        ("64:ff9b::7f00:1", False),
        ("2002:7f00:1::", False),
        ("not-an-ip", False),
    ],
)
def test_is_public_address(address: str, public: bool) -> None:
    assert is_public_address(address) is public


@respx.mock
async def test_follows_redirects_to_final_url() -> None:
    respx.head(host=PUBLIC_IP, path="/abc").mock(
        return_value=httpx.Response(301, headers={"Location": "https://landing.example/x?y=1"})
    )
    respx.head(host=OTHER_PUBLIC_IP, path="/x").mock(return_value=httpx.Response(200))
    resolver = resolver_for({"bit.ly": [PUBLIC_IP], "landing.example": [OTHER_PUBLIC_IP]})

    result = await resolve_redirects("https://bit.ly/abc", resolver=resolver)

    assert result.resolved
    assert result.final_url == "https://landing.example/x?y=1"
    assert result.hops == ["https://landing.example/x?y=1"]
    assert resolver.calls == ["bit.ly", "landing.example"]


@respx.mock
async def test_request_goes_to_verified_ip_with_original_host() -> None:
    route = respx.head(host=PUBLIC_IP, path="/abc").mock(return_value=httpx.Response(200))

    await resolve_redirects("https://bit.ly/abc", resolver=resolver_for({"bit.ly": [PUBLIC_IP]}))

    request = route.calls.last.request
    assert request.url.host == PUBLIC_IP
    assert request.headers["Host"] == "bit.ly"
    assert request.extensions["sni_hostname"] == "bit.ly"


@respx.mock
async def test_relative_location_is_resolved() -> None:
    respx.head(host=PUBLIC_IP, path="/a").mock(
        return_value=httpx.Response(302, headers={"Location": "/b"})
    )
    respx.head(host=PUBLIC_IP, path="/b").mock(return_value=httpx.Response(200))

    result = await resolve_redirects(
        "http://short.example/a", resolver=resolver_for({"short.example": [PUBLIC_IP]})
    )

    assert result.final_url == "http://short.example/b"


@respx.mock
async def test_redirect_to_private_address_is_blocked() -> None:
    respx.head(host=PUBLIC_IP, path="/abc").mock(
        return_value=httpx.Response(302, headers={"Location": "http://internal.example/admin"})
    )
    resolver = resolver_for({"bit.ly": [PUBLIC_IP], "internal.example": ["10.0.0.5"]})

    result = await resolve_redirects("https://bit.ly/abc", resolver=resolver)

    assert not result.resolved
    assert result.error is FetchError.BLOCKED_ADDRESS
    assert result.hops == ["http://internal.example/admin"]


async def test_any_private_answer_blocks_the_host() -> None:
    resolver = resolver_for({"mixed.example": [PUBLIC_IP, "127.0.0.1"]})

    result = await resolve_redirects("https://mixed.example/", resolver=resolver)

    assert result.error is FetchError.BLOCKED_ADDRESS


@pytest.mark.parametrize(
    ("url", "error"),
    [
        ("http://127.0.0.1/", FetchError.BLOCKED_ADDRESS),
        ("http://169.254.169.254/latest/meta-data/", FetchError.BLOCKED_ADDRESS),
        ("http://[::1]/", FetchError.BLOCKED_ADDRESS),
        ("http://[::ffff:127.0.0.1]/", FetchError.BLOCKED_ADDRESS),
        ("http://100.64.1.1/", FetchError.BLOCKED_ADDRESS),
        ("http://public.example:8080/", FetchError.BAD_PORT),
        ("https://public.example:22/", FetchError.BAD_PORT),
        ("file:///etc/passwd", FetchError.BAD_SCHEME),
        ("ftp://public.example/", FetchError.BAD_SCHEME),
        ("gopher://public.example/", FetchError.BAD_SCHEME),
        ("http://unknown.example/", FetchError.DNS_FAILED),
    ],
)
async def test_unsafe_targets_are_refused(url: str, error: FetchError) -> None:
    result = await resolve_redirects(url, resolver=resolver_for({"public.example": [PUBLIC_IP]}))

    assert result.error is error
    assert result.final_url is None


@respx.mock
async def test_redirect_to_disallowed_port_is_refused() -> None:
    respx.head(host=PUBLIC_IP, path="/abc").mock(
        return_value=httpx.Response(302, headers={"Location": "http://public.example:6379/"})
    )
    resolver = resolver_for({"bit.ly": [PUBLIC_IP], "public.example": [PUBLIC_IP]})

    result = await resolve_redirects("https://bit.ly/abc", resolver=resolver)

    assert result.error is FetchError.BAD_PORT


@respx.mock
async def test_stops_after_max_redirects() -> None:
    def loop(request: httpx.Request) -> httpx.Response:
        step = int(request.url.path.strip("/") or 0)
        return httpx.Response(302, headers={"Location": f"/{step + 1}"})

    respx.head(host=PUBLIC_IP).mock(side_effect=loop)

    result = await resolve_redirects(
        "http://loop.example/0", resolver=resolver_for({"loop.example": [PUBLIC_IP]})
    )

    assert result.error is FetchError.TOO_MANY_REDIRECTS
    assert len(result.hops) == MAX_REDIRECTS + 1


@respx.mock
async def test_five_redirects_are_allowed() -> None:
    def chain(request: httpx.Request) -> httpx.Response:
        step = int(request.url.path.strip("/") or 0)
        if step == MAX_REDIRECTS:
            return httpx.Response(200)
        return httpx.Response(302, headers={"Location": f"/{step + 1}"})

    respx.head(host=PUBLIC_IP).mock(side_effect=chain)

    result = await resolve_redirects(
        "http://chain.example/0", resolver=resolver_for({"chain.example": [PUBLIC_IP]})
    )

    assert result.resolved
    assert result.final_url == f"http://chain.example/{MAX_REDIRECTS}"


@respx.mock
async def test_falls_back_to_get_when_head_not_allowed() -> None:
    respx.head(host=PUBLIC_IP, path="/abc").mock(return_value=httpx.Response(405))
    get_route = respx.get(host=PUBLIC_IP, path="/abc").mock(
        return_value=httpx.Response(301, headers={"Location": "https://final.example/"})
    )
    respx.head(host=OTHER_PUBLIC_IP, path="/").mock(return_value=httpx.Response(200))
    resolver = resolver_for({"bit.ly": [PUBLIC_IP], "final.example": [OTHER_PUBLIC_IP]})

    result = await resolve_redirects("https://bit.ly/abc", resolver=resolver)

    assert get_route.called
    assert result.final_url == "https://final.example/"


async def test_total_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.scanner.safe_fetch as safe_fetch

    monkeypatch.setattr(safe_fetch, "TIMEOUT_SECONDS", 0.05)

    async def slow_resolver(_host: str, _port: int) -> list[str]:
        await asyncio.sleep(1)
        return [PUBLIC_IP]

    result = await resolve_redirects("https://slow.example/", resolver=slow_resolver)

    assert result.error is FetchError.TIMEOUT


@respx.mock
async def test_network_error_is_reported() -> None:
    respx.head(host=PUBLIC_IP).mock(side_effect=httpx.ConnectError("refused"))

    result = await resolve_redirects(
        "https://down.example/", resolver=resolver_for({"down.example": [PUBLIC_IP]})
    )

    assert result.error is FetchError.NETWORK
