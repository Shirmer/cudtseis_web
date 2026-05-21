from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import uuid
from typing import Any


SLUG_RE = re.compile(r"[^a-z0-9]+")


def clean_slug(value: str, *, fallback: str = "item", max_length: int = 80) -> str:
    normalized = value.strip().lower()
    normalized = SLUG_RE.sub("-", normalized).strip("-")
    return (normalized or fallback)[:max_length].strip("-") or fallback


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def paper_id_from_metadata(metadata: dict[str, Any]) -> str:
    doi = str(metadata.get("doi") or "").strip().lower()
    if doi:
        return f"doi-{clean_slug(doi, fallback='paper')}"

    semantic_scholar_id = str(metadata.get("semanticScholarId") or metadata.get("semantic_scholar_id") or "").strip()
    if semantic_scholar_id:
        return f"s2-{clean_slug(semantic_scholar_id, fallback='paper')}"

    title = str(metadata.get("title") or "untitled paper")
    year = str(metadata.get("year") or "unknown")
    authors = metadata.get("authors") or []
    first_author = authors[0] if isinstance(authors, list) and authors else ""
    fingerprint = sha256(f"{title}|{year}|{first_author}".encode("utf-8")).hexdigest()[:10]
    return f"paper-{clean_slug(title, fallback='paper')}-{year}-{fingerprint}"


def document_id_from_file(paper_id: str, file_digest: str) -> str:
    return f"{clean_slug(paper_id, fallback='paper', max_length=90)}-{file_digest[:12]}"


def unit_id_from_parts(document_id: str, unit_index: int, content_type: str = "text") -> str:
    return f"{document_id}:{content_type}:{unit_index:06d}"


def point_id_from_unit_id(unit_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"cudtseis-geo-rag:{unit_id}"))
