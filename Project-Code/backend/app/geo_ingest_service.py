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

from .geo_ids import document_id_from_file, file_sha256, paper_id_from_metadata, point_id_from_unit_id, unit_id_from_parts
from .models import DocumentKnowledgeCard, GeoDocument, KnowledgeUnit
from .paper_database import get_paper_detail
from .rag_engines import get_geo_rag_engine_status, index_document_with_primary_engine, normalized_geo_rag_engine
from .settings import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
WHITESPACE_RE = re.compile(r"\s+")
SUPPORTED_DOCUMENT_SUFFIXES = {".pdf", ".txt", ".md"}


def initialize_geo_knowledge(db: Session) -> dict[str, Any]:
    rag_engine_status = get_geo_rag_engine_status()
    rag_status = rag_engine_status.get("raganything", {})
    ready = bool(rag_status.get("ready"))
    store = {
        "status": "ready" if ready else "not-ready",
        "backend": "raganything",
        "collection": settings.raganything_working_dir,
        "vectorSize": 0,
        "message": "RAGAnything/LightRAG is the primary RAG index. The legacy self-built vector index has been removed.",
        "warning": "" if ready else str(rag_status.get("reason") or "RAGAnything is not ready."),
    }
    return {
        **store,
        "documents": db.query(GeoDocument).count(),
        "units": db.query(KnowledgeUnit).count(),
        "knowledgeCards": db.query(DocumentKnowledgeCard).count(),
        "indexVersion": settings.geo_rag_index_version,
        "storageBackend": _storage_backend(),
        "ragEngine": rag_engine_status,
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
    force = bool(payload.get("force", False))

    metadata = _metadata_from_payload(payload)
    paper_id = str(payload.get("paperId") or "").strip()
    if paper_id:
        _merge_known_paper_metadata(metadata, paper_id)
    else:
        paper_id = paper_id_from_metadata(metadata)

    document_id = str(payload.get("documentId") or "").strip() or document_id_from_file(paper_id, digest)
    existing = _find_existing_document_for_ingest(db, document_id=document_id, digest=digest, doi=metadata.get("doi") or "")
    if existing is not None and not force and _existing_document_is_complete(existing):
        _cleanup_duplicate_upload_source(source_path, existing)
        return {
            **document_status(existing),
            "vectorStore": {},
            "embeddingBackend": _engine_embedding_backend(),
            "ragEngine": {
                "selected": settings.geo_rag_engine,
                "index": "skipped-duplicate-document",
            },
            "message": (
                "Document already exists; skipped duplicate import. "
                "Set force=true only when you intentionally want to rebuild it."
            ),
        }

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
    if normalized_geo_rag_engine() == "raganything":
        return _ingest_geo_document_with_raganything_engine(
            db=db,
            existing=existing,
            document_id=document_id,
            paper_id=paper_id,
            source_path=source_path,
            stored_path=stored_path,
            stored_file_name=stored_file_name,
            digest=digest,
            metadata=metadata,
            title=metadata.get("title") or source_path.stem,
            authors=metadata.get("authors") or [],
            year=metadata.get("year"),
            doi=metadata.get("doi") or "",
            source_url=metadata.get("sourceUrl") or metadata.get("source_url") or "",
        )

    raise RuntimeError("RAGAnything is the only supported literature RAG engine.")


def _existing_document_is_complete(document: GeoDocument) -> bool:
    # A failed import can leave metadata and the stored PDF behind before the
    # RAGAnything/LightRAG index is written. Only a finished document with
    # parsed blocks should be treated as a real duplicate.
    if str(document.status or "").lower() != "indexed":
        return False
    if int(document.unit_count or 0) <= 0:
        return False
    metadata = document.metadata_json if isinstance(document.metadata_json, dict) else {}
    return bool(metadata.get("raganythingContentStats"))

def _ingest_geo_document_with_raganything_engine(
    *,
    db: Session,
    existing: GeoDocument | None,
    document_id: str,
    paper_id: str,
    source_path: Path,
    stored_path: Path,
    stored_file_name: str,
    digest: str,
    metadata: dict[str, Any],
    title: str,
    authors: list[str],
    year: int | None,
    doi: str,
    source_url: str,
) -> dict[str, Any]:
    parser = f"raganything:{settings.raganything_parser}"
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
    document.parser_version = "raganything-engine-v1"
    document.status = "indexing"
    document.page_count = 0
    document.unit_count = 0
    document.metadata_json = metadata
    db.merge(document)
    db.query(KnowledgeUnit).filter(KnowledgeUnit.document_id == document_id).delete(synchronize_session=False)
    db.query(DocumentKnowledgeCard).filter(DocumentKnowledgeCard.document_id == document_id).delete(synchronize_session=False)
    db.commit()

    try:
        engine_result = index_document_with_primary_engine(
            file_path=str(stored_path),
            document_id=document_id,
            parser=parser,
        )
    except Exception:
        db.rollback()
        document.status = "failed"
        document.updated_at = datetime.now(timezone.utc)
        db.merge(document)
        db.commit()
        _cleanup_upload_stage_file(source_path, stored_path)
        raise

    content_stats = engine_result.get("contentStats") or {}
    content_blocks = engine_result.get("contentBlocks") if isinstance(engine_result.get("contentBlocks"), list) else []
    inserted_units = _insert_document_text_chunks(
        db,
        document_id=document_id,
        paper_id=paper_id,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        source_url=source_url,
        storage_uri=metadata["storageUri"],
        content_blocks=content_blocks,
    )
    page_count = int(content_stats.get("pages") or 0)
    unit_count = inserted_units or int(content_stats.get("blocks") or 0)
    multimodal_units = int(content_stats.get("multimodalBlocks") or 0)
    document.page_count = page_count
    document.unit_count = unit_count
    document.metadata_json = {
        **metadata,
        "raganythingContentStats": content_stats,
        "raganythingOutputDir": engine_result.get("outputDir", ""),
    }
    document_card = _raganything_document_card(
        document_id=document_id,
        paper_id=paper_id,
        title=title,
        authors=authors,
        year=year,
        doi=doi,
        source_url=source_url,
        storage_uri=metadata["storageUri"],
        content_stats=content_stats,
        engine_result=engine_result,
    )
    db.merge(
        DocumentKnowledgeCard(
            id=document_id,
            document_id=document_id,
            paper_id=paper_id,
            title=title,
            schema_version=document_card["schemaVersion"],
            card_json=document_card,
            card_text=document_card.get("searchableText", ""),
        )
    )
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
        "pages": page_count,
        "units": unit_count,
        "multimodalUnits": multimodal_units,
        "storageUri": metadata["storageUri"],
        "fileSha256": digest,
        "vectorStore": {
            "status": "not-used",
            "backend": "raganything-lightrag",
            "message": "RAGAnything/LightRAG is the primary index; legacy dual-write is disabled.",
        },
        "embeddingBackend": _engine_embedding_backend(),
        "ragEngine": {
            "selected": "raganything",
            "index": {
                key: value
                for key, value in engine_result.items()
                if key not in {"contentBlocks"}
            },
        },
        "knowledgeCard": {
            "schemaVersion": document_card["schemaVersion"],
            "researchQuestions": document_card.get("researchQuestions", []),
            "keyFindings": document_card.get("keyFindings", [])[:3],
            "limitations": document_card.get("limitations", []),
            "sourceStats": document_card.get("sourceStats", {}),
        },
        "message": "Document was stored and indexed by RAGAnything/LightRAG.",
    }


