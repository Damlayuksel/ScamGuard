import re

import pytest

from app.scanner.data import load_json
from app.scanner.text_rules import analyze_text, max_text_score, normalize_pattern

DANGEROUS_THRESHOLD = 70


def _matched(text: str) -> list[str]:
    return analyze_text(text).matched


def test_all_patterns_compile_and_have_turkish_reasons() -> None:
    data = load_json("text_patterns.json")
    ids = [entry["id"] for entry in data["patterns"]]

    assert len(ids) == len(set(ids))
    for entry in data["patterns"]:
        re.compile(normalize_pattern(entry["pattern"]))
        assert entry["category"] in {"urgency", "impersonation", "reward", "info_request"}
        assert entry["reason"]


def test_pattern_normalisation_keeps_escapes() -> None:
    assert normalize_pattern(r"\bŞİFRE\S+\W") == r"\bsifre\S+\W"


@pytest.mark.parametrize(
    "text",
    [
        "HESABINIZ ASKIYA ALINACAKTIR",
        "Hesabınız askıya alınacaktır",
        "hesabiniz askiya alinacaktir",
        "HESABİNİZ ASKİYA ALİNACAKTİR",
    ],
)
def test_case_and_turkish_letter_variants_match(text: str) -> None:
    assert "urgency_account_suspended" in _matched(text)


@pytest.mark.parametrize(
    ("text", "pattern_id"),
    [
        ("Bugün SON GÜN, kaçırmayın", "urgency_last_day"),
        ("24 saat içinde ödeme yapmazsanız", "urgency_hours"),
        ("Kartınız bloke edilmiştir", "urgency_account_suspended"),
        ("Gönderiniz imha edilecektir", "urgency_destroyed"),
        ("e-Devlet üzerinden bildirim", "impersonation_edevlet"),
        ("Gümrük ücreti ödenmediği için bekliyor", "impersonation_customs_fee"),
        ("Adres bilgileriniz eksik olduğu için teslim edilemedi", "impersonation_delivery_failed"),
        ("Trafik cezası borcunuz bulunmaktadır", "impersonation_tax_fine"),
        ("Ben Ankara Cumhuriyet Savcılığından arıyorum", "impersonation_authority"),
        ("Tebrikler, iPhone KAZANDINIZ!", "reward_won"),
        ("150 TL iade alacağınız var", "reward_refund"),
        ("Bonus puanınız yüklendi, hemen kullanın", "reward_bonus_points"),
        ("IBAN numaranızı gönderin", "info_iban"),
        ("TR12 0006 4000 0011 2345 6789 01 hesabına yatırın", "info_iban"),
        ("Kart numaranızı ve CVV kodunu yazın", "info_card"),
        ("Size gelen doğrulama kodunu paylaşın", "info_otp"),
        ("Şifrenizi güncelleyin", "info_password"),
        ("TC kimlik numaranızı girin", "info_identity"),
        ("Ödeme yapınız aksi halde", "info_payment"),
    ],
)
def test_pattern_categories(text: str, pattern_id: str) -> None:
    assert pattern_id in _matched(text)


def test_text_score_is_capped_and_never_dangerous_alone() -> None:
    text = (
        "SON UYARI! Hesabınız 24 saat içinde askıya alınacak. e-Devlet iade alacağınız var, "
        "kart numaranızı, CVV ve doğrulama kodunu, şifrenizi ve IBAN bilginizi hemen gönderin. "
        "Kazandınız! Gümrük ücreti ödeyin."
    )

    result = analyze_text(text)

    assert result.score == max_text_score() == 40
    assert result.score < DANGEROUS_THRESHOLD
    assert len(result.reasons) == len(result.matched) > 5


def test_each_pattern_counts_once() -> None:
    once = analyze_text("şifre")
    twice = analyze_text("şifre şifre şifre")

    assert once.score == twice.score
    assert twice.matched.count("info_password") == 1


@pytest.mark.parametrize(
    "text",
    [
        "Akşam yemeğe gelir misin?",
        "Toplantı yarın saat 10'da, unutma.",
        "Annemin doğum günü için pasta aldım",
    ],
)
def test_ordinary_messages_score_low(text: str) -> None:
    assert analyze_text(text).score < 30


@pytest.mark.parametrize(
    ("text", "pattern_id"),
    [
        ("Hesabınız güvenlik nedeniyle askıya alınacaktır", "urgency_account_suspended"),
        ("Hattınız 24 saat içinde kapatılacaktır", "urgency_account_suspended"),
        ("Hesabınıza yeni bir cihazdan giriş yapıldı", "urgency_new_device_login"),
        ("Adınız bir soruşturmada geçiyor", "impersonation_investigation"),
        ("Paranızı güvenli hesaba aktarmanız gerekiyor", "info_safe_account"),
        ("Hemen doğrulayın", "info_verify_details"),
        ("Bilgilerinizi güncelleyiniz", "info_verify_details"),
    ],
)
def test_added_scam_patterns(text: str, pattern_id: str) -> None:
    assert pattern_id in _matched(text)
