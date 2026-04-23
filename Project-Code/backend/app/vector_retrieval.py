from __future__ import annotations

from collections import Counter
from pathlib import Path
from hashlib import sha256
import json
import math
import re
from typing import Any

import requests

from .settings import settings


TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)


class HashingVectorIndex:
    def __init__(self, dimensions: int = 256):
        self.dimensions = dimensions
        self.items: list[dict[str, Any]] = []
        self.provider = "hashing"
        self.model = f"hashing-{dimensions}"

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        for document in documents:
            vector = _embed_text_hashing(document.get("content", ""), self.dimensions)
            self.items.append(_make_item(document, vector))

    def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
        query_vector = _embed_text_hashing(query, self.dimensions)
        return _search_items(self.items, query_vector, top_k)

    def save(self, path: str) -> None:
        _write_index_payload(
            path,
            {
                "provider": self.provider,
                "model": self.model,
                "dimensions": self.dimensions,
                "items": self.items,
            },
        )

    @classmethod
    def load(cls, path: str) -> "HashingVectorIndex | None":
        payload = _read_index_payload(path)
        if payload is None:
            return None
        index = cls(dimensions=int(payload.get("dimensions", 256)))
        index.items = list(payload.get("items", []))
        return index


class OpenAIEmbeddingIndex:
    def __init__(self, api_key: str, model: str, dimensions: int):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.items: list[dict[str, Any]] = []
        self.provider = "openai"

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        texts = [str(document.get("content", "")) for document in documents]
        vectors = _embed_texts_openai(texts, self.model, self.api_key, self.dimensions)
        for document, vector in zip(documents, vectors):
            self.items.append(_make_item(document, vector))

    def search(self, query: str, top_k: int = 6) -> list[dict[str, Any]]:
        query_vector = _embed_texts_openai([query], self.model, self.api_key, self.dimensions)[0]
        return _search_items(self.items, query_vector, top_k)

    def save(self, path: str) -> None:
        _write_index_payload(
            path,
            {
                "provider": self.provider,
                "model": self.model,
                "dimensions": self.dimensions,
                "items": self.items,
            },
        )

    @classmethod
    def load(cls, path: str, api_key: str) -> "OpenAIEmbeddingIndex | None":
        payload = _read_index_payload(path)
        if payload is None:
            return None
        index = cls(
            api_key=api_key,
            model=str(payload.get("model") or settings.openai_embedding_model),
            dimensions=int(payload.get("dimensions", settings.rag_vector_dimensions)),
        )
        index.items = list(payload.get("items", []))
        return index


def build_or_load_index(
    *,
    documents: list[dict[str, Any]],
    store_key: str,
    force_rebuild: bool = False,
) -> tuple[HashingVectorIndex | OpenAIEmbeddingIndex, str]:
    path = _event_store_path(store_key)
    docs_signature = _documents_signature(documents)

    if settings.openai_api_key:
        loaded = None if force_rebuild else OpenAIEmbeddingIndex.load(path, settings.openai_api_key)
        if loaded and _payload_matches_documents(loaded.items, docs_signature):
            return loaded, "openai-persistent"
        index = OpenAIEmbeddingIndex(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dimensions=settings.rag_vector_dimensions,
        )
        documents_with_signature = _attach_signature(documents, docs_signature)
        index.add_documents(documents_with_signature)
        index.save(path)
        return index, "openai-fresh"

    loaded_hashing = None if force_rebuild else HashingVectorIndex.load(path)
    if loaded_hashing and _payload_matches_documents(loaded_hashing.items, docs_signature):
        return loaded_hashing, "hashing-persistent"
    index = HashingVectorIndex(dimensions=settings.rag_vector_dimensions)
    documents_with_signature = _attach_signature(documents, docs_signature)
    index.add_documents(documents_with_signature)
    index.save(path)
    return index, "hashing-fresh"


def resolve_store_path(store_key: str) -> str:
    return _event_store_path(store_key)


def _attach_signature(documents: list[dict[str, Any]], signature: str) -> list[dict[str, Any]]:
    return [
        {
            **document,
            "metadata": {
                **dict(document.get("metadata", {})),
                "documentsSignature": signature,
            },
        }
        for document in documents
    ]


def _payload_matches_documents(items: list[dict[str, Any]], signature: str) -> bool:
    if not items:
        return False
    stored_signature = str(items[0].get("metadata", {}).get("documentsSignature", ""))
    return stored_signature == signature


def _documents_signature(documents: list[dict[str, Any]]) -> str:
    payload = [
        {
            "id": document.get("id", ""),
            "title": document.get("title", ""),
            "content": document.get("content", ""),
        }
        for document in documents
    ]
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _event_store_path(store_key: str) -> str:
    safe_key = re.sub(r"[^a-zA-Z0-9._-]+", "_", store_key)
    return str(Path(settings.rag_vector_store_dir) / f"{safe_key}.json")


def _make_item(document: dict[str, Any], vector: list[float]) -> dict[str, Any]:
    return {
        "id": document.get("id", ""),
        "sourceType": document.get("sourceType", ""),
        "title": document.get("title", ""),
        "content": document.get("content", ""),
        "metadata": document.get("metadata", {}),
        "vector": vector,
    }


def _search_items(items: list[dict[str, Any]], query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in items:
        score = _cosine_similarity(query_vector, item["vector"])
        if score <= 0:
            continue
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [
        {
            "id": item["id"],
            "sourceType": item["sourceType"],
            "title": item["title"],
            "content": item["content"],
            "metadata": item["metadata"],
            "score": round(score, 4),
        }
        for score, item in scored[:top_k]
    ]


def _read_index_payload(path: str) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    return json.loads(target.read_text(encoding="utf-8"))


def _write_index_payload(path: str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _embed_text_hashing(text: str, dimensions: int) -> list[float]:
    counts = Counter(token.lower() for token in TOKEN_RE.findall(text) if len(token) > 1)
    vector = [0.0] * dimensions
    for token, count in counts.items():
        bucket = hash(token) % dimensions
        vector[bucket] += float(count)
    return _normalize(vector)


def _embed_texts_openai(texts: list[str], model: str, api_key: str, dimensions: int) -> list[list[float]]:
    response = requests.post(
        f"{settings.openai_base_url.rstrip('/')}/embeddings",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "input": texts,
            "model": model,
            "dimensions": dimensions,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data", [])
    return [list(item.get("embedding", [])) for item in data]


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