def _raganything_document_card(
    *,
    document_id: str,
    paper_id: str,
    title: str,
    authors: list[str],
    year: int | None,
    doi: str,
    source_url: str,
    storage_uri: str,
    content_stats: dict[str, Any],
    engine_result: dict[str, Any],
) -> dict[str, Any]:
    type_counts = content_stats.get("typeCounts") or {}
    samples = content_stats.get("sampleBlocks") or []
    sample_text = "\n".join(
        f"- [{item.get('type', 'text')} p.{item.get('page', '-')}] {item.get('text', '')}"
        for item in samples[:6]
        if isinstance(item, dict)
    )
    searchable_text = "\n".join(
        item
        for item in [
            title,
            "; ".join(authors),
            doi,
            source_url,
            sample_text,
        ]
        if item
    )
    limitations = [
        "文本 chunk 已写入本地 KnowledgeUnit 表；关系图谱仍由 RAGAnything/LightRAG 管理。",
        "若页面数或类型统计为 0，通常表示解析输出未生成 content_list，需检查 MinerU/RAGAnything 日志。",
    ]
    if int(content_stats.get("ocrBlocks") or 0) > 0:
        limitations.insert(
            0,
            "该文献使用 OCR 兜底抽取扫描页文本，检索可用但文字精度受扫描质量影响。",
        )
    if content_stats.get("parseFallback"):
        limitations.insert(
            0,
            "当前文献使用了轻量降级解析；后续补齐 MinerU/VLM/系统依赖后，可重新解析为完整多模态结果。",
        )
    return {
        "schemaVersion": "raganything-document-card-v1",
        "documentId": document_id,
        "paperId": paper_id,
        "title": title,
        "authors": authors,
        "year": year,
        "doi": doi,
        "sourceUrl": source_url,
        "storageUri": storage_uri,
        "sourceStats": {
            "documents": 1,
            "pages": int(content_stats.get("pages") or 0),
            "units": int(content_stats.get("blocks") or 0),
            "multimodalUnits": int(content_stats.get("multimodalBlocks") or 0),
            "ocrBlocks": int(content_stats.get("ocrBlocks") or 0),
            "typeCounts": type_counts,
            "sourceCounts": content_stats.get("sourceCounts") or {},
            "parser": content_stats.get("parser") or settings.raganything_parser,
            "requestedParseMethod": content_stats.get("requestedParseMethod") or settings.raganything_parse_method,
            "parseMethod": content_stats.get("parseMethod") or settings.raganything_parse_method,
            "parseFallback": bool(content_stats.get("parseFallback")),
            "parseFallbackReason": content_stats.get("parseFallbackReason", ""),
            "engine": "RAGAnything/LightRAG",
        },
        "researchQuestions": [
            "这篇文献研究了什么地质或地震科学问题？",
            "文献使用了哪些数据、方法、图表或公式证据？",
            "该文献的结论、适用范围和不确定性是什么？",
        ],
        "keyFindings": [
            "文献已由 RAGAnything 解析并写入 LightRAG 主索引。",
            "正文、图表、公式等多模态内容由 RAGAnything 负责组织与检索。",
            "本系统保留文献元数据、原文位置和解析统计，便于审查与迁移。",
        ],
        "limitations": limitations,
        "engineResult": {
            key: value
            for key, value in engine_result.items()
            if key not in {"contentStats", "contentBlocks"}
        },
        "sampleEvidence": samples[:8],
        "searchableText": searchable_text,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
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
                    "ragEngine": result.get("ragEngine", {}),
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


def _insert_document_text_chunks(
    db: Session,
    *,
    document_id: str,
    paper_id: str,
    title: str,
    authors: list[str],
    year: int | None,
    doi: str,
    source_url: str,
    storage_uri: str,
    content_blocks: list[dict[str, Any]],
) -> int:
    inserted = 0
    for block in content_blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("type") or block.get("content_type") or "text").strip().lower()
        text = _clean_text(block.get("text") or block.get("caption") or block.get("html") or "")
        if block_type != "text" or not text:
            continue
        inserted += 1
        page = block.get("page_idx", block.get("page"))
        page_number = page + 1 if isinstance(page, int) and page >= 0 else page if isinstance(page, int) else None
        section = str(block.get("section") or block.get("title") or "").strip()
        block_metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        unit_id = unit_id_from_parts(document_id, inserted, "text")
        db.merge(
            KnowledgeUnit(
                id=unit_id,
                document_id=document_id,
                paper_id=paper_id,
                unit_index=inserted,
                content_type="text",
                text=text,
                page=page_number,
                section=section,
                citation_json={
                    "paperId": paper_id,
                    "documentId": document_id,
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "doi": doi,
                    "sourceUrl": source_url,
                    "storageUri": storage_uri,
                },
                embedding_backend=_engine_embedding_backend(),
                index_version=settings.geo_rag_index_version,
                qdrant_point_id=point_id_from_unit_id(unit_id),
                metadata_json={
                    "engine": "raganything",
                    "source": block_metadata.get("source") or "content_list",
                    "parser": settings.raganything_parser,
                    "parseMethod": "local-ocr" if block_metadata.get("ocr") else settings.raganything_parse_method,
                    "ocr": bool(block_metadata.get("ocr")),
                    "ocrEngine": block_metadata.get("ocrEngine", ""),
                    "ocrLanguage": block_metadata.get("ocrLanguage", ""),
                    "ocrDpi": block_metadata.get("ocrDpi", 0),
                    "sectionRole": _section_role(section, text),
                    "evidenceRole": _evidence_role(_section_role(section, text)),
                },
            )
        )
    db.flush()
    return inserted


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
    return _search_geo_knowledge_with_raganything(db, query=query, top_k=top_k, filters=filters)

