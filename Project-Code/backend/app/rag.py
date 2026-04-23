"""
Lightweight RAG helpers built on top of the existing event and literature flow.

This module keeps the current architecture intact:
- reuse earthquake event payloads from the database
- reuse literature abstracts already fetched by literature.py
- add local retrieval and answer composition as a separate service layer

It is intentionally dependency-light so the project can adopt a stronger
embedding/vector backend later without rewriting API contracts.
"""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any

from .vector_retrieval import build_or_load_index, resolve_store_path

TOKEN_RE = re.compile(r"[\w\-]+", re.UNICODE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "with",
    "为什么",
    "什么",
    "如何",
    "哪些",
    "多少",
    "吗",
    "呢",
    "了",
    "和",
    "与",
    "及",
    "在",
    "对",
    "将",
    "把",
    "是",
    "有",
    "中",
    "里",
    "该",
    "次",
    "这次",
    "这场",
    "这个",
    "一下",
}

QUESTION_HINTS = {
    "mechanism": ("机制", "构造", "断层", "成因", "mechanism", "tectonic", "fault"),
    "sequence": ("余震", "序列", "前震", "活动性", "aftershock", "sequence", "seismicity"),
    "hazard": ("风险", "危险", "灾害", "影响", "hazard", "risk", "damage", "landslide"),
    "monitoring": ("监测", "预警", "波形", "定位", "monitoring", "warning", "waveform"),
    "literature": ("论文", "文献", "paper", "literature", "study", "studies"),
}


def answer_event_question(
    *,
    question: str,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    synthesis: dict[str, Any] | None = None,
    top_k: int = 6,
) -> dict[str, Any]:
    """
    Build a lightweight event-aware RAG answer using existing event and literature data.
    """
    clean_question = _clean_text(question)
    docs = build_event_rag_documents(
        event=event,
        cohort_events=cohort_events,
        papers=papers,
        synthesis=synthesis or {},
    )
    retrieved, retrieval_mode = retrieve_documents(
        clean_question,
        docs,
        top_k=top_k,
        store_key=str(event.get("id", "latest-event")),
    )
    answer = compose_answer(
        question=clean_question,
        event=event,
        cohort_events=cohort_events,
        papers=papers,
        retrieved_docs=retrieved,
        synthesis=synthesis or {},
    )

    return {
        "question": clean_question,
        "answer": answer,
        "retrievedContexts": retrieved,
        "contextCount": len(retrieved),
        "retrievalMode": retrieval_mode,
        "suggestedQuestions": suggest_follow_up_questions(event, papers),
    }


def prepare_event_vector_index(
    *,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    synthesis: dict[str, Any] | None = None,
    force_rebuild: bool = False,
) -> dict[str, Any]:
    docs = build_event_rag_documents(
        event=event,
        cohort_events=cohort_events,
        papers=papers,
        synthesis=synthesis or {},
    )
    _, mode = build_or_load_index(
        documents=docs,
        store_key=str(event.get("id", "latest-event")),
        force_rebuild=force_rebuild,
    )
    return {
        "eventId": str(event.get("id", "")),
        "documents": len(docs),
        "retrievalMode": mode,
        "storePath": resolve_store_path(str(event.get("id", "latest-event"))),
    }


def build_event_rag_documents(
    *,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    synthesis: dict[str, Any],
) -> list[dict[str, Any]]:
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
                "metadata": {
                    "topicCount": len(topic_signals),
                },
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
                paragraphs = section.get("paragraphs") or []
                section_text = " ".join(
                    _clean_text(paragraph)
                    for paragraph in paragraphs
                    if _clean_text(paragraph)
                )
                if not section_text:
                    continue
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
        if not content:
            continue
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


def retrieve_documents(
    question: str,
    docs: list[dict[str, Any]],
    top_k: int = 6,
    store_key: str = "default",
) -> tuple[list[dict[str, Any]], str]:
    tokens = _tokenize(question)
    if not docs:
        return [], "no-documents"

    vector_index, provider_mode = build_or_load_index(documents=docs, store_key=store_key)
    vector_hits = {item["id"]: item for item in vector_index.search(question, top_k=max(top_k * 2, 6))}

    scored: list[tuple[float, dict[str, Any], float]] = []
    for doc in docs:
        keyword_score = _score_document(question, tokens, doc)
        vector_score = float(vector_hits.get(doc["id"], {}).get("score", 0.0))
        score = keyword_score + vector_score * 3
        if score <= 0:
            continue
        scored.append((score, doc, vector_score))

    if not scored:
        scored = [(0.1, doc, 0.0) for doc in docs[:top_k]]

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, doc, vector_score in scored[:top_k]:
        results.append(
            {
                "id": doc["id"],
                "sourceType": doc["sourceType"],
                "title": doc["title"],
                "content": _shorten_text(doc["content"], 420),
                "score": round(score, 4),
                "metadata": {
                    **doc.get("metadata", {}),
                    "vectorScore": round(vector_score, 4),
                },
            }
        )
    return results, f"hybrid-keyword-vector:{provider_mode}"


