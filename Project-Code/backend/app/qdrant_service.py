from __future__ import annotations

import atexit
from pathlib import Path
from typing import Any
import json
import math

from .settings import settings


_CLIENT_CACHE: dict[str, Any] = {}


def close_qdrant_clients() -> None:
    for client in list(_CLIENT_CACHE.values()):
        try:
            client.close()
        except Exception:
            pass
    _CLIENT_CACHE.clear()


atexit.register(close_qdrant_clients)


def init_knowledge_store() -> dict[str, Any]:
    client, reason, backend = _get_qdrant_client()
    if client is None:
        _fallback_path().parent.mkdir(parents=True, exist_ok=True)
        return {
            "status": "ready",
            "backend": "local-fallback",
            "collection": settings.qdrant_collection,
            "vectorSize": settings.geo_rag_embedding_dim,
            "message": "Qdrant is unavailable; using local JSON fallback for development.",
            "warning": reason,
        }

    try:
        from qdrant_client.http import models as qmodels

        if not _collection_exists(client):
            client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=qmodels.VectorParams(
                    size=settings.geo_rag_embedding_dim,
                    distance=qmodels.Distance.COSINE,
                ),
            )
        return {
            "status": "ready",
            "backend": backend,
            "collection": settings.qdrant_collection,
            "vectorSize": settings.geo_rag_embedding_dim,
            "message": "Qdrant collection is ready.",
            "warning": "",
        }
    except Exception as exc:
        return {
            "status": "ready",
            "backend": "local-fallback",
            "collection": settings.qdrant_collection,
            "vectorSize": settings.geo_rag_embedding_dim,
            "message": "Qdrant initialization failed; using local JSON fallback for development.",
            "warning": str(exc),
        }


