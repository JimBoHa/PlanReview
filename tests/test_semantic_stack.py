from __future__ import annotations

from datetime import date

from planreview.models import Standard
from planreview.services.document_analysis import (
    DrawingIntelligence,
    PageSemantics,
)
from planreview.services.graph import build_project_graph
from planreview.services.ontology import detect_symbols, detect_systems
from planreview.services.rules import run_rules
from planreview.services.spec_parser import parse_spec_sections


def test_ontology_detects_symbols_and_systems() -> None:
    text = "Provide GFCI receptacle and panelboard in accessible corridor."
    assert "electrical.receptacle.gfci" in detect_symbols(text)
    assert "electrical.panelboard" in detect_symbols(text)
    assert "electrical.power" in detect_systems(text)
    assert "architectural.accessibility" in detect_systems(text)


def test_spec_parser_extracts_sections_and_requirements() -> None:
    sections = parse_spec_sections(
        "SECTION 26 05 19 LOW-VOLTAGE ELECTRICAL POWER CONDUCTORS AND CABLES\n"
        "Provide copper conductors.\n"
        "Contractor shall verify feeder sizes.\n"
        "SECTION 08 11 13 HOLLOW METAL DOORS AND FRAMES\n"
        "Install doors in accessible routes.\n"
    )
    assert [section.section_number for section in sections] == ["26 05 19", "08 11 13"]
    assert any(req.modal_strength == "directive" for req in sections[0].requirements)
    assert any(req.modal_strength == "mandatory" for req in sections[0].requirements)
    assert "door" in sections[1].entities


def test_graph_rule_flags_orphan_drawing_page_when_specs_exist() -> None:
    drawing_semantics = PageSemantics(
        page_class="plan",
        sheet_number="E101",
        sheet_title="POWER PLAN",
        discipline="electrical",
        symbol_ids=["electrical.panelboard"],
        system_ids=["electrical.power"],
    )
    graph = build_project_graph(
        [("doc-1", 1, drawing_semantics, "panelboard feeder conduit layout")],
        parse_spec_sections(
            "SECTION 08 11 13 HOLLOW METAL DOORS AND FRAMES\nInstall doors in accessible routes."
        ),
    )
    findings = run_rules(
        "",
        [_electrical_standard()],
        [_electrical_standard()],
        intelligence=DrawingIntelligence(
            line_count=100,
            horizontal_line_count=50,
            vertical_line_count=50,
            rectangle_count=6,
            scale_tokens=["1/8 = 1-0"],
            dimension_tokens=["12 in"],
            symbol_labels=["panelboard"],
            inferred_sheet_type="electrical",
            page_has_vector_content=True,
        ),
        semantics=drawing_semantics,
        project_graph=graph,
        page_node_id="page:doc-1:1",
        document_kind="drawings",
    )
    assert any(
        item.citation == "Drawing-to-spec semantic coordination review" for item in findings
    )


def _electrical_standard() -> Standard:
    return Standard(
        id="nfpa70-2023",
        issuer="NFPA",
        family="NEC",
        code="NFPA 70",
        version="2023",
        title="National Electrical Code",
        publication_date=date(2023, 1, 1),
        effective_date=date(2023, 1, 1),
        citation="NFPA 70 2023 (NEC)",
        tags_csv="electrical,local,permit",
    )
