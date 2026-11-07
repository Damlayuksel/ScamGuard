import pytest

from app.core.textnorm import fold_confusables, normalize_text
from app.scanner.extract import MAX_LINKS, extract_links
from app.scanner.url_rules import (
    AT_SIGN_SCORE,
    BRAND_SCORE,
    PUNYCODE_SCORE,
    RAW_IP_SCORE,
    RISKY_TLD_SCORE,
    SUBDOMAIN_SCORE,
    analyze_url,
    impersonated_brand,
)


def _analyze(url: str):
    result = analyze_url(url)
    assert result is not None
    return result


# --- extraction -------------------------------------------------------------


def test_extracts_scheme_www_and_bare_links() -> None:
    text = (
        "Kargonuz bekliyor: https://ptt-kargo.xyz/takip?id=1. "
        "Detay için www.example-shop.com, ayrıca ziraat-giris.top/login adresine girin!"
    )

    assert extract_links(text).urls == [
        "https://ptt-kargo.xyz/takip?id=1",
        "http://www.example-shop.com",
        "http://ziraat-giris.top/login",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Saat 14.30'da görüşelim, tutar 1.250,00 TL",
        "E-posta: ali.veli@gmail.com",
        "versiyon 2.0.1 yayında",
    ],
)
def test_ignores_non_links(text: str) -> None:
    assert extract_links(text).urls == []


def test_strips_trailing_punctuation_and_unbalanced_parenthesis() -> None:
    text = "Linke tıklayın (https://evil-site.com/a) ve https://evil-site.com/b?!"

    assert extract_links(text).urls == ["https://evil-site.com/a", "https://evil-site.com/b"]


def test_deduplicates_and_caps_links() -> None:
    links = " ".join(f"https://site{i}.com" for i in range(MAX_LINKS + 3))
    result = extract_links(f"https://site0.com {links}")

    assert len(result.urls) == MAX_LINKS
    assert result.urls[0] == "https://site0.com"
    assert result.truncated


def test_unicode_domains_are_extracted() -> None:
    assert extract_links("ziraat-güvenlik.com adresine girin").urls == [
        "http://ziraat-güvenlik.com"
    ]


# --- text normalisation used by domain checks -------------------------------


def test_turkish_normalisation() -> None:
    assert normalize_text("HESABINIZ") == normalize_text("Hesabınız") == "hesabiniz"
    assert normalize_text("İADE") == normalize_text("iade") == "iade"
    assert normalize_text("ŞİFRE Güncelleme") == "sifre guncelleme"


def test_cyrillic_lookalikes_fold_to_latin() -> None:
    assert fold_confusables("zіrааt") == "ziraat"


# --- URL rules --------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.turkiye.gov.tr/e-devlet-giris",
        "https://ziraatbank.com.tr",
        "https://giris.ziraatbank.com.tr/tr",
        "https://www.ptt.gov.tr",
    ],
)
def test_official_domains_score_zero(url: str) -> None:
    result = _analyze(url)

    assert result.official
    assert result.score == 0
    assert result.reasons == []


def test_official_name_inside_other_domain_is_not_official() -> None:
    result = _analyze("https://turkiye.gov.tr.giris-yap.xyz/login")

    assert not result.official
    assert result.domain == "giris-yap.xyz"
    assert result.score == BRAND_SCORE + RISKY_TLD_SCORE
    assert "e-Devlet" in result.reasons[0]


@pytest.mark.parametrize(
    ("url", "brand"),
    [
        ("https://z1raat-guvenlik.top", "Ziraat Bankası"),
        ("https://ziraatbankasi-online.com", "Ziraat Bankası"),
        ("https://www.garantibbva-bonus.com", "Garanti BBVA"),
        ("https://ptt-kargo-takip.com", "PTT"),
        ("https://e-devlet-iade.com", "e-Devlet"),
        ("https://yurticikargo-teslimat.net", "Yurtiçi Kargo"),
        ("https://akbnak-giris.com", "Akbank"),
    ],
)
def test_brand_impersonation(url: str, brand: str) -> None:
    result = _analyze(url)

    assert result.score >= BRAND_SCORE
    assert f"'{brand}'" in result.reasons[0]


@pytest.mark.parametrize(
    "host",
    ["pttavm.com", "shopping-site.com", "ingilizce-kurs.com", "tebrikler.org", "kargo.com"],
)
def test_short_brands_need_exact_label(host: str) -> None:
    assert impersonated_brand(host) is None


def test_punycode_homograph() -> None:
    host = "zіrааtbank.com".encode("idna").decode()
    result = _analyze(f"https://{host}/giris")

    assert result.host.startswith("xn--")
    assert result.score == BRAND_SCORE + PUNYCODE_SCORE


def test_raw_ip_url() -> None:
    result = _analyze("http://198.51.100.4/ziraat/login")

    assert result.score == RAW_IP_SCORE
    assert result.domain == "198.51.100.4"


def test_at_sign_in_authority() -> None:
    result = _analyze("https://www.ziraatbank.com.tr@evil-site.com/login")

    assert result.host == "evil-site.com"
    assert AT_SIGN_SCORE <= result.score
    assert any("'@'" in reason for reason in result.reasons)


def test_at_sign_in_query_is_not_flagged() -> None:
    assert _analyze("https://shop-site.com/?mail=a@b.com").score == 0


def test_many_subdomains() -> None:
    result = _analyze("https://a.b.c.d.example-site.com")

    assert result.score == SUBDOMAIN_SCORE


def test_risky_tld() -> None:
    result = _analyze("https://kampanya-firsat.xyz")

    assert result.score == RISKY_TLD_SCORE
    assert ".xyz" in result.reasons[0]


def test_shortener_is_flagged_but_not_scored_here() -> None:
    result = _analyze("https://bit.ly/3abcDEF")

    assert result.shortener
    assert result.score == 0


def test_score_is_capped_at_100() -> None:
    host = "zіrааt".encode("idna").decode()
    result = _analyze(f"https://user@a.b.c.d.{host}.xyz")

    assert result.score == 100


def test_invalid_url_returns_none() -> None:
    assert analyze_url("http://[::1") is None


@pytest.mark.parametrize(
    "host",
    [
        "kampanya-firsat.xyz",
        "hazir-kredi.com",
        "turkce-dersi.com",
        "garaj-kapisi.com",
        "zirve-tur.com",
        "araba-ilanlari.com",
        "kuveyt-gezi.com",
    ],
)
def test_common_turkish_words_are_not_brand_typos(host: str) -> None:
    assert impersonated_brand(host) is None


@pytest.mark.parametrize(
    ("host", "brand"),
    [
        ("vodafon.com", "Vodafone"),
        ("ziraaat.com", "Ziraat Bankası"),
        ("trendyoll.shop", "Trendyol"),
        ("hepsibrada.com", "Hepsiburada"),
        ("denizbnk.com", "DenizBank"),
        ("yapikreddi.com", "Yapı Kredi"),
        ("papra.com", "Papara"),
    ],
)
def test_brand_typos_are_detected(host: str, brand: str) -> None:
    found = impersonated_brand(host)

    assert found is not None
    assert found.name == brand
