from __future__ import annotations

from typing import Any

from .literature_search import _build_cohort_stats, _build_summary, _extract_topic_signals


def synthesize_event_and_literature(
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    topic_signals = _extract_topic_signals(papers)
    cohort_stats = _build_cohort_stats(cohort_events)
    summary = _build_summary(event, cohort_stats, papers, topic_signals)
    return {
        "cohort": cohort_stats,
        "topicSignals": topic_signals,
        "summary": summary,
    }
