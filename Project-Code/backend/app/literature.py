"""
Lightweight literature retrieval and abstract-first synthesis helpers.

This module borrows the multi-source search idea from AutoResearchClaw,
but keeps the implementation self-contained for the CDUT seismic dashboard.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import math
import re
import threading
import time
from typing import Any

import requests


OPENALEX_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
REQUEST_TIMEOUT = 20
SEARCH_CACHE_TTL_SECONDS = 6 * 60 * 60
DISTANCE_PREFIX_RE = re.compile(r"^\s*\d+(?:\.\d+)?\s*km\s+[A-Z-]+\s+of\s+", re.I)
WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")

SEARCH_CACHE: dict[str, dict[str, Any]] = {}
SEARCH_CACHE_LOCK = threading.Lock()


TOPIC_RULES = [
    {
        "key": "tectonics",
        "label": "构造背景与震源机制",
        "description": "文献更关注断层几何、震源机制、应力传递和板块构造控制。",
        "keywords": (
            "tectonic",
            "seismotectonic",
            "fault",
            "rupture",
            "stress",
            "plate boundary",
            "focal mechanism",
            "slip",
            "subduction",
        ),
    },
    {
        "key": "seismicity",
        "label": "地震序列与活动性分析",
        "description": "文献集中讨论余震、前震、地震序列演化和区域活动性变化。",
        "keywords": (
            "aftershock",
            "foreshock",
            "sequence",
            "swarm",
            "seismicity",
            "catalog",
            "b-value",
            "stress drop",
        ),
    },
    {
        "key": "hazard",
        "label": "危险性与地表影响",
        "description": "文献强调地震危险性、强震动、海啸、滑坡或液化等影响评估。",
        "keywords": (
            "hazard",
            "ground motion",
            "intensity",
            "damage",
            "landslide",
            "liquefaction",
            "tsunami",
            "risk",
            "loss",
        ),
    },
    {
        "key": "monitoring",
        "label": "监测方法与反演技术",
        "description": "文献偏向波形反演、层析成像、地球物理监测和快速识别方法。",
        "keywords": (
            "waveform",
            "inversion",
            "tomography",
            "geodetic",
            "insar",
            "gps",
            "detection",
            "classification",
            "early warning",
            "machine learning",
        ),
    },
]


def search_related_papers(
    event: dict[str, Any],
    *,
    limit: int = 12,
    year_min: int = 2015,
    semantic_scholar_api_key: str = "",
    openalex_email: str = "",
) -> dict[str, Any]:
    """
    Search related literature for a selected earthquake event.

    The strategy is abstract-first: query OpenAlex first, then use
    Semantic Scholar only as a supplement when results are sparse.
    """
    queries = build_event_queries(event)
    cache_key = (
        f"{event.get('id', '')}|{event.get('updated', event.get('time', ''))}|"
        f"{limit}|{year_min}|{'1' if semantic_scholar_api_key else '0'}"
    )

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    papers: list[dict[str, Any]] = []
    source_breakdown: Counter[str] = Counter()
    query_notes: list[str] = []

    # OpenAlex is generous and often returns abstracts.
    for query in queries:
        openalex_results = _search_openalex(query, limit=6, year_min=year_min, email=openalex_email)
        if openalex_results:
            papers.extend(openalex_results)
            source_breakdown["OpenAlex"] += len(openalex_results)
        else:
            query_notes.append(f"OpenAlex 未从查询 “{query}” 返回稳定结果。")

        if len(_deduplicate_papers(papers)) >= limit:
            break

    deduped = _deduplicate_papers(papers)

    # Use Semantic Scholar only when we still need more coverage.
    if len(deduped) < limit:
        for query in queries:
            s2_results = _search_semantic_scholar(
                query,
                limit=4,
                year_min=year_min,
                api_key=semantic_scholar_api_key,
            )
            if s2_results:
                papers.extend(s2_results)
                source_breakdown["Semantic Scholar"] += len(s2_results)
            else:
                query_notes.append(f"Semantic Scholar 未从查询 “{query}” 返回稳定结果。")

            deduped = _deduplicate_papers(papers)
            if len(deduped) >= limit:
                break

    deduped.sort(
        key=lambda paper: (
            int(paper.get("citationCount") or 0),
            int(paper.get("year") or 0),
            len(paper.get("abstract") or ""),
        ),
        reverse=True,
    )

    final_papers = [_decorate_paper(paper) for paper in deduped[:limit]]
    response = {
        "mode": "abstract-first",
        "queryPlan": {
            "queries": queries,
            "yearMin": year_min,
            "sources": ["OpenAlex", "Semantic Scholar"],
            "strategy": "优先检索题录与摘要，不批量下载 PDF。",
        },
        "sourceBreakdown": dict(source_breakdown),
        "papers": final_papers,
        "notes": _compact_notes(query_notes),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    _cache_put(cache_key, response)
    return response


def synthesize_event_and_literature(
    event: dict[str, Any],
    cohort_events: list[dict[str, Any]],
    papers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a fast scientific synthesis from event metadata and abstracts."""
    topic_signals = _extract_topic_signals(papers)
    cohort_stats = _build_cohort_stats(cohort_events)
    summary = _build_summary(event, cohort_stats, papers, topic_signals)

    return {
        "cohort": cohort_stats,
        "topicSignals": topic_signals,
        "summary": summary,
    }


