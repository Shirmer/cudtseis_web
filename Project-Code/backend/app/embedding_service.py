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

    if provider in {"vikingdb", "auto"} and _vikingdb_configured():
        try:
            return _embed_with_vikingdb(cleaned)
        except Exception:
            return _fallback_embeddings(cleaned, "vikingdb-fallback")

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


def _vikingdb_configured() -> bool:
    return bool(
        settings.vikingdb_ak
        and settings.vikingdb_sk
        and settings.vikingdb_host
        and settings.vikingdb_region
        and settings.geo_rag_embedding_model
    )


def _embed_with_vikingdb(texts: list[str]) -> EmbeddingResult:
    try:
        from volcengine.viking_db import EmbModel, RawData, VikingDBService
    except Exception as exc:
        raise RuntimeError("vikingdb-python-sdk is not installed") from exc

    service = VikingDBService(
        settings.vikingdb_host,
        settings.vikingdb_region,
        settings.vikingdb_ak,
        settings.vikingdb_sk,
    )
    batch_size = max(1, min(settings.geo_rag_embedding_batch_size, 100))
    vectors: list[list[float]] = []
    model = EmbModel(
        settings.geo_rag_embedding_model,
        params={
            "return_dense": True,
            "return_sparse": False,
            "return_token_usage": False,
        },
    )

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        raw_data = [RawData("text", text) for text in batch]
        response = service.embedding_v2(model, raw_data)
        vectors.extend(_extract_vikingdb_vectors(response))

    if len(vectors) != len(texts):
        raise RuntimeError("VikingDB embedding API returned an unexpected number of vectors")
    return EmbeddingResult(
        vectors=vectors,
        backend="vikingdb",
        model=settings.geo_rag_embedding_model,
    )


def _extract_vikingdb_vectors(response: Any) -> list[list[float]]:
    payload = response
    if hasattr(response, "dict"):
        payload = response.dict()
    elif hasattr(response, "__dict__") and not isinstance(response, dict):
        payload = response.__dict__

    if isinstance(payload, dict):
        candidates = (
            payload.get("data")
            or payload.get("result")
            or payload.get("items")
            or payload.get("embedding")
            or payload.get("embeddings")
            or payload
        )
    else:
        candidates = payload

    if isinstance(candidates, dict):
        vectors = _vectors_from_item(candidates)
        if vectors:
            return vectors
        candidates = list(candidates.values())

    if isinstance(candidates, list):
        vectors: list[list[float]] = []
        for item in candidates:
            vectors.extend(_vectors_from_item(item))
        if vectors:
            return vectors

    raise RuntimeError("Unable to extract dense vectors from VikingDB embedding response")


def _vectors_from_item(item: Any) -> list[list[float]]:
    if hasattr(item, "dict"):
        item = item.dict()
    elif hasattr(item, "__dict__") and not isinstance(item, dict):
        item = item.__dict__

    if isinstance(item, list) and item and all(isinstance(value, (int, float)) for value in item):
        return [[float(value) for value in item]]

    if not isinstance(item, dict):
        return []

    vector_keys = [
        "sentence_dense_embedding",
        "dense_embedding",
        "text_dense_embedding",
        "embedding",
        "vector",
    ]
    for key in vector_keys:
        value = item.get(key)
        if isinstance(value, list) and value and all(isinstance(entry, (int, float)) for entry in value):
            return [[float(entry) for entry in value]]
        if isinstance(value, list) and value and isinstance(value[0], list):
            return [[float(entry) for entry in vector] for vector in value]

    nested_vectors: list[list[float]] = []
    for value in item.values():
        nested_vectors.extend(_vectors_from_item(value))
    return nested_vectors


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
