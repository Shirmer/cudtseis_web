from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

import requests
from sqlalchemy.orm import Session

from .evidence_service import build_evidence_pack
from .geo_ingest_service import search_geo_knowledge
from .models import GeoRagRun
from .settings import settings


def answer_paper_question(
    db: Session,
    *,
    question: str,
    paper_id: str | None = None,
    top_k: int = 6,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    search_filters = dict(filters or {})
    if paper_id:
        search_filters["paper_id"] = paper_id
    search_result = search_geo_knowledge(db, query=question, top_k=top_k, filters=search_filters)
    evidence_pack = build_evidence_pack(
        question=question,
        results=search_result["results"],
        purpose="paper-question-answering",
    )
    answer, generation_mode = _answer_with_evidence(question=question, evidence_pack=evidence_pack)
    response = _build_response(
        question=question,
        answer=answer,
        evidence_pack=evidence_pack,
        search_result=search_result,
        mode="paper-geo-rag",
        generation_mode=generation_mode,
    )
    _log_run(db, response)
    return response


def answer_event_geo_analysis(
    db: Session,
    *,
    event: dict[str, Any],
    question: str,
    top_k: int = 8,
) -> dict[str, Any]:
    event_context = _event_context(event)
    combined_question = f"{question}\n\nEarthquake event context:\n{event_context}"
    search_result = search_geo_knowledge(db, query=combined_question, top_k=top_k, filters={})
    evidence_pack = build_evidence_pack(
        question=question,
        results=search_result["results"],
        purpose="earthquake-event-geological-analysis",
        event=event,
    )
    answer, generation_mode = _answer_with_evidence(
        question=question,
        evidence_pack=evidence_pack,
        event_context=event_context,
    )
    response = _build_response(
        question=question,
        answer=answer,
        evidence_pack=evidence_pack,
        search_result=search_result,
        mode="event-geo-rag",
        generation_mode=generation_mode,
        event=event,
    )
    _log_run(db, response)
    return response


def _answer_with_evidence(
    *,
    question: str,
    evidence_pack: dict[str, Any],
    event_context: str = "",
) -> tuple[str, str]:
    if settings.openai_api_key:
        try:
            return _call_chat_completion(question=question, evidence_pack=evidence_pack, event_context=event_context), "llm"
        except Exception as exc:
            return _template_answer(question, evidence_pack, event_context, warning=str(exc)), "template-fallback"
    return _template_answer(question, evidence_pack, event_context), "template"


def _call_chat_completion(*, question: str, evidence_pack: dict[str, Any], event_context: str) -> str:
    evidence_lines = []
    for evidence in evidence_pack.get("evidence", []):
        evidence_lines.append(
            f"[{evidence['id']}] {evidence['title']} p.{evidence.get('page') or '-'}: {evidence['text']}"
        )
    prompt = "\n".join(evidence_lines) or "No evidence was retrieved."
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful geology and seismology RAG analyst. "
                "Answer in Chinese. Use only the supplied evidence. "
                "Cite evidence IDs like [E1]. State uncertainty and avoid unsupported prediction."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Event context:\n{event_context or 'N/A'}\n\n"
                f"Evidence:\n{prompt}\n\n"
                "Return a concise but scientifically cautious answer."
            ),
        },
    ]
    response = requests.post(
        settings.openai_base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={"model": settings.geo_rag_chat_model, "messages": messages, "temperature": 0.2},
        timeout=90,
    )
    if not response.ok:
        detail = response.text.strip().replace("\n", " ")
        if len(detail) > 500:
            detail = detail[:500] + "..."
        raise RuntimeError(
            f"LLM API returned HTTP {response.status_code} for model "
            f"{settings.geo_rag_chat_model}: {detail or response.reason}"
        )
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _template_answer(
    question: str,
    evidence_pack: dict[str, Any],
    event_context: str,
    *,
    warning: str = "",
) -> str:
    evidence = evidence_pack.get("evidence", [])
    if not evidence:
        base = "当前知识库没有检索到足够相关的文献证据，因此不能给出可靠的专业结论。"
        if event_context:
            base += f"\n事件上下文：{event_context}"
        return base + "\n建议先导入相关地质学/地震学文献，再重新提问。"

    lines = ["基于当前已入库文献，先给出有证据支撑的初步分析："]
    for item in evidence[:4]:
        snippet = item.get("text", "").strip()
        if len(snippet) > 180:
            snippet = snippet[:180] + "..."
        lines.append(f"- [{item['id']}] {snippet}")
    lines.append(f"综合判断：这个问题需要围绕上述证据展开，当前置信度为 {evidence_pack.get('confidence', 'low')}。")
    lines.append("不确定性：若证据不是目标区域、目标断层或同类构造背景的文献，只能作为类比依据，不能直接当作结论。")
    if warning:
        lines.append(f"生成提示：LLM 调用失败，已使用本地模板回答。原因：{warning}")
    return "\n".join(lines)


def _build_response(
    *,
    question: str,
    answer: str,
    evidence_pack: dict[str, Any],
    search_result: dict[str, Any],
    mode: str,
    generation_mode: str,
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "question": question,
        "answer": answer,
        "retrievalMode": f"{search_result['backend']}+{generation_mode}",
        "mode": mode,
        "event": event,
        "evidencePack": evidence_pack,
        "retrievedContexts": [
            {
                "id": item.get("unitId", ""),
                "sourceType": "geo-literature",
                "title": item.get("title", ""),
                "content": item.get("text", ""),
                "score": item.get("score", 0.0),
                "metadata": item.get("metadata", {}),
            }
            for item in search_result.get("results", [])
        ],
        "suggestedQuestions": [
            "这些证据分别支持哪些结论？",
            "当前回答有哪些不确定性？",
            "还需要补充哪些类型的文献？",
        ],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "diagnostics": {
            "collection": search_result.get("collection", ""),
            "warning": search_result.get("warning", ""),
            "embeddingBackend": search_result.get("embeddingBackend", ""),
            "storeStats": search_result.get("storeStats", {}),
            "retrieval": search_result.get("diagnostics", {}),
        },
    }


def _event_context(event: dict[str, Any]) -> str:
    return (
        f"id={event.get('id')}; place={event.get('place')}; magnitude={event.get('mag')}; "
        f"depth_km={event.get('depth_km')}; lon={event.get('lon')}; lat={event.get('lat')}; "
        f"time={event.get('time')}"
    )


def _log_run(db: Session, response: dict[str, Any]) -> None:
    try:
        run = GeoRagRun(
            id=str(uuid.uuid4()),
            mode=response["mode"],
            question=response["question"],
            answer=response["answer"],
            retrieval_mode=response["retrievalMode"],
            evidence_pack_json=response["evidencePack"],
            metadata_json=response.get("diagnostics", {}),
        )
        db.add(run)
        db.commit()
    except Exception:
        db.rollback()
