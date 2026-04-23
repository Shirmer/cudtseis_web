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
import xml.etree.ElementTree as ET

import requests


OPENALEX_URL = "https://api.openalex.org/works"
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "https://export.arxiv.org/api/query"
REQUEST_TIMEOUT = 20
SEARCH_CACHE_TTL_SECONDS = 6 * 60 * 60
DISTANCE_PREFIX_RE = re.compile(r"^\s*\d+(?:\.\d+)?\s*km\s+[A-Z-]+\s+of\s+", re.I)
WHITESPACE_RE = re.compile(r"\s+")
NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]")
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?$")

ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

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
    query_notes: list[str] = []

    source_plan = (
        ("OpenAlex", lambda query: _search_openalex(query, limit=6, year_min=year_min, email=openalex_email)),
        (
            "Semantic Scholar",
            lambda query: _search_semantic_scholar(
                query,
                limit=4,
                year_min=year_min,
                api_key=semantic_scholar_api_key,
            ),
        ),
        ("arXiv", lambda query: _search_arxiv(query, limit=4, year_min=year_min)),
    )

    for source_name, search_fn in source_plan:
        source_started = False
        for query in queries:
            results = search_fn(query)
            source_started = True
            if results:
                papers.extend(results)
            else:
                query_notes.append(f"{source_name} 未从查询 “{query}” 返回稳定结果。")

            if source_name != "arXiv" and len(_deduplicate_papers(papers)) >= limit:
                break

        deduped = _deduplicate_papers(papers)
        if len(deduped) >= limit and source_name == "arXiv":
            break
        if len(deduped) >= limit and source_started:
            continue

    deduped = _deduplicate_papers(papers)
    deduped.sort(
        key=lambda paper: (
            int(paper.get("citationCount") or 0),
            int(paper.get("year") or 0),
            len(paper.get("abstract") or ""),
        ),
        reverse=True,
    )

    final_papers = [_decorate_paper(paper) for paper in deduped[:limit]]
    final_breakdown = Counter(str(paper.get("source") or "Unknown") for paper in final_papers)
    response = {
        "mode": "public-api-abstract-first",
        "queryPlan": {
            "queries": queries,
            "yearMin": year_min,
            "sources": ["OpenAlex", "Semantic Scholar", "arXiv"],
            "strategy": "通过 OpenAlex、Semantic Scholar 和 arXiv 公共 API 聚合检索题录与摘要，不批量下载 PDF。",
        },
        "sourceBreakdown": dict(final_breakdown),
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


def _search_arxiv(query: str, *, limit: int, year_min: int) -> list[dict[str, Any]]:
    params = {
        "search_query": _build_arxiv_query(query),
        "start": "0",
        "max_results": str(min(limit, 10)),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    xml_payload = _request_text(ARXIV_URL, params=params)
    if not xml_payload:
        return []

    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        return []

    papers: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        title = _clean_text(entry.findtext("atom:title", default="", namespaces=ARXIV_NS))
        if not title:
            continue

        published_text = _clean_text(
            entry.findtext("atom:published", default="", namespaces=ARXIV_NS)
        )
        year = int(published_text[:4]) if len(published_text) >= 4 and published_text[:4].isdigit() else 0
        if year_min > 0 and year and year < year_min:
            continue

        entry_id = _clean_text(entry.findtext("atom:id", default="", namespaces=ARXIV_NS))
        arxiv_id_match = ARXIV_ID_RE.search(entry_id)
        arxiv_id = arxiv_id_match.group(1) if arxiv_id_match else ""

        primary_category = entry.find("arxiv:primary_category", ARXIV_NS)
        venue = primary_category.attrib.get("term", "") if primary_category is not None else ""
        doi = _clean_text(entry.findtext("arxiv:doi", default="", namespaces=ARXIV_NS))

        url = ""
        for link in entry.findall("atom:link", ARXIV_NS):
            href = _clean_text(link.attrib.get("href"))
            rel = _clean_text(link.attrib.get("rel"))
            link_type = _clean_text(link.attrib.get("type"))
            if rel == "alternate" and link_type == "text/html" and href:
                url = href
                break
        if not url and arxiv_id:
            url = f"https://arxiv.org/abs/{arxiv_id}"

        papers.append(
            {
                "paperId": f"arxiv-{arxiv_id}" if arxiv_id else title.lower(),
                "title": title,
                "authors": [
                    _clean_text(author.findtext("atom:name", default="", namespaces=ARXIV_NS))
                    for author in entry.findall("atom:author", ARXIV_NS)
                    if _clean_text(author.findtext("atom:name", default="", namespaces=ARXIV_NS))
                ],
                "year": year,
                "abstract": _clean_text(
                    entry.findtext("atom:summary", default="", namespaces=ARXIV_NS)
                ),
                "venue": venue or "arXiv preprint",
                "citationCount": 0,
                "doi": doi,
                "url": url,
                "source": "arXiv",
            }
        )
    return papers


def _request_text(
    url: str,
    *,
    params: dict[str, str],
    headers: dict[str, str] | None = None,
) -> str | None:
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None


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
    paper_stats = _build_paper_stats(papers)
    top_signal = topic_signals[0] if topic_signals else None

    if top_signal:
        headline = f"{region} M{mag:.1f} 地震重点解读"
        subtitle = f"当前证据更偏向“{top_signal['label']}”这条解释主线，建议优先关注构造背景、序列演化和风险指向。"
    else:
        headline = f"{region} M{mag:.1f} 地震重点解读"
        subtitle = "当前文献聚焦度有限，现阶段判断主要基于事件参数和同期地震活动背景。"

    lead = (
        f"{time_text}，{place} 发生 M{mag:.1f}、深度约 {depth if depth is not None else '未知'} km 的{depth_class}地震。"
        f"系统结合 {cohort_total} 条同期事件与 {paper_stats['total']} 篇相关摘要，给出面向研判的快速结论。"
    )

    overview_section = {
        "key": "overview",
        "title": "核心判断",
        "paragraphs": [
            (
                f"这次事件应放在 {leading_region_text} 一带的活动背景中理解。"
                f"就单次事件而言，M{mag:.1f} 已具备持续跟踪价值；若与当前样本相比，它仍属于需要重点复核的中强事件。"
            ),
        ],
    }

    interpretation_section = {
        "key": "interpretation",
        "title": "机制侧重点",
        "paragraphs": [
            (
                f"{'当前摘要证据最集中指向“' + top_signal['label'] + '”框架，' if top_signal else '当前文献主题尚未高度集中，'}"
                f"更适合优先从区域构造位置、断层活动方式和后续序列演化三个角度切入，而不是孤立解读单个参数。"
            ),
        ],
    }

    risk_section = {
        "key": "risk",
        "title": "监测建议",
        "paragraphs": [
            (
                f"短期内建议把关注点放在余震迁移、震级衰减和邻近构造响应上。"
                f"{'浅源特征意味着更需要注意近场断层与地表影响。' if depth is not None and depth < 70 else '若震源较深，则更应从区域构造应力背景解释其意义。'}"
            ),
        ],
    }

    limitations_section = {
        "key": "limits",
        "title": "证据边界",
        "paragraphs": [
            (
                "当前结论基于公开 API 返回的题录和摘要，适合作为快速研判入口；若要形成正式科研结论，仍需补充全文、震源机制与形变观测等证据。"
            ),
        ],
    }

    evidence_cards = _build_evidence_cards(papers)[:2]
    closing = _build_closing_paragraph(place, region, mag, depth, top_signal, paper_stats)
    gap_text = (
        "当前为摘要级证据链结论，适合快速判断，不宜直接替代正式综述或论文级论证。"
    )

    sections = [
        overview_section,
        interpretation_section,
        risk_section,
        limitations_section,
    ]

    key_points = [
        (
            f"事件定位：{place}，M{mag:.1f}，{depth_class}地震，"
            f"需要放在 {leading_region_text} 的区域活动背景下理解。"
        ),
        (
            f"研究主线：{'优先参考“' + top_signal['label'] + '”框架。' if top_signal else '当前没有单一主导主题，建议并行看构造、序列和危险性。'}"
        ),
        (
            f"当前重点：优先盯余震序列变化、邻近断层响应，以及{'近场影响' if depth is not None and depth < 70 else '区域构造解释'}。"
        ),
    ]

    return {
        "headline": headline,
        "subtitle": subtitle,
        "abstract": lead,
        "sections": sections,
        "evidenceCards": evidence_cards,
        "closing": closing,
        "limitations": gap_text,
        # Backward-compatible fallback fields.
        "eventContext": lead,
        "keyPoints": key_points,
        "evidenceSnippets": [card["text"] for card in evidence_cards],
        "researchGap": limitations_section["paragraphs"][0],
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


def _build_paper_stats(papers: list[dict[str, Any]]) -> dict[str, Any]:
    years = [int(paper.get("year") or 0) for paper in papers if int(paper.get("year") or 0) > 0]
    source_counts = Counter(str(paper.get("source") or "Unknown") for paper in papers)
    venue_counts = Counter(
        _clean_text(paper.get("venue")) or str(paper.get("source") or "Unknown")
        for paper in papers
    )

    return {
        "total": len(papers),
        "sourceCounts": dict(source_counts),
        "venues": [venue for venue, _ in venue_counts.most_common(3)],
        "minYear": min(years) if years else 0,
        "maxYear": max(years) if years else 0,
        "avgYear": round(sum(years) / len(years), 1) if years else 0,
    }


def _build_literature_scope_paragraph(
    region: str,
    paper_stats: dict[str, Any],
    top_signal: dict[str, Any] | None,
) -> str:
    if paper_stats["total"] <= 0:
        return (
            "当前尚未得到稳定的文献样本，因此这一轮解读更多依赖事件参数本身，"
            "还不能把区域研究共识完整展开。"
        )

    sources_text = _format_counter_text(paper_stats["sourceCounts"], unit="篇")
    venue_text = "、".join(paper_stats["venues"]) if paper_stats["venues"] else "多个跨学科期刊/数据库来源"
    year_text = (
        f"{paper_stats['minYear']}-{paper_stats['maxYear']}"
        if paper_stats["minYear"] and paper_stats["maxYear"]
        else "近年"
    )
    signal_text = (
        f"其中最突出的主题是“{top_signal['label']}”，说明研究者更倾向于从该角度解释区域地震活动。"
        if top_signal
        else "目前尚未形成足够清晰的主题集中趋势。"
    )

    return (
        f"本次检索直接调用 OpenAlex、Semantic Scholar 与 arXiv 的公共 API，围绕 {region} 及相近构造语义形成"
        f"{paper_stats['total']} 篇去重结果，来源构成为 {sources_text}。这些结果主要分布在 {year_text} 年，"
        f"高频发表平台包括 {venue_text}。{signal_text}"
    )


def _build_literature_consensus_paragraph(
    topic_signals: list[dict[str, Any]],
    papers: list[dict[str, Any]],
) -> str:
    if not papers:
        return "由于缺少摘要样本，当前还不能对研究共识做更细的归纳。"

    signal_labels = "、".join(signal["label"] for signal in topic_signals[:3]) if topic_signals else "区域背景研究"
    top_papers = _top_papers(papers, limit=2)
    paper_text = "；".join(
        f"《{_clean_text(paper.get('title'))}》把重点放在{_clean_text(paper.get('relevanceHint') or paper.get('venue') or '区域地震背景')}"
        for paper in top_papers
    )

    return (
        f"从主题分布上看，当前摘要样本主要围绕 {signal_labels} 展开，这说明相关研究并不是只看单次地震本身，"
        "而是强调把它放进区域构造、序列演化和危险性评估的联合框架里理解。"
        f"{paper_text}。这类文献结构与传统地震学综述较为接近，因此适合直接转化为界面中的科研结论页面。"
    )


def _build_mechanism_paragraph(
    place: str,
    region: str,
    depth: float | None,
    magnitude: float,
    top_signal: dict[str, Any] | None,
) -> str:
    if depth is None:
        depth_text = "由于震源深度尚不完整，机制判断需要保留更大不确定性。"
    elif depth < 70:
        depth_text = "震源较浅，通常更容易与上地壳断层活动、应力快速释放和近场破裂过程联系起来。"
    elif depth < 300:
        depth_text = "震源处于中等深度范围，研究上往往会联系板片俯冲、脱水脆化或中深层应力重分布。"
    else:
        depth_text = "深源特征明显，这类事件在机制上更常被放进深部板片动力学或地幔转换带背景中讨论。"

    signal_text = (
        f"当前最强的文献主题是“{top_signal['label']}”，说明对 {region} 附近事件的解释更偏向 {top_signal['description']}"
        if top_signal
        else f"当前文献主题还未充分集中，因此对 {region} 的机制解释需要更多辅助观测支撑。"
    )

    mag_text = (
        "从震级看，这一事件已具备独立进入研究样本库的价值，"
        if magnitude >= 5
        else "虽然震级未到强震级别，但它仍可作为区域应力演化的一个局部样本，"
    )

    return (
        f"就机制解释而言，{place} 地震首先应结合其深度特征来理解。{depth_text}"
        f"{mag_text}{signal_text}。因此，现阶段更稳妥的判断不是直接下定论某一条断层已完全控制该事件，"
        "而是认为它反映了区域构造应力场在特定深度带上的一次可识别释放。"
    )


def _build_sequence_paragraph(
    place: str,
    depth: float | None,
    magnitude: float,
    topic_signals: list[dict[str, Any]],
) -> str:
    sequence_bias = next((signal for signal in topic_signals if signal["key"] == "seismicity"), None)
    hazard_bias = next((signal for signal in topic_signals if signal["key"] == "hazard"), None)

    if sequence_bias:
        sequence_text = (
            "文献中对地震序列和活动性分析的关注较高，这提示后续需要继续跟踪余震时空迁移、b 值变化和目录完备性。"
        )
    else:
        sequence_text = "目前没有看到序列研究在主题中占据绝对主导，因此后续仍需靠新的观测数据判断余震链条是否会显著发展。"

    if hazard_bias or magnitude >= 6:
        hazard_text = "同时，危险性维度不能忽视，尤其要关注强震动衰减、局地放大效应以及潜在次生灾害响应。"
    elif depth is not None and depth < 20:
        hazard_text = "由于震源浅，近场地表响应和地形相关风险仍应列入后续监测清单。"
    else:
        hazard_text = "若后续没有明显余震放大，这一事件更可能体现为区域背景活动的一次中等强度扰动。"

    return (
        f"从事件序列的角度看，{place} 不能只作为单点震例处理。{sequence_text}"
        f"{hazard_text} 这也是为什么界面中的总结应当写成长段落综述，而不是只给出一句简短标签。"
    )


def _build_hazard_paragraph(
    place: str,
    magnitude: float,
    depth: float | None,
    topic_signals: list[dict[str, Any]],
) -> str:
    monitoring_bias = next((signal for signal in topic_signals if signal["key"] == "monitoring"), None)
    if magnitude >= 6:
        base = (
            f"{place} 事件已达到强震研究关注阈值，快速评估时需要同时看震源参数、局地场地条件和后续余震响应，"
            "因为这些因素会共同影响危险性判断。"
        )
    elif depth is not None and depth < 20:
        base = (
            f"{place} 事件虽然不一定会造成广域影响，但浅源特征意味着局部强震动和地表破坏更值得警惕。"
        )
    else:
        base = (
            f"{place} 事件的直接破坏性未必极端，但在区域活动性研究中仍有价值，"
            "因为它可能代表某一应力分区进入新的活跃阶段。"
        )

    if monitoring_bias:
        follow_up = (
            "由于监测方法类文献也占有一定比例，说明现有研究倾向于结合波形、定位误差和多源观测做快速反演。"
        )
    else:
        follow_up = "现阶段最重要的是继续保持台网连续监测，避免仅凭一次事件参数就过度解释其危险性。"

    return f"{base}{follow_up}"


def _build_monitoring_paragraph(
    place: str,
    magnitude: float,
    depth: float | None,
    topic_signals: list[dict[str, Any]],
) -> str:
    top_topics = "、".join(signal["label"] for signal in topic_signals[:2]) if topic_signals else "区域构造背景"
    depth_hint = (
        "重点补做震源机制解和断层几何约束"
        if depth is None or depth < 70
        else "重点关注深部应力迁移与序列持续性"
    )
    magnitude_hint = "加强余震自动检测和地震目录滚动更新" if magnitude >= 5 else "持续记录后续小震活动以验证是否出现成簇演化"

    return (
        f"就监测建议而言，当前最值得继续投入的方向是：{depth_hint}，{magnitude_hint}。"
        f"如果后续要把界面内容进一步升级成可发表级的研究笔记，应围绕 {top_topics} 两条主线建立更系统的数据抽取和全文阅读流程。"
    )


def _build_evidence_cards(papers: list[dict[str, Any]]) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for paper in _top_papers(papers, limit=3):
        title = _clean_text(paper.get("title"))
        cards.append(
            {
                "title": title or "摘要证据",
                "text": _pick_evidence_sentence(_clean_text(paper.get("abstract"))),
                "citation": _paper_citation_meta(paper),
            }
        )
    return cards


def _build_closing_paragraph(
    place: str,
    region: str,
    magnitude: float,
    depth: float | None,
    top_signal: dict[str, Any] | None,
    paper_stats: dict[str, Any],
) -> str:
    signal_text = (
        f"文献更支持从“{top_signal['label']}”框架理解这次事件。"
        if top_signal
        else "当前文献尚未形成足够稳定的单一解释框架。"
    )
    depth_text = (
        "浅源特征提示应优先检查近场断层与地表响应。"
        if depth is not None and depth < 70
        else "其深度特征更适合结合区域构造背景来解释。"
    )
    return (
        f"综合判断，{place} M{magnitude:.1f} 地震值得继续跟踪。"
        f"{signal_text} 当前已汇总 {paper_stats['total']} 篇摘要级证据；{depth_text}"
    )


def _format_counter_text(counter_like: dict[str, int], unit: str = "") -> str:
    if not counter_like:
        return f"0{unit}"
    return "、".join(
        f"{label} {count}{unit}"
        for label, count in counter_like.items()
    )


def _top_papers(papers: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return sorted(
        papers,
        key=lambda paper: (
            int(paper.get("citationCount") or 0),
            int(paper.get("year") or 0),
            len(_clean_text(paper.get("abstract"))),
        ),
        reverse=True,
    )[:limit]


def _paper_citation_meta(paper: dict[str, Any]) -> str:
    venue = _clean_text(paper.get("venue")) or str(paper.get("source") or "Unknown")
    year = int(paper.get("year") or 0)
    citation_count = int(paper.get("citationCount") or 0)
    if citation_count > 0:
        return f"{venue} · {year or '未知年份'} · 引用 {citation_count}"
    return f"{venue} · {year or '未知年份'}"


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


def _build_arxiv_query(query: str) -> str:
    tokens = [
        token
        for token in re.split(r"[^a-zA-Z0-9]+", query)
        if token and token.lower() not in {"the", "and", "for", "with", "into", "from", "near"}
    ]
    if not tokens:
        return "all:earthquake"
    return " AND ".join(f"all:{token}" for token in tokens[:6])


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
