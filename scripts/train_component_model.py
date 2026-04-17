#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from planreview.services.component_model import (
    build_samples_from_document,
    build_seed_sample,
    predict_components,
    save_component_samples,
    train_component_profiles,
)
from planreview.services.manufacturer_corpus import (
    ManufacturerDocument,
    load_manufacturer_corpus,
)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    corpus_manifest_path = project_root / "data" / "manufacturer-corpus" / "manifest.json"
    if not corpus_manifest_path.exists():
        raise FileNotFoundError(
            "Manufacturer corpus manifest not found. "
            "Run scripts/fetch_manufacturer_corpus.py first."
        )

    manifest = json.loads(corpus_manifest_path.read_text())
    fetched_documents = [
        ManufacturerDocument(
            manufacturer=item["manufacturer"],
            component_label=item["component_label"],
            component_family=item["component_family"],
            title=item["title"],
            url=item["url"],
        )
        for item in manifest
    ]
    path_map = {item["url"]: Path(item["path"]) for item in manifest}
    configured_documents = list(load_manufacturer_corpus())

    samples = []
    seen_urls: set[str] = set()
    for document in configured_documents:
        seen_urls.add(document.url)
        path = path_map.get(document.url)
        if path and path.exists():
            samples.extend(build_samples_from_document(path, document))
        else:
            samples.append(build_seed_sample(document))
    for document in fetched_documents:
        if document.url in seen_urls:
            continue
        path = path_map[document.url]
        samples.extend(build_samples_from_document(path, document))

    save_component_samples(samples)
    profiles = train_component_profiles(samples)
    print(f"Trained {len(profiles)} component profiles from {len(samples)} page samples.")

    evaluation_hits = 0
    evaluation_total = 0
    for sample in samples[: min(100, len(samples))]:
        predictions = predict_components(sample.text, limit=1)
        if predictions and predictions[0].label == sample.label:
            evaluation_hits += 1
        evaluation_total += 1
    if evaluation_total:
        print(f"Self-check top-1 accuracy: {evaluation_hits / evaluation_total:.2%}")


if __name__ == "__main__":
    main()
