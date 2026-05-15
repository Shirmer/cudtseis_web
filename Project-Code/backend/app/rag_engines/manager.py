from __future__ import annotations

from typing import Any

from ..settings import settings


SUPPORTED_ENGINES = {"raganything"}


def normalized_geo_rag_engine() -> str:
    return "raganything"


def get_geo_rag_engine_status() -> dict[str, Any]:
    from ..raganything_service import get_raganything_status

    engine = normalized_geo_rag_engine()
    raganything_status = get_raganything_status()
    return {
        "selected": engine,
        "supported": sorted(SUPPORTED_ENGINES),
        "raganything": raganything_status,
    }


def index_document_with_primary_engine(
    *,
    file_path: str,
    document_id: str,
    parser: str,
) -> dict[str, Any]:
    from ..raganything_service import ingest_document_with_raganything_sync

    return ingest_document_with_raganything_sync(
        file_path=file_path,
        doc_id=document_id,
        parser=None if parser == "plain-text" else settings.raganything_parser,
        parse_method=settings.raganything_parse_method,
        fail_on_error=True,
    )


def answer_with_raganything_if_configured(
    *,
    question: str,
    evidence_pack: dict[str, Any],
    knowledge_cards: dict[str, Any],
    event_context: str = "",
) -> dict[str, Any] | None:
    engine = normalized_geo_rag_engine()
    if engine != "raganything":
        return None

    from ..raganything_service import query_raganything_sync

    query = _raganything_question(
        question=question,
        evidence_pack=evidence_pack,
        knowledge_cards=knowledge_cards,
        event_context=event_context,
    )
    result = query_raganything_sync(
        question=query,
        mode=settings.raganything_query_mode,
        fail_on_error=True,
    )
    if result.get("status") != "ready":
        return None
    return {
        "answer": result.get("answer", ""),
        "mode": f"raganything:{result.get('queryMode', settings.raganything_query_mode)}",
        "diagnostics": result,
    }


def _raganything_question(
    *,
    question: str,
    evidence_pack: dict[str, Any],
    knowledge_cards: dict[str, Any],
    event_context: str,
) -> str:
    evidence_lines: list[str] = []
    for evidence in evidence_pack.get("evidence", [])[:8]:
        evidence_lines.append(
            f"[{evidence.get('id')}] {evidence.get('title')} p.{evidence.get('page') or '-'}: "
            f"{str(evidence.get('text') or '')[:900]}"
        )

    question_card = knowledge_cards.get("question", {})
    limitations = question_card.get("limitations") or evidence_pack.get("limitations") or []
    return (
        "请作为谨慎的科研 RAG 分析器回答问题。优先使用 RAGAnything/LightRAG 知识库中的关系检索结果，"
        "同时和下方本系统检索出的证据交叉核对。不要编造未被文献支持的结论。\n\n"
        f"问题：{question}\n\n"
        f"事件上下文：{event_context or 'N/A'}\n\n"
        "本系统证据包：\n"
        + ("\n".join(evidence_lines) if evidence_lines else "未检索到本系统证据。")
        + "\n\n"
        f"已知限制：{'; '.join(str(item) for item in limitations[:5]) or 'N/A'}\n\n"
        "请用中文回答，尽量给出证据依据、逻辑链条和不确定性。"
    )
