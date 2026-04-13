from __future__ import annotations

import json
import time
from datetime import UTC, datetime

import fitz
from sqlmodel import select

from planreview.config import get_settings
from planreview.database import session_scope
from planreview.models import (
    Discrepancy,
    JobStatus,
    Project,
    ProjectStandard,
    ReviewJob,
    Standard,
    UploadedDocument,
)
from planreview.services.rules import run_rules


def _clip_for_anchor(page: fitz.Page, anchor: str) -> fitz.Rect:
    if anchor:
        hits = page.search_for(anchor)
        if hits:
            rect = hits[0]
            return fitz.Rect(rect.x0 - 36, rect.y0 - 24, rect.x1 + 140, rect.y1 + 36)
    page_rect = page.rect
    return fitz.Rect(
        page_rect.x0 + 24,
        page_rect.y0 + 24,
        min(page_rect.x1, 420),
        min(page_rect.y1, 220),
    )


def _save_thumbnail(project_id: str, row_number: int, page: fitz.Page, clip: fitz.Rect) -> str:
    settings = get_settings()
    thumbnails_dir = settings.projects_dir / project_id / "artifacts"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    target = thumbnails_dir / f"thumb-{row_number}.png"
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), clip=clip, alpha=False)
    pixmap.save(target)
    return f"artifacts/{project_id}/{target.name}"


def _extract_text(page: fitz.Page) -> str:
    return page.get_text("text")


def _load_project_context(
    project_id: str,
) -> tuple[Project, list[UploadedDocument], list[Standard], list[Standard]]:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        documents = session.exec(
            select(UploadedDocument).where(UploadedDocument.project_id == project_id)
        ).all()
        selected_relations = session.exec(
            select(ProjectStandard).where(ProjectStandard.project_id == project_id)
        ).all()
        selected_ids = [item.standard_id for item in selected_relations]
        selected_standards = []
        if selected_ids:
            selected_standards = session.exec(
                select(Standard).where(Standard.id.in_(selected_ids))
            ).all()
        all_standards = session.exec(select(Standard)).all()
    return project, list(documents), list(selected_standards), list(all_standards)


def _reset_findings(project_id: str, job_id: str) -> None:
    with session_scope() as session:
        rows = session.exec(select(Discrepancy).where(Discrepancy.project_id == project_id)).all()
        for row in rows:
            session.delete(row)
        job = session.get(ReviewJob, job_id)
        if job:
            job.findings_count = 0
            job.processed_pages = 0
            job.error_message = ""


def review_project(project_id: str, job_id: str) -> None:
    _project, documents, selected_standards, all_standards = _load_project_context(project_id)
    _reset_findings(project_id, job_id)
    total_pages = sum(document.page_count for document in documents)
    with session_scope() as session:
        job = session.get(ReviewJob, job_id)
        if not job:
            raise ValueError("Job not found")
        job.total_pages = total_pages
        job.processed_pages = 0
        job.findings_count = 0
        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or datetime.now(UTC)

    row_number = 1
    started = time.time()
    processed_pages = 0
    for document in documents:
        with fitz.open(document.stored_path) as pdf:
            for index, page in enumerate(pdf, start=1):
                text = _extract_text(page)
                page_label = page.get_label() or str(index)
                findings = run_rules(text, selected_standards, all_standards)
                for finding in findings:
                    clip = _clip_for_anchor(page, finding.anchor)
                    thumb = _save_thumbnail(project_id, row_number, page, clip)
                    discrepancy = Discrepancy(
                        project_id=project_id,
                        job_id=job_id,
                        row_number=row_number,
                        document_id=document.id,
                        document_kind=document.kind.value,
                        page_label=page_label,
                        page_number=index,
                        citation=finding.citation,
                        description=finding.description,
                        thumbnail_path=thumb,
                        markup_rect=json.dumps([clip.x0, clip.y0, clip.x1, clip.y1]),
                    )
                    with session_scope() as session:
                        session.add(discrepancy)
                        job = session.get(ReviewJob, job_id)
                        if job:
                            job.findings_count = row_number
                    row_number += 1

                processed_pages += 1
                elapsed = max(time.time() - started, 1.0)
                seconds_per_page = elapsed / max(processed_pages, 1)
                eta_seconds = int((total_pages - processed_pages) * seconds_per_page)
                with session_scope() as session:
                    job = session.get(ReviewJob, job_id)
                    if job:
                        job.processed_pages = processed_pages
                        job.eta_seconds = max(eta_seconds, 0)

    with session_scope() as session:
        job = session.get(ReviewJob, job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.eta_seconds = 0
