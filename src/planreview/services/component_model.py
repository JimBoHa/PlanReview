from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz

from planreview.config import get_settings
from planreview.services.manufacturer_corpus import ManufacturerDocument
from planreview.services.semantic_model import get_local_semantic_encoder


@dataclass
class ComponentSample:
    label: str
    family: str
    manufacturer: str
    source_title: str
    source_url: str
    page_number: int
    text: str


@dataclass
class ComponentPrediction:
    label: str
    family: str
    score: float


def _model_dir() -> Path:
    return get_settings().base_dir / "models" / "component-model"


def _artifact_paths() -> tuple[Path, Path]:
    model_dir = _model_dir()
    model_dir.mkdir(parents=True, exist_ok=True)
    return model_dir / "samples.jsonl", model_dir / "label_profiles.json"


def build_samples_from_pdf(
    pdf_path: Path,
    document: ManufacturerDocument,
    *,
    min_text_chars: int = 30,
) -> list[ComponentSample]:
    from planreview.services.document_analysis import analyze_page

    samples: list[ComponentSample] = []
    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            analysis = analyze_page(page, kind="drawings")
            text = analysis.text.strip()
            if len(text) < min_text_chars:
                continue
            samples.append(
                ComponentSample(
                    label=document.component_label,
                    family=document.component_family,
                    manufacturer=document.manufacturer,
                    source_title=document.title,
                    source_url=document.url,
                    page_number=page_number,
                    text=text[:5000],
                )
            )
    return samples


def build_samples_from_document(
    path: Path,
    document: ManufacturerDocument,
) -> list[ComponentSample]:
    if path.suffix.lower() == ".html":
        return build_samples_from_html(path, document)
    return build_samples_from_pdf(path, document)


def build_samples_from_html(
    html_path: Path,
    document: ManufacturerDocument,
    *,
    min_text_chars: int = 80,
) -> list[ComponentSample]:
    text = _strip_html(html_path.read_text(errors="ignore"))
    if len(text) < min_text_chars:
        return []
    return [
        ComponentSample(
            label=document.component_label,
            family=document.component_family,
            manufacturer=document.manufacturer,
            source_title=document.title,
            source_url=document.url,
            page_number=1,
            text=text[:5000],
        )
    ]


def build_seed_sample(document: ManufacturerDocument) -> ComponentSample:
    return ComponentSample(
        label=document.component_label,
        family=document.component_family,
        manufacturer=document.manufacturer,
        source_title=document.title,
        source_url=document.url,
        page_number=1,
        text=(
            f"{document.manufacturer} {document.title} {document.component_label} "
            f"{document.component_family} product data sheet engineering diagram"
        ),
    )


def save_component_samples(samples: list[ComponentSample]) -> None:
    samples_path, _profiles_path = _artifact_paths()
    with samples_path.open("w") as handle:
        for sample in samples:
            handle.write(json.dumps(asdict(sample)) + "\n")


def train_component_profiles(samples: list[ComponentSample]) -> dict[str, dict]:
    grouped: dict[str, dict[str, object]] = {}
    for sample in samples:
        payload = grouped.setdefault(
            sample.label,
            {
                "label": sample.label,
                "family": sample.family,
                "texts": [],
                "manufacturers": set(),
            },
        )
        payload["texts"].append(sample.text)
        payload["manufacturers"].add(sample.manufacturer)

    profiles: dict[str, dict] = {}
    for label, payload in grouped.items():
        texts = payload["texts"]
        profiles[label] = {
            "label": label,
            "family": payload["family"],
            "text": "\n".join(texts[:40]),
            "manufacturers": sorted(payload["manufacturers"]),
            "sample_count": len(texts),
        }

    _samples_path, profiles_path = _artifact_paths()
    profiles_path.write_text(json.dumps(profiles, indent=2))
    return profiles


def load_component_profiles() -> dict[str, dict]:
    _samples_path, profiles_path = _artifact_paths()
    if not profiles_path.exists():
        return {}
    return json.loads(profiles_path.read_text())


def predict_components(text: str, *, limit: int = 5) -> list[ComponentPrediction]:
    profiles = load_component_profiles()
    if not profiles or not text.strip():
        return []
    encoder = get_local_semantic_encoder()
    candidates = {
        label: f"{payload['label']} {payload['family']}\n{payload['text']}"
        for label, payload in profiles.items()
    }
    ranked = encoder.rank(text[:5000], candidates, threshold=0.18)
    predictions: list[ComponentPrediction] = []
    for match in ranked[:limit]:
        payload = profiles[match.target_id]
        predictions.append(
            ComponentPrediction(
                label=payload["label"],
                family=payload["family"],
                score=match.score,
            )
        )
    return predictions


def _strip_html(value: str) -> str:
    value = re.sub(r"(?is)<script.*?>.*?</script>", " ", value)
    value = re.sub(r"(?is)<style.*?>.*?</style>", " ", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = value.replace("&nbsp;", " ").replace("&amp;", "&")
    return " ".join(value.split())
