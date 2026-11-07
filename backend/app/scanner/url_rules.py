"""Rule-based URL analysis (layer 2) without network access.

Domain age (RDAP) and shortener resolution need the network and are applied by the
pipeline on top of this result.
"""

import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from rapidfuzz.distance import OSA

from app.core.textnorm import fold_confusables
from app.scanner.data import Brand, brands, risky_tlds, shortener_hosts
from app.scanner.hosts import (
    is_official,
    normalize_host,
    parse_ip,
    registered_domain,
    split_host,
)

MAX_LINK_SCORE = 100

BRAND_SCORE = 40
PUNYCODE_SCORE = 30
DOMAIN_AGE_SCORE = 30
RAW_IP_SCORE = 20
AT_SIGN_SCORE = 20
SUBDOMAIN_SCORE = 10
RISKY_TLD_SCORE = 10
UNRESOLVED_SHORTENER_SCORE = 10

MAX_SUBDOMAIN_LABELS = 3
_SUBSTRING_MIN_LENGTH = 4
_FUZZY_MIN_LENGTH = 5
_FUZZY_MAX_DISTANCE = 2
_SHORT_FUZZY_KEYWORD = 6
_SPLIT_LABELS = re.compile(r"[.-]")


@dataclass
class LinkAnalysis:
    """Result for one link. `url` lives only in memory for the duration of the request."""

    url: str
    host: str
    domain: str
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    official: bool = False
    shortener: bool = False

    def add(self, points: int, reason: str) -> None:
        self.score = min(MAX_LINK_SCORE, self.score + points)
        self.reasons.append(reason)


def _decode_label(label: str) -> str:
    if label.startswith("xn--"):
        try:
            return label.encode("ascii").decode("idna")
        except UnicodeError:
            return label
    return label


def _name_parts(host: str) -> list[str]:
    """Host labels without the public suffix, decoded and folded to plain Latin letters."""
    subdomain, domain, _suffix = split_host(host)
    labels = [label for label in f"{subdomain}.{domain}".split(".") if label and label != "www"]
    text = ".".join(fold_confusables(_decode_label(label)) for label in labels)
    return [part for part in _SPLIT_LABELS.split(text) if part]


def _is_typo_of(part: str, keyword: str) -> bool:
    """Typo-squat check. Plain Levenshtein <= 2 on short Turkish words is too noisy
    ("firsat" vs "ziraat", "hazir" vs "hazine"), so the edit must keep the first letter,
    change the length by at most one, and stay within 1 edit for keywords up to
    6 letters (2 above). Transpositions count as one edit (OSA distance)."""
    if part[0] != keyword[0] or abs(len(part) - len(keyword)) > 1:
        return False
    max_distance = 1 if len(keyword) <= _SHORT_FUZZY_KEYWORD else _FUZZY_MAX_DISTANCE
    return OSA.distance(part, keyword, score_cutoff=max_distance) <= max_distance


def _keyword_matches(keyword: str, parts: list[str], compact: str) -> bool:
    if len(keyword) < _SUBSTRING_MIN_LENGTH:
        return keyword in parts
    if keyword in compact:
        return True
    if len(keyword) >= _FUZZY_MIN_LENGTH:
        return any(
            len(part) >= _SUBSTRING_MIN_LENGTH and _is_typo_of(part, keyword) for part in parts
        )
    return False


def impersonated_brand(host: str) -> Brand | None:
    parts = _name_parts(host)
    compact = "".join(parts)
    for brand in brands():
        if any(_keyword_matches(keyword, parts, compact) for keyword in brand.keywords):
            return brand
    return None


def _host_and_authority(url: str) -> tuple[str | None, str]:
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
    except ValueError:
        return None, ""
    return (normalize_host(hostname) if hostname else None), parts.netloc


def is_shortener(host: str) -> bool:
    shorteners = shortener_hosts()
    return host in shorteners or registered_domain(host) in shorteners


def analyze_url(url: str) -> LinkAnalysis | None:
    """Scores one URL. Returns None when the URL has no usable host."""
    host, authority = _host_and_authority(url)
    if host is None:
        return None
    ip = parse_ip(host)
    domain = registered_domain(host) or host
    result = LinkAnalysis(url=url, host=host, domain=domain)

    if is_official(host):
        result.official = True
        return result

    result.shortener = is_shortener(host)

    if ip is None:
        brand = impersonated_brand(host)
        if brand is not None:
            result.add(BRAND_SCORE, f"Bu adres '{brand.name}' markasını taklit ediyor olabilir.")

    if "xn--" in host:
        result.add(
            PUNYCODE_SCORE,
            "Adreste gerçek harflere benzeyen farklı alfabelerden karakterler var.",
        )

    if ip is not None:
        result.add(RAW_IP_SCORE, "Adres, bir site adı yerine doğrudan sayılardan (IP) oluşuyor.")

    if "@" in authority:
        result.add(
            AT_SIGN_SCORE,
            "Adreste '@' işareti var. Bu işaret gerçek adresi gizlemek için kullanılabilir.",
        )

    subdomain, _domain, suffix = split_host(host)
    if subdomain and len(subdomain.split(".")) > MAX_SUBDOMAIN_LABELS:
        result.add(SUBDOMAIN_SCORE, "Adres alışılmadık kadar çok parçadan oluşuyor.")

    tld = suffix.rsplit(".", 1)[-1] if suffix else ""
    if tld in risky_tlds():
        result.add(
            RISKY_TLD_SCORE,
            f"Adresin uzantısı (.{tld}) dolandırıcılıkta sık kullanılıyor.",
        )

    return result
