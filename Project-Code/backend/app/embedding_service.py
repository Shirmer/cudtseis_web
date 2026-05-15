from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
import re
from typing import Any

import requests

from .settings import settings


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]
    backend: str
    model: str


def embed_texts(texts: list[str]) -> EmbeddingResult:
    cleaned = [text or "" for text in texts]
    provider = settings.geo_rag_embedding_provider.lower().strip()
    if provider in {"http", "tei"} and settings.geo_rag_embedding_url:
        try:
            return _embed_with_http(cleaned)
        except Exception as exc:
            if not settings.geo_rag_embedding_allow_fallback:
                raise RuntimeError("HTTP embedding service failed and fallback is disabled") from exc
            return _fallback_embeddings(cleaned, "http-fallback")

    if provider in {"openai", "auto"} and settings.openai_api_key and settings.openai_embedding_model:
        try:
            return _embed_with_openai(cleaned)
        except Exception:
            return _fallback_embeddings(cleaned, "hashing-fallback")

    vectors = [_hash_embedding(text, settings.geo_rag_embedding_dim) for text in cleaned]
    return EmbeddingResult(vectors=vectors, backend="hashing", model="local-hash")


def embed_text(text: str) -> EmbeddingResult:
    return embed_texts([text])


def _embed_with_openai(texts: list[str]) -> EmbeddingResult:
    url = settings.openai_base_url.rstrip("/") + "/embeddings"
    payload: dict[str, Any] = {
        "model": settings.openai_embedding_model,
        "input": texts,
    }
    if settings.geo_rag_embedding_dim > 0:
        payload["dimensions"] = settings.geo_rag_embedding_dim

    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    ordered = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
    vectors = [item["embedding"] for item in ordered]
    if len(vectors) != len(texts):
        raise RuntimeError("Embedding API returned an unexpected number of vectors")
    return EmbeddingResult(vectors=vectors, backend="openai-compatible", model=settings.openai_embedding_model)


def _fallback_embeddings(texts: list[str], backend: str) -> EmbeddingResult:
    vectors = [_hash_embedding(text, settings.geo_rag_embedding_dim) for text in texts]
    return EmbeddingResult(vectors=vectors, backend=backend, model="local-hash")


def _embed_with_http(texts: list[str]) -> EmbeddingResult:
    model = settings.geo_rag_embedding_model or "text-embeddings-inference"
    headers = {"Content-Type": "application/json"}
    if settings.geo_rag_embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.geo_rag_embedding_api_key}"
        headers["api-key"] = settings.geo_rag_embedding_api_key

    response = requests.post(
        settings.geo_rag_embedding_url,
        headers=headers,
        json={
            "model": model,
            "input": texts,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    vectors = _extract_http_vectors(data)
    if len(vectors) != len(texts):
        raise RuntimeError("HTTP embedding service returned an unexpected number of vectors")
    return EmbeddingResult(vectors=vectors, backend="http", model=model)


def _extract_http_vectors(data: Any) -> list[list[float]]:
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        ordered = sorted(data["data"], key=lambda item: item.get("index", 0) if isinstance(item, dict) else 0)
        vectors = [
            item.get("embedding")
            for item in ordered
            if isinstance(item, dict) and isinstance(item.get("embedding"), list)
        ]
        if vectors:
            return [[float(value) for value in vector] for vector in vectors]

    if isinstance(data, dict) and isinstance(data.get("embeddings"), list):
        embeddings = data["embeddings"]
        if embeddings and isinstance(embeddings[0], list):
            return [[float(value) for value in vector] for vector in embeddings]

    raise RuntimeError("Unable to extract vectors from HTTP embedding response")


def _hash_embedding(text: str, dimensions: int) -> list[float]:
    size = max(32, dimensions)
    vector = [0.0] * size
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % size
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + min(len(token), 12) / 12.0
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]
