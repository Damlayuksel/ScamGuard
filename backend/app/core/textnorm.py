"""Turkish-aware text normalisation shared by text rules and domain checks.

Steps: NFKC -> Turkish lower-casing (İ->i, I->ı) -> ASCII folding (ç->c ğ->g ı->i ö->o ş->s ü->u).
After this, "HESABINIZ", "Hesabınız" and "hesabiniz" are identical.
"""

import unicodedata

_TURKISH_UPPER = str.maketrans({"İ": "i", "I": "ı"})
_ASCII_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")

# Look-alike letters from other scripts used in homograph domains (Cyrillic, Greek, IPA).
_CONFUSABLES = str.maketrans(
    {
        "а": "a",  # Cyrillic a
        "е": "e",  # Cyrillic ie
        "о": "o",  # Cyrillic o
        "р": "p",  # Cyrillic er
        "с": "c",  # Cyrillic es
        "у": "y",  # Cyrillic u
        "х": "x",  # Cyrillic ha
        "і": "i",  # Cyrillic byelorussian-ukrainian i
        "ј": "j",  # Cyrillic je
        "ѕ": "s",  # Cyrillic dze
        "ԁ": "d",  # Cyrillic komi de
        "ӏ": "l",  # Cyrillic palochka
        "ԛ": "q",  # Cyrillic qa
        "ԝ": "w",  # Cyrillic we
        "ο": "o",  # Greek omicron
        "α": "a",  # Greek alpha
        "ν": "v",  # Greek nu
        "ι": "i",  # Greek iota
        "κ": "k",  # Greek kappa
        "τ": "t",  # Greek tau
        "ρ": "p",  # Greek rho
        "ɡ": "g",  # Latin script g
    }
)


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return text.translate(_TURKISH_UPPER).lower().translate(_ASCII_FOLD)


def fold_confusables(text: str) -> str:
    """normalize_text plus mapping of look-alike letters from other scripts to Latin."""
    return normalize_text(text).translate(_CONFUSABLES)