def upsert_vectors(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        status = init_knowledge_store()
        status["points"] = 0
        return status

    client, reason, backend = _get_qdrant_client()
    if client is not None:
        try:
            init_knowledge_store()
            from qdrant_client.http import models as qmodels

            points = [
                qmodels.PointStruct(
                    id=item["point_id"],
                    vector=item["vector"],
                    payload=item["payload"],
                )
                for item in items
            ]
            client.upsert(collection_name=settings.qdrant_collection, points=points, wait=True)
            return {
                "status": "indexed",
                "backend": backend,
                "collection": settings.qdrant_collection,
                "points": len(items),
                "message": "Knowledge units were indexed into Qdrant.",
                "warning": "",
            }
        except Exception as exc:
            reason = str(exc)

    _upsert_fallback(items)
    return {
        "status": "indexed",
        "backend": "local-fallback",
        "collection": settings.qdrant_collection,
        "points": len(items),
        "message": "Knowledge units were indexed into the local fallback store.",
        "warning": reason,
    }


def search_vectors(
    query_vector: list[float],
    *,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    clean_filters = _clean_filters(filters or {})
    client, reason, backend = _get_qdrant_client()
    if client is not None:
        try:
            init_knowledge_store()
            hits = _search_qdrant(client, query_vector, top_k=top_k, filters=clean_filters)
            return {
                "backend": backend,
                "collection": settings.qdrant_collection,
                "results": hits,
                "warning": "",
            }
        except Exception as exc:
            reason = str(exc)

    hits = _search_fallback(query_vector, top_k=top_k, filters=clean_filters)
    return {
        "backend": "local-fallback",
        "collection": settings.qdrant_collection,
        "results": hits,
        "warning": reason,
    }


def _get_qdrant_client() -> tuple[Any | None, str, str]:
    try:
        from qdrant_client import QdrantClient
    except Exception as exc:
        return None, f"qdrant-client is not available: {exc}", "local-fallback"

    try:
        if settings.qdrant_use_local:
            path = Path(settings.qdrant_local_path)
            path.mkdir(parents=True, exist_ok=True)
            cache_key = f"local:{path.resolve()}"
            if cache_key not in _CLIENT_CACHE:
                _CLIENT_CACHE[cache_key] = QdrantClient(path=str(path))
            client = _CLIENT_CACHE[cache_key]
            backend = "qdrant-local"
        else:
            cache_key = f"remote:{settings.qdrant_url}:{settings.qdrant_api_key}"
            if cache_key not in _CLIENT_CACHE:
                _CLIENT_CACHE[cache_key] = QdrantClient(
                    url=settings.qdrant_url,
                    api_key=settings.qdrant_api_key or None,
                    timeout=5.0,
                )
            client = _CLIENT_CACHE[cache_key]
            backend = "qdrant"
        client.get_collections()
        return client, "", backend
    except Exception as exc:
        return None, str(exc), "local-fallback"


def _collection_exists(client: Any) -> bool:
    try:
        return bool(client.collection_exists(collection_name=settings.qdrant_collection))
    except AttributeError:
        collections = client.get_collections().collections
        return any(item.name == settings.qdrant_collection for item in collections)


def _search_qdrant(
    client: Any,
    query_vector: list[float],
    *,
    top_k: int,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    from qdrant_client.http import models as qmodels

    query_filter = _build_qdrant_filter(qmodels, filters)
    try:
        hits = client.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
    except AttributeError:
        response = client.query_points(
            collection_name=settings.qdrant_collection,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )
        hits = getattr(response, "points", response)

    return [
        {
            "score": float(getattr(hit, "score", 0.0) or 0.0),
            "payload": getattr(hit, "payload", {}) or {},
        }
        for hit in hits
    ]


def _build_qdrant_filter(qmodels: Any, filters: dict[str, Any]) -> Any | None:
    conditions = []
    for key, value in filters.items():
        if isinstance(value, list):
            values = [item for item in value if item not in (None, "")]
            if not values:
                continue
            try:
                match = qmodels.MatchAny(any=values)
            except Exception:
                match = qmodels.MatchValue(value=values[0])
        else:
            if value in (None, ""):
                continue
            match = qmodels.MatchValue(value=value)
        conditions.append(qmodels.FieldCondition(key=key, match=match))

    if not conditions:
        return None
    return qmodels.Filter(must=conditions)


def _fallback_path() -> Path:
    return Path(settings.geo_rag_fallback_store_path)


def _load_fallback() -> dict[str, Any]:
    path = _fallback_path()
    if not path.exists():
        return {"points": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"points": []}


def _write_fallback(payload: dict[str, Any]) -> None:
    path = _fallback_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _upsert_fallback(items: list[dict[str, Any]]) -> None:
    payload = _load_fallback()
    existing = {item["point_id"]: item for item in payload.get("points", [])}
    for item in items:
        existing[item["point_id"]] = {
            "point_id": item["point_id"],
            "vector": item["vector"],
            "payload": item["payload"],
        }
    payload["points"] = list(existing.values())
    _write_fallback(payload)


def _search_fallback(
    query_vector: list[float],
    *,
    top_k: int,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    payload = _load_fallback()
    scored: list[tuple[float, dict[str, Any]]] = []
    for item in payload.get("points", []):
        item_payload = item.get("payload", {})
        if not _payload_matches(item_payload, filters):
            continue
        score = _cosine(query_vector, item.get("vector", []))
        scored.append((score, item_payload))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [{"score": score, "payload": payload} for score, payload in scored[:top_k]]


def _clean_filters(filters: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in filters.items() if value not in (None, "", [])}


def _payload_matches(payload: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        actual = payload.get(key)
        if isinstance(expected, list):
            if isinstance(actual, list):
                if not set(expected).intersection(set(actual)):
                    return False
            elif actual not in expected:
                return False
        elif isinstance(actual, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


def _cosine(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    numerator = sum(left[index] * right[index] for index in range(size))
    left_norm = math.sqrt(sum(value * value for value in left[:size]))
    right_norm = math.sqrt(sum(value * value for value in right[:size]))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
