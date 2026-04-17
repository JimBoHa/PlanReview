from __future__ import annotations

from datetime import date

from planreview.models import Standard
from planreview.services.rules import detect_corridor_width_issues


def test_corridor_rule_does_not_match_shall_lines_or_wall_thickness() -> None:
    standard = Standard(
        id="ibc-2021",
        issuer="ICC",
        family="IBC",
        code="IBC",
        version="2021",
        title="International Building Code",
        publication_date=date(2020, 10, 1),
        effective_date=date(2020, 10, 1),
        citation="IBC 2021",
        tags_csv="building,life-safety,local,permit",
    )
    text = (
        'ANY LITE SHALL NOT EXCEED 30 INCHES.\n'
        'CUTOUT SHALL BE SEPARATED BY 6" OR MORE.\n'
        'PROJECT 1/4" INTO CORRIDOR.\n'
        'MULLION ON CORRIDOR SIDE OF WALL.\n'
        '4" WALL THICKNESS.\n'
    )
    findings = detect_corridor_width_issues(text, [standard])
    assert findings == []
