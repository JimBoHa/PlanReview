from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from sqlmodel import select

from planreview.database import session_scope
from planreview.models import ReviewJob, UploadedDocument
from planreview.services.automation import automate_project_baseline
from planreview.services.review import review_project

EXECUTOR = ThreadPoolExecutor(max_workers=1)


def _run_and_finalize(project_id: str, job_id: str) -> None:
    try:
        with session_scope() as session:
            job = session.get(ReviewJob, job_id)
            if job:
                job.phase = "building automated baseline"
        automate_project_baseline(project_id)
        review_project(project_id, job_id)
    except Exception as exc:
        with session_scope() as session:
            job = session.get(ReviewJob, job_id)
            if job:
                job.status = "failed"
                job.phase = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.now(UTC)


def start_review_job(project_id: str) -> ReviewJob:
    with session_scope() as session:
        documents = session.exec(
            select(UploadedDocument).where(UploadedDocument.project_id == project_id)
        ).all()
        total_pages = sum(item.page_count for item in documents)
        job = ReviewJob(
            project_id=project_id,
            total_pages=total_pages,
            phase="queued",
            started_at=datetime.now(UTC),
        )
        session.add(job)
        session.flush()
        session.refresh(job)
        job_id = job.id
    EXECUTOR.submit(_run_and_finalize, project_id, job_id)
    with session_scope() as session:
        job = session.get(ReviewJob, job_id)
        if not job:
            raise ValueError("Job not found after creation")
        return job
