from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class OntologySymbol:
    id: str
    discipline: str
    category: str
    canonical_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class OntologySystem:
    id: str
    discipline: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class SymbolOntology:
    symbols: tuple[OntologySymbol, ...]
    systems: tuple[OntologySystem, ...]


def _ontology_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "symbol_ontology.json"


@lru_cache
def load_symbol_ontology() -> SymbolOntology:
    payload = json.loads(_ontology_path().read_text())
    return SymbolOntology(
        symbols=tuple(
            OntologySymbol(
                id=item["id"],
                discipline=item["discipline"],
                category=item["category"],
                canonical_name=item["canonical_name"],
                aliases=tuple(alias.lower() for alias in item["aliases"]),
            )
            for item in payload["symbols"]
        ),
        systems=tuple(
            OntologySystem(
                id=item["id"],
                discipline=item["discipline"],
                aliases=tuple(alias.lower() for alias in item["aliases"]),
            )
            for item in payload["systems"]
        ),
    )


def detect_symbols(text: str) -> list[str]:
    lowered = text.lower()
    matches: list[str] = []
    for symbol in load_symbol_ontology().symbols:
        if any(alias in lowered for alias in symbol.aliases):
            matches.append(symbol.id)
    return matches


def detect_systems(text: str) -> list[str]:
    lowered = text.lower()
    matches: list[str] = []
    for system in load_symbol_ontology().systems:
        if any(alias in lowered for alias in system.aliases):
            matches.append(system.id)
    return matches
