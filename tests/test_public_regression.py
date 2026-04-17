from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

PUBLIC_SAMPLE_PATH = Path(
    os.getenv(
        "PLANREVIEW_PUBLIC_SAMPLE_PDF",
        "/Users/InfrastructureDashboard/tmp/planreview-samples/uccs-bid-set-drawings.pdf",
    )
)


@pytest.mark.skipif(
    os.getenv("PLANREVIEW_RUN_PUBLIC_REGRESSION") != "1" or not PUBLIC_SAMPLE_PATH.exists(),
    reason="public regression sample is opt-in",
)
def test_public_uccs_regression(app_client) -> None:
    client = app_client
    project_response = client.post(
        "/api/projects",
        json={
            "name": "UCCS Public Regression",
            "address": "3650 North Nevada Ave, Colorado Springs, CO 80907",
            "contract_signed_on": "2021-05-04",
            "notes": "Public regression fixture",
        },
    )
    project_response.raise_for_status()
    project_id = project_response.json()["project"]["id"]

    with PUBLIC_SAMPLE_PATH.open("rb") as handle:
        upload_response = client.post(
            f"/api/projects/{project_id}/documents",
            data={"kind": "drawings"},
            files={"file": (PUBLIC_SAMPLE_PATH.name, handle, "application/pdf")},
        )
    upload_response.raise_for_status()

    automation_response = client.post(f"/api/projects/{project_id}/automation")
    automation_response.raise_for_status()
    review_response = client.post(f"/api/projects/{project_id}/review")
    review_response.raise_for_status()
    job_id = review_response.json()["job"]["id"]

    deadline = time.time() + 1800
    payload: dict | None = None
    while time.time() < deadline:
        poll_response = client.get(f"/api/jobs/{job_id}")
        poll_response.raise_for_status()
        payload = poll_response.json()
        if payload["job"]["status"] in {"completed", "failed"}:
            break
        time.sleep(1.0)

    assert payload is not None
    assert payload["job"]["status"] == "completed"
    exports_response = client.get(f"/api/projects/{project_id}/exports")
    exports_response.raise_for_status()
    exports = exports_response.json()["exports"]
    assert Path(exports["excel"]).exists()
    assert Path(exports["drawings"]).exists()
