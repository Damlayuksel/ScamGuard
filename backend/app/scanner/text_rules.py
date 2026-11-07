"""Message text rules (layer 3).

Patterns live in data/text_patterns.json and are matched against Turkish-normalised text
(see app.core.textnorm). The text score is capped at 40, so text alone can never reach
"Tehlikeli" (70). The message text is only used in memory.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.core.textnorm import normalize_text
from app.scanner.data import load_json


@dataclass(frozen=True)
class TextPattern:
    id: str
    category: str
    weight: int
    regex: re.Pattern[str]
    reason: str


@dataclass
class TextResult:
    score: int = 0
    matched: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def normalize_pattern(pattern: str) -> str:
    """Normalises the literal letters of a regex like message text, keeping escapes
    such as \\S or \\W untouched (lower-casing them would change their meaning)."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\" and i + 1 < len(pattern):
            out.append(pattern[i : i + 2])
            i += 2
            continue
        out.append(normalize_text(char))
        i += 1
    return "".join(out)


@lru_cache
def _rules() -> tuple[int, tuple[TextPattern, ...]]:
    data = load_json("text_patterns.json")
    patterns = tuple(
        TextPattern(
            id=entry["id"],
            category=entry["category"],
            weight=int(entry["weight"]),
            regex=re.compile(normalize_pattern(entry["pattern"])),
            reason=entry["reason"],
        )
        for entry in data["patterns"]
    )
    return int(data["max_score"]), patterns


def max_text_score() -> int:
    return _rules()[0]


def analyze_text(text: str) -> TextResult:
    max_score, patterns = _rules()
    normalized = normalize_text(text)
    result = TextResult()
    total = 0
    for pattern in patterns:
        if pattern.regex.search(normalized):
            total += pattern.weight
            result.matched.append(pattern.id)
            result.reasons.append(pattern.reason)
    result.score = min(max_score, total)
    return result
