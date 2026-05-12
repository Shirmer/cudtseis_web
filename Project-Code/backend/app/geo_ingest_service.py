from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import subprocess
import uuid
from typing import Any, AsyncIterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .embedding_service import embed_text, embed_texts
from .geo_ids import document_id_from_file, file_sha256, paper_id_from_metadata, point_id_from_unit_id, unit_id_from_parts
from .models import GeoDocument, KnowledgeUnit
from .paper_database import get_paper_detail
from .qdrant_service import init_knowledge_store, search_vectors, upsert_vectors
from .settings import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WHITESPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{1,}|[\u4e00-\u9fff]{2,}")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？.!?])\s+")
SUPPORTED_DOCUMENT_SUFFIXES = {".pdf", ".txt", ".md"}


def initialize_geo_knowledge(db: Session) -> dict[str, Any]:
    store = init_knowledge_store()
    return {
        **store,
        "documents": db.query(GeoDocument).count(),
        "units": db.query(KnowledgeUnit).count(),
        "indexVersion": settings.geo_rag_index_version,
        "storageBackend": _storage_backend(),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


async def save_uploaded_geo_document(chunks: AsyncIterator[bytes], filename: str) -> dict[str, Any]:
    safe_name = _safe_upload_filename(filename)
    suffix = Path(safe_name).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        raise ValueError("Only PDF, TXT, and Markdown files can be uploaded.")

    stage_root = _geo_upload_stage_root()
    stage_root.mkdir(parents=True, exist_ok=True)
    temp_path = stage_root / f".upload-{uuid.uuid4().hex}{suffix}"
    size_bytes = 0
    try:
        with temp_path.open("wb") as stream:
            async for chunk in chunks:
                if not chunk:
                    continue
                size_bytes += len(chunk)
                stream.write(chunk)
        if size_bytes == 0:
            raise ValueError("Uploaded file is empty.")

        digest = file_sha256(temp_path)
        final_path = stage_root / f"upload-{digest[:12]}-{safe_name}"
        if final_path.exists():
            temp_path.unlink(missing_ok=True)
        else:
            temp_path.replace(final_path)
        return {
            "filePath": str(final_path),
            "fileName": final_path.name,
            "storageUri": _storage_uri(final_path),
            "storageBackend": _storage_backend(),
            "fileSha256": digest,
            "sizeBytes": size_bytes,
            "message": "File uploaded to the local ingest staging directory.",
        }
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def ingest_geo_document(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    source_path = _resolve_source_path(str(payload.get("filePath") or ""))
    digest = file_sha256(source_path)

    metadata = _metadata_from_payload(payload)
    paper_id = str(payload.get("paperId") or "").strip()
    if paper_id:
        _merge_known_paper_metadata(metadata, paper_id)
    else:
        paper_id = paper_id_from_metadata(metadata)

    document_id = str(payload.get("documentId") or "").strip() or document_id_from_file(paper_id, digest)
    stored_file = _store_document_file(source_path, document_id=document_id)
    stored_path = Path(stored_file["localPath"])
    stored_file_name = Path(stored_file["storagePath"]).name
    metadata.update(
        {
            "sourcePath": str(stored_path) if stored_file["backend"] == "local" else "",
            "storagePath": stored_file["storagePath"],
            "storageUri": stored_file["storageUri"],
            "storageBackend": stored_file["backend"],
            "publicUrl": stored_file.get("publicUrl", ""),
            "originalSourcePath": str(source_path),
            "originalFileName": source_path.name,
        }
    )
    existing = db.get(GeoDocument, document_id)
    if existing is not None and not payload.get("force", False):
        _cleanup_upload_stage_file(source_path, stored_path)
        return {
            **document_status(existing),
            "vectorStore": init_knowledge_store(),
            "embeddingBackend": "",
            "message": "Document already exists. Set force=true to rebuild its knowledge units.",
        }

    pages = _extract_pages(stored_path)
    units = _build_knowledge_units(pages)
    if not units:
        raise ValueError("No extractable text was found in the document.")

    title = metadata.get("title") or source_path.stem
    authors = metadata.get("authors") or []
    year = metadata.get("year")
    doi = metadata.get("doi") or ""
    source_url = metadata.get("sourceUrl") or metadata.get("source_url") or ""
    parser = payload.get("parser") or ("pymupdf-multimodal-lite" if stored_path.suffix.lower() == ".pdf" else "plain-text")

    document = existing or GeoDocument(id=document_id)
    document.paper_id = paper_id
    document.title = title
    document.authors_json = authors
    document.year = year
    document.doi = doi
    document.source_url = source_url
    document.file_name = stored_file_name
    document.file_sha256 = digest
    document.parser = parser
    document.parser_version = "geo-parser-v3"
    document.status = "indexing"
    document.page_count = len(pages)
    document.unit_count = len(units)
    document.metadata_json = metadata
    db.merge(document)
    db.query(KnowledgeUnit).filter(KnowledgeUnit.document_id == document_id).delete(synchronize_session=False)
    db.flush()

    embedding_result = embed_texts([unit_data["text"] for unit_data in units])
    vector_items: list[dict[str, Any]] = []
    unit_type_counts = Counter(str(unit_data.get("content_type", "text")) for unit_data in units)
    for index, (unit_data, vector) in enumerate(zip(units, embedding_result.vectors), start=1):
        content_type = str(unit_data.get("content_type") or "text")
        unit_id = unit_id_from_parts(document_id, index, content_type)
        point_id = point_id_from_unit_id(unit_id)
        tags = _extract_geo_tags(f"{title}\n{unit_data['text']}")
        text_quality = unit_data.get("text_quality", {})
        citation = {
            "paperId": paper_id,
            "documentId": document_id,
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "page": unit_data["page"],
            "sourceUrl": source_url,
            "storageUri": metadata["storageUri"],
        }
        unit = KnowledgeUnit(
            id=unit_id,
            document_id=document_id,
            paper_id=paper_id,
            unit_index=index,
            content_type=content_type,
            text=unit_data["text"],
            page=unit_data["page"],
            section=unit_data.get("section", ""),
            bbox_json=unit_data.get("bbox", {}),
            regions_json=tags["regions"],
            faults_json=tags["faults"],
            topics_json=tags["topics"],
            geo_entities_json=tags,
            modality_json=unit_data.get("modality", {"parser": parser, "contentType": content_type}),
            citation_json=citation,
            embedding_backend=embedding_result.backend,
            index_version=settings.geo_rag_index_version,
            qdrant_point_id=point_id,
            metadata_json={
                "fileSha256": digest,
                "chunkChars": len(unit_data["text"]),
                "language": unit_data.get("language", "unknown"),
                "textQuality": text_quality,
                "sectionRole": unit_data.get("section_role", "body"),
                "evidenceRole": unit_data.get("evidence_role", "primary"),
                "parserVersion": "geo-parser-v3",
                "storageUri": metadata["storageUri"],
            },
        )
        db.add(unit)
        vector_items.append(
            {
                "point_id": point_id,
                "vector": vector,
                "payload": _unit_payload(
                    unit_id=unit_id,
                    document_id=document_id,
                    paper_id=paper_id,
                    title=title,
                    authors=authors,
                    year=year,
                    doi=doi,
                    source_url=source_url,
                    content_type=content_type,
                    text=unit_data["text"],
                    page=unit_data["page"],
                    section=unit_data.get("section", ""),
                    section_role=unit_data.get("section_role", "body"),
                    evidence_role=unit_data.get("evidence_role", "primary"),
                    language=unit_data.get("language", "unknown"),
                    text_quality=text_quality,
                    bbox=unit_data.get("bbox", {}),
                    modality=unit_data.get("modality", {"parser": parser, "contentType": content_type}),
                    tags=tags,
                    citation=citation,
                ),
            }
        )

    vector_store = upsert_vectors(vector_items)
    document.status = "indexed"
    document.updated_at = datetime.now(timezone.utc)
    db.merge(document)
    db.commit()
    _cleanup_upload_stage_file(source_path, stored_path)

    return {
        "documentId": document_id,
        "paperId": paper_id,
        "title": title,
        "status": "indexed",
        "parser": parser,
        "pages": len(pages),
        "units": len(units),
        "multimodalUnits": sum(count for item_type, count in unit_type_counts.items() if item_type != "text"),
        "storageUri": metadata["storageUri"],
        "fileSha256": digest,
        "vectorStore": vector_store,
        "embeddingBackend": embedding_result.backend,
        "message": "Document was parsed, chunked, embedded, and indexed.",
    }


def ingest_geo_document_batch(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    directory = _resolve_batch_directory(str(payload.get("directoryPath") or ""))
    recursive = bool(payload.get("recursive", False))
    force = bool(payload.get("force", False))
    limit = int(payload.get("limit") or 100)
    limit = max(1, min(limit, 1000))
    extensions = {
        str(item).lower().strip()
        for item in (payload.get("extensions") or list(SUPPORTED_DOCUMENT_SUFFIXES))
        if str(item).strip()
    }
    extensions = {item if item.startswith(".") else f".{item}" for item in extensions}
    extensions = extensions.intersection(SUPPORTED_DOCUMENT_SUFFIXES) or SUPPORTED_DOCUMENT_SUFFIXES

    iterator = directory.rglob("*") if recursive else directory.glob("*")
    files = sorted(path for path in iterator if path.is_file() and path.suffix.lower() in extensions)[:limit]
    items: list[dict[str, Any]] = []
    for path in files:
        try:
            result = ingest_geo_document(
                db,
                {
                    "filePath": str(path),
                    "title": path.stem,
                    "force": force,
                },
            )
            skipped = "already exists" in str(result.get("message", "")).lower()
            items.append(
                {
                    "filePath": str(path),
                    "status": "skipped" if skipped else result.get("status", "indexed"),
                    "documentId": result.get("documentId", ""),
                    "paperId": result.get("paperId", ""),
                    "title": result.get("title", path.stem),
                    "pages": result.get("pages", 0),
                    "units": result.get("units", 0),
                    "multimodalUnits": result.get("multimodalUnits", 0),
                    "storageUri": result.get("storageUri", ""),
                    "embeddingBackend": result.get("embeddingBackend", ""),
                    "message": result.get("message", ""),
                    "error": "",
                }
            )
        except Exception as exc:
            db.rollback()
            items.append(
                {
                    "filePath": str(path),
                    "status": "failed",
                    "documentId": "",
                    "paperId": "",
                    "title": path.stem,
                    "pages": 0,
                    "units": 0,
                    "multimodalUnits": 0,
                    "storageUri": "",
                    "embeddingBackend": "",
                    "message": "",
                    "error": str(exc),
                }
            )

    status_counts = Counter(item["status"] for item in items)
    return {
        "directoryPath": str(directory),
        "recursive": recursive,
        "limit": limit,
        "total": len(items),
        "succeeded": status_counts.get("indexed", 0),
        "skipped": status_counts.get("skipped", 0),
        "failed": status_counts.get("failed", 0),
        "items": items,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def get_geo_document_status(db: Session, document_id: str) -> dict[str, Any]:
    document = db.get(GeoDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_status(document)


def get_knowledge_unit_context(db: Session, unit_id: str, window: int = 1) -> dict[str, Any]:
    unit = db.get(KnowledgeUnit, unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail="Knowledge unit not found")

    document = db.get(GeoDocument, unit.document_id)
    citation = unit.citation_json or {}
    title = document.title if document is not None else citation.get("title", "")
    window = max(1, min(int(window), 3))
    start_index = max(1, unit.unit_index - window)
    end_index = unit.unit_index + window

    neighbors = (
        db.query(KnowledgeUnit)
        .filter(KnowledgeUnit.document_id == unit.document_id)
        .filter(KnowledgeUnit.unit_index >= start_index)
        .filter(KnowledgeUnit.unit_index <= end_index)
        .order_by(KnowledgeUnit.unit_index.asc(), KnowledgeUnit.content_type.asc())
        .all()
    )
    source_available = _document_source_available(document) if document is not None else False

    return {
        "unitId": unit.id,
        "documentId": unit.document_id,
        "paperId": unit.paper_id,
        "title": title,
        "page": unit.page,
        "fileName": document.file_name if document is not None else "",
        "sourceAvailable": source_available,
        "items": [_context_item(item, unit, title) for item in neighbors],
    }


def resolve_geo_document_file(db: Session, document_id: str) -> Path:
    document = db.get(GeoDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    source_path = _find_document_file(document)
    if source_path is None:
        raise HTTPException(status_code=404, detail="Original document file was not found on this machine")
    return source_path


def resolve_geo_document_source(db: Session, document_id: str) -> dict[str, Any]:
    document = db.get(GeoDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    public_url = _document_public_url(document)
    if public_url:
        return {"kind": "url", "url": public_url, "fileName": document.file_name}

    source_path = _find_document_file(document)
    if source_path is not None:
        return {"kind": "file", "path": source_path, "fileName": source_path.name}

    raise HTTPException(status_code=404, detail="Original document file was not found in local or cloud storage")


def search_geo_knowledge(
    db: Session,
    *,
    query: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    search_filters = _normalize_search_filters(filters or {})
    search_filters.setdefault("index_version", settings.geo_rag_index_version)
    embedding = embed_text(query)
    candidate_k = max(top_k * 8, 30)
    vector_response = search_vectors(embedding.vectors[0], top_k=candidate_k, filters=search_filters)
    dense_results = [_hit_from_vector_result(hit) for hit in vector_response["results"]]
    keyword_results = _keyword_search_units(db, query=query, top_k=candidate_k, filters=search_filters)
    results, diagnostics = _merge_and_rerank_results(
        query=query,
        dense_results=dense_results,
        keyword_results=keyword_results,
        top_k=top_k,
        vector_backend=vector_response["backend"],
        embedding_backend=embedding.backend,
    )
    return {
        "query": query,
        "topK": top_k,
        "filters": search_filters,
        "backend": vector_response["backend"],
        "collection": vector_response["collection"],
        "warning": vector_response.get("warning", ""),
        "embeddingBackend": embedding.backend,
        "results": results,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "diagnostics": diagnostics,
        "storeStats": {
            "documents": db.query(GeoDocument).count(),
            "units": db.query(KnowledgeUnit).count(),
        },
    }


def document_status(document: GeoDocument) -> dict[str, Any]:
    return {
        "documentId": document.id,
        "paperId": document.paper_id,
        "title": document.title,
        "status": document.status,
        "parser": document.parser,
        "pages": document.page_count,
        "units": document.unit_count,
        "fileSha256": document.file_sha256,
        "metadata": document.metadata_json or {},
        "createdAt": document.created_at.isoformat() if document.created_at else "",
        "updatedAt": document.updated_at.isoformat() if document.updated_at else "",
    }


def _store_document_file(source_path: Path, *, document_id: str) -> dict[str, Any]:
    backend = _storage_backend()
    if backend == "ssh":
        return _store_document_file_via_ssh(source_path, document_id=document_id)
    return _store_document_file_locally(source_path, document_id=document_id)


def _store_document_file_locally(source_path: Path, *, document_id: str) -> dict[str, Any]:
    storage_root = _geo_storage_root()
    storage_root.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix.lower()
    target_path = storage_root / f"{document_id}{suffix}"

    source_resolved = source_path.expanduser().resolve(strict=False)
    target_resolved = target_path.expanduser().resolve(strict=False)
    if source_resolved == target_resolved:
        return _stored_file_record(
            backend="local",
            local_path=target_resolved,
            storage_path=str(target_resolved),
            storage_uri=_storage_uri(target_resolved),
        )

    if not target_resolved.exists() or file_sha256(target_resolved) != file_sha256(source_resolved):
        shutil.copy2(source_resolved, target_resolved)
    return _stored_file_record(
        backend="local",
        local_path=target_resolved,
        storage_path=str(target_resolved),
        storage_uri=_storage_uri(target_resolved),
        public_url=_public_url_for_file(target_resolved.name),
    )


def _store_document_file_via_ssh(source_path: Path, *, document_id: str) -> dict[str, Any]:
    host = settings.geo_rag_storage_ssh_host.strip()
    user = settings.geo_rag_storage_ssh_user.strip() or "root"
    if not host:
        raise RuntimeError("GEO_RAG_STORAGE_BACKEND=ssh requires GEO_RAG_STORAGE_SSH_HOST.")

    suffix = source_path.suffix.lower()
    remote_root = settings.geo_rag_storage_remote_root.rstrip("/")
    remote_path = f"{remote_root}/{document_id}{suffix}"
    target = f"{user}@{host}:{remote_path}"

    _run_storage_command([*_ssh_command_prefix(), f"{user}@{host}", "mkdir", "-p", remote_root])
    _run_storage_command([*_scp_command_prefix(), str(source_path), target])

    return _stored_file_record(
        backend="ssh",
        local_path=source_path.expanduser().resolve(strict=False),
        storage_path=remote_path,
        storage_uri=f"ssh://{user}@{host}{remote_path}",
        public_url=_public_url_for_file(f"{document_id}{suffix}"),
    )


def _stored_file_record(
    *,
    backend: str,
    local_path: Path,
    storage_path: str,
    storage_uri: str,
    public_url: str = "",
) -> dict[str, Any]:
    return {
        "backend": backend,
        "localPath": str(local_path),
        "storagePath": storage_path,
        "storageUri": storage_uri,
        "publicUrl": public_url,
    }


def _storage_uri(path: Path) -> str:
    storage_root = _geo_storage_root()
    resolved = path.expanduser().resolve(strict=False)
    try:
        relative = resolved.relative_to(storage_root)
        return f"local://{relative.as_posix()}"
    except ValueError:
        return str(resolved)


def _storage_backend() -> str:
    backend = settings.geo_rag_storage_backend.strip().lower()
    if backend in {"", "filesystem"}:
        return "local"
    if backend in {"local", "ssh"}:
        return backend
    raise RuntimeError(f"Unsupported GEO_RAG_STORAGE_BACKEND: {settings.geo_rag_storage_backend}")


def _geo_upload_stage_root() -> Path:
    root = Path(settings.geo_rag_upload_stage_root).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    return root.resolve(strict=False)


def _cleanup_upload_stage_file(source_path: Path, stored_path: Path) -> None:
    stage_root = _geo_upload_stage_root()
    source_resolved = source_path.expanduser().resolve(strict=False)
    stored_resolved = stored_path.expanduser().resolve(strict=False)
    try:
        source_resolved.relative_to(stage_root)
    except ValueError:
        return
    if source_resolved.name.startswith("upload-") and (
        source_resolved != stored_resolved or _storage_backend() == "ssh"
    ):
        source_resolved.unlink(missing_ok=True)


def _ssh_command_prefix() -> list[str]:
    args = ["ssh", "-p", str(settings.geo_rag_storage_ssh_port)]
    key_path = settings.geo_rag_storage_ssh_key_path.strip()
    if key_path:
        args.extend(["-i", str(Path(key_path).expanduser())])
    return args


def _scp_command_prefix() -> list[str]:
    args = ["scp", "-P", str(settings.geo_rag_storage_ssh_port)]
    key_path = settings.geo_rag_storage_ssh_key_path.strip()
    if key_path:
        args.extend(["-i", str(Path(key_path).expanduser())])
    return args


def _run_storage_command(command: list[str]) -> None:
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"Cloud document storage command failed: {detail}")


def _public_url_for_file(file_name: str) -> str:
    base_url = settings.geo_rag_storage_public_base_url.strip().rstrip("/")
    if not base_url:
        return ""
    return f"{base_url}/{file_name}"


def _safe_upload_filename(filename: str) -> str:
    raw = Path(filename or "document.pdf").name.strip()
    if not raw:
        raw = "document.pdf"
    stem = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "-", Path(raw).stem).strip(".-")
    suffix = Path(raw).suffix.lower()
    stem = stem[:120] or "document"
    return f"{stem}{suffix}"


def _context_item(unit: KnowledgeUnit, anchor: KnowledgeUnit, fallback_title: str) -> dict[str, Any]:
    citation = unit.citation_json or {}
    metadata = unit.metadata_json or {}
    if unit.id == anchor.id:
        position = "current"
    elif unit.unit_index < anchor.unit_index:
        position = "before"
    elif unit.unit_index > anchor.unit_index:
        position = "after"
    else:
        position = "nearby"

    return {
        "unitId": unit.id,
        "documentId": unit.document_id,
        "paperId": unit.paper_id,
        "title": citation.get("title") or fallback_title,
        "contentType": unit.content_type,
        "text": unit.text,
        "page": unit.page,
        "unitIndex": unit.unit_index,
        "position": position,
        "metadata": {
            "section": unit.section,
            "bbox": unit.bbox_json or {},
            "modality": unit.modality_json or {},
            "sectionRole": metadata.get("sectionRole") or _section_role(unit.section or "", unit.text),
            "evidenceRole": metadata.get("evidenceRole") or _evidence_role(
                metadata.get("sectionRole") or _section_role(unit.section or "", unit.text)
            ),
            "language": metadata.get("language", "unknown"),
        },
    }


def _find_document_file(document: GeoDocument) -> Path | None:
    metadata = document.metadata_json or {}
    candidates: list[Path] = []

    for key in ("storagePath", "sourcePath", "filePath"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(Path(value.strip()))
    storage_uri = metadata.get("storageUri")
    if isinstance(storage_uri, str) and storage_uri.startswith("local://"):
        candidates.append(_geo_storage_root() / storage_uri.removeprefix("local://"))

    if document.file_name:
        candidates.append(_geo_storage_root() / document.file_name)

    for candidate in candidates:
        resolved = _resolve_candidate_file(candidate)
        if resolved is not None:
            return resolved

    storage_root = _geo_storage_root()
    if document.file_name and storage_root.exists():
        for match in storage_root.rglob(document.file_name):
            resolved = _resolve_candidate_file(match)
            if resolved is not None:
                return resolved
    return None


def _document_source_available(document: GeoDocument) -> bool:
    return bool(_document_public_url(document) or _find_document_file(document))


def _document_public_url(document: GeoDocument) -> str:
    metadata = document.metadata_json or {}
    public_url = metadata.get("publicUrl")
    if isinstance(public_url, str) and public_url.strip():
        return public_url.strip()

    storage_uri = metadata.get("storageUri")
    if isinstance(storage_uri, str) and storage_uri.startswith(("http://", "https://")):
        return storage_uri

    if metadata.get("storageBackend") == "ssh" and document.file_name:
        return _public_url_for_file(document.file_name)

    return ""


def _geo_storage_root() -> Path:
    root = Path(settings.geo_rag_storage_root).expanduser()
    if not root.is_absolute():
        root = PROJECT_ROOT / root
    return root.resolve(strict=False)


def _resolve_candidate_file(path: Path) -> Path | None:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.resolve(strict=False)
    return resolved if resolved.is_file() else None


def _resolve_source_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("filePath is required")
    if raw_path.startswith("local://"):
        candidate = _geo_storage_root() / raw_path.removeprefix("local://")
    else:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate

    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"Document file does not exist: {resolved}")
    if resolved.is_dir():
        raise ValueError(
            "Document path is a directory. Please provide a specific PDF, TXT, or Markdown file path."
        )
    if not resolved.is_file():
        raise ValueError(f"Document path is not a regular file: {resolved}")
    return resolved


def _resolve_batch_directory(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("directoryPath is required")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"Batch directory does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Batch path is not a directory: {resolved}")
    return resolved


def _metadata_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    authors = payload.get("authors") or []
    if isinstance(authors, str):
        authors = [item.strip() for item in authors.split(",") if item.strip()]
    return {
        "paperId": payload.get("paperId") or "",
        "documentId": payload.get("documentId") or "",
        "title": payload.get("title") or "",
        "authors": authors,
        "year": payload.get("year"),
        "doi": payload.get("doi") or "",
        "sourceUrl": payload.get("sourceUrl") or "",
    }


def _merge_known_paper_metadata(metadata: dict[str, Any], paper_id: str) -> None:
    detail = get_paper_detail(paper_id)
    if detail is None:
        return
    metadata["title"] = metadata.get("title") or detail.get("title") or ""
    metadata["authors"] = metadata.get("authors") or detail.get("authors") or []
    metadata["year"] = metadata.get("year") or detail.get("year")
    metadata["doi"] = metadata.get("doi") or detail.get("doi") or ""
    metadata["sourceUrl"] = metadata.get("sourceUrl") or detail.get("url") or ""


def _extract_pages(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf_pages(path)
    if suffix in {".txt", ".md"}:
        return [{"page": 1, "text": path.read_text(encoding="utf-8", errors="ignore")}]
    raise ValueError("Only PDF, TXT, and Markdown files are supported in the MVP ingester.")


def _extract_pdf_pages(path: Path) -> list[dict[str, Any]]:
    try:
        return _extract_pdf_pages_with_pymupdf_blocks(path)
    except Exception:
        return _extract_pdf_pages_with_pypdf(path)


def _extract_pdf_pages_with_pypdf(path: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except Exception:
        return _extract_pdf_pages_with_pymupdf(path)

    reader = PdfReader(str(path))
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = _normalize_extracted_text(page.extract_text() or "")
        pages.append(
            {
                "page": index,
                "text": text,
                "paragraphs": [text] if text else [],
                "elements": [],
                "quality": _text_quality(text),
            }
        )
    return pages


def _extract_pdf_pages_with_pymupdf_blocks(path: Path) -> list[dict[str, Any]]:
    import fitz

    pages: list[dict[str, Any]] = []
    with fitz.open(path) as document:
        for page_index, page in enumerate(document, start=1):
            raw_blocks = page.get_text("blocks")
            blocks: list[dict[str, Any]] = []
            page_width = float(page.rect.width)
            mid_x = page_width / 2
            for block in raw_blocks:
                x0, y0, x1, y1 = [float(value) for value in block[:4]]
                if len(block) >= 7 and block[6] != 0:
                    if block[6] == 1:
                        blocks.append(
                            {
                                "x0": x0,
                                "y0": y0,
                                "x1": x1,
                                "y1": y1,
                                "column": -1,
                                "text": "",
                                "content_type": "figure",
                                "bbox": _bbox(x0, y0, x1, y1),
                            }
                        )
                    continue
                text = _normalize_extracted_text(str(block[4] or ""))
                if not text or _looks_like_page_marker(text):
                    continue
                width = max(1.0, x1 - x0)
                if width > page_width * 0.62:
                    column = -1
                elif (x0 + x1) / 2 < mid_x:
                    column = 0
                else:
                    column = 1
                content_type = "text"
                if _looks_like_equation(text):
                    content_type = "equation"
                elif _looks_like_table_text(text):
                    content_type = "table"
                blocks.append(
                    {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1,
                        "column": column,
                        "text": text,
                        "content_type": content_type,
                        "bbox": _bbox(x0, y0, x1, y1),
                    }
                )

            ordered = _order_page_blocks(blocks)
            paragraphs = [item["text"] for item in ordered if item.get("text")]
            text = "\n\n".join(paragraphs)
            elements = _layout_elements_from_blocks(page_index, ordered, paragraphs)
            elements.extend(_extract_page_table_elements(page, page_index, paragraphs))
            pages.append(
                {
                    "page": page_index,
                    "text": text,
                    "paragraphs": paragraphs,
                    "elements": elements,
                    "quality": _text_quality(text),
                }
            )
    return _strip_repeated_page_lines(pages)


def _extract_pdf_pages_with_pymupdf(path: Path) -> list[dict[str, Any]]:
    try:
        import fitz
    except Exception as exc:
        raise ValueError("pypdf or PyMuPDF is required to parse PDFs. Run python dev.py setup first.") from exc

    pages: list[dict[str, Any]] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            text = _normalize_extracted_text(page.get_text("text"))
            pages.append(
                {
                    "page": index,
                    "text": text,
                    "paragraphs": [text] if text else [],
                    "elements": [],
                    "quality": _text_quality(text),
                }
            )
    return pages


def _chunk_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments = _page_segments(pages)
    chunks: list[dict[str, Any]] = []
    chunk_chars = max(300, settings.geo_rag_chunk_chars)
    overlap = min(max(0, settings.geo_rag_chunk_overlap), chunk_chars // 2)
    buffer: list[str] = []
    start_page: int | None = None
    section = ""
    section_role = ""
    evidence_role = ""
    quality: dict[str, Any] = {}

    def flush(*, keep_tail: bool = False) -> str:
        nonlocal buffer, start_page, section, section_role, evidence_role, quality
        current_text = " ".join(buffer)
        text = WHITESPACE_RE.sub(" ", " ".join(buffer)).strip()
        if text:
            chunk_section_role = section_role or _section_role(section, text)
            chunk_evidence_role = evidence_role or _evidence_role(chunk_section_role)
            chunks.append(
                {
                    "page": start_page or 1,
                    "text": text,
                    "section": section,
                    "section_role": chunk_section_role,
                    "evidence_role": chunk_evidence_role,
                    "language": _detect_language(text),
                    "text_quality": {
                        **_text_quality(text),
                        **quality,
                        "sectionRole": chunk_section_role,
                        "evidenceRole": chunk_evidence_role,
                    },
                }
            )
        tail = current_text[-overlap:].strip() if keep_tail and overlap > 0 else ""
        buffer = []
        start_page = None
        section = ""
        section_role = ""
        evidence_role = ""
        quality = {}
        return tail

    for segment in segments:
        segment_section = segment.get("section", "")
        segment_section_role = segment.get("section_role") or _section_role(segment_section, segment["text"])
        segment_evidence_role = segment.get("evidence_role") or _evidence_role(segment_section_role)
        for piece in _split_long_text(segment["text"], chunk_chars):
            if buffer and not _roles_can_overlap(evidence_role, segment_evidence_role):
                flush(keep_tail=False)
            current_text = " ".join(buffer)
            if buffer and len(current_text) + len(piece) > chunk_chars:
                tail = flush(keep_tail=_roles_can_overlap(evidence_role, segment_evidence_role))
                if tail:
                    buffer.append(tail)
            if start_page is None:
                start_page = segment["page"]
            if segment_section:
                section = segment_section
            section_role = segment_section_role
            evidence_role = segment_evidence_role
            quality = segment.get("quality", {})
            buffer.append(piece)
    flush()
    return chunks


def _build_knowledge_units(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text_units = _chunk_pages(pages)
    multimodal_units = _extract_multimodal_units(pages)
    for index, unit in enumerate(text_units, start=1):
        unit.setdefault("content_type", "text")
        unit.setdefault("bbox", {})
        unit.setdefault("modality", {"contentType": "text", "parser": "pymupdf-multimodal-lite"})
        unit["_sort"] = (int(unit.get("page") or 1), index * 10, 0)
    for index, unit in enumerate(multimodal_units, start=1):
        unit["_sort"] = (int(unit.get("page") or 1), int(unit.get("order") or index * 10), 1)

    ordered = sorted([*text_units, *multimodal_units], key=lambda item: item.get("_sort", (0, 0, 0)))
    for item in ordered:
        item.pop("_sort", None)
    return ordered


def _extract_multimodal_units(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for page in pages:
        paragraphs = [str(item) for item in page.get("paragraphs") or []]
        for element_index, element in enumerate(page.get("elements") or [], start=1):
            content_type = str(element.get("content_type") or "figure")
            if content_type not in {"figure", "table", "equation"}:
                continue
            description = _multimodal_description(content_type, page["page"], element, paragraphs)
            if not description:
                continue
            units.append(
                {
                    "content_type": content_type,
                    "page": page["page"],
                    "text": description,
                    "section": element.get("section", ""),
                    "section_role": "body",
                    "evidence_role": "context" if content_type in {"figure", "table"} else "primary",
                    "language": _detect_language(description),
                    "text_quality": {
                        "status": "structured-multimodal-lite",
                        "source": "pymupdf-layout",
                        "contentType": content_type,
                    },
                    "bbox": element.get("bbox", {}),
                    "order": int(element.get("order") or element_index * 10),
                    "modality": {
                        "parser": "pymupdf-multimodal-lite",
                        "contentType": content_type,
                        "kind": element.get("kind", content_type),
                        "caption": element.get("caption", ""),
                    },
                }
            )
    return units


def _layout_elements_from_blocks(
    page_number: int,
    blocks: list[dict[str, Any]],
    paragraphs: list[str],
) -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, block in enumerate(blocks, start=1):
        content_type = str(block.get("content_type") or "text")
        if content_type == "text":
            continue
        text = str(block.get("text") or "").strip()
        caption = _nearest_caption(content_type, text, paragraphs)
        key = (content_type, text[:160] or str(block.get("bbox", {})))
        if key in seen:
            continue
        seen.add(key)
        elements.append(
            {
                "content_type": content_type,
                "kind": "layout-block",
                "page": page_number,
                "text": text,
                "caption": caption,
                "bbox": block.get("bbox", {}),
                "order": index * 10,
            }
        )
    return elements


def _extract_page_table_elements(page: Any, page_number: int, paragraphs: list[str]) -> list[dict[str, Any]]:
    if not hasattr(page, "find_tables"):
        return []
    try:
        result = page.find_tables()
    except Exception:
        return []

    elements: list[dict[str, Any]] = []
    for index, table in enumerate(getattr(result, "tables", []) or [], start=1):
        bbox = getattr(table, "bbox", None)
        text = ""
        try:
            rows = table.extract()
            text = _table_rows_preview(rows)
        except Exception:
            rows = []
        caption = _nearest_caption("table", text, paragraphs)
        elements.append(
            {
                "content_type": "table",
                "kind": "detected-table",
                "page": page_number,
                "text": text,
                "caption": caption,
                "bbox": _bbox(*bbox) if bbox else {},
                "order": index * 10 + 5,
                "rows": len(rows or []),
            }
        )
    return elements


def _multimodal_description(
    content_type: str,
    page_number: int,
    element: dict[str, Any],
    paragraphs: list[str],
) -> str:
    label = {"figure": "Figure/image", "table": "Table", "equation": "Equation"}[content_type]
    text = WHITESPACE_RE.sub(" ", str(element.get("text") or "")).strip()
    caption = str(element.get("caption") or _nearest_caption(content_type, text, paragraphs)).strip()
    pieces = [f"{label} candidate on page {page_number}."]
    if caption:
        pieces.append(f"Caption or nearby label: {caption}")
    if text:
        pieces.append(f"Extracted content: {text}")
    if not caption and not text and content_type != "figure":
        return ""
    if content_type == "figure" and not caption and not text:
        pieces.append("Visual content detected; use the original PDF for inspection.")
    return " ".join(pieces)


def _table_rows_preview(rows: list[list[Any]], max_rows: int = 6) -> str:
    lines: list[str] = []
    for row in (rows or [])[:max_rows]:
        cells = [WHITESPACE_RE.sub(" ", str(cell or "")).strip() for cell in row]
        cells = [cell for cell in cells if cell]
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def _nearest_caption(content_type: str, text: str, paragraphs: list[str]) -> str:
    patterns = {
        "figure": r"^(fig\.?|figure|图)\s*[\dA-Za-z一二三四五六七八九十]+",
        "table": r"^(table|表)\s*[\dA-Za-z一二三四五六七八九十]+",
        "equation": r"^(equation|eq\.?|公式)\s*[\dA-Za-z一二三四五六七八九十]+",
    }
    pattern = patterns.get(content_type, "")
    for paragraph in paragraphs:
        normalized = WHITESPACE_RE.sub(" ", paragraph).strip()
        if pattern and re.search(pattern, normalized, re.IGNORECASE):
            return normalized[:500]
    if content_type in {"table", "equation"} and text:
        return text[:240]
    return ""


def _looks_like_equation(text: str) -> bool:
    normalized = WHITESPACE_RE.sub(" ", text).strip()
    if len(normalized) > 260:
        return False
    if re.search(r"[=∑∫√≈≤≥±×÷α-ωΑ-Ω]", normalized) and re.search(r"[A-Za-z0-9]", normalized):
        return True
    return bool(re.search(r"\([0-9]{1,3}\)\s*$", normalized) and re.search(r"[=+\-*/]", normalized))


def _looks_like_table_text(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return False
    numeric_lines = sum(1 for line in lines if len(re.findall(r"[-+]?\d+(?:\.\d+)?", line)) >= 3)
    delimiter_lines = sum(1 for line in lines if "\t" in line or " | " in line)
    return numeric_lines >= 2 or delimiter_lines >= 2


def _bbox(x0: float, y0: float, x1: float, y1: float) -> dict[str, float]:
    return {
        "x0": round(float(x0), 2),
        "y0": round(float(y0), 2),
        "x1": round(float(x1), 2),
        "y1": round(float(y1), 2),
    }


def _order_page_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not blocks:
        return []
    left = [item for item in blocks if item["column"] == 0]
    right = [item for item in blocks if item["column"] == 1]
    full = [item for item in blocks if item["column"] == -1]
    if len(left) >= 3 and len(right) >= 3:
        ordered: list[dict[str, Any]] = []
        remaining_full = sorted(full, key=lambda item: item["y0"])
        for item in remaining_full:
            if item["y0"] < min(block["y0"] for block in left + right):
                ordered.append(item)
        ordered.extend(sorted(left, key=lambda item: item["y0"]))
        ordered.extend(sorted(right, key=lambda item: item["y0"]))
        ordered.extend(
            item
            for item in remaining_full
            if item not in ordered
        )
        return ordered
    return sorted(blocks, key=lambda item: (round(item["y0"] / 12), item["x0"]))


def _strip_repeated_page_lines(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: Counter[str] = Counter()
    for page in pages:
        paragraphs = page.get("paragraphs", [])
        for text in [*paragraphs[:2], *paragraphs[-2:]]:
            key = _line_key(text)
            if key:
                candidates[key] += 1

    repeated = {key for key, count in candidates.items() if count >= 3 and len(key) > 8}
    if not repeated:
        return pages

    cleaned_pages = []
    for page in pages:
        paragraphs = [
            text
            for text in page.get("paragraphs", [])
            if _line_key(text) not in repeated
        ]
        text = "\n\n".join(paragraphs)
        cleaned_pages.append({**page, "paragraphs": paragraphs, "text": text, "quality": _text_quality(text)})
    return cleaned_pages


def _line_key(text: str) -> str:
    key = re.sub(r"\d+", "#", WHITESPACE_RE.sub(" ", text.lower())).strip()
    if len(key) < 5:
        return ""
    return key[:120]


def _normalize_extracted_text(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"(?<=[A-Za-z])-\n(?=[A-Za-z])", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [line.strip() for line in text.splitlines()]
    paragraphs: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if not line:
            if buffer:
                paragraphs.append(" ".join(buffer).strip())
                buffer = []
            continue
        buffer.append(line)
    if buffer:
        paragraphs.append(" ".join(buffer).strip())
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph)


def _looks_like_page_marker(text: str) -> bool:
    normalized = text.strip()
    return bool(re.fullmatch(r"[\-–—]?\s*\d{1,4}\s*[\-–—]?", normalized))


def _page_segments(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current_section = ""
    for page in pages:
        paragraphs = page.get("paragraphs") or [page.get("text", "")]
        for paragraph in paragraphs:
            text = WHITESPACE_RE.sub(" ", str(paragraph or "")).strip()
            if not text:
                continue
            if _looks_like_heading(text):
                current_section = text[:180]
                continue
            if _looks_like_references_heading(text):
                current_section = "References"
            section_role = _section_role(current_section, text)
            evidence_role = _evidence_role(section_role)
            segments.append(
                {
                    "page": page["page"],
                    "text": text,
                    "section": current_section,
                    "section_role": section_role,
                    "evidence_role": evidence_role,
                    "quality": {
                        **(page.get("quality", {}) or {}),
                        "sectionRole": section_role,
                        "evidenceRole": evidence_role,
                    },
                }
            )
    return segments


def _looks_like_heading(text: str) -> bool:
    if len(text) > 140 or text.endswith("."):
        return False
    if re.match(r"^\d+(\.\d+)*\s+[A-Z\u4e00-\u9fff]", text):
        return True
    heading_words = {
        "acknowledgement",
        "acknowledgements",
        "abstract",
        "appendix",
        "introduction",
        "methods",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
        "funding",
        "references",
        "supplementary material",
        "摘要",
        "致谢",
        "引言",
        "方法",
        "结果",
        "讨论",
        "结论",
        "基金",
        "参考文献",
        "附录",
    }
    return text.lower() in heading_words


def _looks_like_references_heading(text: str) -> bool:
    return text.lower() in {"references", "bibliography", "参考文献"}


def _section_role(section: str, text: str = "") -> str:
    normalized = WHITESPACE_RE.sub(" ", f"{section}\n{text[:220]}".lower()).strip()
    if re.search(r"\b(references|bibliography|works cited|literature cited)\b|参考文献", normalized):
        return "references"
    if re.search(r"\backnowledg(e)?ments?\b|致谢", normalized):
        return "acknowledgement"
    if re.search(r"\bfunding\b|基金", normalized):
        return "funding"
    if re.search(r"\bappendix\b|supplementary material|附录", normalized):
        return "appendix"
    if re.search(r"\babstract\b|摘要", normalized):
        return "abstract"
    return "body"


def _evidence_role(section_role: str) -> str:
    if section_role in {"references", "acknowledgement", "funding"}:
        return "low-evidence"
    if section_role in {"appendix", "abstract"}:
        return "context"
    return "primary"


def _roles_can_overlap(current_role: str, next_role: str) -> bool:
    if not current_role or not next_role:
        return True
    if "low-evidence" in {current_role, next_role}:
        return current_role == next_role
    return True


def _split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    sentences = SENTENCE_SPLIT_RE.split(text)
    pieces: list[str] = []
    buffer: list[str] = []
    for sentence in sentences:
        if len(" ".join(buffer)) + len(sentence) > max_chars and buffer:
            pieces.append(" ".join(buffer).strip())
            buffer = []
        if len(sentence) > max_chars:
            pieces.extend(sentence[start : start + max_chars] for start in range(0, len(sentence), max_chars))
        else:
            buffer.append(sentence)
    if buffer:
        pieces.append(" ".join(buffer).strip())
    return [piece for piece in pieces if piece]


def _detect_language(text: str) -> str:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk and cjk >= latin * 0.2:
        return "zh"
    if latin:
        return "en"
    return "unknown"


def _text_quality(text: str) -> dict[str, Any]:
    if not text:
        return {"status": "empty", "chars": 0, "spaceRatio": 0.0, "lineJoinRisk": 1.0}
    chars = len(text)
    spaces = text.count(" ")
    joined_words = len(re.findall(r"[a-z][A-Z]", text))
    return {
        "status": "ok" if chars >= 80 else "short",
        "chars": chars,
        "spaceRatio": round(spaces / max(chars, 1), 4),
        "lineJoinRisk": round(min(1.0, joined_words / max(chars / 120, 1)), 4),
    }


def _extract_geo_tags(text: str) -> dict[str, Any]:
    normalized = text.lower()
    topic_map = {
        "earthquake": "earthquake",
        "fault": "fault",
        "seismic": "seismology",
        "tectonic": "tectonics",
        "aftershock": "aftershock",
        "rupture": "rupture",
        "hazard": "hazard",
        "supershear": "supershear",
        "subduction": "subduction",
        "strike-slip": "strike-slip",
        "thrust": "thrust",
        "normal fault": "normal-fault",
        "moment magnitude": "magnitude",
        "地震": "earthquake",
        "断层": "fault",
        "构造": "tectonics",
        "余震": "aftershock",
        "破裂": "rupture",
        "危险性": "hazard",
        "滑坡": "landslide",
        "同震": "coseismic",
        "震源": "hypocenter",
        "震级": "magnitude",
        "活动断裂": "active-fault",
        "龙门山": "longmenshan",
        "汶川": "wenchuan",
    }
    topics = sorted({label for token, label in topic_map.items() if token in normalized})
    regions = sorted(
        {
            item
            for item in ["China", "Sichuan", "Tibet", "Yunnan", "Japan", "Turkey", "Syria", "Anatolia", "Himalaya"]
            if item.lower() in normalized
        }
    )
    faults = sorted(set(re.findall(r"[A-Z][A-Za-z -]{2,40} Fault", text)))
    if "龙门山" in text:
        faults.append("Longmenshan Fault")
    if "east anatolian fault" in normalized:
        faults.append("East Anatolian Fault")
    faults = sorted(set(faults))
    return {"topics": topics, "regions": regions, "faults": faults}


def _unit_payload(
    *,
    unit_id: str,
    document_id: str,
    paper_id: str,
    title: str,
    authors: list[str],
    year: int | None,
    doi: str,
    source_url: str,
    content_type: str,
    text: str,
    page: int | None,
    section: str,
    section_role: str,
    evidence_role: str,
    language: str,
    text_quality: dict[str, Any],
    bbox: dict[str, Any],
    modality: dict[str, Any],
    tags: dict[str, Any],
    citation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "unit_id": unit_id,
        "document_id": document_id,
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi,
        "source_url": source_url,
        "content_type": content_type,
        "text": text,
        "page": page,
        "section": section,
        "section_role": section_role,
        "evidence_role": evidence_role,
        "language": language,
        "text_quality": text_quality,
        "bbox": bbox,
        "modality": modality,
        "regions": tags.get("regions", []),
        "faults": tags.get("faults", []),
        "topics": tags.get("topics", []),
        "index_version": settings.geo_rag_index_version,
        "citation": citation,
    }


def _normalize_search_filters(filters: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "paperId": "paper_id",
        "documentId": "document_id",
        "contentType": "content_type",
        "indexVersion": "index_version",
    }
    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        target = aliases.get(key, key)
        if value not in (None, "", []):
            normalized[target] = value
    return normalized


def _keyword_search_units(
    db: Session,
    *,
    query: str,
    top_k: int,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    terms = _query_terms(query)
    if not terms:
        return []

    rows = db.query(KnowledgeUnit)
    if filters.get("index_version"):
        rows = rows.filter(KnowledgeUnit.index_version == filters["index_version"])
    if filters.get("paper_id"):
        rows = rows.filter(KnowledgeUnit.paper_id == filters["paper_id"])
    if filters.get("document_id"):
        rows = rows.filter(KnowledgeUnit.document_id == filters["document_id"])
    if filters.get("content_type"):
        rows = rows.filter(KnowledgeUnit.content_type == filters["content_type"])

    scored: list[tuple[float, KnowledgeUnit]] = []
    for unit in rows.limit(5000).all():
        if not _json_filter_matches(unit, filters):
            continue
        score = _keyword_score(query_terms=terms, text=unit.text, unit=unit)
        if score > 0:
            scored.append((score, unit))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [_hit_from_unit(unit, score) for score, unit in scored[:top_k]]


def _json_filter_matches(unit: KnowledgeUnit, filters: dict[str, Any]) -> bool:
    for key, value in filters.items():
        if key in {"index_version", "paper_id", "document_id", "content_type"}:
            continue
        if key == "topics" and value:
            if not set(value).intersection(set(unit.topics_json or [])):
                return False
        if key == "regions" and value:
            if not set(value).intersection(set(unit.regions_json or [])):
                return False
        if key == "faults" and value:
            if not set(value).intersection(set(unit.faults_json or [])):
                return False
    return True


def _hit_from_unit(unit: KnowledgeUnit, score: float) -> dict[str, Any]:
    citation = unit.citation_json or {}
    metadata = unit.metadata_json or {}
    return {
        "unitId": unit.id,
        "documentId": unit.document_id,
        "paperId": unit.paper_id,
        "title": citation.get("title", ""),
        "contentType": unit.content_type,
        "text": unit.text,
        "page": unit.page,
        "score": score,
        "citation": citation,
        "metadata": {
            "authors": citation.get("authors", []),
            "year": citation.get("year"),
            "doi": citation.get("doi", ""),
            "sourceUrl": citation.get("sourceUrl", ""),
            "regions": unit.regions_json or [],
            "faults": unit.faults_json or [],
            "topics": unit.topics_json or [],
            "section": unit.section,
            "sectionRole": metadata.get("sectionRole") or _section_role(unit.section or "", unit.text),
            "evidenceRole": metadata.get("evidenceRole") or _evidence_role(
                metadata.get("sectionRole") or _section_role(unit.section or "", unit.text)
            ),
            "language": metadata.get("language", "unknown"),
            "textQuality": metadata.get("textQuality", {}),
        },
    }


def _merge_and_rerank_results(
    *,
    query: str,
    dense_results: list[dict[str, Any]],
    keyword_results: list[dict[str, Any]],
    top_k: int,
    vector_backend: str,
    embedding_backend: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    query_terms = _query_terms(query)
    combined: dict[str, dict[str, Any]] = {}
    max_dense = max([item.get("score", 0.0) for item in dense_results] or [0.0])
    max_keyword = max([item.get("score", 0.0) for item in keyword_results] or [0.0])

    for item in dense_results:
        entry = combined.setdefault(item["unitId"], {**item, "_dense": 0.0, "_keyword": 0.0})
        entry["_dense"] = max(entry["_dense"], _safe_norm(item.get("score", 0.0), max_dense))
    for item in keyword_results:
        entry = combined.setdefault(item["unitId"], {**item, "_dense": 0.0, "_keyword": 0.0})
        entry["_keyword"] = max(entry["_keyword"], _safe_norm(item.get("score", 0.0), max_keyword))
        if not entry.get("text"):
            entry.update(item)

    candidates: list[dict[str, Any]] = []
    for item in combined.values():
        metadata_boost = _metadata_boost(query_terms, item)
        evidence_weight = _evidence_weight(item)
        base_score = 0.62 * item["_dense"] + 0.30 * item["_keyword"] + 0.08 * metadata_boost
        final_score = base_score * evidence_weight
        item["score"] = round(final_score, 6)
        item["metadata"] = {
            **(item.get("metadata") or {}),
            "retrievalBreakdown": {
                "dense": round(item["_dense"], 4),
                "keyword": round(item["_keyword"], 4),
                "metadata": round(metadata_boost, 4),
                "evidenceWeight": round(evidence_weight, 4),
                "final": round(final_score, 4),
            },
        }
        candidates.append(item)

    candidates.sort(key=lambda item: item["score"], reverse=True)
    selected = _select_diverse(candidates, top_k=top_k)
    diagnostics = _retrieval_diagnostics(
        selected=selected,
        candidates=candidates,
        dense_results=dense_results,
        keyword_results=keyword_results,
        query_terms=query_terms,
        vector_backend=vector_backend,
        embedding_backend=embedding_backend,
    )
    for item in selected:
        item.pop("_dense", None)
        item.pop("_keyword", None)
    return selected, diagnostics


def _select_diverse(candidates: list[dict[str, Any]], *, top_k: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    doc_counts: Counter[str] = Counter()
    page_counts: Counter[str] = Counter()
    remaining = candidates[:]
    while remaining and len(selected) < top_k:
        best_index = 0
        best_score = -1.0
        for index, item in enumerate(remaining):
            doc_id = item.get("documentId", "")
            page_key = f"{doc_id}:{item.get('page')}"
            adjusted = item["score"] - 0.08 * doc_counts[doc_id] - 0.04 * page_counts[page_key]
            if adjusted > best_score:
                best_index = index
                best_score = adjusted
        chosen = remaining.pop(best_index)
        selected.append(chosen)
        doc_counts[chosen.get("documentId", "")] += 1
        page_counts[f"{chosen.get('documentId', '')}:{chosen.get('page')}"] += 1
    return selected


def _retrieval_diagnostics(
    *,
    selected: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    dense_results: list[dict[str, Any]],
    keyword_results: list[dict[str, Any]],
    query_terms: list[str],
    vector_backend: str,
    embedding_backend: str,
) -> dict[str, Any]:
    doc_counts = Counter(item.get("documentId", "") for item in selected)
    top_doc_share = 0.0
    if selected and doc_counts:
        top_doc_share = max(doc_counts.values()) / len(selected)
    quality_flags: list[str] = []
    if not selected:
        quality_flags.append("no_evidence")
    if top_doc_share >= 0.75 and len(selected) >= 4:
        quality_flags.append("top_results_concentrated_in_one_document")
    if any((item.get("metadata") or {}).get("textQuality", {}).get("lineJoinRisk", 0) > 0.5 for item in selected):
        quality_flags.append("possible_pdf_text_joining_noise")
    low_evidence_candidates = sum(1 for item in candidates if _is_low_evidence(item))
    low_evidence_selected = sum(1 for item in selected if _is_low_evidence(item))
    if low_evidence_candidates:
        quality_flags.append("low_evidence_sections_downweighted")
    if low_evidence_selected:
        quality_flags.append("low_evidence_sections_in_selected_results")

    return {
        "retrievalStrategy": "dense+keyword+metadata+diversity",
        "vectorBackend": vector_backend,
        "embeddingBackend": embedding_backend,
        "queryTerms": query_terms[:20],
        "candidateCount": len(candidates),
        "denseCandidateCount": len(dense_results),
        "keywordCandidateCount": len(keyword_results),
        "selectedCount": len(selected),
        "lowEvidenceCandidateCount": low_evidence_candidates,
        "lowEvidenceSelectedCount": low_evidence_selected,
        "topDocumentShare": round(top_doc_share, 4),
        "qualityFlags": quality_flags,
        "scoreMeaning": "final = (0.62*dense + 0.30*keyword + 0.08*metadata) * evidenceWeight, then diversity selection",
    }


def _safe_norm(score: float, max_score: float) -> float:
    if max_score <= 0:
        return 0.0
    return max(0.0, min(1.0, score / max_score))


def _metadata_boost(query_terms: list[str], item: dict[str, Any]) -> float:
    metadata = item.get("metadata") or {}
    values = []
    for key in ["topics", "regions", "faults", "section"]:
        value = metadata.get(key)
        if isinstance(value, list):
            values.extend(str(entry).lower() for entry in value)
        elif value:
            values.append(str(value).lower())
    haystack = " ".join(values)
    if not haystack:
        return 0.0
    matched = sum(1 for term in query_terms if term.lower() in haystack)
    return min(1.0, matched / max(len(query_terms), 1) * 2)


def _keyword_score(*, query_terms: list[str], text: str, unit: KnowledgeUnit) -> float:
    normalized = text.lower()
    matched = 0
    weighted = 0.0
    for term in query_terms:
        term_lower = term.lower()
        count = normalized.count(term_lower)
        if count:
            matched += 1
            weighted += min(3, count) * (1.5 if len(term_lower) >= 5 else 1.0)
    metadata_text = " ".join(
        [
            unit.section or "",
            " ".join(unit.topics_json or []),
            " ".join(unit.regions_json or []),
            " ".join(unit.faults_json or []),
        ]
    ).lower()
    metadata_hits = sum(1 for term in query_terms if term.lower() in metadata_text)
    coverage = matched / max(len(query_terms), 1)
    score = coverage * 0.7 + min(1.0, weighted / 12) * 0.2 + min(1.0, metadata_hits / 4) * 0.1
    metadata = unit.metadata_json or {}
    evidence_role = metadata.get("evidenceRole") or _evidence_role(metadata.get("sectionRole") or _section_role(unit.section or "", unit.text))
    if evidence_role == "low-evidence":
        score *= 0.25
    elif evidence_role == "context":
        score *= 0.75
    return score


def _query_terms(query: str) -> list[str]:
    raw_terms = TOKEN_RE.findall(query)
    terms: list[str] = []
    for term in raw_terms:
        if re.fullmatch(r"[\u4e00-\u9fff]{2,}", term):
            terms.append(term)
            if len(term) > 2:
                terms.extend(term[index : index + 2] for index in range(len(term) - 1))
        elif len(term) >= 2:
            terms.append(term.lower())
    seen = set()
    ordered: list[str] = []
    for term in terms:
        if term not in seen:
            ordered.append(term)
            seen.add(term)
    return ordered


def _hit_from_vector_result(hit: dict[str, Any]) -> dict[str, Any]:
    payload = hit.get("payload", {})
    return {
        "unitId": payload.get("unit_id", ""),
        "documentId": payload.get("document_id", ""),
        "paperId": payload.get("paper_id", ""),
        "title": payload.get("title", ""),
        "contentType": payload.get("content_type", "text"),
        "text": payload.get("text", ""),
        "page": payload.get("page"),
        "score": float(hit.get("score", 0.0) or 0.0),
        "citation": payload.get("citation", {}),
        "metadata": {
            "authors": payload.get("authors", []),
            "year": payload.get("year"),
            "doi": payload.get("doi", ""),
            "sourceUrl": payload.get("source_url", ""),
            "regions": payload.get("regions", []),
            "faults": payload.get("faults", []),
            "topics": payload.get("topics", []),
            "section": payload.get("section", ""),
            "bbox": payload.get("bbox", {}),
            "modality": payload.get("modality", {}),
            "sectionRole": payload.get("section_role") or _section_role(payload.get("section", ""), payload.get("text", "")),
            "evidenceRole": payload.get("evidence_role")
            or _evidence_role(_section_role(payload.get("section", ""), payload.get("text", ""))),
            "language": payload.get("language", "unknown"),
            "textQuality": payload.get("text_quality", {}),
        },
    }


def _evidence_weight(item: dict[str, Any]) -> float:
    role = (item.get("metadata") or {}).get("evidenceRole", "primary")
    if role == "low-evidence":
        return 0.25
    if role == "context":
        return 0.75
    return 1.0


def _is_low_evidence(item: dict[str, Any]) -> bool:
    return (item.get("metadata") or {}).get("evidenceRole") == "low-evidence"
