from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from sqlmodel import select

from planreview.config import get_settings
from planreview.database import session_scope
from planreview.models import (
    Discrepancy,
    Project,
    ProjectStandard,
    ReviewJob,
    Standard,
    UploadedDocument,
)
from planreview.schemas import ProjectCreate, StandardsSelection
from planreview.services.catalog import (
    compare_selection_to_suggestions,
    search_catalog,
    suggest_standards,
)
from planreview.services.documents import save_uploaded_document
from planreview.services.export import export_project_outputs
from planreview.services.jobs import start_review_job

router = APIRouter()


def _dump(model) -> dict:
    payload = model.model_dump(mode="json")
    if hasattr(model, "id"):
        payload["id"] = model.id
    return payload


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse("index.html", {"request": request})


@router.post("/api/projects")
def create_project(payload: ProjectCreate) -> dict:
    project = Project(**payload.model_dump())
    with session_scope() as session:
        session.add(project)
        session.flush()
        session.refresh(project)
    return {"project": _dump(project)}


@router.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        selected = session.exec(
            select(Standard, ProjectStandard)
            .join(ProjectStandard, Standard.id == ProjectStandard.standard_id)
            .where(ProjectStandard.project_id == project_id)
        ).all()
        documents = session.exec(
            select(UploadedDocument).where(UploadedDocument.project_id == project_id)
        ).all()
    return {
        "project": _dump(project),
        "selected_standards": [
            {**_dump(standard), "source": relation.source, "user_state": relation.user_state}
            for standard, relation in selected
        ],
        "documents": [_dump(document) for document in documents],
    }


@router.post("/api/projects/{project_id}/documents")
async def upload_document(
    project_id: str,
    kind: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        document = save_uploaded_document(session, project_id=project_id, kind=kind, file=file)
    return {"document": _dump(document)}


@router.get("/api/catalog/search")
def catalog_search(q: str = "", limit: int = 50) -> dict:
    return {"items": [item.model_dump() for item in search_catalog(q=q, limit=limit)]}


@router.post("/api/projects/{project_id}/suggest-standards")
def suggest_for_project(project_id: str) -> dict:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
    suggestions = suggest_standards(project)
    return {"suggestions": [item.model_dump() for item in suggestions]}


@router.post("/api/projects/{project_id}/standards")
def update_standards(project_id: str, payload: StandardsSelection) -> dict:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        existing = session.exec(
            select(ProjectStandard).where(ProjectStandard.project_id == project_id)
        ).all()
        for relation in existing:
            session.delete(relation)
        for item in payload.items:
            session.add(ProjectStandard(project_id=project_id, **item.model_dump()))
    return {"ok": True}


@router.get("/api/projects/{project_id}/standards/diff")
def diff_standards(project_id: str) -> dict:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        selected_ids = {
            relation.standard_id
            for relation in session.exec(
                select(ProjectStandard).where(ProjectStandard.project_id == project_id)
            ).all()
        }
    comparison = compare_selection_to_suggestions(project, selected_ids)
    return comparison


@router.post("/api/projects/{project_id}/review")
def start_review(project_id: str) -> dict:
    job = start_review_job(project_id)
    return {"job": _dump(job)}


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with session_scope() as session:
        job = session.get(ReviewJob, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        discrepancies = session.exec(
            select(Discrepancy).where(Discrepancy.job_id == job_id).order_by(Discrepancy.row_number)
        ).all()
    return {
        "job": _dump(job),
        "discrepancies": [_dump(item) for item in discrepancies],
    }


@router.get("/api/projects/{project_id}/exports")
def build_exports(project_id: str) -> dict:
    paths = export_project_outputs(project_id)
    return {"exports": paths}


@router.get("/api/projects/{project_id}/discrepancies")
def list_discrepancies(project_id: str) -> dict:
    with session_scope() as session:
        rows = session.exec(
            select(Discrepancy)
            .where(Discrepancy.project_id == project_id)
            .order_by(Discrepancy.row_number)
        ).all()
    return {"items": [_dump(row) for row in rows]}


@router.get("/artifacts/{project_id}/{filename}")
def download_artifact(project_id: str, filename: str) -> FileResponse:
    settings = get_settings()
    path = settings.projects_dir / project_id / "artifacts" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@router.get("/downloads/{project_id}/{filename}")
def download_export(project_id: str, filename: str) -> FileResponse:
    settings = get_settings()
    path = settings.projects_dir / project_id / "exports" / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)