def build_event_queries(event: dict[str, Any]) -> list[str]:
    """Create short, diversified search queries for a selected earthquake."""
    place = str(event.get("place") or "").strip()
    normalized_place = _normalize_place(place)
    region = _extract_region(normalized_place)
    depth = _as_float(event.get("depth_km"))
    event_type = str(event.get("type") or "earthquake").replace("_", " ").strip() or "earthquake"

    context_terms = ["earthquake", "seismicity", "tectonics"]
    if depth is not None:
        if depth < 70:
            context_terms.extend(["fault", "shallow crust"])
        elif depth < 300:
            context_terms.extend(["intermediate depth", "subduction"])
        else:
            context_terms.extend(["deep focus", "mantle transition"])

    if _looks_offshore(place):
        context_terms.extend(["offshore", "hazard"])

    seeds = [
        f"{region} earthquake tectonics",
        f"{region} seismicity fault",
        f"{region} {event_type} geophysics",
        f"{normalized_place} earthquake",
        " ".join(dict.fromkeys(context_terms)),
    ]

    seen: set[str] = set()
    queries: list[str] = []
    for raw_query in seeds:
        query = _shorten_query(raw_query)
        if not query:
            continue
        lowered = query.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        queries.append(query)
        if len(queries) >= 4:
            break

    return queries or ["earthquake tectonics seismicity"]


def _search_openalex(query: str, *, limit: int, year_min: int, email: str) -> list[dict[str, Any]]:
    params: dict[str, str] = {
        "search": query,
        "per_page": str(min(limit, 25)),
        "select": (
            "id,title,authorships,publication_year,primary_location,"
            "cited_by_count,doi,ids,abstract_inverted_index"
        ),
    }
    if year_min > 0:
        params["filter"] = f"from_publication_date:{year_min}-01-01"
    if email:
        params["mailto"] = email

    data = _request_json(OPENALEX_URL, params=params)
    results = data.get("results", []) if isinstance(data, dict) else []
    if not isinstance(results, list):
        return []

    papers: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        if not title:
            continue
        doi = _clean_text(item.get("doi")).replace("https://doi.org/", "").replace("http://doi.org/", "")
        ids = item.get("ids") or {}
        if not isinstance(ids, dict):
            ids = {}
        papers.append(
            {
                "paperId": _clean_text(ids.get("openalex") or item.get("id")),
                "title": title,
                "authors": _openalex_authors(item.get("authorships")),
                "year": int(item.get("publication_year") or 0),
                "abstract": _reconstruct_openalex_abstract(item.get("abstract_inverted_index")),
                "venue": _openalex_venue(item.get("primary_location")),
                "citationCount": int(item.get("cited_by_count") or 0),
                "doi": doi,
                "url": _paper_url(doi, ids, item.get("id")),
                "source": "OpenAlex",
            }
        )
    return papers


