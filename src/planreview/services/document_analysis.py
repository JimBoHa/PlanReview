from __future__ import annotations

import importlib
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from planreview.services.component_model import predict_components
from planreview.services.ontology import detect_symbols, detect_systems

CODE_PATTERNS = [
    r"\bIBC(?:\s|-)?20\d{2}\b",
    r"\bIFC(?:\s|-)?20\d{2}\b",
    r"\bIMC(?:\s|-)?20\d{2}\b",
    r"\bIPC(?:\s|-)?20\d{2}\b",
    r"\bIECC(?:\s|-)?20\d{2}\b",
    r"\bNFPA\s+\d{1,3}(?:\s+20\d{2})?\b",
    r"\b2010 ADA Standards\b",
    r"\bADA\b",
    r"\bICC A117\.1(?:-\d{4})?\b",
    r"\bFAA-STD-019f,\s*Chg\s*\d+\b",
    r"\bAC 150/5370-10[A-Z]\b",
]
DETAIL_REFERENCE_PATTERN = re.compile(
    r"\b(\d{1,2})\s*/\s*([A-Z]{1,4}-?\d{1,3}(?:\.\d{1,2}){0,3}[A-Z]?)\b"
)
SECTION_REFERENCE_PATTERN = re.compile(
    r"\b(?:SEE\s+|PER\s+|REF(?:ER(?:\s+TO)?)?\s+)?SECTION\s+(\d{2}\s+\d{2}\s+\d{2})\b",
    re.I,
)
SHEET_NUMBER_PATTERN = re.compile(r"\b([A-Z]{1,4}-?\d{1,3}(?:\.\d{1,2}){0,3}[A-Z]?)\b")
SHEET_NUMBER_SCORE_PATTERN = re.compile(r"^[A-Z]{1,4}-?\d{1,3}(?:\.\d{1,2}){0,3}[A-Z]?$")
DETAIL_CONTEXT_PATTERN = re.compile(
    r"\b(?:DETAIL|SECTION|ELEVATION|CALLOUT|RISER|PLAN|SHEET|SIM\.?|TYP\.?)\b",
    re.I,
)
FINISH_CODE_PATTERN = re.compile(r"^[A-Z]{1,4}-\d(?:\.\d)?[A-Z]?$")
DISCIPLINE_PREFIXES = {
    "A": "architectural",
    "AD": "architectural",
    "C": "civil",
    "CS": "civil",
    "E": "electrical",
    "EP": "electrical",
    "ES": "electrical",
    "FA": "fire-alarm",
    "FP": "fire-protection",
    "FS": "fire-protection",
    "G": "general",
    "I": "interiors",
    "L": "landscape",
    "LS": "life-safety",
    "M": "mechanical",
    "P": "plumbing",
    "S": "structural",
    "T": "telecom",
}


@dataclass
class DrawingIntelligence:
    line_count: int
    horizontal_line_count: int
    vertical_line_count: int
    rectangle_count: int
    scale_tokens: list[str]
    dimension_tokens: list[str]
    symbol_labels: list[str]
    inferred_sheet_type: str
    page_has_vector_content: bool
    ocr_used: bool = False


@dataclass
class PageSemantics:
    page_class: str
    sheet_number: str
    sheet_title: str
    discipline: str
    detail_references: list[str] = field(default_factory=list)
    referenced_sheets: list[str] = field(default_factory=list)
    spec_section_references: list[str] = field(default_factory=list)
    code_citations: list[str] = field(default_factory=list)
    room_tags: list[str] = field(default_factory=list)
    symbol_ids: list[str] = field(default_factory=list)
    system_ids: list[str] = field(default_factory=list)
    predicted_component_labels: list[str] = field(default_factory=list)
    has_legend: bool = False
    has_title_block: bool = False


@dataclass
class DocumentSemantics:
    kind: str
    pages: list[PageSemantics]
    sheet_numbers: set[str] = field(default_factory=set)
    referenced_sheets: set[str] = field(default_factory=set)
    spec_sections: set[str] = field(default_factory=set)
    code_citations: set[str] = field(default_factory=set)
    legend_pages: set[int] = field(default_factory=set)


@dataclass
class ProjectSemanticContext:
    sheet_numbers: set[str] = field(default_factory=set)
    spec_sections: set[str] = field(default_factory=set)
    code_citations: set[str] = field(default_factory=set)


