from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_HEADER_PATTERN = re.compile(
    r"^\s*SECTION\s+(\d{2}\s+\d{2}\s+\d{2})\s*(.+)?$",
    re.I | re.M,
)
REQUIREMENT_VERBS = (
    "shall",
    "must",
    "provide",
    "install",
    "submit",
    "coordinate",
    "comply",
    "verify",
    "maintain",
)
ENTITY_PATTERNS = (
    r"\bdoors?\b",
    r"\bcorridor\b",
    r"\bramp\b",
    r"\bguard\b",
    r"\bpanel\b",
    r"\bfeeder\b",
    r"\bconduit\b",
    r"\bsprinkler\b",
    r"\bfire alarm\b",
    r"\baccessible\b",
    r"\bdrain(?:age)?\b",
)


@dataclass
class SpecRequirement:
    section_number: str
    text: str
    entities: list[str] = field(default_factory=list)
    modal_strength: str = "informational"


@dataclass
class SpecSectionSemantics:
    section_number: str
    title: str
    text: str
    requirements: list[SpecRequirement] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _extract_entities(text: str) -> list[str]:
    lowered = text.lower()
    entities: list[str] = []
    for pattern in ENTITY_PATTERNS:
        for match in re.finditer(pattern, lowered, re.I):
            entity = _normalize_whitespace(match.group(0).lower()).rstrip("s")
            if entity not in entities:
                entities.append(entity)
    return entities


def _split_sections(text: str) -> list[tuple[str, str, str]]:
    matches = list(SECTION_HEADER_PATTERN.finditer(text))
    if not matches:
        return []
    sections: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section_number = _normalize_whitespace(match.group(1))
        title = _normalize_whitespace(match.group(2) or "")
        body = text[start:end].strip()
        sections.append((section_number, title, body))
    return sections


def _extract_requirements(section_number: str, text: str) -> list[SpecRequirement]:
    requirements: list[SpecRequirement] = []
    for raw_line in text.splitlines():
        line = _normalize_whitespace(raw_line)
        if len(line) < 20:
            continue
        lowered = line.lower()
        matched_verb = next((verb for verb in REQUIREMENT_VERBS if verb in lowered), None)
        if not matched_verb:
            continue
        modal_strength = "mandatory" if matched_verb in {"shall", "must", "comply"} else "directive"
        requirements.append(
            SpecRequirement(
                section_number=section_number,
                text=line,
                entities=_extract_entities(line),
                modal_strength=modal_strength,
            )
        )
    return requirements[:200]


def parse_spec_sections(text: str) -> list[SpecSectionSemantics]:
    sections = _split_sections(text)
    return [
        SpecSectionSemantics(
            section_number=section_number,
            title=title,
            text=body,
            requirements=_extract_requirements(section_number, body),
            entities=_extract_entities(body),
        )
        for section_number, title, body in sections
    ]
