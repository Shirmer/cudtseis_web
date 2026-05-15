from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import uuid

import requests
from sqlalchemy.orm import Session

from .evidence_service import build_evidence_pack, build_question_knowledge_card
from .geo_ingest_service import search_geo_knowledge
from .models import DocumentKnowledgeCard, GeoRagRun
from .rag_engines import answer_with_raganything_if_configured, get_geo_rag_engine_status
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
    knowledge_cards = _build_knowledge_cards(db, question=question, evidence_pack=evidence_pack)
    answer, generation_mode = _answer_with_evidence(
        question=question,
        evidence_pack=evidence_pack,
        knowledge_cards=knowledge_cards,
    )
    response = _build_response(
        question=question,
        answer=answer,
        evidence_pack=evidence_pack,
        knowledge_cards=knowledge_cards,
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
    knowledge_cards = _build_knowledge_cards(db, question=question, evidence_pack=evidence_pack, event=event)
    answer, generation_mode = _answer_with_evidence(
        question=question,
        evidence_pack=evidence_pack,
        knowledge_cards=knowledge_cards,
        event_context=event_context,
    )
    response = _build_response(
        question=question,
        answer=answer,
        evidence_pack=evidence_pack,
        knowledge_cards=knowledge_cards,
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
    knowledge_cards: dict[str, Any],
    event_context: str = "",
) -> tuple[str, str]:
    raganything_answer = answer_with_raganything_if_configured(
        question=question,
        evidence_pack=evidence_pack,
        knowledge_cards=knowledge_cards,
        event_context=event_context,
    )
    if raganything_answer and raganything_answer.get("answer"):
        return raganything_answer["answer"], raganything_answer["mode"]

    if settings.openai_api_key:
        try:
            return _call_chat_completion(
                question=question,
                evidence_pack=evidence_pack,
                knowledge_cards=knowledge_cards,
                event_context=event_context,
            ), "llm"
        except Exception as exc:
            return _template_answer(question, evidence_pack, knowledge_cards, event_context, warning=str(exc)), "template-fallback"
    return _template_answer(question, evidence_pack, knowledge_cards, event_context), "template"


def _call_chat_completion(
    *,
    question: str,
    evidence_pack: dict[str, Any],
    knowledge_cards: dict[str, Any],
    event_context: str,
) -> str:
    evidence_lines = []
    for evidence in evidence_pack.get("evidence", []):
        evidence_lines.append(
            f"[{evidence['id']}] {evidence['title']} p.{evidence.get('page') or '-'}: {evidence['text']}"
        )
    prompt = "\n".join(evidence_lines) or "No evidence was retrieved."
    question_card = knowledge_cards.get("question", {})
    card_prompt = _compact_card_for_prompt(question_card)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a careful geology and seismology RAG analyst. "
                "Answer in Chinese. Use only the supplied evidence. "
                "Cite evidence IDs like [E1]. Use the structured knowledge card to organize reasoning. "
                "State uncertainty and avoid unsupported prediction."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Event context:\n{event_context or 'N/A'}\n\n"
                f"Structured question knowledge card:\n{card_prompt}\n\n"
                f"Evidence:\n{prompt}\n\n"
                "Return a concise but scientifically cautious answer with evidence IDs and limitations."
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
    knowledge_cards: dict[str, Any],
    event_context: str,
    *,
    warning: str = "",
) -> str:
    evidence = evidence_pack.get("evidence", [])
    question_card = knowledge_cards.get("question", {})
    if not evidence:
        base = "当前知识库没有检索到足够相关的文献证据，因此不能给出可靠的专业结论。"
        if event_context:
            base += f"\n事件上下文：{event_context}"
        return base + "\n建议先导入相关地质学/地震学文献，再重新提问。"

    lines = ["基于当前已入库文献，先给出有证据支撑的初步分析："]
    for item in question_card.get("supportingEvidence", [])[:4]:
        snippet = item.get("claimText", "").strip()
        lines.append(f"- [{item.get('evidenceId')}] {snippet}")
    lines.append(f"综合判断：这个问题需要围绕上述证据展开，当前置信度为 {evidence_pack.get('confidence', 'low')}。")
    limitations = question_card.get("limitations") or [
        "若证据不是目标区域、目标断层或同类构造背景的文献，只能作为类比依据，不能直接当作结论。"
    ]
    lines.append("不确定性：" + "；".join(str(item) for item in limitations[:3]))
    if warning:
        lines.append(f"生成提示：LLM 调用失败，已使用本地模板回答。原因：{warning}")
    return "\n".join(lines)


def _build_response(
    *,
    question: str,
    answer: str,
    evidence_pack: dict[str, Any],
    knowledge_cards: dict[str, Any],
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
        "knowledgeCards": knowledge_cards,
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
            "ragEngine": get_geo_rag_engine_status(),
        },
    }


def _event_context(event: dict[str, Any]) -> str:
    return (
        f"id={event.get('id')}; place={event.get('place')}; magnitude={event.get('mag')}; "
        f"depth_km={event.get('depth_km')}; lon={event.get('lon')}; lat={event.get('lat')}; "
        f"time={event.get('time')}"
    )


def _build_knowledge_cards(
    db: Session,
    *,
    question: str,
    evidence_pack: dict[str, Any],
    event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    question_card = build_question_knowledge_card(question=question, evidence_pack=evidence_pack, event=event)
    document_ids = [
        str(item.get("documentId") or "")
        for item in evidence_pack.get("evidence", [])
        if str(item.get("documentId") or "")
    ]
    unique_ids = list(dict.fromkeys(document_ids))
    document_cards = []
    if unique_ids:
        rows = (
            db.query(DocumentKnowledgeCard)
            .filter(DocumentKnowledgeCard.document_id.in_(unique_ids))
            .all()
        )
        by_document = {row.document_id: row for row in rows}
        for document_id in unique_ids:
            row = by_document.get(document_id)
            if row is None:
                continue
            document_cards.append(
                {
                    "documentId": row.document_id,
                    "paperId": row.paper_id,
                    "title": row.title,
                    "schemaVersion": row.schema_version,
                    "card": row.card_json,
                }
            )
    return {
        "question": question_card,
        "documents": document_cards,
    }


def _compact_card_for_prompt(card: dict[str, Any]) -> str:
    if not card:
        return "N/A"
    lines = [
        f"confidence: {card.get('confidence', 'low')}",
        f"evidenceCount: {card.get('evidenceCount', 0)}",
        f"documentCount: {card.get('documentCount', 0)}",
    ]
    limitations = card.get("limitations") or []
    if limitations:
        lines.append("limitations:")
        for item in limitations[:5]:
            lines.append(f"- {item}")
    support = card.get("supportingEvidence") or []
    if support:
        lines.append("supportingEvidence:")
        for item in support[:8]:
            lines.append(
                f"- {item.get('evidenceId')}: p.{item.get('page') or '-'} "
                f"{item.get('sectionRole', 'unknown')} {item.get('claimText', '')}"
            )
    return "\n".join(lines)


def _log_run(db: Session, response: dict[str, Any]) -> None:
    try:
        run = GeoRagRun(
            id=str(uuid.uuid4()),
            mode=response["mode"],
            question=response["question"],
            answer=response["answer"],
            retrieval_mode=response["retrievalMode"],
            evidence_pack_json=response["evidencePack"],
            metadata_json={
                "diagnostics": response.get("diagnostics", {}),
                "knowledgeCards": response.get("knowledgeCards", {}),
            },
        )
        db.add(run)
        db.commit()
    except Exception:
        db.rollback()
