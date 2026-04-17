from __future__ import annotations

from datetime import date

import fitz

from planreview.models import Standard
from planreview.services.document_analysis import (
    analyze_page,
    build_document_semantics,
    build_project_semantic_context,
)
from planreview.services.rules import run_rules


def test_semantic_rules_flag_missing_detail_sheet() -> None:
    drawing_analysis = _analyze_text_page(
        "A101\nFIRST FLOOR PLAN\nDETAIL 3/A601\nSCALE: 1/8\" = 1'-0\"",
        kind="drawings",
    )
    drawing_document = build_document_semantics([drawing_analysis], kind="drawings")
    project_context = build_project_semantic_context([drawing_document])

    findings = run_rules(
        drawing_analysis.text,
        [_building_standard()],
        [_building_standard()],
        intelligence=drawing_analysis.intelligence,
        semantics=drawing_analysis.semantics,
        document_semantics=drawing_document,
        project_context=project_context,
        document_kind="drawings",
    )

    assert any(
        item.citation == "Drawing callout coordination review" and "A601" in item.description
        for item in findings
    )


def test_semantic_rules_compare_drawing_refs_to_specs() -> None:
    drawing_analysis = _analyze_text_page(
        "A101\nFIRST FLOOR PLAN\nSEE SECTION 09 29 00\nSCALE: 1/8\" = 1'-0\"",
        kind="drawings",
    )
    drawing_document = build_document_semantics([drawing_analysis], kind="drawings")
    project_context = build_project_semantic_context([drawing_document])

    findings = run_rules(
        drawing_analysis.text,
        [_building_standard()],
        [_building_standard()],
        intelligence=drawing_analysis.intelligence,
        semantics=drawing_analysis.semantics,
        document_semantics=drawing_document,
        project_context=project_context,
        document_kind="drawings",
    )
    assert any(
        item.citation == "Drawing-to-spec coordination review" and "09 29 00" in item.description
        for item in findings
    )

    spec_analysis = _analyze_text_page(
        "SECTION 09 29 00\nGYPSUM BOARD\nPART 1 - GENERAL",
        kind="specs",
    )
    spec_document = build_document_semantics([spec_analysis], kind="specs")
    project_context = build_project_semantic_context([drawing_document, spec_document])
    findings = run_rules(
        drawing_analysis.text,
        [_building_standard()],
        [_building_standard()],
        intelligence=drawing_analysis.intelligence,
        semantics=drawing_analysis.semantics,
        document_semantics=drawing_document,
        project_context=project_context,
        document_kind="drawings",
    )
    assert not any(item.citation == "Drawing-to-spec coordination review" for item in findings)


def test_sheet_number_extraction_prefers_title_block_style_sheet_ids() -> None:
    analysis = _analyze_text_page(
        "GENERAL NOTES\n"
        "SHEET NUMBER\n"
        "PROJECT NUMBER\n"
        "SHEET TITLE\n"
        "PLUMBING SCHEDULES\n"
        "P7.1\n"
        "CD\n"
        "Author\n",
        kind="drawings",
    )
    assert analysis.semantics.sheet_number == "P7.1"


def test_sheet_number_extraction_ignores_grid_tags_when_dotted_sheet_id_exists() -> None:
    analysis = _analyze_text_page(
        "N-1\nS-4\nGENERAL NOTES\nSHEET NUMBER\nSHEET TITLE\nSTRUCTURAL NOTES\nS1.0\nCD\n",
        kind="drawings",
    )
    assert analysis.semantics.sheet_number == "S1.0"


def test_detail_reference_ignores_finish_codes() -> None:
    analysis = _analyze_text_page(
        "REFER TO THE AF SERIES SHEETS FOR INTERIOR FINISH INFORMATION.\n"
        "P-1/T-2/3\n"
        "MWP-1/2\n"
        "T-1\n",
        kind="drawings",
    )
    assert analysis.semantics.detail_references == []


def _building_standard() -> Standard:
    return Standard(
        id="ibc-2021",
        issuer="ICC",
        family="IBC",
        code="IBC",
        version="2021",
        title="International Building Code",
        publication_date=date(2020, 10, 1),
        effective_date=date(2020, 10, 1),
        citation="IBC 2021",
        tags_csv="building,local,permit",
    )


def _analyze_text_page(text: str, *, kind: str):
    document = fitz.open()
    page = document.new_page()
    cursor_y = 72
    for line in text.splitlines():
        page.insert_text((72, cursor_y), line, fontsize=12)
        cursor_y += 16
    analysis = analyze_page(page, kind=kind)
    document.close()
    return analysis
