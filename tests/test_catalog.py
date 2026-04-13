from __future__ import annotations

from datetime import date

from planreview.models import Project
from planreview.services.catalog import suggest_standards


def test_suggestions_respect_contract_date(app_client) -> None:
    project = Project(
        name="Airport rehab",
        address="1 Aviation Way, Los Angeles, CA",
        contract_signed_on=date(2020, 6, 1),
        is_federal=True,
        is_faa=True,
        requires_local_permit=True,
    )
    suggested_ids = {item.standard_id for item in suggest_standards(project)}
    assert "nfpa70-2020" in suggested_ids
    assert "nfpa70-2023" not in suggested_ids
    assert "faa-std-019f-chg2" in suggested_ids
    assert "faa-std-019f-chg3" not in suggested_ids