@dataclass
class PageAnalysis:
    text: str
    base_text: str
    ocr_text: str
    intelligence: DrawingIntelligence
    semantics: PageSemantics


def _ocr_page_text(page: fitz.Page) -> str:
    try:
        ocrmac = importlib.import_module("ocrmac.ocrmac")
    except ModuleNotFoundError:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        image_path = Path(handle.name)
    try:
        page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False).save(image_path)
        results = ocrmac.text_from_image(str(image_path), language_preference=["en-US"])
        return "\n".join(result[0] for result in results if result and result[0]).strip()
    except Exception:
        return ""
    finally:
        image_path.unlink(missing_ok=True)


def _merge_text(base_text: str, ocr_text: str) -> str:
    if not ocr_text:
        return base_text
    if not base_text:
        return ocr_text
    if ocr_text.lower() in base_text.lower():
        return base_text
    return f"{base_text}\n{ocr_text}"


def _extract_scale_tokens(text: str) -> list[str]:
    patterns = [
        r"scale\s*:?\s*([^\n]+)",
        r"(\d+/\d+\s*\"?\s*=\s*\d+'\s*-\s*\d+\")",
        r"(nts|not to scale)",
    ]
    found: list[str] = []
    lowered = text.lower()
    for pattern in patterns:
        for match in re.finditer(pattern, lowered, re.I):
            token = match.group(1) if match.groups() else match.group(0)
            cleaned = token.strip()
            if cleaned and cleaned not in found:
                found.append(cleaned)
    return found


