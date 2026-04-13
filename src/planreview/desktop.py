from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn

from planreview.app import create_app
from planreview.config import get_settings
from planreview.database import init_db
from planreview.services.catalog import ensure_catalog_seeded


def main() -> None:
    settings = get_settings()
    init_db()
    ensure_catalog_seeded()
    app = create_app()
    config = uvicorn.Config(app=app, host=settings.host, port=settings.port, log_level="info")
    server = uvicorn.Server(config=config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.0)
    webbrowser.open(f"http://{settings.host}:{settings.port}")
    while thread.is_alive():
        time.sleep(0.5)
