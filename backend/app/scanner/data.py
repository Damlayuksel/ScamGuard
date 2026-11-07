"""Loads rule files from backend/data/. Files are read once per process."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@lru_cache
def load_json(name: str) -> Any:
    with (DATA_DIR / name).open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache
def never_block_hosts() -> frozenset[str]:
    return frozenset(load_json("never_block.json")["hosts"])


@lru_cache
def never_block_suffixes() -> tuple[str, ...]:
    return tuple(load_json("never_block.json").get("suffixes", ()))


@lru_cache
def official_domains() -> frozenset[str]:
    return frozenset(load_json("official_domains.json")["domains"])


@dataclass(frozen=True)
class Brand:
    name: str
    keywords: tuple[str, ...]


@lru_cache
def brands() -> tuple[Brand, ...]:
    return tuple(
        Brand(name=entry["name"], keywords=tuple(entry["keywords"]))
        for entry in load_json("brands.json")["brands"]
    )


@lru_cache
def risky_tlds() -> frozenset[str]:
    return frozenset(load_json("risky_tlds.json")["tlds"])


@lru_cache
def shortener_hosts() -> frozenset[str]:
    return frozenset(load_json("shorteners.json")["hosts"])