def _search_semantic_scholar(
    query: str,
    *,
    limit: int,
    year_min: int,
    api_key: str,
) -> list[dict[str, Any]]:
    params: dict[str, str] = {
        "query": query,
        "limit": str(min(limit, 20)),
        "fields": "paperId,title,abstract,year,venue,citationCount,authors,externalIds,url",
    }
    if year_min > 0:
        params["year"] = f"{year_min}-"

    headers = {"Accept": "application/json"}
    if api_key:
        headers["x-api-key"] = api_key

    data = _request_json(SEMANTIC_SCHOLAR_URL, params=params, headers=headers)
    results = data.get("data", []) if isinstance(data, dict) else []
    if not isinstance(results, list):
        return []

    papers: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        if not title:
            continue
        external_ids = item.get("externalIds") or {}
        if not isinstance(external_ids, dict):
            external_ids = {}
        doi = _clean_text(external_ids.get("DOI"))
        papers.append(
            {
                "paperId": _clean_text(item.get("paperId")),
                "title": title,
                "authors": _s2_authors(item.get("authors")),
                "year": int(item.get("year") or 0),
                "abstract": _clean_text(item.get("abstract")),
                "venue": _clean_text(item.get("venue")),
                "citationCount": int(item.get("citationCount") or 0),
                "doi": doi,
                "url": _clean_text(item.get("url")) or (f"https://doi.org/{doi}" if doi else ""),
                "source": "Semantic Scholar",
            }
        )
    return papers


