from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from planreview.models import Standard


@dataclass
class FindingDraft:
    citation: str
    description: str
    anchor: str


AMPACITY_TABLE = {
    250: 255,
    300: 285,
    350: 310,
    400: 335,
    500: 380,
    600: 420,
}


def _selected_families(selected_standards: Iterable[Standard]) -> set[str]:
    return {item.family for item in selected_standards}


def _selected_tags(selected_standards: Iterable[Standard]) -> set[str]:
    tags: set[str] = set()
    for item in selected_standards:
        tags.update(tag for tag in item.tags_csv.split(",") if tag)
    return tags


def _parse_inches(value: str) -> float:
    cleaned = value.strip().replace('"', "")
    if "/" in cleaned:
        top, bottom = cleaned.split("/")
        return float(top) / float(bottom)
    return float(cleaned)


def detect_version_mismatches(
    text: str, selected_standards: list[Standard], all_standards: list[Standard]
) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    selected_by_family = {item.family: item for item in selected_standards}
    for candidate in all_standards:
        if candidate.family not in selected_by_family:
            continue
        selected = selected_by_family[candidate.family]
        if candidate.id == selected.id:
            continue
        versions = [
            candidate.citation,
            f"{candidate.code} {candidate.version}",
            f"{candidate.code}, {candidate.version}",
        ]
        matched = next((value for value in versions if value.lower() in text.lower()), None)
        if matched:
            findings.append(
                FindingDraft(
                    citation=selected.citation,
                    description=(
                        f"Document references {matched}, but the selected baseline for "
                        f"{selected.family} is {selected.citation}."
                    ),
                    anchor=matched,
                )
            )
    return findings


def detect_ampacity_issues(text: str, selected_standards: list[Standard]) -> list[FindingDraft]:
    tags = _selected_tags(selected_standards)
    if "electrical" not in tags:
        return []

    breaker_match = re.search(r"(\d{2,4})\s*A(?:MP)?\s*(?:breaker|cb|circuit breaker)", text, re.I)
    wire_match = re.search(r"(\d{2,4})\s*(?:k?cmil|mcm)", text, re.I)
    if not breaker_match or not wire_match:
        return []

    breaker_size = int(breaker_match.group(1))
    wire_size = int(wire_match.group(1))
    ampacity = AMPACITY_TABLE.get(wire_size)
    if ampacity is None or ampacity >= breaker_size:
        return []
    anchor = breaker_match.group(0)
    return [
        FindingDraft(
            citation="NEC 310.16 / conductor ampacity",
            description=(
                f"Drawing shows {wire_size} kcmil or mcm conductor on a {breaker_size}A "
                "breaker. The bundled ampacity table flags that conductor as undersized "
                "for the shown overcurrent protection."
            ),
            anchor=anchor,
        )
    ]


def _parse_fraction(value: str) -> float:
    top, bottom = value.split("/")
    return float(top) / float(bottom)


def detect_slope_issues(text: str, selected_standards: list[Standard]) -> list[FindingDraft]:
    tags = _selected_tags(selected_standards)
    if "plumbing" not in tags and "drainage" not in tags:
        return []

    findings: list[FindingDraft] = []
    for line in text.splitlines():
        if "slope" not in line.lower():
            continue
        slope_match = re.search(r"(\d+/\d+)\s*(?:in|inch|\"?)\s*/\s*ft", line, re.I)
        if not slope_match:
            continue
        size_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|\")", line, re.I)
        slope = _parse_fraction(slope_match.group(1))
        size_inches = float(size_match.group(1)) if size_match else 0.0
        minimum = 1 / 8 if size_inches >= 3 else 1 / 4
        if slope < minimum:
            findings.append(
                FindingDraft(
                    citation="IPC 704.1 / minimum drainage slope",
                    description=(
                        f"Indicated slope {slope_match.group(1)} in/ft is below the "
                        f"bundled minimum of {minimum:g} in/ft for the pipe size shown."
                    ),
                    anchor=slope_match.group(0),
                )
            )
    return findings


