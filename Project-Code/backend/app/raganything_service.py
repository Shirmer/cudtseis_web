from __future__ import annotations

import asyncio
import inspect
import importlib.util
import json
import math
import os
from io import BytesIO
from pathlib import Path
import re
import sys
import threading
from typing import Any
from dataclasses import fields

from fastapi import HTTPException

from .embedding_service import embed_texts
from .settings import settings


_RAG_INSTANCE: Any | None = None
_RAG_LOCK = threading.RLock()
_RAG_LOOP: asyncio.AbstractEventLoop | None = None
_RAG_LOOP_THREAD: threading.Thread | None = None
_RAG_LOOP_THREAD_ID: int | None = None
_RAG_LOOP_LOCK = threading.Lock()
_RAG_OPERATION_LOCK: asyncio.Lock | None = None
WHITESPACE_RE = re.compile(r"\s+")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAGANYTHING_UPSTREAM_ROOT = PROJECT_ROOT / "RAG-Anything-main"
RAGANYTHING_UPSTREAM_REQUIRED_FILES = [
    "setup.py",
    "requirements.txt",
    "raganything/__init__.py",
    "raganything/raganything.py",
    "raganything/config.py",
    "raganything/processor.py",
    "raganything/query.py",
    "raganything/parser.py",
    "raganything/modalprocessors.py",
    "raganything/utils.py",
    "raganything/enhanced_markdown.py",
    "raganything/batch.py",
    "raganything/batch_parser.py",
    "raganything/base.py",
    "raganything/callbacks.py",
    "raganything/prompt.py",
    "raganything/prompt_manager.py",
    "raganything/prompts_zh.py",
    "raganything/resilience.py",
    "raganything/asset_urls.py",
    "raganything/omml_extractor.py",
]


