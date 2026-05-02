from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

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


def initialize_geo_knowledge(db: Session) -> dict[str, Any]:
    store = init_knowledge_store()
    return {
        **store,
        "documents": db.query(GeoDocument).count(),
        "units": db.query(KnowledgeUnit).count(),
        "indexVersion": settings.geo_rag_index_version,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


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
    existing = db.get(GeoDocument, document_id)
    if existing is not None and not payload.get("force", False):
        return {
            **document_status(existing),
            "vectorStore": init_knowledge_store(),
            "embeddingBackend": "",
            "message": "Document already exists. Set force=true to rebuild its knowledge units.",
        }

    pages = _extract_pages(source_path)
    chunks = _chunk_pages(pages)
    if not chunks:
        raise ValueError("No extractable text was found in the document.")

    title = metadata.get("title") or source_path.stem
    authors = metadata.get("authors") or []
    year = metadata.get("year")
    doi = metadata.get("doi") or ""
    source_url = metadata.get("sourceUrl") or metadata.get("source_url") or ""
    parser = payload.get("parser") or ("pymupdf-blocks" if source_path.suffix.lower() == ".pdf" else "plain-text")

    document = existing or GeoDocument(id=document_id)
    document.paper_id = paper_id
    document.title = title
    document.authors_json = authors
    document.year = year
    document.doi = doi
    document.source_url = source_url
    document.file_name = source_path.name
    document.file_sha256 = digest
    document.parser = parser
    document.parser_version = "mvp-text-v1"
    document.status = "indexing"
    document.page_count = len(pages)
    document.unit_count = len(chunks)
    document.metadata_json = metadata
    db.merge(document)
    db.query(KnowledgeUnit).filter(KnowledgeUnit.document_id == document_id).delete(synchronize_session=False)
    db.flush()

    embedding_result = embed_texts([chunk["text"] for chunk in chunks])
    vector_items: list[dict[str, Any]] = []
    for index, (chunk, vector) in enumerate(zip(chunks, embedding_result.vectors), start=1):
        unit_id = unit_id_from_parts(document_id, index, "text")
        point_id = point_id_from_unit_id(unit_id)
        tags = _extract_geo_tags(f"{title}\n{chunk['text']}")
        text_quality = chunk.get("text_quality", {})
        citation = {
            "paperId": paper_id,
            "documentId": document_id,
            "title": title,
            "authors": authors,
            "year": year,
            "doi": doi,
            "page": chunk["page"],
            "sourceUrl": source_url,
        }
        unit = KnowledgeUnit(
            id=unit_id,
            document_id=document_id,
            paper_id=paper_id,
            unit_index=index,
            content_type="text",
            text=chunk["text"],
            page=chunk["page"],
            section=chunk.get("section", ""),
            bbox_json={},
            regions_json=tags["regions"],
            faults_json=tags["faults"],
            topics_json=tags["topics"],
            geo_entities_json=tags,
            modality_json={"parser": parser, "contentType": "text"},
            citation_json=citation,
            embedding_backend=embedding_result.backend,
            index_version=settings.geo_rag_index_version,
            qdrant_point_id=point_id,
            metadata_json={
                "fileSha256": digest,
                "chunkChars": len(chunk["text"]),
                "language": chunk.get("language", "unknown"),
                "textQuality": text_quality,
                "parserVersion": "geo-parser-v2",
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
                    text=chunk["text"],
                    page=chunk["page"],
                    section=chunk.get("section", ""),
                    language=chunk.get("language", "unknown"),
                    text_quality=text_quality,
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

    return {
        "documentId": document_id,
        "paperId": paper_id,
        "title": title,
        "status": "indexed",
        "parser": parser,
        "pages": len(pages),
        "units": len(chunks),
        "fileSha256": digest,
        "vectorStore": vector_store,
        "embeddingBackend": embedding_result.backend,
        "message": "Document was parsed, chunked, embedded, and indexed.",
    }


def get_geo_document_status(db: Session, document_id: str) -> dict[str, Any]:
    document = db.get(GeoDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_status(document)


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


def _resolve_source_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("filePath is required")
    if raw_path.startswith("local://"):
        candidate = Path(settings.geo_rag_storage_root) / raw_path.removeprefix("local://")
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
        pages.append({"page": index, "text": text, "paragraphs": [text] if text else [], "quality": _text_quality(text)})
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
                if len(block) >= 7 and block[6] != 0:
                    continue
                x0, y0, x1, y1 = [float(value) for value in block[:4]]
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
                blocks.append({"x0": x0, "y0": y0, "column": column, "text": text})

            ordered = _order_page_blocks(blocks)
            paragraphs = [item["text"] for item in ordered]
            text = "\n\n".join(paragraphs)
            pages.append(
                {
                    "page": page_index,
                    "text": text,
                    "paragraphs": paragraphs,
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
            pages.append({"page": index, "text": text, "paragraphs": [text] if text else [], "quality": _text_quality(text)})
    return pages


def _chunk_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments = _page_segments(pages)
    chunks: list[dict[str, Any]] = []
    chunk_chars = max(300, settings.geo_rag_chunk_chars)
    overlap = min(max(0, settings.geo_rag_chunk_overlap), chunk_chars // 2)
    buffer: list[str] = []
    start_page: int | None = None
    section = ""
    quality: dict[str, Any] = {}

    def flush() -> None:
        nonlocal buffer, start_page, section, quality
        text = WHITESPACE_RE.sub(" ", " ".join(buffer)).strip()
        if text:
            chunks.append(
                {
                    "page": start_page or 1,
                    "text": text,
                    "section": section,
                    "language": _detect_language(text),
                    "text_quality": {**_text_quality(text), **quality},
                }
            )
        buffer = []
        start_page = None
        section = ""
        quality = {}

    for segment in segments:
        for piece in _split_long_text(segment["text"], chunk_chars):
            current_text = " ".join(buffer)
            if buffer and len(current_text) + len(piece) > chunk_chars:
                tail = current_text[-overlap:].strip()
                flush()
                if tail:
                    buffer.append(tail)
            if start_page is None:
                start_page = segment["page"]
            if segment.get("section"):
                section = segment["section"]
            quality = segment.get("quality", {})
            buffer.append(piece)
    flush()
    return chunks


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
            segments.append(
                {
                    "page": page["page"],
                    "text": text,
                    "section": current_section,
                    "quality": page.get("quality", {}),
                }
            )
    return segments


def _looks_like_heading(text: str) -> bool:
    if len(text) > 140 or text.endswith("."):
        return False
    if re.match(r"^\d+(\.\d+)*\s+[A-Z\u4e00-\u9fff]", text):
        return True
    heading_words = {
        "abstract",
        "introduction",
        "methods",
        "methodology",
        "results",
        "discussion",
        "conclusion",
        "conclusions",
        "references",
        "摘要",
        "引言",
        "方法",
        "结果",
        "讨论",
        "结论",
        "参考文献",
    }
    return text.lower() in heading_words


def _looks_like_references_heading(text: str) -> bool:
    return text.lower() in {"references", "bibliography", "参考文献"}


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
    text: str,
    page: int | None,
    section: str,
    language: str,
    text_quality: dict[str, Any],
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
        "content_type": "text",
        "text": text,
        "page": page,
        "section": section,
        "language": language,
        "text_quality": text_quality,
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
        final_score = 0.62 * item["_dense"] + 0.30 * item["_keyword"] + 0.08 * metadata_boost
        item["score"] = round(final_score, 6)
        item["metadata"] = {
            **(item.get("metadata") or {}),
            "retrievalBreakdown": {
                "dense": round(item["_dense"], 4),
                "keyword": round(item["_keyword"], 4),
                "metadata": round(metadata_boost, 4),
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

    return {
        "retrievalStrategy": "dense+keyword+metadata+diversity",
        "vectorBackend": vector_backend,
        "embeddingBackend": embedding_backend,
        "queryTerms": query_terms[:20],
        "candidateCount": len(candidates),
        "denseCandidateCount": len(dense_results),
        "keywordCandidateCount": len(keyword_results),
        "selectedCount": len(selected),
        "topDocumentShare": round(top_doc_share, 4),
        "qualityFlags": quality_flags,
        "scoreMeaning": "final = 0.62*dense + 0.30*keyword + 0.08*metadata, then diversity selection",
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
    return coverage * 0.7 + min(1.0, weighted / 12) * 0.2 + min(1.0, metadata_hits / 4) * 0.1


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
            "language": payload.get("language", "unknown"),
            "textQuality": payload.get("text_quality", {}),
        },
    }
