"""Combines the four layers into one scan result.

Precedence (CLAUDE.md):
1. Any blacklisted link -> 100, "Tehlikeli".
2. At least one link and every link official -> 0 (text score is not added).
3. Otherwise total = min(100, highest link score + text score).

The message text and full URLs exist only inside this request.
"""

import asyncio
from dataclasses import dataclass, field

from app.models import BlacklistSource, ScanLevel
from app.scanner import blacklist, rdap
from app.scanner.extract import MAX_LINKS, extract_links
from app.scanner.hosts import parse_ip
from app.scanner.safe_fetch import resolve_redirects
from app.scanner.text_rules import analyze_text
from app.scanner.url_rules import (
    DOMAIN_AGE_SCORE,
    MAX_LINK_SCORE,
    UNRESOLVED_SHORTENER_SCORE,
    LinkAnalysis,
    analyze_url,
)

DANGEROUS_MIN = 70
SUSPICIOUS_MIN = 30
MAX_TOTAL_SCORE = 100

_SOURCE_NAMES = {
    BlacklistSource.USOM: "USOM",
    BlacklistSource.URLHAUS: "URLhaus",
    BlacklistSource.COMMUNITY: "kullanıcı bildirimleri",
}


@dataclass
class LinkResult:
    domain: str
    score: int
    reasons: list[str]
    official: bool = False
    blacklisted: bool = False
    # Every registered domain seen for this link (including redirect targets).
    domains: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    level: ScanLevel
    score: int
    reasons: list[str]
    links: list[LinkResult]


def level_for(score: int) -> ScanLevel:
    if score >= DANGEROUS_MIN:
        return ScanLevel.DANGEROUS
    if score >= SUSPICIOUS_MIN:
        return ScanLevel.SUSPICIOUS
    return ScanLevel.NO_KNOWN_THREAT


def _blacklist_reason(hit: blacklist.BlacklistHit) -> str:
    names = ", ".join(_SOURCE_NAMES[source] for source in hit.sources)
    return f"Bu adres zararlı bağlantılar listesinde bulunuyor ({names})."


async def _score_static(analysis: LinkAnalysis) -> tuple[LinkAnalysis, bool]:
    """Adds blacklist and domain-age checks to a static analysis. Returns (analysis, hit)."""
    hit = await blacklist.lookup(analysis.host)
    if hit is not None:
        analysis.score = MAX_LINK_SCORE
        analysis.reasons.insert(0, _blacklist_reason(hit))
        return analysis, True
    if analysis.official:
        return analysis, False
    if parse_ip(analysis.host) is None and await rdap.is_new_domain(analysis.domain):
        analysis.add(DOMAIN_AGE_SCORE, "Bu site çok yeni açılmış (30 günden kısa süre önce).")
    return analysis, False


async def _scan_link(url: str) -> LinkResult | None:
    analysis = analyze_url(url)
    if analysis is None:
        return None
    analysis, hit = await _score_static(analysis)
    result = LinkResult(
        domain=analysis.domain,
        score=analysis.score,
        reasons=list(analysis.reasons),
        official=analysis.official,
        blacklisted=hit,
        domains=[analysis.domain],
    )
    if hit or not analysis.shortener:
        return result

    fetch = await resolve_redirects(url)
    for hop in fetch.hops:
        hop_analysis = analyze_url(hop)
        if hop_analysis is None:
            continue
        hop_analysis, hop_hit = await _score_static(hop_analysis)
        result.domains.append(hop_analysis.domain)
        if hop_hit:
            result.blacklisted = True
        if hop_analysis.score >= result.score or hop_hit:
            result.score = hop_analysis.score
            result.reasons = [
                f"Bu kısa link '{hop_analysis.domain}' adresine yönlendiriyor.",
                *hop_analysis.reasons,
            ]

    if fetch.resolved and fetch.final_url is not None:
        final = analyze_url(fetch.final_url)
        if final is not None and final.official and not result.blacklisted:
            result.official = True
            result.score = 0
            result.reasons = []
    else:
        result.score = min(MAX_LINK_SCORE, result.score + UNRESOLVED_SHORTENER_SCORE)
        result.reasons.append("Bu kısa linkin nereye gittiği tespit edilemedi.")
    return result


async def scan(text: str) -> ScanResult:
    extracted = extract_links(text)
    scanned = await asyncio.gather(*(_scan_link(url) for url in extracted.urls))
    links = [link for link in scanned if link is not None]
    text_result = analyze_text(text)

    all_official = bool(links) and all(link.official for link in links)
    if any(link.blacklisted for link in links):
        score = MAX_TOTAL_SCORE
    elif all_official:
        score = 0
    else:
        link_score = max((link.score for link in links if not link.official), default=0)
        score = min(MAX_TOTAL_SCORE, link_score + text_result.score)

    reasons: list[str] = []
    for link in sorted(links, key=lambda item: item.score, reverse=True):
        reasons.extend(reason for reason in link.reasons if reason not in reasons)
    if not all_official:
        reasons.extend(text_result.reasons)
    if extracted.truncated:
        reasons.append(f"Mesajda çok sayıda link vardı; yalnızca ilk {MAX_LINKS} link tarandı.")

    return ScanResult(level=level_for(score), score=score, reasons=reasons, links=links)
