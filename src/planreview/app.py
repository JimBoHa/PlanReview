from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from planreview.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="PlanReview")
    package_dir = Path(__file__).resolve().parent
    app.mount("/static", StaticFiles(directory=package_dir / "static"), name="static")
    app.include_router(router)
    app.state.templates = Jinja2Templates(directory=str(package_dir / "templates"))
    return app
