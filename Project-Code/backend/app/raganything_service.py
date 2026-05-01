from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .rag import build_event_rag_documents
from .settings import settings


_RAG_INSTANCE: Any | None = None
_RAG_LOCK = asyncio.Lock()


def get_raganything_status() -> dict[str, Any]:
    available, reason = _check_available()
    return {
        "enabled": settings.raganything_enabled,
        "available": available,
        "reason": reason,
        "workingDir": settings.raganything_working_dir,
        "outputDir": settings.raganything_output_dir,
        "documentDir": settings.raganything_document_dir,
        "parser": settings.raganything_parser,
        "parseMethod": settings.raganything_parse_method,
        "queryMode": settings.raganything_query_mode,
    }


async def ingest_event_bundle_with_raganything(
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
    rag = await _get_raganything()
    target = _resolve_document_path(file_path)
    output_dir = Path(settings.raganything_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    await rag.process_document_complete(
        file_path=str(target),
        output_dir=str(output_dir),
        parse_method=parse_method or settings.raganything_parse_method,
        parser=parser or settings.raganything_parser,
        doc_id=doc_id,
    )
    return {
        "status": "ready",
        "mode": "raganything-document-parser",
        "documents": 1,
        "storePath": settings.raganything_working_dir,
        "message": f"Document parsed and inserted: {target.name}",
    }


async def query_raganything(
    *,
    question: str,
    mode: str | None = None,
    vlm_enhanced: bool | None = None,
) -> dict[str, Any]:
    rag = await _get_raganything()
    kwargs: dict[str, Any] = {"mode": mode or settings.raganything_query_mode}
    if vlm_enhanced is not None:
        kwargs["vlm_enhanced"] = vlm_enhanced
    result = await rag.aquery(question, **kwargs)
    return {
        "question": question,
        "answer": str(result),
        "retrievalMode": f"raganything:{kwargs['mode']}",
        "mode": "raganything",
    }


async def _get_raganything() -> Any:
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
    async with _RAG_LOCK:
        if _RAG_INSTANCE is not None:
            return _RAG_INSTANCE

        from lightrag.llm.openai import openai_complete_if_cache, openai_embed
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
            embedding_dim=settings.raganything_embedding_dim,
            max_token_size=settings.raganything_max_token_size,
            func=partial(
                openai_embed.func,
                model=settings.openai_embedding_model,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            ),
        )
        config = RAGAnythingConfig(
            working_dir=str(working_dir),
            parser=settings.raganything_parser,
            parse_method=settings.raganything_parse_method,
            enable_image_processing=settings.raganything_enable_image_processing,
            enable_table_processing=settings.raganything_enable_table_processing,
            enable_equation_processing=settings.raganything_enable_equation_processing,
        )
        _RAG_INSTANCE = RAGAnything(
            config=config,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            embedding_func=embedding_func,
        )
        return _RAG_INSTANCE


def _check_available() -> tuple[bool, str]:
    try:
        import raganything  # noqa: F401
        import lightrag  # noqa: F401
    except ImportError as exc:
        return False, f"RAGAnything dependency is not installed: {exc.name}."
    return True, "RAGAnything dependency is installed."


def _resolve_document_path(file_path: str) -> Path:
    root = Path(settings.raganything_document_dir).resolve()
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if root != resolved and root not in resolved.parents:
        raise HTTPException(
            status_code=400,
            detail=f"Document must be inside RAGANYTHING_DOCUMENT_DIR: {root}",
        )
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail=f"Document not found: {resolved}")
    return resolved


def _marker_path(doc_id: str) -> Path:
    return Path(settings.raganything_working_dir) / ".ingested" / f"{doc_id}.txt"


def _safe_id(value: Any) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in str(value))