def compose_answer(
    *,
    question: str,
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
    retrieved_docs: list[dict[str, Any]],
    synthesis: dict[str, Any],
) -> str:
    place = _clean_text(event.get("place")) or "未知区域"
    mag = _safe_float(event.get("mag"))
    depth = _safe_float(event.get("depth_km"))
    topic_signals = synthesis.get("topicSignals") if isinstance(synthesis, dict) else []
    top_signal = topic_signals[0] if isinstance(topic_signals, list) and topic_signals else None
    top_label = _clean_text(top_signal.get("label")) if isinstance(top_signal, dict) else ""

    opening = (
        f"结合当前事件参数、同时间窗地震样本和已检索到的论文摘要来看，"
        f"{place} 这次 M{mag:.1f} 地震"
        if mag is not None
        else f"结合当前事件参数、同时间窗地震样本和已检索到的论文摘要来看，{place} 这次地震"
    )

    intent = _infer_question_intent(question)
    if intent == "mechanism":
        focus = (
            f"更适合从“{top_label}”这条线去理解。"
            if top_label
            else "目前更适合先从区域构造背景和震源参数两条线去理解。"
        )
    elif intent == "sequence":
        focus = "更需要关注它是否会演化成可识别的地震序列，以及余震时空迁移特征。"
    elif intent == "hazard":
        focus = "需要同时看震级、深度、局地场地条件和后续活动变化，不能只看单个参数。"
    elif intent == "monitoring":
        focus = "最值得做的是把事件参数、后续小震活动和相关研究方法放在一起动态跟踪。"
    elif intent == "literature":
        focus = "可以直接从当前检索到的高相关论文里抽出最接近该问题的证据。"
    else:
        focus = "说明它更适合用一个事件驱动的微型综述页来回答，而不是一句标签式结论。"

    evidence_lines: list[str] = []
    for doc in retrieved_docs[:3]:
        title = _clean_text(doc.get("title"))
        source_type = _clean_text(doc.get("sourceType"))
        content = _clean_text(doc.get("content"))
        if not content:
            continue
        label = {
            "event": "事件参数",
            "cohort": "样本统计",
            "paper": "相关文献",
            "topic-signals": "主题信号",
            "summary-section": "综述片段",
            "synthesis": "综合结论",
            "cohort-examples": "对比事件",
        }.get(source_type, "检索上下文")
        evidence_lines.append(f"{label}《{title}》指出：{content}")

    papers_count = len(papers)
    cohort_count = len(cohort_events)
    trailing = (
        f"当前回答基于 {papers_count} 篇摘要级文献和 {cohort_count} 条同窗事件样本做的本地检索增强。"
        if papers_count or cohort_count
        else "当前回答主要基于已有事件参数与综述信息。"
    )

    if depth is not None:
        depth_sentence = f"震源深度约 {depth:g} km，这会直接影响对机制和风险的解释。"
    else:
        depth_sentence = "由于震源深度信息有限，相关解释需要保留不确定性。"

    answer_parts = [
        f"{opening} {focus}",
        depth_sentence,
        trailing,
    ]
    if evidence_lines:
        answer_parts.append("可直接支撑这个判断的上下文有：" + " ".join(evidence_lines))
    return " ".join(part for part in answer_parts if part)


def suggest_follow_up_questions(event: dict[str, Any], papers: list[dict[str, Any]]) -> list[str]:
    place = _clean_text(event.get("place")) or "该区域"
    suggestions = [
        f"{place} 这次地震更像构造背景驱动还是序列活动驱动？",
        f"{place} 这次事件后续最该关注哪些监测指标？",
        f"当前检索到的文献里，哪些论文最能解释 {place} 的地震机制？",
    ]
    if not papers:
        return suggestions[:2]
    return suggestions


def _score_document(question: str, tokens: list[str], doc: dict[str, Any]) -> float:
    title = _clean_text(doc.get("title"))
    content = _clean_text(doc.get("content"))
    haystack = f"{title} {content}".lower()

    score = 0.0
    token_counts = Counter(_tokenize(haystack))
    for token in tokens:
        count = token_counts.get(token, 0)
        if count <= 0:
            continue
        score += min(count, 3) * 1.2
        if token in title.lower():
            score += 1.4

    source_type = _clean_text(doc.get("sourceType"))
    if source_type == "paper":
        score += 0.2
    elif source_type == "event":
        score += 0.5
    elif source_type in {"topic-signals", "synthesis", "summary-section"}:
        score += 0.35

    intent = _infer_question_intent(question)
    if intent == "literature" and source_type == "paper":
        score += 1.8
    elif intent == "mechanism" and source_type in {"paper", "topic-signals", "summary-section"}:
        score += 1.2
    elif intent == "sequence" and source_type in {"cohort", "cohort-examples", "summary-section"}:
        score += 1.1
    elif intent == "hazard" and source_type in {"summary-section", "paper", "cohort"}:
        score += 1.0
    elif intent == "monitoring" and source_type in {"summary-section", "paper", "topic-signals"}:
        score += 1.0

    return score


def _infer_question_intent(question: str) -> str:
    lowered = question.lower()
    for intent, keywords in QUESTION_HINTS.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return intent
    return "general"


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(_clean_text(text))
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


def _shorten_text(text: str, max_length: int) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 1].rstrip()}..."


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