def detect_accessibility_door_width_issues(
    text: str,
    selected_standards: list[Standard],
) -> list[FindingDraft]:
    tags = _selected_tags(selected_standards)
    if "accessibility" not in tags:
        return []

    findings: list[FindingDraft] = []
    for line in text.splitlines():
        lowered = line.lower()
        if "door" not in lowered or "clear" not in lowered:
            continue
        width_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|\")", line, re.I)
        if not width_match:
            continue
        clear_width = float(width_match.group(1))
        if clear_width < 32:
            findings.append(
                FindingDraft(
                    citation="ADA 404.2.3 / CBC 11B-404.2.3",
                    description=(
                        f"Door clear width is shown as {clear_width:g} inches, below the "
                        "bundled 32-inch minimum clear opening requirement."
                    ),
                    anchor=width_match.group(0),
                )
            )
    return findings


def detect_ramp_slope_issues(text: str, selected_standards: list[Standard]) -> list[FindingDraft]:
    tags = _selected_tags(selected_standards)
    if "accessibility" not in tags:
        return []

    findings: list[FindingDraft] = []
    for line in text.splitlines():
        if "ramp" not in line.lower():
            continue
        ratio_match = re.search(r"(\d+)\s*:\s*(\d+)", line)
        if ratio_match:
            rise = float(ratio_match.group(1))
            run = float(ratio_match.group(2))
            if rise / run > (1 / 12):
                findings.append(
                    FindingDraft(
                        citation="ADA 405.2 / CBC 11B-405.2",
                        description=(
                            f"Ramp slope {ratio_match.group(0)} is steeper than the bundled "
                            "1:12 maximum running slope."
                        ),
                        anchor=ratio_match.group(0),
                    )
                )
                continue
        percent_match = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
        if percent_match and float(percent_match.group(1)) > 8.33:
            findings.append(
                FindingDraft(
                    citation="ADA 405.2 / CBC 11B-405.2",
                    description=(
                        f"Ramp slope {percent_match.group(1)}% exceeds the bundled 8.33% "
                        "maximum running slope."
                    ),
                    anchor=percent_match.group(0),
                )
            )
    return findings


def detect_corridor_width_issues(
    text: str,
    selected_standards: list[Standard],
) -> list[FindingDraft]:
    tags = _selected_tags(selected_standards)
    if "building" not in tags and "life-safety" not in tags:
        return []

    findings: list[FindingDraft] = []
    for line in text.splitlines():
        lowered = line.lower()
        if "corridor" not in lowered and "hall" not in lowered:
            continue
        width_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|\")", line, re.I)
        if not width_match:
            continue
        width = float(width_match.group(1))
        if width < 44:
            findings.append(
                FindingDraft(
                    citation="IBC 1020 / CBC corridor width / NFPA 101 means of egress",
                    description=(
                        f"Corridor width is shown as {width:g} inches, below the bundled "
                        "44-inch minimum used by this review rule pack."
                    ),
                    anchor=width_match.group(0),
                )
            )
    return findings


def detect_guard_height_issues(text: str, selected_standards: list[Standard]) -> list[FindingDraft]:
    tags = _selected_tags(selected_standards)
    if "building" not in tags and "accessibility" not in tags:
        return []

    findings: list[FindingDraft] = []
    for line in text.splitlines():
        if "guard" not in line.lower():
            continue
        height_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|\")", line, re.I)
        if not height_match:
            continue
        height = float(height_match.group(1))
        if height < 42:
            findings.append(
                FindingDraft(
                    citation="IBC 1015.3 / CBC guard height",
                    description=(
                        f"Guard height is shown as {height:g} inches, below the bundled "
                        "42-inch minimum used by this review rule pack."
                    ),
                    anchor=height_match.group(0),
                )
            )
    return findings


def run_rules(
    text: str,
    selected_standards: list[Standard],
    all_standards: list[Standard],
) -> list[FindingDraft]:
    findings: list[FindingDraft] = []
    findings.extend(detect_version_mismatches(text, selected_standards, all_standards))
    findings.extend(detect_ampacity_issues(text, selected_standards))
    findings.extend(detect_slope_issues(text, selected_standards))
    findings.extend(detect_accessibility_door_width_issues(text, selected_standards))
    findings.extend(detect_ramp_slope_issues(text, selected_standards))
    findings.extend(detect_corridor_width_issues(text, selected_standards))
    findings.extend(detect_guard_height_issues(text, selected_standards))
    return findings