def _request_json(
    url: str,
    *,
    params: dict[str, str],
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | list[Any] | None:
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def _build_summary(
    event: dict[str, Any],
    cohort_stats: dict[str, Any],
    papers: list[dict[str, Any]],
    topic_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    place = str(event.get("place") or "未知区域")
    normalized_place = _normalize_place(place)
    region = _extract_region(normalized_place)
    mag = _as_float(event.get("mag")) or 0.0
    depth = _as_float(event.get("depth_km"))
    depth_class = _depth_class(depth)
    time_text = _format_time(event.get("time"))

    cohort_total = int(cohort_stats.get("total") or 0)
    max_mag = _as_float(cohort_stats.get("maxMagnitude")) or mag
    leading_regions = [item["region"] for item in cohort_stats.get("topRegions", [])[:3]]
    leading_region_text = "、".join(leading_regions) if leading_regions else "当前监测区域"

    if topic_signals:
        top_signal = topic_signals[0]
        headline = (
            f"{region} M{mag:.1f} 事件与“{top_signal['label']}”文献主题最相关"
        )
        literature_core = (
            f"摘要级检索结果显示，“{top_signal['label']}”是最突出的研究方向，"
            f"说明该区域研究通常从 {top_signal['description']} 的角度解释地震活动。"
        )
    else:
        headline = f"{region} M{mag:.1f} 事件的文献结果仍在补充"
        literature_core = (
            "当前未获得稳定的摘要级文献结果，因此下面的总结以地震目录统计为主，"
            "建议在网络稳定时再次触发检索。"
        )

    key_points = [
        (
            f"本次事件发生于 {time_text}，地点为 {place}，震级 M{mag:.1f}，"
            f"震源深度 {depth if depth is not None else '未知'} km，属于{depth_class}事件。"
        ),
        (
            f"与该事件一并纳入面板分析的当前地震样本共有 {cohort_total} 条，"
            f"最大震级达到 M{max_mag:.1f}，空间上主要集中在 {leading_region_text}。"
        ),
        literature_core,
    ]

    if mag >= 6:
        key_points.append(
            "事件震级已经进入强震区间，摘要级文献通常会额外关注余震持续性、"
            "强震动衰减以及次生灾害链条。"
        )
    elif depth is not None and depth < 20:
        key_points.append(
            "震源较浅，快速研判时应优先关注近场强震动、地表破裂和滑坡等浅表响应。"
        )
    else:
        key_points.append(
            "从深度和区域分布看，建议把这次事件放在更长时间尺度的区域活动性背景中解读。"
        )

    if papers:
        evidence = [
            paper["evidenceSnippet"]
            for paper in papers
            if paper.get("evidenceSnippet")
        ][:3]
    else:
        evidence = []

    gap_text = (
        "当前总结仅使用 OpenAlex 与 Semantic Scholar 返回的题录、摘要和关键词，"
        "没有批量下载全文 PDF，因此更适合做快速科研研判，而不是正式综述。"
    )

    return {
        "headline": headline,
        "eventContext": (
            f"{normalized_place} 在当前样本中表现为一个{depth_class}地震案例，"
            f"适合与区域活动性、构造环境和危险性研究联合解读。"
        ),
        "keyPoints": key_points,
        "evidenceSnippets": evidence,
        "researchGap": (
            "后续如果要形成更完整的科学结论，建议对高相关文献继续做全文抓取、"
            "震源机制图件核验以及与台网波形结果的交叉验证。"
        ),
        "limitations": gap_text,
    }


def _build_cohort_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "total": 0,
            "maxMagnitude": 0,
            "averageMagnitude": 0,
            "averageDepthKm": 0,
            "topRegions": [],
            "depthBands": [],
        }

    magnitudes = [_as_float(event.get("mag")) or 0.0 for event in events]
    depths = [
        depth
        for depth in (_as_float(event.get("depth_km")) for event in events)
        if depth is not None
    ]

    region_counter = Counter(
        _extract_region(_normalize_place(str(event.get("place") or "")))
        for event in events
    )

    shallow = 0
    intermediate = 0
    deep = 0
    for depth in depths:
        if depth < 70:
            shallow += 1
        elif depth < 300:
            intermediate += 1
        else:
            deep += 1

    return {
        "total": len(events),
        "maxMagnitude": max(magnitudes),
        "averageMagnitude": round(sum(magnitudes) / len(magnitudes), 2),
        "averageDepthKm": round(sum(depths) / len(depths), 2) if depths else 0,
        "topRegions": [
            {"region": region, "count": count}
            for region, count in region_counter.most_common(5)
            if region
        ],
        "depthBands": [
            {"label": "浅源(<70km)", "count": shallow},
            {"label": "中源(70-300km)", "count": intermediate},
            {"label": "深源(>300km)", "count": deep},
        ],
    }


def _extract_topic_signals(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for rule in TOPIC_RULES:
        matched_ids: set[str] = set()
        for paper in papers:
            haystack = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
            if any(keyword in haystack for keyword in rule["keywords"]):
                matched_ids.add(str(paper.get("paperId") or paper.get("title") or ""))
        if matched_ids:
            signals.append(
                {
                    "key": rule["key"],
                    "label": rule["label"],
                    "description": rule["description"],
                    "paperCount": len(matched_ids),
                }
            )

    signals.sort(key=lambda item: item["paperCount"], reverse=True)
    return signals[:4]


def _decorate_paper(paper: dict[str, Any]) -> dict[str, Any]:
    abstract = _clean_text(paper.get("abstract"))
    evidence = _pick_evidence_sentence(abstract)
    decorated = deepcopy(paper)
    decorated["abstract"] = abstract
    decorated["abstractPreview"] = _shorten_preview(abstract)
    decorated["evidenceSnippet"] = evidence
    decorated["authorsText"] = _authors_text(paper.get("authors"))
    decorated["relevanceHint"] = _paper_relevance_hint(decorated)
    return decorated


def _paper_relevance_hint(paper: dict[str, Any]) -> str:
    haystack = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    for rule in TOPIC_RULES:
        if any(keyword in haystack for keyword in rule["keywords"]):
            return rule["label"]
    return "区域地震背景参考"


def _deduplicate_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_doi: dict[str, int] = {}
    seen_title: dict[str, int] = {}

    for paper in papers:
        doi = _clean_text(paper.get("doi")).lower()
        title_norm = _normalize_title(_clean_text(paper.get("title")))
        existing_index: int | None = None

        if doi and doi in seen_doi:
            existing_index = seen_doi[doi]
        elif title_norm and title_norm in seen_title:
            existing_index = seen_title[title_norm]

        if existing_index is None:
            deduped.append(paper)
            idx = len(deduped) - 1
            if doi:
                seen_doi[doi] = idx
            if title_norm:
                seen_title[title_norm] = idx
            continue

        old_paper = deduped[existing_index]
        if _paper_rank_tuple(paper) > _paper_rank_tuple(old_paper):
            deduped[existing_index] = paper
            if doi:
                seen_doi[doi] = existing_index
            if title_norm:
                seen_title[title_norm] = existing_index

    return deduped


def _paper_rank_tuple(paper: dict[str, Any]) -> tuple[int, int, int]:
    return (
        int(paper.get("citationCount") or 0),
        int(paper.get("year") or 0),
        len(_clean_text(paper.get("abstract"))),
    )


def _cache_get(key: str) -> dict[str, Any] | None:
    now = time.time()
    with SEARCH_CACHE_LOCK:
        item = SEARCH_CACHE.get(key)
        if item is None:
            return None
        if now - item["timestamp"] > SEARCH_CACHE_TTL_SECONDS:
            SEARCH_CACHE.pop(key, None)
            return None
        return deepcopy(item["payload"])


def _cache_put(key: str, payload: dict[str, Any]) -> None:
    with SEARCH_CACHE_LOCK:
        SEARCH_CACHE[key] = {"timestamp": time.time(), "payload": deepcopy(payload)}


def _normalize_place(place: str) -> str:
    cleaned = DISTANCE_PREFIX_RE.sub("", place or "").strip()
    return WHITESPACE_RE.sub(" ", cleaned)


def _extract_region(place: str) -> str:
    parts = [segment.strip() for segment in place.split(",") if segment.strip()]
    if not parts:
        return place or "未知区域"
    return parts[-1] if len(parts) > 1 else parts[0]


def _shorten_query(query: str, max_terms: int = 6) -> str:
    tokens = [
        token
        for token in re.split(r"[^a-zA-Z0-9]+", query)
        if token and token.lower() not in {"the", "and", "for", "with", "into", "from", "near"}
    ]
    if not tokens:
        return ""
    return " ".join(tokens[:max_terms])


def _normalize_title(title: str) -> str:
    lowered = title.lower()
    lowered = NON_ALNUM_RE.sub(" ", lowered)
    return WHITESPACE_RE.sub(" ", lowered).strip()


def _reconstruct_openalex_abstract(inverted_index: Any) -> str:
    if not isinstance(inverted_index, dict):
        return ""

    words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                words.append((position, word))

    words.sort(key=lambda item: item[0])
    return _clean_text(" ".join(word for _, word in words))


def _openalex_authors(authorships: Any) -> list[str]:
    if not isinstance(authorships, list):
        return []
    names: list[str] = []
    for authorship in authorships:
        if not isinstance(authorship, dict):
            continue
        author = authorship.get("author") or {}
        if isinstance(author, dict):
            name = _clean_text(author.get("display_name"))
            if name:
                names.append(name)
    return names


def _s2_authors(authors: Any) -> list[str]:
    if not isinstance(authors, list):
        return []
    names: list[str] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("name"))
        if name:
            names.append(name)
    return names


def _authors_text(authors: Any) -> str:
    if not isinstance(authors, list) or not authors:
        return "作者信息缺失"
    if len(authors) <= 3:
        return ", ".join(str(author) for author in authors)
    return f"{', '.join(str(author) for author in authors[:3])} 等"


def _openalex_venue(primary_location: Any) -> str:
    if not isinstance(primary_location, dict):
        return ""
    source = primary_location.get("source") or {}
    if not isinstance(source, dict):
        return ""
    return _clean_text(source.get("display_name"))


def _paper_url(doi: str, ids: dict[str, Any], openalex_id: Any) -> str:
    if doi:
        return f"https://doi.org/{doi}"
    raw_arxiv = _clean_text(ids.get("arxiv"))
    if raw_arxiv:
        return raw_arxiv
    if openalex_id:
        return _clean_text(openalex_id)
    return ""


def _pick_evidence_sentence(abstract: str) -> str:
    if not abstract:
        return ""
    segments = re.split(r"(?<=[.!?])\s+", abstract)
    for segment in segments:
        trimmed = segment.strip()
        if len(trimmed) >= 80:
            return _shorten_preview(trimmed, 220)
    return _shorten_preview(abstract, 220)


def _shorten_preview(text: str, max_length: int = 260) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 1].rstrip()}…"


def _format_time(value: Any) -> str:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return str(value) or "未知时间"


def _depth_class(depth: float | None) -> str:
    if depth is None:
        return "未知深度"
    if depth < 70:
        return "浅源"
    if depth < 300:
        return "中源"
    return "深源"


def _looks_offshore(place: str) -> bool:
    lowered = place.lower()
    return any(
        keyword in lowered
        for keyword in ("island", "sea", "ocean", "coast", "offshore", "trench")
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return WHITESPACE_RE.sub(" ", str(value)).strip()


def _compact_notes(notes: list[str]) -> list[str]:
    compacted: list[str] = []
    seen: set[str] = set()
    for note in notes:
        if not note or note in seen:
            continue
        seen.add(note)
        compacted.append(note)
    return compacted[:4]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number