def _search_geo_knowledge_with_raganything(
    db: Session,
    *,
    query: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from .raganything_service import query_raganything_sync

    search_filters = _normalize_search_filters(filters or {})
    hits = _search_project_text_chunks(db, query=query, top_k=top_k, filters=search_filters)
    if hits:
        return {
            "query": query,
            "topK": top_k,
            "filters": search_filters,
            "backend": "raganything",
            "collection": settings.raganything_working_dir,
            "warning": "LightRAG chunk store is unavailable; using project KnowledgeUnit chunks.",
            "embeddingBackend": _engine_embedding_backend(),
            "results": hits,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "diagnostics": {
                "retrievalStrategy": "project-knowledge-unit-chunks",
                "engine": {"status": "skipped", "reason": "Project chunk index returned evidence first."},
                "qualityFlags": ["project_chunk_index"],
                "evidenceFragments": len(hits),
            },
            "storeStats": {
                "documents": db.query(GeoDocument).count(),
                "units": db.query(KnowledgeUnit).count(),
            },
        }
    result: dict[str, Any]
    try:
        result = query_raganything_sync(
            question=query,
            mode=settings.raganything_query_mode,
            only_need_prompt=True,
            fail_on_error=True,
        )
    except Exception as exc:
        result = {"status": "failed", "reason": str(exc), "queryMode": settings.raganything_query_mode}
    content = str(result.get("answer") or "")
    hits = _raganything_hits_from_context(
        db,
        query=query,
        content=content,
        top_k=top_k,
        filters=search_filters,
    )
    retrieval_strategy = "raganything-lightrag-primary"
    quality_flags = [] if hits else ["no_raganything_context"]
    if not hits:
        hits = _search_project_text_chunks(db, query=query, top_k=top_k, filters=search_filters)
        if hits:
            retrieval_strategy = "project-knowledge-unit-chunks"
            quality_flags = ["lightrag_context_unavailable", "project_chunk_fallback"]
    return {
        "query": query,
        "topK": top_k,
        "filters": search_filters,
        "backend": "raganything",
        "collection": settings.raganything_working_dir,
        "warning": "",
        "embeddingBackend": _engine_embedding_backend(),
        "results": hits,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "diagnostics": {
            "retrievalStrategy": retrieval_strategy,
            "engine": result,
            "qualityFlags": quality_flags if hits else ["no_raganything_context", "no_project_chunks"],
            "evidenceFragments": len(hits),
        },
        "storeStats": {
            "documents": db.query(GeoDocument).count(),
            "units": db.query(KnowledgeUnit).count(),
        },
    }


def _search_project_text_chunks(
    db: Session,
    *,
    query: str,
    top_k: int,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    rows = db.query(KnowledgeUnit, GeoDocument).outerjoin(GeoDocument, GeoDocument.id == KnowledgeUnit.document_id)
    rows = rows.filter(KnowledgeUnit.content_type == "text")
    document_filter = str(filters.get("document_id") or "").strip()
    paper_filter = str(filters.get("paper_id") or "").strip()
    if document_filter:
        rows = rows.filter(KnowledgeUnit.document_id == document_filter)
    if paper_filter:
        rows = rows.filter(KnowledgeUnit.paper_id == paper_filter)
    candidates = rows.limit(1000).all()
    terms = _search_terms(query)
    scored: list[tuple[int, KnowledgeUnit, GeoDocument | None]] = []
    for unit, document in candidates:
        haystack = f"{document.title if document is not None else ''} {unit.text}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score > 0 or not terms:
            scored.append((score, unit, document))
    scored.sort(key=lambda item: (item[0], len(item[1].text or "")), reverse=True)
    hits: list[dict[str, Any]] = []
    for index, (score, unit, document) in enumerate(scored[:top_k], start=1):
        title = document.title if document is not None else (unit.citation_json or {}).get("title", "")
        citation = unit.citation_json or {}
        public_url = _document_public_url(document) if document is not None else ""
        if public_url:
            citation = {**citation, "publicUrl": public_url}
        hits.append(
            {
                "unitId": unit.id,
                "documentId": unit.document_id,
                "paperId": unit.paper_id,
                "title": title or unit.paper_id,
                "contentType": unit.content_type,
                "text": unit.text[:1800],
                "page": unit.page,
                "score": max(0.1, min(1.0, 0.35 + score * 0.08 - (index - 1) * 0.03)),
                "citation": citation,
                "metadata": {
                    "engine": "project-chunk-index",
                    "queryMode": "keyword",
                    "fragmentIndex": index,
                    "matchedDocument": document is not None,
                    "note": "Fallback evidence from project KnowledgeUnit chunks.",
                },
            }
        )
    return hits


def _raganything_hits_from_context(
    db: Session,
    *,
    query: str,
    content: str,
    top_k: int,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    if not content.strip():
        return []
    documents = db.query(GeoDocument).all()
    fragments = _split_raganything_context(content, top_k=max(top_k, 1))
    hits: list[dict[str, Any]] = []
    document_filter = str(filters.get("document_id") or "").strip()
    paper_filter = str(filters.get("paper_id") or "").strip()
    for index, fragment in enumerate(fragments[:top_k], start=1):
        document = _match_document_for_raganything_fragment(documents, fragment)
        if document_filter and (document is None or document.id != document_filter):
            continue
        if paper_filter and (document is None or document.paper_id != paper_filter):
            continue
        citation: dict[str, Any] = {}
        if document is not None:
            citation = {
                "paperId": document.paper_id,
                "documentId": document.id,
                "title": document.title,
                "authors": document.authors_json or [],
                "year": document.year,
                "doi": document.doi,
                "sourceUrl": document.source_url,
                "storageUri": (document.metadata_json or {}).get("storageUri", ""),
                "publicUrl": _document_public_url(document),
            }
        hits.append(
            {
                "unitId": f"raganything-{uuid.uuid5(uuid.NAMESPACE_URL, query + ':' + str(index))}",
                "documentId": document.id if document is not None else "",
                "paperId": document.paper_id if document is not None else "",
                "title": document.title if document is not None else "RAGAnything retrieved evidence",
                "contentType": "raganything-context",
                "text": fragment,
                "page": _extract_page_hint(fragment),
                "score": max(0.05, 1.0 - (index - 1) * 0.06),
                "citation": citation,
                "metadata": {
                    "engine": "raganything",
                    "queryMode": settings.raganything_query_mode,
                    "onlyNeedPrompt": True,
                    "fragmentIndex": index,
                    "matchedDocument": bool(document),
                    "note": "This evidence fragment is extracted from the RAGAnything/LightRAG retrieval prompt.",
                },
            }
        )
    return hits


def _split_raganything_context(content: str, *, top_k: int) -> list[str]:
    cleaned = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []
    raw_parts = re.split(r"\n\s*\n+|(?=\n\s*(?:##+|\[\d+\]|Source|File|Document|Chunk)\b)", cleaned)
    fragments: list[str] = []
    for part in raw_parts:
        text = WHITESPACE_RE.sub(" ", part).strip(" -:\n\t")
        if len(text) < 80:
            continue
        if text.lower().startswith(("you are ", "system:", "assistant:")):
            continue
        fragments.append(text[:1800])
    if len(fragments) <= 1 and len(cleaned) > 1800:
        fragments = []
        cursor = 0
        chunk_size = 1200
        while cursor < len(cleaned) and len(fragments) < top_k:
            fragment = WHITESPACE_RE.sub(" ", cleaned[cursor : cursor + chunk_size]).strip()
            if fragment:
                fragments.append(fragment)
            cursor += chunk_size
    return fragments[:top_k]


def _match_document_for_raganything_fragment(
    documents: list[GeoDocument],
    fragment: str,
) -> GeoDocument | None:
    lower = fragment.lower()
    for document in documents:
        candidates = [
            document.id,
            document.paper_id,
            document.file_name,
            document.title,
            Path(document.file_name).stem if document.file_name else "",
        ]
        if any(candidate and candidate.lower() in lower for candidate in candidates):
            return document
    return None


def _extract_page_hint(fragment: str) -> int | None:
    match = re.search(r"\b(?:p\.?|page|页)\s*[:#.-]?\s*(\d{1,4})\b", fragment, re.IGNORECASE)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


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


def _find_existing_document_for_ingest(
    db: Session,
    *,
    document_id: str,
    digest: str,
    doi: str,
) -> GeoDocument | None:
    document = db.get(GeoDocument, document_id)
    if document is not None:
        return document

    document = (
        db.query(GeoDocument)
        .filter(GeoDocument.file_sha256 == digest)
        .order_by(GeoDocument.created_at.asc())
        .first()
    )
    if document is not None:
        return document

    normalized_doi = str(doi or "").strip()
    if normalized_doi:
        return (
            db.query(GeoDocument)
            .filter(GeoDocument.doi == normalized_doi)
            .order_by(GeoDocument.created_at.asc())
            .first()
        )
    return None


def _cleanup_duplicate_upload_source(source_path: Path, existing: GeoDocument) -> None:
    existing_path = _find_document_file(existing)
    _cleanup_upload_stage_file(source_path, existing_path or source_path)


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


def _engine_embedding_backend() -> str:
    if normalized_geo_rag_engine() == "raganything":
        return f"raganything:{settings.geo_rag_embedding_model or settings.openai_embedding_model or 'engine-default'}"
    return ""


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



def _normalize_search_filters(filters: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key in (
        "paper_id",
        "document_id",
        "content_type",
        "section_role",
        "evidence_role",
        "language",
        "index_version",
    ):
        value = filters.get(key)
        if value is not None and str(value).strip():
            normalized[key] = str(value).strip()
    topics = filters.get("topics")
    if isinstance(topics, list):
        cleaned = [str(item).strip() for item in topics if str(item).strip()]
        if cleaned:
            normalized["topics"] = cleaned
    return normalized


def _search_terms(query: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[\w\u4e00-\u9fff]+", str(query or "").lower()):
        if len(token) <= 1:
            continue
        terms.append(token)
        terms.extend(_bilingual_query_expansions(token))
        if re.search(r"[\u4e00-\u9fff]", token) and len(token) > 2:
            terms.extend(token[index : index + 2] for index in range(len(token) - 1))
    return list(dict.fromkeys(terms))


def _bilingual_query_expansions(token: str) -> list[str]:
    expansions = {
        "地震": ["earthquake", "seismic", "seismicity", "shock"],
        "断层": ["fault", "faulting", "faults"],
        "破裂": ["rupture", "surface rupture", "ruptures"],
        "构造": ["tectonic", "tectonics", "crustal", "plate"],
        "板块": ["plate", "plates", "plate tectonics"],
        "震级": ["magnitude", "magnitudes"],
        "滑动": ["slip", "displacement"],
        "俯冲": ["subduction", "underthrusting", "thrust"],
    }
    return expansions.get(token, [])


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return WHITESPACE_RE.sub(" ", str(value)).strip()


def _section_role(section: str, text: str) -> str:
    lower = f"{section} {text[:300]}".lower()
    if any(marker in lower for marker in ("abstract", "摘要")):
        return "abstract"
    if any(marker in lower for marker in ("conclusion", "summary", "结论")):
        return "conclusion"
    if any(marker in lower for marker in ("method", "data", "方法", "数据")):
        return "method"
    if any(marker in lower for marker in ("result", "discussion", "结果", "讨论")):
        return "finding"
    return "body"


def _evidence_role(section_role: str) -> str:
    if section_role in {"abstract", "conclusion"}:
        return "claim"
    if section_role in {"method"}:
        return "method"
    if section_role in {"finding"}:
        return "evidence"
    return "context"
