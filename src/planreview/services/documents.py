from __future__ import annotations

import re

import fitz
from fastapi import UploadFile
from sqlmodel import Session

from planreview.config import get_settings
from planreview.models import DocumentKind, UploadedDocument


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "document.pdf"


def save_uploaded_document(
    session: Session,
    project_id: str,
    kind: str,
    file: UploadFile,
) -> UploadedDocument:
    settings = get_settings()
    project_dir = settings.projects_dir / project_id / "uploads"
    project_dir.mkdir(parents=True, exist_ok=True)
    filename = _safe_name(file.filename or f"{kind}.pdf")
    target = project_dir / f"{kind}-{filename}"
    content = file.file.read()
    target.write_bytes(content)
    with fitz.open(target) as document:
        page_count = document.page_count
    record = UploadedDocument(
        project_id=project_id,
        kind=DocumentKind(kind),
        original_name=filename,
        stored_path=str(target),
        page_count=page_count,
    )
    session.add(record)
    session.flush()
    session.refresh(record)
    return record
