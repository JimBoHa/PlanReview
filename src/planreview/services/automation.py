from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlmodel import select

from planreview.database import session_scope
from planreview.models import Project, ProjectStandard, Standard, UploadedDocument
from planreview.services.catalog import suggest_standards
from planreview.services.document_analysis import extract_document_text


@dataclass
class AutomationResult:
    authorities: list[str]
    standards: list[dict]
    evidence: list[str]


def _document_corpus(
    project_id: str,
) -> tuple[Project, list[UploadedDocument], list[Standard], str]:
    with session_scope() as session:
        project = session.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        documents = session.exec(
            select(UploadedDocument).where(UploadedDocument.project_id == project_id)
        ).all()
        standards = session.exec(select(Standard)).all()
    corpus_parts = [
        extract_document_text(document.stored_path, kind=document.kind.value)
        for document in documents
    ]
    corpus = "\n".join(part for part in corpus_parts if part).lower()
    return project, list(documents), list(standards), corpus


def _infer_project_flags(project: Project, corpus: str) -> Project:
    lowered_address = project.address.lower()
    payload = project.model_dump()
    payload["is_federal"] = project.is_federal or any(
        token in corpus
        for token in [
            "federal government",
            "general services administration",
            "gsa",
            "usc",
            "usace",
        ]
    )
    payload["is_military"] = project.is_military or any(
        token in corpus for token in ["department of defense", "u.s. army corps", "ufc ", "ufgs "]
    )
    payload["is_faa"] = project.is_faa or any(
        token in corpus for token in ["faa", "federal aviation administration", "ac 150/5370"]
    )
    payload["requires_local_permit"] = project.requires_local_permit or any(
        token in lowered_address for token in [", ca", ", tx", ", ny", ", wa", ", fl", ", az"]
    )
    return Project(**payload)


def _match_standard(standard: Standard, corpus: str) -> bool:
    candidates = [
        standard.citation.lower(),
        f"{standard.code} {standard.version}".lower(),
        f"{standard.code}, {standard.version}".lower(),
        standard.title.lower(),
    ]
    return any(candidate and candidate in corpus for candidate in candidates)


def _detected_standards(standards: list[Standard], corpus: str) -> list[Standard]:
    matches = [standard for standard in standards if _match_standard(standard, corpus)]
    winners: dict[str, Standard] = {}
    for standard in matches:
        current = winners.get(standard.family)
        standard_date = standard.effective_date or date.min
        current_date = current.effective_date or date.min if current else date.min
        if not current or standard_date >= current_date:
            winners[standard.family] = standard
    return list(winners.values())


def automate_project_baseline(project_id: str) -> AutomationResult:
    project, _documents, standards, corpus = _document_corpus(project_id)
    inferred_project = _infer_project_flags(project, corpus)
    suggested = suggest_standards(inferred_project)
    suggested_map = {item.standard_id: item.rationale for item in suggested}
    standard_map = {item.id: item for item in standards}
    detected = _detected_standards(standards, corpus)
    detected_by_family = {item.family: item for item in detected}

    final_standards: list[tuple[Standard, str]] = []
    for standard in detected:
        final_standards.append((standard, "automation-detected"))
    for suggested_id, _rationale in suggested_map.items():
        standard = standard_map.get(suggested_id)
        if not standard:
            continue
        if standard.family in detected_by_family:
            continue
        final_standards.append((standard, "automation-suggested"))

    with session_scope() as session:
        existing = session.exec(
            select(ProjectStandard).where(ProjectStandard.project_id == project_id)
        ).all()
        for row in existing:
            session.delete(row)
        for standard, source in final_standards:
            session.add(
                ProjectStandard(
                    project_id=project_id,
                    standard_id=standard.id,
                    source=source,
                    user_state="selected",
                )
            )

    authorities = ["Local building department"]
    if ", ca" in project.address.lower() or " california" in project.address.lower():
        authorities.append("California Building Standards / Title 24")
    if inferred_project.is_federal:
        authorities.append("Federal owner / agency requirements")
    if inferred_project.is_military:
        authorities.append("Department of Defense / UFC-UFGS")
    if inferred_project.is_faa:
        authorities.append("Federal Aviation Administration")
    if any("ada" in item.id or "icc-a1171" in item.id for item, _ in final_standards):
        authorities.append("Accessibility review authority")

    evidence: list[str] = []
    evidence_patterns = [
        "title 24",
        "california building code",
        "ibc",
        "nfpa",
        "ada",
        "icc a117.1",
        "ufc",
        "ufgs",
        "faa",
    ]
    for token in evidence_patterns:
        if token in corpus:
            evidence.append(f"Detected document reference: {token}")
    if ", ca" in project.address.lower() or " california" in project.address.lower():
        evidence.append("Address implies California state jurisdiction.")

    return AutomationResult(
        authorities=authorities,
        standards=[
            {
                "id": standard.id,
                "citation": standard.citation,
                "family": standard.family,
                "version": standard.version,
                "source": source,
            }
            for standard, source in final_standards
        ],
        evidence=evidence,
    )
