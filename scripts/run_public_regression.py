#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

PUBLIC_SAMPLE_URL = (
    "https://pdc.uccs.edu/sites/g/files/kjihxj1346/files/inline-files/"
    "2021-0525_UCCS%20BID%20SET%20-%20Drawings.pdf"
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sample_dir = project_root.parent / "tmp" / "planreview-samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    sample_path = sample_dir / "uccs-bid-set-drawings.pdf"
    if not sample_path.exists():
        with httpx.stream(
            "GET",
            PUBLIC_SAMPLE_URL,
            follow_redirects=True,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            with sample_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)

    os.environ["PLANREVIEW_BASE_DIR"] = str(project_root.parent / "tmp" / "planreview-public-run")

    from planreview.app import create_app
    from planreview.config import get_settings
    from planreview.database import get_engine, init_db
    from planreview.services.catalog import ensure_catalog_seeded

    get_settings.cache_clear()
    get_engine.cache_clear()
    init_db()
    ensure_catalog_seeded()

    client = TestClient(create_app())
    project_response = client.post(
        "/api/projects",
        json={
            "name": "UCCS Public Regression",
            "address": "3650 North Nevada Ave, Colorado Springs, CO 80907",
            "contract_signed_on": "2021-05-04",
            "notes": "Public regression harness",
        },
    )
    project_response.raise_for_status()
    project_id = project_response.json()["project"]["id"]

    with sample_path.open("rb") as handle:
        upload_response = client.post(
            f"/api/projects/{project_id}/documents",
            data={"kind": "drawings"},
            files={"file": (sample_path.name, handle, "application/pdf")},
        )
    upload_response.raise_for_status()

    automation_response = client.post(f"/api/projects/{project_id}/automation")
    automation_response.raise_for_status()

    review_response = client.post(f"/api/projects/{project_id}/review")
    review_response.raise_for_status()
    job_id = review_response.json()["job"]["id"]

    deadline = time.time() + 1800
    last_payload: dict | None = None
    while time.time() < deadline:
        poll_response = client.get(f"/api/jobs/{job_id}")
        poll_response.raise_for_status()
        last_payload = poll_response.json()
        if last_payload["job"]["status"] in {"completed", "failed"}:
            break
        time.sleep(1.0)

    if not last_payload or last_payload["job"]["status"] != "completed":
        raise RuntimeError(f"Public regression run did not complete successfully: {last_payload}")

    exports_response = client.get(f"/api/projects/{project_id}/exports")
    exports_response.raise_for_status()
    excel_path = Path(exports_response.json()["exports"]["excel"])
    desktop_target = Path.home() / "Desktop" / "PlanReview-UCCS-comment-log.xlsx"
    shutil.copy2(excel_path, desktop_target)

    print(f"Project: {project_id}")
    print(f"Findings: {last_payload['job']['findings_count']}")
    print(f"Excel: {desktop_target}")


if __name__ == "__main__":
    main()
