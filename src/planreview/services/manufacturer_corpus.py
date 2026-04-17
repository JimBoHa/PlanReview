from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class ManufacturerDocument:
    manufacturer: str
    component_label: str
    component_family: str
    title: str
    url: str


def _corpus_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "manufacturer_corpus.json"


@lru_cache
def load_manufacturer_corpus() -> tuple[ManufacturerDocument, ...]:
    payload = json.loads(_corpus_path().read_text())
    return tuple(
        ManufacturerDocument(
            manufacturer=item["manufacturer"],
            component_label=item["component_label"],
            component_family=item["component_family"],
            title=item["title"],
            url=item["url"],
        )
        for item in payload["documents"]
    )
