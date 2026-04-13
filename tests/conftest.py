from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PLANREVIEW_BASE_DIR", str(tmp_path / "planreview-data"))

    from planreview.app import create_app
    from planreview.config import get_settings
    from planreview.database import get_engine, init_db
    from planreview.services.catalog import ensure_catalog_seeded

    get_settings.cache_clear()
    get_engine.cache_clear()
    init_db()
    ensure_catalog_seeded()
    return TestClient(create_app())


def make_pdf(path: Path, pages: list[str]) -> Path:
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    document.save(path)
    document.close()
    return path