def _extract_dimension_tokens(text: str) -> list[str]:
    patterns = [
        r"\b\d+'\s*-\s*\d+\"",
        r"\b\d+(?:\.\d+)?\s*(?:in|inch|\")",
        r"\b\d+/\d+\s*(?:in|inch|\")",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            token = match.group(0).strip()
            if token not in found:
                found.append(token)
    return found[:50]


def _extract_symbol_labels(text: str) -> list[str]:
    return [item.rsplit(".", 1)[-1].replace("_", " ") for item in detect_symbols(text)]


def _normalize_sheet_number(value: str) -> str:
    return value.replace(" ", "").upper()


def _sheet_number_score(candidate: str, line: str, index: int, line_count: int) -> int:
    score = 0
    upper = candidate.upper()
    if SHEET_NUMBER_SCORE_PATTERN.fullmatch(upper):
        score += 3
    if "." in upper:
        score += 8
    if "-" in upper:
        score -= 2
    if upper.startswith(("A", "S", "M", "E", "P", "T", "Y", "AF", "G")):
        score += 2
    lowered = line.lower()
    if "sheet" in lowered or "sheet title" in lowered or "sheet number" in lowered:
        score += 4
    if "cd" in lowered or "author" in lowered or "project number" in lowered:
        score += 2
    if index >= max(line_count - 18, 0):
        score += 4
    if len(upper) <= 8:
        score += 1
    if len(upper) <= 4 and "." not in upper:
        score -= 3
    return score


def _extract_sheet_number(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        upper = line.upper()
        if upper.startswith("SHEET "):
            match = SHEET_NUMBER_PATTERN.search(upper)
            if match:
                return _normalize_sheet_number(match.group(1))
        if SHEET_NUMBER_SCORE_PATTERN.fullmatch(upper) and "." in upper:
            return _normalize_sheet_number(upper)
    candidates: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        for match in SHEET_NUMBER_PATTERN.finditer(line.upper()):
            candidate = _normalize_sheet_number(match.group(1))
            if not any(char.isdigit() for char in candidate):
                continue
            candidates.append((_sheet_number_score(candidate, line, index, len(lines)), candidate))
    if candidates:
        dotted_candidates = [item for item in candidates if "." in item[1]]
        if dotted_candidates:
            candidates = dotted_candidates
        candidates.sort(key=lambda item: (item[0], item[1].count("."), len(item[1])), reverse=True)
        return candidates[0][1]
    return ""


def _extract_sheet_title(text: str, sheet_number: str) -> str:
    lines = [line.strip() for line in text.splitlines()[:50] if line.strip()]
    title_keywords = (
        "plan",
        "elevation",
        "section",
        "detail",
        "schedule",
        "legend",
        "abbreviation",
        "diagram",
        "notes",
        "cover",
    )
    for index, line in enumerate(lines):
        normalized = _normalize_sheet_number(line)
        if sheet_number and normalized == sheet_number:
            for candidate in lines[index + 1 : index + 4]:
                lowered = candidate.lower()
                if len(candidate) <= 100 and any(keyword in lowered for keyword in title_keywords):
                    return candidate
    for line in lines:
        lowered = line.lower()
        if len(line) <= 100 and any(keyword in lowered for keyword in title_keywords):
            return line
    return ""


def _infer_discipline(sheet_number: str, intelligence: DrawingIntelligence, text: str) -> str:
    prefix = re.match(r"[A-Z]{1,4}", sheet_number)
    if prefix:
        candidate = prefix.group(0)
        while candidate:
            if candidate in DISCIPLINE_PREFIXES:
                return DISCIPLINE_PREFIXES[candidate]
            candidate = candidate[:-1]
    return intelligence.inferred_sheet_type or _infer_sheet_type(text, "drawings")


def _extract_detail_references(text: str) -> tuple[list[str], list[str]]:
    references: list[str] = []
    sheets: list[str] = []
    for line in text.splitlines():
        upper_line = line.upper()
        if not DETAIL_CONTEXT_PATTERN.search(upper_line):
            continue
        for match in DETAIL_REFERENCE_PATTERN.finditer(upper_line):
            sheet_number = _normalize_sheet_number(match.group(2))
            if FINISH_CODE_PATTERN.fullmatch(sheet_number):
                continue
            if "." not in sheet_number and "-" in sheet_number:
                continue
            reference = f"{match.group(1)}/{sheet_number}"
            if reference not in references:
                references.append(reference)
            if sheet_number not in sheets:
                sheets.append(sheet_number)
    return references[:50], sheets[:50]


def _normalize_section_reference(value: str) -> str:
    return " ".join(value.split())


def _extract_spec_section_references(text: str) -> list[str]:
    found: list[str] = []
    for match in SECTION_REFERENCE_PATTERN.finditer(text.upper()):
        section = match.group(1)
        if not section:
            continue
        normalized = _normalize_section_reference(section)
        if normalized not in found:
            found.append(normalized)
    return found[:50]


def _extract_code_citations(text: str) -> list[str]:
    citations: list[str] = []
    for pattern in CODE_PATTERNS:
        for match in re.finditer(pattern, text, re.I):
            citation = " ".join(match.group(0).split())
            if citation not in citations:
                citations.append(citation)
    return citations[:50]


def _extract_room_tags(text: str) -> list[str]:
    room_pattern = re.compile(r"\b(?:ROOM|RM)\s+([A-Z]?\d{2,4}[A-Z]?)\b", re.I)
    tags: list[str] = []
    for match in room_pattern.finditer(text):
        tag = match.group(1).upper()
        if tag not in tags:
            tags.append(tag)
    return tags[:50]


def _has_title_block(text: str) -> bool:
    lowered = text.lower()
    markers = ["issue date", "plot date", "project no", "issued for", "drawn by", "checked by"]
    return sum(marker in lowered for marker in markers) >= 2


def _infer_page_class(text: str, kind: str, intelligence: DrawingIntelligence) -> str:
    lowered = text.lower()
    if kind == "specs":
        if "section " in lowered[:400]:
            return "spec-section"
        return "specifications"
    if "abbreviation" in lowered:
        return "abbreviations"
    if "legend" in lowered:
        return "legend"
    if "schedule" in lowered:
        return "schedule"
    if "elevation" in lowered:
        return "elevation"
    if "floor plan" in lowered or "reflected ceiling plan" in lowered:
        return "plan"
    if "single line" in lowered or "one-line" in lowered or "diagram" in lowered:
        return "diagram"
    if "detail" in lowered:
        return "detail"
    if "section" in lowered:
        return "section"
    if _has_title_block(text) and not intelligence.dimension_tokens:
        return "cover"
    return "drawing"


def _extract_semantics(
    text: str,
    *,
    kind: str,
    intelligence: DrawingIntelligence,
) -> PageSemantics:
    sheet_number = _extract_sheet_number(text) if kind == "drawings" else ""
    detail_references, referenced_sheets = _extract_detail_references(text)
    spec_sections = _extract_spec_section_references(text)
    code_citations = _extract_code_citations(text)
    page_class = _infer_page_class(text, kind, intelligence)
    return PageSemantics(
        page_class=page_class,
        sheet_number=sheet_number,
        sheet_title=_extract_sheet_title(text, sheet_number),
        discipline=_infer_discipline(sheet_number, intelligence, text),
        detail_references=detail_references,
        referenced_sheets=referenced_sheets,
        spec_section_references=spec_sections,
        code_citations=code_citations,
        room_tags=_extract_room_tags(text),
        symbol_ids=detect_symbols(text),
        system_ids=detect_systems(text),
        predicted_component_labels=[item.label for item in predict_components(text, limit=3)],
        has_legend="legend" in text.lower(),
        has_title_block=_has_title_block(text),
    )


def _infer_sheet_type(text: str, kind: str) -> str:
    lowered = text.lower()
    if kind == "specs":
        return "specifications"
    if "single line" in lowered or "panel" in lowered:
        return "electrical"
    if "floor plan" in lowered or "corridor" in lowered:
        return "architectural"
    if "plumbing" in lowered or "slope" in lowered:
        return "plumbing"
    if "fire alarm" in lowered or "sprinkler" in lowered:
        return "fire-protection"
    return "drawing"


def _analyze_geometry(page: fitz.Page, text: str, kind: str, ocr_used: bool) -> DrawingIntelligence:
    drawings = page.get_drawings()
    line_count = 0
    horizontal = 0
    vertical = 0
    rectangles = 0
    for drawing in drawings:
        for item in drawing.get("items", []):
            operator = item[0]
            if operator == "l":
                line_count += 1
                start, end = item[1], item[2]
                if abs(start.y - end.y) < 0.5:
                    horizontal += 1
                if abs(start.x - end.x) < 0.5:
                    vertical += 1
            elif operator == "re":
                rectangles += 1
    return DrawingIntelligence(
        line_count=line_count,
        horizontal_line_count=horizontal,
        vertical_line_count=vertical,
        rectangle_count=rectangles,
        scale_tokens=_extract_scale_tokens(text),
        dimension_tokens=_extract_dimension_tokens(text),
        symbol_labels=_extract_symbol_labels(text),
        inferred_sheet_type=_infer_sheet_type(text, kind),
        page_has_vector_content=bool(drawings),
        ocr_used=ocr_used,
    )


def analyze_page(page: fitz.Page, *, kind: str) -> PageAnalysis:
    base_text = page.get_text("text").strip()
    should_ocr = len(base_text) < 60 or (not base_text and bool(page.get_images()))
    ocr_text = _ocr_page_text(page) if should_ocr else ""
    merged = _merge_text(base_text, ocr_text).strip()
    intelligence = _analyze_geometry(page, merged, kind, bool(ocr_text))
    semantics = _extract_semantics(merged, kind=kind, intelligence=intelligence)
    return PageAnalysis(
        text=merged,
        base_text=base_text,
        ocr_text=ocr_text,
        intelligence=intelligence,
        semantics=semantics,
    )


def build_document_semantics(
    page_analyses: list[PageAnalysis],
    *,
    kind: str,
) -> DocumentSemantics:
    semantics = [item.semantics for item in page_analyses]
    return DocumentSemantics(
        kind=kind,
        pages=semantics,
        sheet_numbers={
            item.sheet_number for item in semantics if item.sheet_number and kind == "drawings"
        },
        referenced_sheets={
            sheet for item in semantics for sheet in item.referenced_sheets if kind == "drawings"
        },
        spec_sections={
            section for item in semantics for section in item.spec_section_references
        },
        code_citations={citation for item in semantics for citation in item.code_citations},
        legend_pages={
            index
            for index, item in enumerate(semantics, start=1)
            if item.has_legend or item.page_class in {"legend", "abbreviations"}
        },
    )


def build_project_semantic_context(
    documents: list[DocumentSemantics],
) -> ProjectSemanticContext:
    return ProjectSemanticContext(
        sheet_numbers={sheet for document in documents for sheet in document.sheet_numbers},
        spec_sections={
            section
            for document in documents
            if document.kind == "specs"
            for section in document.spec_sections
        },
        code_citations={citation for document in documents for citation in document.code_citations},
    )


def extract_document_text(document_path: str, *, kind: str, max_pages: int | None = None) -> str:
    chunks: list[str] = []
    with fitz.open(document_path) as pdf:
        for index, page in enumerate(pdf, start=1):
            analysis = analyze_page(page, kind=kind)
            if analysis.text:
                chunks.append(analysis.text)
            if max_pages is not None and index >= max_pages:
                break
    return "\n".join(chunks)
