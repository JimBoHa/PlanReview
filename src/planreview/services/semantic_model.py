from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache

TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9./-]{1,}")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


@dataclass
class SemanticMatch:
    target_id: str
    score: float


class LocalSemanticEncoder:
    def __init__(self) -> None:
        self._backend = None
        self._load_backend()

    def _load_backend(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception:
            self._backend = None
            return
        try:
            self._backend = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception:
            self._backend = None

    def similarity(self, left: str, right: str) -> float:
        if not left.strip() or not right.strip():
            return 0.0
        if self._backend is not None:
            left_embedding, right_embedding = self._backend.encode(
                [left, right],
                normalize_embeddings=True,
            )
            return float(left_embedding @ right_embedding)
        return _fallback_similarity(left, right)

    def rank(
        self,
        source: str,
        candidates: dict[str, str],
        *,
        threshold: float = 0.2,
    ) -> list[SemanticMatch]:
        matches = [
            SemanticMatch(target_id=target_id, score=self.similarity(source, text))
            for target_id, text in candidates.items()
        ]
        return sorted(
            [match for match in matches if match.score >= threshold],
            key=lambda item: item.score,
            reverse=True,
        )


def _fallback_similarity(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    left_counts = _term_counts(left_tokens)
    right_counts = _term_counts(right_tokens)
    numerator = sum(left_counts[token] * right_counts.get(token, 0.0) for token in left_counts)
    left_norm = math.sqrt(sum(value * value for value in left_counts.values()))
    right_norm = math.sqrt(sum(value * value for value in right_counts.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _term_counts(tokens: list[str]) -> dict[str, float]:
    counts: dict[str, float] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0.0) + 1.0
    return counts


@lru_cache
def get_local_semantic_encoder() -> LocalSemanticEncoder:
    return LocalSemanticEncoder()
