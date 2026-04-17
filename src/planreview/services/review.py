from __future__ import annotations

import json
import time
from dataclasses import dataclass
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
from planreview.services.document_analysis import (
    DocumentSemantics,
    PageAnalysis,
    analyze_page,
    build_document_semantics,
    build_project_semantic_context,
)
from planreview.services.graph import ProjectGraph, build_project_graph
from planreview.services.rules import run_rules
from planreview.services.spec_parser import SpecSectionSemantics, parse_spec_sections


@dataclass
class PreparedPage:
    page_number: int
    page_label: str
    analysis: PageAnalysis


@dataclass
class PreparedDocument:
    document: UploadedDocument
    pages: list[PreparedPage]
    semantics: DocumentSemantics
    full_text: str
    spec_sections: list[SpecSectionSemantics]


def _clip_for_anchor(page: fitz.Page, anchor: str) -> fitz.Rect:
    page_rect = page.rect
    if anchor:
        hits = page.search_for(anchor)
        if hits:
            rect = hits[0]
            clip = fitz.Rect(rect.x0 - 36, rect.y0 - 24, rect.x1 + 140, rect.y1 + 36)
            bounded = _expand_rect(clip & page_rect, page_rect, factor=1.15)
            if bounded.width >= 24 and bounded.height >= 24:
                return bounded
    return _expand_rect(
        fitz.Rect(
        page_rect.x0 + 24,
        page_rect.y0 + 24,
        min(page_rect.x1, 420),
        min(page_rect.y1, 220),
        ),
        page_rect,
        factor=1.15,
    )


def _expand_rect(rect: fitz.Rect, bounds: fitz.Rect, *, factor: float) -> fitz.Rect:
    width_growth = rect.width * (factor - 1.0) / 2
    height_growth = rect.height * (factor - 1.0) / 2
    expanded = fitz.Rect(
        rect.x0 - width_growth,
        rect.y0 - height_growth,
        rect.x1 + width_growth,
        rect.y1 + height_growth,
    )
    return expanded & bounds


def _save_thumbnail(project_id: str, row_number: int, page: fitz.Page, clip: fitz.Rect) -> str:
    settings = get_settings()
    thumbnails_dir = settings.projects_dir / project_id / "artifacts"
    thumbnails_dir.mkdir(parents=True, exist_ok=True)
    target = thumbnails_dir / f"thumb-{row_number}.png"
    safe_clip = clip & page.rect
    if safe_clip.width < 24 or safe_clip.height < 24:
        safe_clip = _expand_rect(
            fitz.Rect(
                page.rect.x0 + 24,
                page.rect.y0 + 24,
                min(page.rect.x1, 420),
                min(page.rect.y1, 220),
            ),
            page.rect,
            factor=1.15,
        )
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), clip=safe_clip, alpha=False)
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


def _prepare_documents(
    documents: list[UploadedDocument],
    job_id: str,
) -> list[PreparedDocument]:
    prepared: list[PreparedDocument] = []
    for document in documents:
        pages: list[PreparedPage] = []
        with fitz.open(document.stored_path) as pdf:
            for index, page in enumerate(pdf, start=1):
                analysis = analyze_page(page, kind=document.kind.value)
                pages.append(
                    PreparedPage(
                        page_number=index,
                        page_label=page.get_label() or str(index),
                        analysis=analysis,
                    )
                )
                with session_scope() as session:
                    job = session.get(ReviewJob, job_id)
                    if job:
                        job.phase = f"extracting semantics from {document.kind.value} page {index}"
        prepared.append(
            PreparedDocument(
                document=document,
                pages=pages,
                semantics=build_document_semantics(
                    [item.analysis for item in pages],
                    kind=document.kind.value,
                ),
                full_text="\n".join(
                    item.analysis.text for item in pages if item.analysis.text
                ),
                spec_sections=parse_spec_sections(
                    "\n".join(item.analysis.text for item in pages if item.analysis.text)
                )
                if document.kind.value == "specs"
                else [],
            )
        )
    return prepared


def _build_graph(prepared_documents: list[PreparedDocument]) -> ProjectGraph:
    drawing_pages = [
        (
            prepared.document.id,
            page.page_number,
            page.analysis.semantics,
            page.analysis.text,
        )
        for prepared in prepared_documents
        if prepared.document.kind.value == "drawings"
        for page in prepared.pages
    ]
    spec_sections = [
        section
        for prepared in prepared_documents
        if prepared.document.kind.value == "specs"
        for section in prepared.spec_sections
    ]
    return build_project_graph(drawing_pages, spec_sections)


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
        job.phase = "analyzing uploads"
        job.started_at = job.started_at or datetime.now(UTC)

    prepared_documents = _prepare_documents(documents, job_id)
    project_context = build_project_semantic_context(
        [item.semantics for item in prepared_documents]
    )
    graph = _build_graph(prepared_documents)
    row_number = 1
    started = time.time()
    processed_pages = 0
    for prepared in prepared_documents:
        document = prepared.document
        with fitz.open(document.stored_path) as pdf:
            for prepared_page in prepared.pages:
                index = prepared_page.page_number
                page = pdf[index - 1]
                page_analysis = prepared_page.analysis
                text = page_analysis.text or _extract_text(page)
                page_label = page_analysis.semantics.sheet_number or prepared_page.page_label
                findings = run_rules(
                    text,
                    selected_standards,
                    all_standards,
                    intelligence=page_analysis.intelligence,
                    semantics=page_analysis.semantics,
                    document_semantics=prepared.semantics,
                    project_context=project_context,
                    project_graph=graph,
                    page_node_id=f"page:{document.id}:{index}",
                    document_kind=document.kind.value,
                )
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
                        job.phase = f"reviewing {document.kind.value} page {index}"

    with session_scope() as session:
        job = session.get(ReviewJob, job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(UTC)
            job.eta_seconds = 0
            job.phase = "completed"
