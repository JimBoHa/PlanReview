#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import httpx

from planreview.services.manufacturer_corpus import load_manufacturer_corpus


def _safe_name(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    corpus_dir = project_root / "data" / "manufacturer-corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    failures: list[dict] = []

    timeout = httpx.Timeout(180.0, connect=20.0, read=180.0)
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        for document in load_manufacturer_corpus():
            manufacturer_dir = corpus_dir / _safe_name(document.manufacturer)
            manufacturer_dir.mkdir(parents=True, exist_ok=True)
            try:
                target = manufacturer_dir / _target_name(document, client)
                if not target.exists():
                    with client.stream("GET", document.url) as response:
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if "pdf" not in content_type and "html" not in content_type:
                            raise ValueError(
                                f"Unsupported content type: {content_type or 'unknown'}"
                            )
                        with target.open("wb") as handle:
                            for chunk in response.iter_bytes():
                                handle.write(chunk)
                manifest.append(
                    {
                        "manufacturer": document.manufacturer,
                        "component_label": document.component_label,
                        "component_family": document.component_family,
                        "title": document.title,
                        "url": document.url,
                        "path": str(target),
                    }
                )
            except Exception as exc:
                failures.append(
                    {
                        "manufacturer": document.manufacturer,
                        "component_label": document.component_label,
                        "url": document.url,
                        "error": str(exc),
                    }
                )

    (corpus_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (corpus_dir / "failures.json").write_text(json.dumps(failures, indent=2))
    print(f"Fetched {len(manifest)} manufacturer documents into {corpus_dir}")
    if failures:
        print(f"{len(failures)} manufacturer documents failed. See failures.json")


def _target_name(document, client: httpx.Client) -> str:
    try:
        response = client.head(document.url)
        content_type = response.headers.get("content-type", "").lower()
    except Exception:
        content_type = ""
    suffix = ".html" if "html" in content_type else ".pdf"
    return f"{_safe_name(document.component_label)}{suffix}"


if __name__ == "__main__":
    main()
