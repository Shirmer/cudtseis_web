from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .cache_utils import TTLCache
from .event_service import get_event_payload, query_events_payload
from .literature import search_related_papers, synthesize_event_and_literature
from .settings import settings


RESEARCH_CACHE = TTLCache[dict[str, Any]](ttl_seconds=1800)


def build_event_research_bundle(
    db: Session,
    *,
    event_id: str,
    hours: int,
    minMag: float,
    cohortLimit: int,
    paperLimit: int,
    yearMin: int,
) -> dict[str, Any]:
    cache_key = "|".join(
        [
            event_id,
            str(hours),
            str(minMag),
            str(cohortLimit),
            str(paperLimit),
            str(yearMin),
        ]
    )
    cached = RESEARCH_CACHE.get(cache_key)
    if cached is not None:
        return cached

    event = get_event_payload(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Earthquake event not found")

    cohort_events = query_events_payload(
        db,
        minMag=minMag,
        hours=hours,
        limit=cohortLimit,
    )
    literature = search_related_papers(
        event,
        limit=paperLimit,
        year_min=yearMin,
        semantic_scholar_api_key=settings.semantic_scholar_api_key,
        openalex_email=settings.openalex_email,
    )
    synthesis = synthesize_event_and_literature(
        event=event,
        cohort_events=cohort_events,
        papers=literature["papers"],
    )
    workflow = build_research_workflow(event=event, literature=literature, synthesis=synthesis)
    payload = {
        "event": event,
        "cohort_events": cohort_events,
        "literature": literature,
        "synthesis": synthesis,
        "workflow": workflow,
    }
    RESEARCH_CACHE.put(cache_key, payload)
    return payload


def build_research_workflow(
    *,
    event: dict[str, Any],
    literature: dict[str, Any],
    synthesis: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        {
            "key": "event-context",
            "title": "事件上下文准备",
            "description": f"已加载事件 {event.get('id', '')} 及其基础参数。",
            "status": "completed",
        },
        {
            "key": "literature-search",
            "title": "题录与摘要检索",
            "description": f"已聚合 {len(literature.get('papers', []))} 篇候选论文。",
            "status": "completed",
        },
        {
            "key": "scientific-synthesis",
            "title": "科研综合研判",
            "description": f"已生成 {len(synthesis.get('topicSignals', []))} 个主题信号和综述摘要。",
            "status": "completed",
        },
    ]