def build_event_rag_documents(
    *,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    synthesis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert earthquake workflow data into RAGAnything content-list records."""

    docs: list[dict[str, Any]] = []
    mag = _safe_float(event.get("mag"))
    depth = _safe_float(event.get("depth_km"))
    place = _clean_text(event.get("place")) or "未知区域"
    event_type = _clean_text(event.get("type")) or "earthquake"

    docs.append(
        {
            "id": f"event:{event.get('id', 'unknown')}",
            "sourceType": "event",
            "title": f"事件参数: {place}",
            "content": (
                f"事件编号 {event.get('id', '')}，地点 {place}，事件类型 {event_type}，"
                f"震级 {mag if mag is not None else '未知'}，深度 {depth if depth is not None else '未知'} km，"
                f"时间 {event.get('time', '未知')}，经纬度 {event.get('lon', '未知')}, {event.get('lat', '未知')}。"
            ),
            "metadata": {
                "eventId": event.get("id", ""),
                "place": place,
                "magnitude": mag,
                "depthKm": depth,
            },
        }
    )

    cohort = synthesis.get("cohort") if isinstance(synthesis, dict) else {}
    if isinstance(cohort, dict) and cohort:
        top_regions = cohort.get("topRegions") or []
        top_region_text = "、".join(
            _clean_text(item.get("region"))
            for item in top_regions
            if isinstance(item, dict) and _clean_text(item.get("region"))
        ) or "当前监测区域"
        docs.append(
            {
                "id": f"cohort:{event.get('id', 'unknown')}",
                "sourceType": "cohort",
                "title": "同时间窗地震样本统计",
                "content": (
                    f"当前对比样本共有 {cohort.get('total', 0)} 条事件，最大震级 "
                    f"{cohort.get('maxMagnitude', '未知')}，高频区域包括 {top_region_text}。"
                ),
                "metadata": {
                    "total": cohort.get("total", 0),
                    "maxMagnitude": cohort.get("maxMagnitude"),
                },
            }
        )

    topic_signals = synthesis.get("topicSignals") if isinstance(synthesis, dict) else []
    if isinstance(topic_signals, list) and topic_signals:
        docs.append(
            {
                "id": f"topics:{event.get('id', 'unknown')}",
                "sourceType": "topic-signals",
                "title": "主题信号汇总",
                "content": "；".join(
                    f"{_clean_text(signal.get('label'))}：{_clean_text(signal.get('description'))}"
                    for signal in topic_signals
                    if isinstance(signal, dict)
                ),
                "metadata": {"topicCount": len(topic_signals)},
            }
        )

    summary = synthesis.get("summary") if isinstance(synthesis, dict) else {}
    if isinstance(summary, dict):
        headline = _clean_text(summary.get("headline"))
        subtitle = _clean_text(summary.get("subtitle"))
        closing = _clean_text(summary.get("closingParagraph"))
        if headline or subtitle or closing:
            docs.append(
                {
                    "id": f"summary:{event.get('id', 'unknown')}",
                    "sourceType": "synthesis",
                    "title": headline or "科研综述摘要",
                    "content": " ".join(part for part in (headline, subtitle, closing) if part),
                    "metadata": {},
                }
            )

        sections = summary.get("sections") or []
        if isinstance(sections, list):
            for index, section in enumerate(sections, start=1):
                if not isinstance(section, dict):
                    continue
                title = _clean_text(section.get("title")) or f"总结分段 {index}"
                section_text = " ".join(
                    _clean_text(paragraph)
                    for paragraph in (section.get("paragraphs") or [])
                    if _clean_text(paragraph)
                )
                if section_text:
                    docs.append(
                        {
                            "id": f"summary-section:{event.get('id', 'unknown')}:{index}",
                            "sourceType": "summary-section",
                            "title": title,
                            "content": section_text,
                            "metadata": {"sectionIndex": index},
                        }
                    )

    for index, paper in enumerate(papers, start=1):
        if not isinstance(paper, dict):
            continue
        title = _clean_text(paper.get("title"))
        abstract = _clean_text(paper.get("abstract"))
        evidence = _clean_text(paper.get("evidenceSnippet"))
        relevance = _clean_text(paper.get("relevanceHint"))
        venue = _clean_text(paper.get("venue")) or _clean_text(paper.get("source"))
        year = paper.get("year") or "未知年份"
        content = " ".join(
            part
            for part in (
                f"论文标题 {title}。" if title else "",
                f"研究主题 {relevance}。" if relevance else "",
                f"期刊或来源 {venue}，年份 {year}。" if venue else f"年份 {year}。",
                evidence,
                abstract,
            )
            if part
        )
        if content:
            docs.append(
                {
                    "id": f"paper:{paper.get('paperId') or index}",
                    "sourceType": "paper",
                    "title": title or f"文献 {index}",
                    "content": content,
                    "metadata": {
                        "paperId": paper.get("paperId", ""),
                        "url": paper.get("url", ""),
                        "source": paper.get("source", ""),
                        "year": paper.get("year", 0),
                        "citationCount": paper.get("citationCount", 0),
                    },
                }
            )

    if cohort_events:
        strongest = sorted(
            cohort_events,
            key=lambda item: _safe_float(item.get("mag")) or -math.inf,
            reverse=True,
        )[:5]
        strongest_text = "；".join(
            (
                f"{_clean_text(item.get('place')) or '未知区域'}"
                f" M{(_safe_float(item.get('mag')) or 0):.1f}"
                f" 深度 {(_safe_float(item.get('depth_km')) if _safe_float(item.get('depth_km')) is not None else '未知')} km"
            )
            for item in strongest
        )
        if strongest_text:
            docs.append(
                {
                    "id": f"cohort-strongest:{event.get('id', 'unknown')}",
                    "sourceType": "cohort-examples",
                    "title": "同窗样本中的代表事件",
                    "content": strongest_text,
                    "metadata": {"sampleCount": len(strongest)},
                }
            )

    return docs


def get_raganything_status() -> dict[str, Any]:
    _ensure_backend_venv_bin_on_path()
    _ensure_raganything_source_on_path()
    runtime = _runtime_dependency_status()
    snapshot = _source_snapshot_status()
    available = bool(runtime["available"])
    reason = str(runtime["reason"])
    ready = settings.raganything_enabled and available and bool(settings.openai_api_key)
    required_actions: list[str] = []
    if not settings.raganything_enabled:
        required_actions.append("Set RAGANYTHING_ENABLED=true in Project-Code/backend/.env.local.")
    if not available:
        required_actions.append("Run: python3 dev.py setup-raganything")
    if not settings.openai_api_key:
        required_actions.append("Configure OPENAI_API_KEY and OPENAI_BASE_URL for the OpenAI-compatible LLM endpoint.")
    upstream = snapshot.get("upstreamSource", {})
    if settings.raganything_source_dir and not upstream.get("complete", False):
        required_actions.append("Check RAGANYTHING_SOURCE_DIR or keep RAG-Anything-main in the project root.")
    return {
        "enabled": settings.raganything_enabled,
        "available": available,
        "ready": ready,
        "reason": reason,
        "engineMode": settings.geo_rag_engine,
        "workingDir": settings.raganything_working_dir,
        "outputDir": settings.raganything_output_dir,
        "documentDir": settings.raganything_document_dir,
        "allowedDocumentRoots": [str(path) for path in _allowed_document_roots()],
        "parser": settings.raganything_parser,
        "parseMethod": settings.raganything_parse_method,
        "allowParseFallback": settings.raganything_allow_parse_fallback,
        "parseFallbackMethod": settings.raganything_parse_fallback_method,
        "queryMode": settings.raganything_query_mode,
        "allowQueryFallback": settings.raganything_allow_query_fallback,
        "queryFallbackMode": settings.raganything_query_fallback_mode,
        "dependencies": runtime,
        "sourceSnapshot": snapshot,
        "requiredActions": required_actions,
    }


async def ingest_event_bundle_with_raganything(
    *,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    synthesis: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    return await _run_on_rag_loop(
        lambda: _with_rag_operation(
            lambda: _ingest_event_bundle_with_raganything_impl(
                event=event,
                cohort_events=cohort_events,
                papers=papers,
                synthesis=synthesis,
                force=force,
            )
        )
    )


async def _ingest_event_bundle_with_raganything_impl(
    *,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    synthesis: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    rag = await _get_raganything()
    docs = build_event_rag_documents(
        event=event,
        cohort_events=cohort_events,
        papers=papers,
        synthesis=synthesis or {},
    )
    doc_id = f"event-{_safe_id(event.get('id', 'latest-event'))}"
    marker = _marker_path(doc_id)
    if marker.exists() and not force:
        return {
            "status": "ready",
            "mode": "raganything-content-list-persistent",
            "documents": len(docs),
            "storePath": settings.raganything_working_dir,
            "message": "RAGAnything index already exists for this event bundle.",
        }

    content_list = [
        {
            "type": "text",
            "text": f"{doc['title']}\n{doc['content']}",
            "page_idx": index,
        }
        for index, doc in enumerate(docs)
    ]
    await rag.insert_content_list(
        content_list=content_list,
        file_path=f"{doc_id}.json",
        doc_id=doc_id,
        display_stats=False,
    )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(len(docs)), encoding="utf-8")
    return {
        "status": "ready",
        "mode": "raganything-content-list-fresh",
        "documents": len(docs),
        "storePath": settings.raganything_working_dir,
        "message": "Event literature bundle inserted into RAGAnything.",
    }


async def ingest_document_with_raganything(
    *,
    file_path: str,
    doc_id: str | None = None,
    parse_method: str | None = None,
    parser: str | None = None,
) -> dict[str, Any]:
    return await _run_on_rag_loop(
        lambda: _with_rag_operation(
            lambda: _ingest_document_with_raganything_impl(
                file_path=file_path,
                doc_id=doc_id,
                parse_method=parse_method,
                parser=parser,
            )
        )
    )


async def _ingest_document_with_raganything_impl(
    *,
    file_path: str,
    doc_id: str | None = None,
    parse_method: str | None = None,
    parser: str | None = None,
) -> dict[str, Any]:
    rag = await _get_raganything()
    target = _resolve_document_path(file_path)
    output_dir = Path(settings.raganything_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    effective_parser = parser or settings.raganything_parser
    requested_parse_method = _normalize_parse_method(parse_method or settings.raganything_parse_method)
    used_parse_method = requested_parse_method
    fallback_reason = ""
    content_blocks: list[dict[str, Any]] = []
    if effective_parser and hasattr(rag, "config"):
        setattr(rag.config, "parser", effective_parser)
    try:
        await _process_document_with_raganything(
            rag,
            target=target,
            output_dir=output_dir,
            parse_method=requested_parse_method,
            doc_id=doc_id,
        )
    except Exception as exc:
        fallback_method = _normalize_parse_method(settings.raganything_parse_fallback_method)
        if not _can_fallback_parse(
            exc,
            requested_parse_method=requested_parse_method,
            fallback_method=fallback_method,
        ):
            raise
        fallback_reason = _exception_detail(exc)
        used_parse_method = fallback_method
        content_blocks = await _insert_local_text_content_list_fallback(
            rag,
            target=target,
            doc_id=doc_id,
        )
    if not content_blocks:
        content_blocks = _load_latest_content_list(target, output_dir)
    if not content_blocks and target.suffix.lower() == ".pdf" and settings.raganything_enable_ocr_fallback:
        fallback_reason = fallback_reason or "Parser returned no text content; OCR fallback was used."
        used_parse_method = "local-ocr"
        content_blocks = await _insert_local_ocr_content_list_fallback(
            rag,
            target=target,
            doc_id=doc_id,
        )
    content_stats = _content_list_stats(content_blocks)
    if content_stats.get("ocrBlocks"):
        used_parse_method = "local-ocr"
        fallback_reason = fallback_reason or "PDF text extraction produced no usable text; OCR fallback was used."
    content_stats.update(
        {
            "parser": effective_parser,
            "requestedParseMethod": requested_parse_method,
            "parseMethod": used_parse_method,
            "parseFallback": bool(fallback_reason),
        }
    )
    if fallback_reason:
        content_stats["parseFallbackReason"] = fallback_reason[:2000]
    return {
        "status": "ready",
        "mode": "raganything-document-parser-fallback" if fallback_reason else "raganything-document-parser",
        "documents": 1,
        "storePath": settings.raganything_working_dir,
        "outputDir": str(output_dir),
        "contentStats": content_stats,
        "contentBlocks": content_blocks,
        "message": (
            f"Document parsed with fallback {used_parse_method} and inserted: {target.name}"
            if fallback_reason
            else f"Document parsed and inserted: {target.name}"
        ),
    }


async def _process_document_with_raganything(
    rag: Any,
    *,
    target: Path,
    output_dir: Path,
    parse_method: str,
    doc_id: str | None,
) -> None:
    if hasattr(rag, "config"):
        setattr(rag.config, "parse_method", parse_method)
    await rag.process_document_complete(
        file_path=str(target),
        output_dir=str(output_dir),
        parse_method=parse_method,
        doc_id=doc_id,
    )


async def _insert_local_text_content_list_fallback(
    rag: Any,
    *,
    target: Path,
    doc_id: str | None,
) -> list[dict[str, Any]]:
    content_blocks = await asyncio.to_thread(_build_local_text_content_list, target)
    if not content_blocks:
        raise RuntimeError(f"Local text fallback produced no content for {target}")
    await rag.insert_content_list(
        content_list=content_blocks,
        file_path=str(target),
        doc_id=doc_id,
        display_stats=False,
    )
    return content_blocks


async def _insert_local_ocr_content_list_fallback(
    rag: Any,
    *,
    target: Path,
    doc_id: str | None,
) -> list[dict[str, Any]]:
    content_blocks = await asyncio.to_thread(_build_pdf_ocr_content_list, target)
    if not content_blocks:
        raise RuntimeError(f"Local OCR fallback produced no content for {target}")
    await rag.insert_content_list(
        content_list=content_blocks,
        file_path=str(target),
        doc_id=doc_id,
        display_stats=False,
    )
    return content_blocks


def _build_local_text_content_list(target: Path) -> list[dict[str, Any]]:
    suffix = target.suffix.lower()
    if suffix == ".pdf":
        blocks = _build_pdf_text_content_list(target)
        if blocks or not settings.raganything_enable_ocr_fallback:
            return blocks
        return _build_pdf_ocr_content_list(target)
    if suffix in {".txt", ".md"}:
        text = target.read_text(encoding="utf-8", errors="ignore")
        return _text_to_content_blocks(text, page_idx=0, metadata={"source": "local-text"})
    raise RuntimeError(f"Local text fallback does not support {suffix or 'unknown'} files")


def _build_pdf_text_content_list(target: Path) -> list[dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("Local PDF text fallback requires pypdf") from exc

    reader = PdfReader(str(target))
    blocks: list[dict[str, Any]] = []
    for page_index, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        blocks.extend(_text_to_content_blocks(text, page_idx=page_index, metadata={"source": "pdf-text"}))
    return blocks


def _build_pdf_ocr_content_list(target: Path) -> list[dict[str, Any]]:
    try:
        import fitz
    except Exception as exc:
        raise RuntimeError("Local PDF OCR fallback requires PyMuPDF") from exc
    try:
        from PIL import Image
    except Exception as exc:
        raise RuntimeError("Local PDF OCR fallback requires Pillow") from exc
    try:
        import pytesseract
    except Exception as exc:
        raise RuntimeError("Local PDF OCR fallback requires pytesseract") from exc

    dpi = max(96, min(int(settings.raganything_ocr_dpi or 180), 300))
    max_pages = max(1, int(settings.raganything_ocr_max_pages or 120))
    language = str(settings.raganything_ocr_language or "eng").strip() or "eng"
    tesseract_config = str(settings.raganything_ocr_tesseract_config or "").strip()
    blocks: list[dict[str, Any]] = []
    with fitz.open(str(target)) as document:
        page_count = min(len(document), max_pages)
        matrix = fitz.Matrix(dpi / 72, dpi / 72)
        for page_index in range(page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            try:
                text = pytesseract.image_to_string(
                    image,
                    lang=language,
                    config=tesseract_config,
                )
            except Exception as exc:
                raise RuntimeError(f"Local OCR failed on page {page_index + 1}: {_exception_detail(exc)}") from exc
            blocks.extend(
                _text_to_content_blocks(
                    text,
                    page_idx=page_index,
                    metadata={
                        "source": "ocr",
                        "ocr": True,
                        "ocrEngine": "tesseract",
                        "ocrLanguage": language,
                        "ocrDpi": dpi,
                    },
                )
            )
    return blocks


def _text_to_content_blocks(
    text: str,
    *,
    page_idx: int,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    blocks: list[dict[str, Any]] = []
    max_chars = 4000
    overlap = 300
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        segment = cleaned[start:end].strip()
        if segment:
            block: dict[str, Any] = {"type": "text", "text": segment, "page_idx": page_idx}
            if metadata:
                block["metadata"] = dict(metadata)
            blocks.append(block)
        if end >= len(cleaned):
            break
        start = max(0, end - overlap)
    return blocks


def _normalize_parse_method(value: str | None) -> str:
    cleaned = str(value or "").strip()
    return cleaned or "auto"


def _can_fallback_parse(
    exc: Exception,
    *,
    requested_parse_method: str,
    fallback_method: str,
) -> bool:
    if not settings.raganything_allow_parse_fallback:
        return False
    if not fallback_method or fallback_method == requested_parse_method:
        return False
    detail = _exception_detail(exc).lower()
    if any(
        marker in detail
        for marker in (
            "invalid token",
            "unauthorized",
            "authentication",
            "api key",
            "api_key",
            "embedding service failed",
            "document not found",
            "not found:",
        )
    ):
        return False
    # These errors mean the complete MinerU/VLM route cannot run in the current
    # environment, but a text-only RAGAnything parse can still keep the queue useful.
    fallback_markers = (
        "mineru",
        "magic_pdf",
        "hybrid",
        "pipeline",
        "parser",
        "parse",
        "torch",
        "libgl",
        "opencv",
        "modelscope",
        "dependency",
        "received unexpected keyword",
    )
    return any(marker in detail for marker in fallback_markers)


async def query_raganything(
    *,
    question: str,
    mode: str | None = None,
    vlm_enhanced: bool | None = None,
    only_need_prompt: bool = False,
) -> dict[str, Any]:
    return await _run_on_rag_loop(
        lambda: _with_rag_operation(
            lambda: _query_raganything_impl(
                question=question,
                mode=mode,
                vlm_enhanced=vlm_enhanced,
                only_need_prompt=only_need_prompt,
            )
        )
    )


async def _query_raganything_impl(
    *,
    question: str,
    mode: str | None = None,
    vlm_enhanced: bool | None = None,
    only_need_prompt: bool = False,
) -> dict[str, Any]:
    rag = await _get_raganything()
    await _ensure_raganything_query_ready(rag)
    if not await _raganything_has_indexed_documents(rag):
        raise HTTPException(
            status_code=409,
            detail=(
                "RAGAnything/LightRAG is ready but the literature index is empty. "
                "Import at least one PDF/TXT/MD document before asking literature questions."
            ),
        )
    requested_mode = _normalize_query_mode(mode or settings.raganything_query_mode)
    attempt_modes = _query_attempt_modes(requested_mode, only_need_prompt=only_need_prompt)
    attempts: list[dict[str, str]] = []
    fallback_reason = ""
    result: Any = None
    used_mode = requested_mode
    for index, attempt_mode in enumerate(attempt_modes):
        kwargs = _query_kwargs(
            mode=attempt_mode,
            vlm_enhanced=vlm_enhanced,
            only_need_prompt=only_need_prompt,
        )
        try:
            result = await rag.aquery(question, **kwargs)
        except ValueError as exc:
            if "No LightRAG instance available" in str(exc):
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "RAGAnything is installed but the LightRAG index is empty or not initialized. "
                        "Import at least one PDF/TXT/MD document before asking literature questions."
                    ),
                ) from exc
            attempts.append({"mode": attempt_mode, "status": "failed", "reason": _exception_detail(exc)[:500]})
            if not _can_retry_query_attempt(
                exc,
                attempt_index=index,
                attempt_count=len(attempt_modes),
                only_need_prompt=only_need_prompt,
            ):
                raise
            fallback_reason = _exception_detail(exc)
            continue
        except Exception as exc:
            attempts.append({"mode": attempt_mode, "status": "failed", "reason": _exception_detail(exc)[:500]})
            if not _can_retry_query_attempt(
                exc,
                attempt_index=index,
                attempt_count=len(attempt_modes),
                only_need_prompt=only_need_prompt,
            ):
                raise
            fallback_reason = _exception_detail(exc)
            continue

        unusable_reason = _unusable_query_result_reason(result)
        if unusable_reason:
            attempts.append({"mode": attempt_mode, "status": "empty", "reason": unusable_reason})
            if index + 1 >= len(attempt_modes):
                card_fallback = await _query_document_cards_fallback(
                    rag=rag,
                    question=question,
                    requested_mode=requested_mode,
                    attempts=attempts,
                    reason=unusable_reason,
                )
                if card_fallback is not None:
                    return card_fallback
                raise _empty_query_http_exception()
            fallback_reason = unusable_reason
            continue

        attempts.append({"mode": attempt_mode, "status": "ready", "reason": ""})
        used_mode = attempt_mode
        break
    else:
        raise HTTPException(
            status_code=502,
            detail=(
                "RAGAnything query failed before producing an answer. "
                f"Attempts: {', '.join(item['mode'] + ':' + item['status'] for item in attempts)}"
            ),
        )

    fallback_active = used_mode != requested_mode
    return {
        "status": "ready",
        "question": question,
        "answer": str(result),
        "retrievalMode": f"raganything:{used_mode}",
        "queryMode": used_mode,
        "mode": "raganything",
        "attemptedQueryModes": [item["mode"] for item in attempts],
        "queryFallback": {
            "active": fallback_active,
            "requestedMode": requested_mode,
            "usedMode": used_mode,
            "reason": fallback_reason[:2000] if fallback_active else "",
            "attempts": attempts,
        },
    }


def _query_kwargs(
    *,
    mode: str,
    vlm_enhanced: bool | None,
    only_need_prompt: bool,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"mode": mode}
    # RAGAnything auto-enables VLM-enhanced query when a vision model exists.
    # The production literature index is text-first today, so default to a
    # stable text query unless the caller explicitly opts into VLM.
    kwargs["vlm_enhanced"] = bool(vlm_enhanced) if vlm_enhanced is not None else False
    if only_need_prompt:
        kwargs["only_need_prompt"] = True
        kwargs["vlm_enhanced"] = False
    return kwargs


def _query_attempt_modes(requested_mode: str, *, only_need_prompt: bool) -> list[str]:
    modes = [requested_mode]
    fallback_mode = _normalize_query_mode(settings.raganything_query_fallback_mode)
    if (
        settings.raganything_allow_query_fallback
        and not only_need_prompt
        and fallback_mode
        and fallback_mode != requested_mode
        and requested_mode not in {"naive", "bypass"}
    ):
        modes.append(fallback_mode)
    return modes


def _normalize_query_mode(value: str | None) -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned or "hybrid"


def _query_result_is_empty(result: Any) -> bool:
    return result is None or (isinstance(result, str) and not result.strip())


def _unusable_query_result_reason(result: Any) -> str:
    if _query_result_is_empty(result):
        return "RAGAnything returned an empty answer."
    if isinstance(result, str) and _query_result_has_no_context(result):
        return "RAGAnything returned a no-context answer."
    return ""


def _query_result_has_no_context(result: str) -> bool:
    normalized = result.lower()
    return "[no-context]" in normalized or "no context" in normalized


def _empty_query_http_exception() -> HTTPException:
    return HTTPException(
        status_code=502,
        detail=(
            "RAGAnything returned an empty answer. Check the LLM API configuration "
            "and confirm that the imported documents have completed indexing."
        ),
    )


def _can_retry_query_attempt(
    exc: Exception,
    *,
    attempt_index: int,
    attempt_count: int,
    only_need_prompt: bool,
) -> bool:
    if only_need_prompt or attempt_index + 1 >= attempt_count:
        return False
    detail = _exception_detail(exc).lower()
    if any(
        marker in detail
        for marker in (
            "invalid token",
            "unauthorized",
            "authentication",
            "api key",
            "api_key",
            "embedding service failed",
            "index is empty",
            "no lightrag instance",
        )
    ):
        return False
    return True


async def _query_document_cards_fallback(
    *,
    rag: Any,
    question: str,
    requested_mode: str,
    attempts: list[dict[str, str]],
    reason: str,
) -> dict[str, Any] | None:
    evidence = _local_chunk_fallback_evidence(question, limit=6)
    evidence_source = "knowledge-unit-chunks"
    if not evidence:
        evidence = _document_card_fallback_evidence(question, limit=5)
        evidence_source = "document-cards"
    if not evidence:
        return None
    fallback_mode = "document-card"
    answer, answer_source, llm_error = await _synthesize_document_card_fallback_answer(
        rag=rag,
        question=question,
        evidence=evidence,
    )
    fallback_attempts = [*attempts, {"mode": fallback_mode, "status": "ready", "reason": ""}]
    return {
        "status": "ready",
        "question": question,
        "answer": answer,
        "retrievalMode": "raganything:document-card-fallback",
        "queryMode": fallback_mode,
        "mode": "raganything",
        "attemptedQueryModes": [item["mode"] for item in fallback_attempts],
        "queryFallback": {
            "active": True,
            "requestedMode": requested_mode,
            "usedMode": fallback_mode,
            "reason": reason[:2000],
            "attempts": fallback_attempts,
            "evidence": evidence,
            "evidenceSource": evidence_source,
            "answerSource": answer_source,
            "llmError": llm_error,
        },
    }


def _local_chunk_fallback_evidence(question: str, *, limit: int = 6) -> list[dict[str, Any]]:
    try:
        from .db import SessionLocal
        from .models import GeoDocument, KnowledgeUnit
    except Exception:
        return []

    try:
        with SessionLocal() as db:
            units = (
                db.query(KnowledgeUnit, GeoDocument)
                .outerjoin(GeoDocument, GeoDocument.id == KnowledgeUnit.document_id)
                .filter(KnowledgeUnit.content_type == "text")
                .limit(500)
                .all()
            )
            scored = [
                _score_knowledge_unit(question, unit, document)
                for unit, document in units
            ]
    except Exception:
        return []
    scored = [item for item in scored if item["score"] > 0 or item["sample"]]
    scored.sort(key=lambda item: (item["score"], len(item["sample"])), reverse=True)
    return scored[: max(1, min(limit, 12))]


def _score_knowledge_unit(question: str, unit: Any, document: Any | None) -> dict[str, Any]:
    title = str(getattr(document, "title", "") or (unit.citation_json or {}).get("title") or unit.paper_id or "")
    text = _clean_text(unit.text)[:1600]
    haystack = f"{title} {text}".lower()
    terms = _fallback_query_terms(question)
    score = sum(1 for term in terms if term and term.lower() in haystack)
    return {
        "documentId": str(unit.document_id or ""),
        "paperId": str(unit.paper_id or ""),
        "title": title,
        "score": score,
        "sample": text,
        "page": unit.page,
        "unitId": unit.id,
        "unitIndex": unit.unit_index,
        "sourceStats": {
            "pages": getattr(document, "page_count", 0) if document is not None else 0,
            "units": getattr(document, "unit_count", 0) if document is not None else 0,
            "source": "knowledge_units",
        },
    }


def _document_card_fallback_evidence(question: str, *, limit: int = 5) -> list[dict[str, Any]]:
    try:
        from .db import SessionLocal
        from .models import DocumentKnowledgeCard
    except Exception:
        return []

    try:
        with SessionLocal() as db:
            cards = (
                db.query(DocumentKnowledgeCard)
                .order_by(DocumentKnowledgeCard.updated_at.desc())
                .limit(80)
                .all()
            )
            scored = [_score_document_card(question, card) for card in cards]
    except Exception:
        return []
    scored = [item for item in scored if item["score"] > 0 or item["sample"]]
    scored.sort(key=lambda item: (item["score"], len(item["sample"])), reverse=True)
    return scored[: max(1, min(limit, 12))]


def _score_document_card(question: str, card: Any) -> dict[str, Any]:
    card_json = card.card_json if isinstance(card.card_json, dict) else {}
    samples = card_json.get("sampleEvidence") or []
    sample_texts: list[str] = []
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        text = _clean_text(sample.get("text"))
        if text:
            sample_texts.append(text)
    sample = " ".join(sample_texts[:3])[:1400]
    haystack = " ".join(
        item
        for item in (
            card.title,
            card.card_text,
            sample,
        )
        if item
    ).lower()
    terms = _fallback_query_terms(question)
    score = sum(1 for term in terms if term and term.lower() in haystack)
    return {
        "documentId": str(card.document_id or ""),
        "paperId": str(card.paper_id or ""),
        "title": str(card.title or ""),
        "score": score,
        "sample": sample,
        "sourceStats": card_json.get("sourceStats") if isinstance(card_json.get("sourceStats"), dict) else {},
    }


def _fallback_query_terms(question: str) -> list[str]:
    terms: list[str] = []
    for token in re.findall(r"[\w\u4e00-\u9fff]+", question.lower()):
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


async def _synthesize_document_card_fallback_answer(
    *,
    rag: Any,
    question: str,
    evidence: list[dict[str, Any]],
) -> tuple[str, str, str]:
    prompt = _document_card_fallback_prompt(question, evidence)
    llm_func = getattr(rag, "llm_model_func", None)
    if llm_func is None:
        return _format_document_card_extract_answer(question, evidence), "extractive", "RAGAnything LLM function is unavailable."
    try:
        result = llm_func(
            prompt,
            system_prompt=(
                "你是地震学和构造地质方向的谨慎科研 RAG 助手。"
                "只能基于用户提供的证据回答，不能编造未出现的文献结论。"
            ),
        )
        if inspect.isawaitable(result):
            result = await result
        answer = _clean_text_preserve_lines(result)
        if not answer:
            raise RuntimeError("LLM returned an empty synthesis.")
        return answer, "llm", ""
    except Exception as exc:
        return _format_document_card_extract_answer(question, evidence), "extractive", _exception_detail(exc)[:1000]


def _document_card_fallback_prompt(question: str, evidence: list[dict[str, Any]]) -> str:
    evidence_lines = []
    for index, item in enumerate(evidence, start=1):
        stats = item.get("sourceStats") if isinstance(item.get("sourceStats"), dict) else {}
        pages = stats.get("pages") or "?"
        units = stats.get("units") or stats.get("blocks") or "?"
        sample = _clean_text(item.get("sample"))[:1600]
        evidence_lines.append(
            f"[{index}] 标题：{item.get('title') or item.get('paperId') or 'Untitled'}\n"
            f"文献ID：{item.get('paperId') or ''}\n"
            f"解析统计：页数 {pages}，文本块 {units}\n"
            f"证据摘录：{sample or '样本文本为空'}"
        )
    return (
        "LightRAG 当前没有返回可用上下文，下面是系统从已入库文献知识卡片中选出的候选证据。"
        "请基于这些证据对用户问题做中文科研分析。\n\n"
        f"用户问题：{question}\n\n"
        "候选证据：\n"
        + "\n\n".join(evidence_lines)
        + "\n\n请按以下结构回答：\n"
        "1. 直接结论：用 2-4 句话回答问题。\n"
        "2. 证据依据：列出 3-5 条证据，标注对应文献标题。\n"
        "3. 不确定性：说明当前只是知识卡片兜底，不等同于完整 LightRAG hybrid 检索。\n"
        "不要输出大段英文原文，不要声称读到了证据之外的信息。"
    )


def _format_document_card_extract_answer(question: str, evidence: list[dict[str, Any]]) -> str:
    lines = [
        "LightRAG 当前没有返回可用上下文，且 LLM 综合分析暂时不可用；下面先基于已入库文献知识卡片和解析样本文本给出保守回答。",
        "",
        f"问题：{question}",
        "",
        "可用证据：",
    ]
    for index, item in enumerate(evidence, start=1):
        stats = item.get("sourceStats") if isinstance(item.get("sourceStats"), dict) else {}
        pages = stats.get("pages") or "?"
        units = stats.get("units") or stats.get("blocks") or "?"
        sample = _clean_text(item.get("sample"))[:500]
        lines.append(
            f"{index}. {item.get('title') or item.get('paperId') or 'Untitled'}"
            f"（页数 {pages}，文本块 {units}）：{sample or '该文献已有入库记录，但知识卡片样本文本较少。'}"
        )
    lines.extend(
        [
            "",
            "使用建议：把以上条目视为临时证据索引；完整结论仍应等待 RAGAnything/LightRAG 恢复上下文检索后再细化。",
        ]
    )
    return "\n".join(lines)


def _clean_text_preserve_lines(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    compact: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank:
                compact.append("")
            previous_blank = True
            continue
        compact.append(line)
        previous_blank = False
    return "\n".join(compact).strip()


def ingest_document_with_raganything_sync(
    *,
    file_path: str,
    doc_id: str | None = None,
    parse_method: str | None = None,
    parser: str | None = None,
    fail_on_error: bool = False,
) -> dict[str, Any]:
    if not settings.raganything_enabled:
        if fail_on_error:
            raise HTTPException(
                status_code=503,
                detail="RAGAnything is disabled. Set RAGANYTHING_ENABLED=true to index documents.",
            )
        return {
            "status": "skipped",
            "engine": "raganything",
            "reason": "RAGAnything is disabled. Set RAGANYTHING_ENABLED=true to index documents.",
        }
    try:
        result = _run_async_from_sync(
            ingest_document_with_raganything(
                file_path=file_path,
                doc_id=doc_id,
                parse_method=parse_method,
                parser=parser,
            )
        )
        return {
            "status": "ready",
            "engine": "raganything",
            "documentId": doc_id or "",
            **result,
        }
    except Exception as exc:
        if fail_on_error:
            raise
        return {
            "status": "failed",
            "engine": "raganything",
            "documentId": doc_id or "",
            "reason": _exception_detail(exc),
        }


def query_raganything_sync(
    *,
    question: str,
    mode: str | None = None,
    vlm_enhanced: bool | None = None,
    only_need_prompt: bool = False,
    fail_on_error: bool = False,
) -> dict[str, Any]:
    if not settings.raganything_enabled:
        if fail_on_error:
            raise HTTPException(status_code=503, detail="RAGAnything is disabled.")
        return {
            "status": "skipped",
            "engine": "raganything",
            "reason": "RAGAnything is disabled.",
        }
    try:
        result = _run_async_from_sync(
            query_raganything(
                question=question,
                mode=mode,
                vlm_enhanced=vlm_enhanced,
                only_need_prompt=only_need_prompt,
            )
        )
        return {
            "status": "ready",
            "engine": "raganything",
            **result,
        }
    except Exception as exc:
        if fail_on_error:
            raise
        return {
            "status": "failed",
            "engine": "raganything",
            "reason": _exception_detail(exc),
        }


async def _run_on_rag_loop(coro_factory):
    if threading.get_ident() == _RAG_LOOP_THREAD_ID:
        return await coro_factory()
    future = asyncio.run_coroutine_threadsafe(coro_factory(), _ensure_rag_loop())
    return await asyncio.wrap_future(future)


async def _with_rag_operation(coro_factory):
    global _RAG_OPERATION_LOCK
    if _RAG_OPERATION_LOCK is None:
        _RAG_OPERATION_LOCK = asyncio.Lock()
    async with _RAG_OPERATION_LOCK:
        return await coro_factory()


def _ensure_rag_loop() -> asyncio.AbstractEventLoop:
    global _RAG_LOOP, _RAG_LOOP_THREAD, _RAG_LOOP_THREAD_ID
    with _RAG_LOOP_LOCK:
        if _RAG_LOOP is not None and _RAG_LOOP.is_running():
            return _RAG_LOOP

        loop = asyncio.new_event_loop()
        ready = threading.Event()

        def run_loop() -> None:
            global _RAG_LOOP_THREAD_ID
            asyncio.set_event_loop(loop)
            _RAG_LOOP_THREAD_ID = threading.get_ident()
            ready.set()
            loop.run_forever()

        thread = threading.Thread(target=run_loop, name="raganything-loop", daemon=True)
        thread.start()
        ready.wait(timeout=10)
        _RAG_LOOP = loop
        _RAG_LOOP_THREAD = thread
        return loop


async def _get_raganything() -> Any:
    _ensure_backend_venv_bin_on_path()
    _ensure_raganything_source_on_path()
    if not settings.raganything_enabled:
        raise HTTPException(
            status_code=503,
            detail="RAGAnything is disabled. Set RAGANYTHING_ENABLED=true in backend .env.",
        )
    available, reason = _check_available()
    if not available:
        raise HTTPException(status_code=503, detail=reason)
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=503,
            detail="RAGAnything requires OPENAI_API_KEY for LLM and embedding calls.",
        )

    global _RAG_INSTANCE
    with _RAG_LOCK:
        if _RAG_INSTANCE is not None:
            return _RAG_INSTANCE

        from lightrag.llm.openai import openai_complete_if_cache
        from lightrag.utils import EmbeddingFunc
        from raganything import RAGAnything, RAGAnythingConfig

        working_dir = Path(settings.raganything_working_dir)
        working_dir.mkdir(parents=True, exist_ok=True)
        Path(settings.raganything_output_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.raganything_document_dir).mkdir(parents=True, exist_ok=True)

        def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            return openai_complete_if_cache(
                settings.raganything_llm_model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                **kwargs,
            )

        def vision_model_func(
            prompt,
            system_prompt=None,
            history_messages=[],
            image_data=None,
            messages=None,
            **kwargs,
        ):
            if messages:
                return openai_complete_if_cache(
                    settings.raganything_vision_model,
                    "",
                    messages=messages,
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                    **kwargs,
                )
            if image_data:
                return openai_complete_if_cache(
                    settings.raganything_vision_model,
                    "",
                    messages=[
                        {"role": "system", "content": system_prompt} if system_prompt else None,
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}",
                                    },
                                },
                            ],
                        },
                    ],
                    api_key=settings.openai_api_key,
                    base_url=settings.openai_base_url,
                    **kwargs,
                )
            return llm_model_func(prompt, system_prompt, history_messages, **kwargs)

        embedding_func = EmbeddingFunc(
            embedding_dim=_raganything_embedding_dim(),
            max_token_size=settings.raganything_max_token_size,
            func=_geo_embedding_for_lightrag,
        )
        config = _make_raganything_config(
            RAGAnythingConfig,
            working_dir=str(working_dir),
            output_dir=settings.raganything_output_dir,
        )
        _RAG_INSTANCE = RAGAnything(
            config=config,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            embedding_func=embedding_func,
            lightrag_kwargs={
                "tokenizer": _local_lightrag_tokenizer(),
            },
        )
        return _RAG_INSTANCE


def _raganything_embedding_dim() -> int:
    if settings.geo_rag_embedding_dim:
        return settings.geo_rag_embedding_dim
    return settings.raganything_embedding_dim


async def _geo_embedding_for_lightrag(texts: list[str]):
    result = await asyncio.to_thread(embed_texts, list(texts))
    try:
        import numpy as np

        return np.array(result.vectors, dtype=np.float32)
    except Exception:
        return result.vectors


async def _ensure_raganything_query_ready(rag: Any) -> None:
    if getattr(rag, "lightrag", None) is not None:
        return
    initializer = getattr(rag, "_ensure_lightrag_initialized", None)
    if initializer is None:
        return
    result = await initializer()
    if isinstance(result, dict) and not result.get("success", False):
        raise HTTPException(
            status_code=503,
            detail=result.get("error") or "Failed to initialize RAGAnything/LightRAG.",
        )


async def _raganything_has_indexed_documents(rag: Any) -> bool:
    return await _raganything_indexed_document_count(rag) > 0


async def _raganything_indexed_document_count(rag: Any) -> int:
    lightrag = getattr(rag, "lightrag", None)
    doc_status = getattr(lightrag, "doc_status", None)
    if doc_status is None:
        return 0
    try:
        counts = await doc_status.get_all_status_counts()
        processed = int(counts.get("processed") or 0)
        if processed > 0:
            return processed
        return int(counts.get("all") or 0)
    except Exception:
        pass
    try:
        _, total_count = await doc_status.get_docs_paginated(page=1, page_size=1)
        return int(total_count or 0)
    except Exception:
        return 0


class _CharacterTokenizerBackend:
    def encode(self, content: str) -> list[int]:
        return [ord(char) for char in str(content or "")]

    def decode(self, tokens: list[int]) -> str:
        chars: list[str] = []
        for token in tokens:
            try:
                value = int(token)
            except (TypeError, ValueError):
                continue
            if 0 <= value <= 0x10FFFF:
                chars.append(chr(value))
        return "".join(chars)


def _local_lightrag_tokenizer() -> Any:
    from lightrag.utils import Tokenizer

    return Tokenizer(model_name="cdut-local-character-tokenizer", tokenizer=_CharacterTokenizerBackend())


def _check_available() -> tuple[bool, str]:
    status = _runtime_dependency_status()
    return bool(status["available"]), str(status["reason"])


def _runtime_dependency_status() -> dict[str, Any]:
    _ensure_raganything_source_on_path()
    raganything_spec = importlib.util.find_spec("raganything")
    lightrag_spec = importlib.util.find_spec("lightrag")
    required = {
        "raganything": raganything_spec is not None,
        "lightrag": lightrag_spec is not None,
    }
    if settings.raganything_parser.strip().lower() == "mineru":
        # RAGAnything calls the MinerU CLI; depending on version, Python imports may expose
        # either mineru or magic_pdf. The command check keeps the status practical for teammates.
        required["mineru"] = _command_exists("mineru") or importlib.util.find_spec("mineru") is not None or importlib.util.find_spec("magic_pdf") is not None
    missing = [name for name, installed in required.items() if not installed]
    available = not missing
    if available:
        reason = "RAGAnything, LightRAG, and parser dependencies are installed."
    else:
        reason = "Missing RAGAnything runtime dependency: " + ", ".join(missing) + "."
    return {
        "available": available,
        "reason": reason,
        "required": required,
        "missing": missing,
        "parser": settings.raganything_parser,
        "raganythingOrigin": str(getattr(raganything_spec, "origin", "") or ""),
        "lightragOrigin": str(getattr(lightrag_spec, "origin", "") or ""),
        "version": _installed_raganything_version(),
    }


def _source_snapshot_status() -> dict[str, Any]:
    upstream_root = _selected_raganything_source_root()
    upstream = _source_tree_status(
        upstream_root,
        required_files=RAGANYTHING_UPSTREAM_REQUIRED_FILES,
        note=(
            "Primary local upstream source. Runtime prefers this tree when present, "
            "falling back to the pip-installed package if it is missing."
        ),
    )
    return {
        "path": upstream["path"],
        "exists": upstream["exists"],
        "complete": upstream["complete"],
        "version": upstream["version"],
        "sourceMode": "local-upstream" if upstream["complete"] else "pip-fallback",
        "runtimeImportOrigin": _runtime_dependency_status().get("raganythingOrigin", ""),
        "upstreamSource": upstream,
    }


def _source_tree_status(
    root: Path,
    *,
    required_files: list[str],
    note: str,
) -> dict[str, Any]:
    missing = [
        relative
        for relative in required_files
        if not (root / relative).is_file()
    ]
    return {
        "path": str(root),
        "exists": root.is_dir(),
        "complete": root.is_dir() and not missing,
        "version": _read_raganything_version(root),
        "requiredFiles": required_files,
        "missingFiles": missing,
        "note": note,
    }


def _read_raganything_version(root: Path) -> str:
    init_file = root / "raganything" / "__init__.py"
    if not init_file.is_file():
        return ""
    try:
        for line in init_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("__version__"):
                return line.split("=", 1)[-1].strip().strip("\"'")
    except OSError:
        return ""
    return ""


def _installed_raganything_version() -> str:
    try:
        import raganything

        return str(getattr(raganything, "__version__", ""))
    except Exception:
        return ""


def _selected_raganything_source_root() -> Path:
    configured = str(settings.raganything_source_dir or "").strip()
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute():
            candidate = PROJECT_ROOT / candidate
        return candidate.expanduser().resolve(strict=False)
    return RAGANYTHING_UPSTREAM_ROOT


def _ensure_raganything_source_on_path() -> None:
    source_root = _selected_raganything_source_root()
    if not source_root.is_dir() or not (source_root / "raganything" / "__init__.py").is_file():
        return
    source_text = str(source_root)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)


def _make_raganything_config(config_cls: Any, *, working_dir: str, output_dir: str) -> Any:
    supported_fields = {field.name for field in fields(config_cls)}
    config_kwargs: dict[str, Any] = {
        "working_dir": working_dir,
        "parser": settings.raganything_parser,
        "parse_method": settings.raganything_parse_method,
        "enable_image_processing": settings.raganything_enable_image_processing,
        "enable_table_processing": settings.raganything_enable_table_processing,
        "enable_equation_processing": settings.raganything_enable_equation_processing,
        "max_concurrent_files": settings.raganything_max_concurrent_files,
    }
    if "parser_output_dir" in supported_fields:
        config_kwargs["parser_output_dir"] = output_dir
    return config_cls(
        **{
            key: value
            for key, value in config_kwargs.items()
            if key in supported_fields
        }
    )


def _command_exists(command: str) -> bool:
    import shutil

    local_command = Path(sys.executable).parent / command
    if local_command.is_file():
        return True
    return shutil.which(command) is not None


def _ensure_backend_venv_bin_on_path() -> None:
    bin_dir = str(Path(sys.executable).parent)
    current = os.environ.get("PATH", "")
    paths = current.split(os.pathsep) if current else []
    if bin_dir and bin_dir not in paths:
        os.environ["PATH"] = os.pathsep.join([bin_dir, *paths])


def _resolve_document_path(file_path: str) -> Path:
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = Path(settings.raganything_document_dir).resolve() / candidate
    resolved = candidate.resolve()

    allowed_roots = _allowed_document_roots()
    if not any(_is_path_inside(resolved, root) for root in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail=(
                "Document must be inside one of the allowed RAG document roots: "
                + ", ".join(str(root) for root in allowed_roots)
            ),
        )
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail=f"Document not found: {resolved}")
    return resolved


def _allowed_document_roots() -> list[Path]:
    roots = [
        Path(settings.raganything_document_dir),
        Path(settings.geo_rag_storage_root),
        Path(settings.geo_rag_upload_stage_root),
    ]
    resolved_roots: list[Path] = []
    for root in roots:
        try:
            resolved = root.expanduser().resolve(strict=False)
        except Exception:
            continue
        if resolved not in resolved_roots:
            resolved_roots.append(resolved)
    return resolved_roots


def _is_path_inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _load_latest_content_list(target: Path, output_dir: Path) -> list[dict[str, Any]]:
    stem = target.stem
    candidates: list[Path] = []
    direct = output_dir / f"{stem}_content_list.json"
    if direct.is_file():
        candidates.append(direct)
    if output_dir.exists():
        candidates.extend(output_dir.rglob(f"{stem}_content_list.json"))
    unique_candidates = sorted(
        {candidate.resolve(strict=False) for candidate in candidates if candidate.is_file()},
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not unique_candidates:
        return []
    try:
        data = json.loads(unique_candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _content_list_stats(content_blocks: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    pages: set[int] = set()
    samples: list[dict[str, Any]] = []
    ocr_blocks = 0
    for block in content_blocks:
        block_type = str(block.get("type") or block.get("content_type") or "unknown")
        type_counts[block_type] = type_counts.get(block_type, 0) + 1
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        source = str(metadata.get("source") or "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1
        if metadata.get("ocr"):
            ocr_blocks += 1
        page = block.get("page_idx", block.get("page"))
        if isinstance(page, int):
            pages.add(page + 1 if page >= 0 else page)
        if len(samples) < 8:
            text = str(block.get("text") or block.get("caption") or block.get("html") or "").strip()
            if text:
                samples.append(
                    {
                        "type": block_type,
                        "page": page + 1 if isinstance(page, int) and page >= 0 else page,
                        "text": text[:600],
                    }
                )
    multimodal = sum(count for key, count in type_counts.items() if key != "text")
    return {
        "blocks": len(content_blocks),
        "pages": len(pages),
        "typeCounts": type_counts,
        "sourceCounts": source_counts,
        "ocrBlocks": ocr_blocks,
        "multimodalBlocks": multimodal,
        "sampleBlocks": samples,
    }


def _run_async_from_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Cannot run sync RAGAnything wrapper while an event loop is already running.")


def _exception_detail(exc: Exception) -> str:
    detail = getattr(exc, "detail", "")
    if detail:
        return str(detail)
    return str(exc)


def _marker_path(doc_id: str) -> Path:
    return Path(settings.raganything_working_dir) / ".ingested" / f"{doc_id}.txt"


def _safe_id(value: Any) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value))


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split()).strip()
