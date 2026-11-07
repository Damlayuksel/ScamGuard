import pytest

from app.scanner.hosts import (
    candidate_hosts,
    host_from_entry,
    is_official,
    is_protected,
    normalize_host,
    registered_domain,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Example.COM.", "example.com"),
        ("  evil.example  ", "evil.example"),
        ("ziraat-güvenlik.com", "xn--ziraat-gvenlik-nsb.com"),
        ("192.0.2.10", "192.0.2.10"),
        ("[2001:db8::0001]", "2001:db8::1"),
        ("", None),
        ("bad host.com", None),
        ("a" * 64 + ".com", None),
    ],
)
def test_normalize_host(raw: str, expected: str | None) -> None:
    assert normalize_host(raw) == expected


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("evil.example", "evil.example"),
        ("https://Evil.Example:8443/login?x=1", "evil.example"),
        ("http://user@evil.example/path", "evil.example"),
        ("evil.example/some/path", "evil.example"),
        ("198.51.100.4", "198.51.100.4"),
        ("http://198.51.100.4:8080/bins/x", "198.51.100.4"),
        ("# comment", None),
        ("   ", None),
    ],
)
def test_host_from_entry(entry: str, expected: str | None) -> None:
    assert host_from_entry(entry) == expected


def test_registered_domain_uses_public_suffix_list() -> None:
    assert registered_domain("turkiye.gov.tr.giris-yap.xyz") == "giris-yap.xyz"
    assert registered_domain("www.turkiye.gov.tr") == "turkiye.gov.tr"
    assert registered_domain("198.51.100.4") is None


def test_candidate_hosts_walks_up_to_registered_domain() -> None:
    assert candidate_hosts("a.b.evil.com") == ["a.b.evil.com", "b.evil.com", "evil.com"]
    assert candidate_hosts("evil.co.uk") == ["evil.co.uk"]
    assert candidate_hosts("x.evil.github.io") == [
        "x.evil.github.io",
        "evil.github.io",
        "github.io",
    ]
    assert candidate_hosts("198.51.100.4") == ["198.51.100.4"]


def test_official_check_is_exact_not_substring() -> None:
    assert is_official("www.turkiye.gov.tr")
    assert not is_official("turkiye.gov.tr.giris-yap.xyz")
    assert not is_official("turkiye-gov-tr.com")


def test_never_block_protects_only_exact_platform_hosts() -> None:
    assert is_protected("github.io")
    assert is_protected("drive.google.com")
    assert not is_protected("evil.github.io")


def test_shared_download_hosts_are_protected_by_suffix() -> None:
    assert is_protected("download1350.mediafire.com")
    assert is_protected("doc-0s-docs.googleusercontent.com")
    assert not is_protected("mediafire.com.evil-site.xyz")
