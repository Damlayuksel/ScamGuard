"""User-facing Turkish texts for scan results. The system never says "kesinlikle güvenli"."""

from app.models import ScanLevel

LABELS: dict[ScanLevel, str] = {
    ScanLevel.DANGEROUS: "Tehlikeli",
    ScanLevel.SUSPICIOUS: "Şüpheli",
    ScanLevel.NO_KNOWN_THREAT: "Bilinen tehdit yok",
}

MESSAGES: dict[ScanLevel, str] = {
    ScanLevel.DANGEROUS: "Bu mesaj büyük olasılıkla dolandırıcılık amaçlı.",
    ScanLevel.SUSPICIOUS: "Bu mesajda dolandırıcılık belirtileri var. Dikkatli olun.",
    ScanLevel.NO_KNOWN_THREAT: "Bilinen bir tehdit bulunamadı, yine de dikkatli olun.",
}

_REPORT = (
    "Mesajı USOM'a (usom.gov.tr) bildirin. Dolandırıldığınızı düşünüyorsanız "
    "155 Polis İmdat'ı arayın."
)

ADVICE: dict[ScanLevel, list[str]] = {
    ScanLevel.DANGEROUS: [
        "Mesajdaki linke tıklamayın.",
        "Kart bilgilerinizi, şifrenizi veya size gelen kodları kimseyle paylaşmayın.",
        "Kimseye para göndermeyin.",
        "Bankanızı kartınızın arkasındaki resmî numaradan arayın.",
        _REPORT,
        "Mesajı silin ve gönderen numarayı engelleyin.",
    ],
    ScanLevel.SUSPICIOUS: [
        "Linke tıklamadan önce kurumu resmî numarasından arayıp doğrulayın.",
        "Kart bilgilerinizi, şifrenizi veya size gelen kodları kimseyle paylaşmayın.",
        "Para göndermeden önce mutlaka doğrulayın.",
        _REPORT,
    ],
    ScanLevel.NO_KNOWN_THREAT: [
        "Bilinen bir tehdit bulamadık ama bu, mesajın kesinlikle güvenli olduğu anlamına gelmez.",
        "Beklemediğiniz mesajlardaki linklere karşı dikkatli olun.",
        "Şifrenizi, kart bilgilerinizi veya size gelen kodları kimseyle paylaşmayın.",
    ],
}
