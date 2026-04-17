from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import uuid4

from sqlmodel import Field, SQLModel


class DocumentKind(StrEnum):
    DRAWINGS = "drawings"
    SPECS = "specs"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Project(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    address: str
    contract_signed_on: date | None = None
    is_federal: bool = False
    is_military: bool = False
    is_faa: bool = False
    requires_local_permit: bool = True
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class Standard(SQLModel, table=True):
    id: str = Field(primary_key=True)
    issuer: str
    family: str
    code: str
    version: str
    title: str
    publication_date: date | None = None
    effective_date: date | None = None
    status: str = "active"
    is_public_metadata: bool = True
    citation: str
    tags_csv: str = ""
    source_url: str = ""


class ProjectStandard(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    standard_id: str = Field(index=True)
    source: str = "user"
    user_state: str = "selected"


class UploadedDocument(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    project_id: str = Field(index=True)
    kind: DocumentKind
    original_name: str
    stored_path: str
    page_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)


class ReviewJob(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    project_id: str = Field(index=True)
    status: JobStatus = Field(default=JobStatus.PENDING)
    total_pages: int = 0
    processed_pages: int = 0
    findings_count: int = 0
    eta_seconds: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    phase: str = "queued"
    error_message: str = ""


class Discrepancy(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: str = Field(index=True)
    job_id: str = Field(index=True)
    row_number: int = 0
    document_id: str = Field(index=True)
    document_kind: str
    page_label: str
    page_number: int
    citation: str
    description: str
    thumbnail_path: str
    markup_rect: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False)
