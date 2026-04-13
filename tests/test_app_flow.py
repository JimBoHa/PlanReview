from __future__ import annotations

import time
from pathlib import Path

from tests.conftest import make_pdf


def test_end_to_end_review_and_export(app_client, tmp_path: Path) -> None:
    client = app_client

    create_response = client.post(
        "/api/projects",
        json={
            "name": "Terminal feeder upgrade",
            "address": "100 Main St, Denver, CO 80202",
            "contract_signed_on": "2022-07-15",
            "is_federal": True,
            "is_faa": True,
            "is_military": False,
            "requires_local_permit": True,
            "notes": "Integration test",
        },
    )
    assert create_response.status_code == 200
    project_id = create_response.json()["project"]["id"]

    drawings_pdf = make_pdf(
        tmp_path / "drawings.pdf",
        [
            (
                "SHEET E1\n"
                "450A breaker serving feeder\n"
                "Provide 250 mcm copper feeder\n"
                "Drain slope 2 in pipe slope 1/16 in/ft\n"
                "Grounding to follow FAA-STD-019f, Chg 2\n"
            )
        ],
    )
    specs_pdf = make_pdf(
        tmp_path / "specs.pdf",
        ["Section 01 42 00 references IBC 2018 and other governing requirements."],
    )

    for kind, path in [("drawings", drawings_pdf), ("specs", specs_pdf)]:
        with path.open("rb") as handle:
            upload_response = client.post(
                f"/api/projects/{project_id}/documents",
                data={"kind": kind},
                files={"file": (path.name, handle, "application/pdf")},
            )
        assert upload_response.status_code == 200

    save_response = client.post(
        f"/api/projects/{project_id}/standards",
        json={
            "items": [
                {"standard_id": "nfpa70-2023", "source": "user", "user_state": "selected"},
                {"standard_id": "ipc-2021", "source": "user", "user_state": "selected"},
                {"standard_id": "faa-std-019f-chg3", "source": "user", "user_state": "selected"},
                {"standard_id": "ibc-2021", "source": "user", "user_state": "selected"},
            ]
        },
    )
    assert save_response.status_code == 200

    review_response = client.post(f"/api/projects/{project_id}/review")
    assert review_response.status_code == 200
    job_id = review_response.json()["job"]["id"]

    job_payload = None
    for _ in range(40):
        poll_response = client.get(f"/api/jobs/{job_id}")
        assert poll_response.status_code == 200
        job_payload = poll_response.json()
        if job_payload["job"]["status"] in {"completed", "failed"}:
            break
        time.sleep(0.2)

    assert job_payload is not None
    assert job_payload["job"]["status"] == "completed"
    discrepancies = job_payload["discrepancies"]
    assert len(discrepancies) >= 4
    assert any("FAA-STD-019f, Chg 2" in item["description"] for item in discrepancies)
    assert any("undersized" in item["description"] for item in discrepancies)
    assert any("minimum drainage slope" in item["citation"] for item in discrepancies)
    assert any("IBC 2018" in item["description"] for item in discrepancies)

    exports_response = client.get(f"/api/projects/{project_id}/exports")
    assert exports_response.status_code == 200
    exports = exports_response.json()["exports"]
    assert Path(exports["excel"]).exists()
    assert Path(exports["drawings"]).exists()
    assert Path(exports["specs"]).exists()
