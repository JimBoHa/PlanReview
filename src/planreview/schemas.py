from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1)
    address: str = Field(min_length=5)
    contract_signed_on: date | None = None
    is_federal: bool = False
    is_military: bool = False
    is_faa: bool = False
    requires_local_permit: bool = True
    notes: str = ""


class StandardChoice(BaseModel):
    standard_id: str
    source: str = "user"
    user_state: str = "selected"


class StandardsSelection(BaseModel):
    items: list[StandardChoice]


class SuggestedStandard(BaseModel):
    standard_id: str
    rationale: str


class SuggestionResponse(BaseModel):
    suggestions: list[SuggestedStandard]


class JobSummary(BaseModel):
    id: str
    status: str
    phase: str
    total_pages: int
    processed_pages: int
    findings_count: int
    eta_seconds: int | None
    error_message: str = ""


class AutomationPreview(BaseModel):
    authorities: list[str]
    standards: list[dict]
    evidence: list[str]
