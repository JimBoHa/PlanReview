# PlanReview

PlanReview is a local-first macOS application for reviewing drawings and specifications against a selected compliance baseline. It runs entirely on the user's machine, exposes a browser-based interface, stores project data in SQLite, and exports:

- an Excel comment log,
- a marked-up drawing set,
- a marked-up specification set.

## Scope of this build

This repository ships a usable local review workflow with:

- project intake for address, contract date, authority questions, and uploads,
- a searchable standards catalog with version-aware suggestions,
- a local PDF processing pipeline that extracts text, detects selected rule-pack discrepancies, captures thumbnails, and writes findings to SQLite,
- live review status with estimated completion time,
- export of Excel and marked-up PDFs,
- macOS packaging, signing, and notarization scripts.

The standards catalog stores metadata and version history. Automated rule coverage is strongest for the bundled public-domain and model-code rule packs and is designed to be extended. Many commercial standards are copyright-restricted, so the application stores citations and version metadata without bundling full copyrighted texts.

## Quick start

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
planreview-serve
```

The app serves at `http://127.0.0.1:8765`.

To launch it like a desktop app:

```bash
planreview-app
```

## Test

```bash
pytest
```

## Build macOS app and DMG

```bash
scripts/build_app.sh
scripts/build_dmg.sh
```

## Notarize

```bash
scripts/notarize_dmg.sh release/PlanReview.dmg
```

## Standards catalog

The seeded catalog is generated in [catalog_seed.py](/Users/InfrastructureDashboard/PlanReview/src/planreview/services/catalog_seed.py) and currently includes 143 versioned standards records, including expanded coverage for:

- California Title 24 / CBSC parts and editions
- ICC code families, including IBC and ICC A117.1
- NFPA code families, including NFPA 70, 72, and 101
- ADA standards and implementing regulations

Each entry includes:

- issuing body,
- family,
- edition/version string,
- publication and effective dates,
- status,
- citation metadata,
- suggestion tags used by the jurisdiction questionnaire.

## Architecture

- FastAPI + Jinja templates for the local web UI
- SQLModel + SQLite for storage
- PyMuPDF for PDF extraction, thumbnail capture, and markup
- Background worker for review jobs
- OpenPyXL for Excel export
