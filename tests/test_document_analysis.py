from __future__ import annotations

from datetime import date

import fitz

from planreview.models import Standard
from planreview.services.document_analysis import DrawingIntelligence, analyze_page
from planreview.services.rules import run_rules


def test_analyze_page_uses_ocr_fallback(monkeypatch) -> None:
    document = fitz.open()
    page = document.new_page()

    monkeypatch.setattr(
        "planreview.services.document_analysis._ocr_page_text",
        lambda _page: 'SCALE: 1/8" = 1\'-0"\nGFCI receptacle symbol',
    )

    analysis = analyze_page(page, kind="drawings")

    assert analysis.ocr_text
    assert analysis.intelligence.ocr_used is True
    assert analysis.intelligence.scale_tokens
    assert "gfci" in analysis.intelligence.symbol_labels
    document.close()


def test_run_rules_uses_drawing_intelligence_signals() -> None:
    selected_standards = [
        Standard(
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
    ]
    findings = run_rules(
        "",
        selected_standards,
        selected_standards,
        intelligence=DrawingIntelligence(
            line_count=0,
            horizontal_line_count=0,
            vertical_line_count=0,
            rectangle_count=0,
            scale_tokens=[],
            dimension_tokens=[],
            symbol_labels=[],
            inferred_sheet_type="drawing",
            page_has_vector_content=False,
        ),
        document_kind="drawings",
    )
    assert findings == []

    document = fitz.open()
    page = document.new_page()
    shape = page.new_shape()
    for offset in range(0, 60, 3):
        shape.draw_line((72 + offset, 72), (72 + offset, 220))
        shape.draw_line((72, 72 + offset), (260, 72 + offset))
    shape.finish(width=1, color=(0, 0, 0))
    shape.commit()

    intelligence = analyze_page(page, kind="drawings").intelligence
    findings = run_rules(
        "",
        selected_standards,
        selected_standards,
        intelligence=intelligence,
        document_kind="drawings",
    )

    citations = {item.citation for item in findings}
    assert "Drawing sheet conventions / scale callout review" in citations
    assert "Drawing annotation / dimension coordination review" in citations
    document.close()
