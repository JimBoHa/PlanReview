from __future__ import annotations

import uvicorn

from planreview.app import create_app
from planreview.config import get_settings
from planreview.database import init_db
from planreview.services.catalog import ensure_catalog_seeded


def main() -> None:
    settings = get_settings()
    init_db()
    ensure_catalog_seeded()
    uvicorn.run(create_app(), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
