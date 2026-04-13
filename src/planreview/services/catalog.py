from __future__ import annotations

from datetime import date

from sqlmodel import select

from planreview.database import session_scope
from planreview.models import Project, Standard
from planreview.schemas import SuggestedStandard
from planreview.services.catalog_seed import build_seed_catalog


def ensure_catalog_seeded() -> None:
    with session_scope() as session:
        existing = session.exec(select(Standard.id)).first()
        if existing:
            return
        for item in build_seed_catalog():
            session.add(Standard(**item))


def search_catalog(q: str = "", limit: int = 50) -> list[Standard]:
    query = q.strip().lower()
    with session_scope() as session:
        standards = session.exec(select(Standard)).all()
    ranked = sorted(
        standards,
        key=lambda item: (
            item.issuer,
            item.family,
            item.code,
            item.effective_date or date.min,
        ),
        reverse=True,
    )
    if not query:
        return list(ranked)[:limit]
    matches = [
        item
        for item in ranked
        if query in " ".join(
            [item.issuer, item.family, item.code, item.version, item.title, item.citation]
        ).lower()
    ]
    return matches[:limit]


def _latest_by_family(tag: str, contract_date: date | None) -> list[Standard]:
    with session_scope() as session:
        standards = session.exec(select(Standard)).all()
    tagged = [item for item in standards if tag in item.tags_csv.split(",")]
    winners: dict[str, Standard] = {}
    for item in tagged:
        if contract_date and item.effective_date and item.effective_date > contract_date:
            continue
        current = winners.get(item.family)
        if not current:
            winners[item.family] = item
            continue
        current_date = current.effective_date or date.min
        item_date = item.effective_date or date.min
        if item_date >= current_date:
            winners[item.family] = item
    return list(winners.values())


def suggest_standards(project: Project) -> list[SuggestedStandard]:
    picks: dict[str, SuggestedStandard] = {}
    address = project.address.lower()

    def add_many(tag: str, rationale: str) -> None:
        for item in _latest_by_family(tag, project.contract_signed_on):
            picks[item.id] = SuggestedStandard(standard_id=item.id, rationale=rationale)

    if project.requires_local_permit:
        permit_tags = [
            "building",
            "fire",
            "mechanical",
            "plumbing",
            "energy",
            "electrical",
            "accessibility",
        ]
        rationale = (
            "Suggested because local permitting and multidisciplinary review were indicated."
        )
        for tag in permit_tags:
            add_many(tag, rationale)
    if ", ca" in address or " california" in address:
        add_many(
            "california",
            (
                "Suggested because the project address appears to be in California "
                "and Title 24 likely applies."
            ),
        )
    if project.is_federal:
        add_many("federal", "Suggested because the project is federal.")
    if project.is_military:
        add_many("military", "Suggested because the project is military and UFC/UFGS likely apply.")
    if project.is_faa:
        add_many("faa", "Suggested because the project was marked as FAA-related.")

    return list(picks.values())


def compare_selection_to_suggestions(project: Project, selected_ids: set[str]) -> dict:
    suggestions = suggest_standards(project)
    suggested_ids = {item.standard_id for item in suggestions}
    standards = {item.id: item for item in search_catalog(limit=5000)}
    items = []
    for standard_id in sorted(suggested_ids | selected_ids):
        standard = standards.get(standard_id)
        if not standard:
            continue
        if standard_id in selected_ids and standard_id in suggested_ids:
            status = "matched"
            reason = "Included both by the user and by the questionnaire."
        elif standard_id in suggested_ids:
            status = "suggested-not-selected"
            reason = next(item.rationale for item in suggestions if item.standard_id == standard_id)
        else:
            status = "selected-not-suggested"
            reason = "Selected manually but not inferred from the questionnaire."
        items.append(
            {
                "status": status,
                "reason": reason,
                "id": standard.id,
                "code": standard.code,
                "version": standard.version,
                "citation": standard.citation,
            }
        )
    return {"items": items}
