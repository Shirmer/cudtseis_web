from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

from .settings import settings


PAPER_PIPELINE = [
    {
        "key": "sources",
        "title": "文献来源",
        "description": "DOI、期刊页、arXiv、机构库、团队本地 PDF 与人工导入记录统一进入候选池。",
    },
    {
        "key": "acquisition",
        "title": "采集与版权控制层",
        "description": "metadata first，采集全文、摘要、作者、年份、DOI、期刊、开放访问链接和授权状态。",
    },
    {
        "key": "metadata-prefilter",
        "title": "元数据预筛选层",
        "description": "先按标题、摘要、年份、来源、关键词和文献类型判断是否入库，减少低质量文献污染索引。",
    },
    {
        "key": "parsing",
        "title": "多模态文档解析层",
        "description": "借鉴 RAG-Anything，将正文、表格、图表说明和公式拆成可追踪的多模态证据单元。",
    },
    {
        "key": "knowledge-extraction",
        "title": "结构化知识抽取层",
        "description": "抽取地点、震级、深度、断层类型、震源机制、余震特征和灾害影响等地震专业字段。",
    },
    {
        "key": "store",
        "title": "多粒度索引层",
        "description": "同时维护文档级、章节级、chunk级、图表级和实体关系索引，避免只靠单一 chunk 召回。",
    },
    {
        "key": "retrieval",
        "title": "混合检索层",
        "description": "融合 Query Rewrite、向量检索、BM25关键词检索、元数据过滤和图谱检索。",
    },
    {
        "key": "rerank",
        "title": "Rerank 重排序层",
        "description": "先召回候选文献，再用轻量 cross-encoder 风格评分重排；后续可替换为 bge-reranker。",
    },
    {
        "key": "evidence",
        "title": "证据构建层",
        "description": "先构建 Claim、Evidence、Citation、Confidence，再进入答案生成，避免无证据结论。",
    },
    {
        "key": "generation",
        "title": "答案生成层",
        "description": "基于 Evidence Pack 生成地震专业解读、风险分析和不确定性说明。",
    },
    {
        "key": "validation",
        "title": "事实校验/反幻觉层",
        "description": "检查每个结论是否被证据支持、引用是否相关、是否存在过度预测或确定性表述。",
    },
    {
        "key": "seismic-output",
        "title": "地震专业解读输出",
        "description": "面向构造背景、震源机制、序列演化、危险性评估和监测建议形成专业解读。",
    },
]


PARSER_SLOTS = ["正文提取", "表格解析", "图片/图表说明", "公式识别"]
RETRIEVAL_MODES = ["Query Rewrite", "向量检索", "BM25关键词检索", "元数据过滤", "图谱检索", "Rerank"]
STORAGE_UNITS = ["文档级索引", "章节级索引", "chunk级索引", "图表级索引", "实体关系索引"]
STRUCTURED_FIELDS = ["location", "magnitude", "depth", "faultType", "mechanism", "aftershock", "hazard"]
VECTOR_DIMENSIONS = 128
TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


PAPER_CATALOG = [
    {
        "id": "paper-eeew-deep-learning",
        "title": "Deep Learning for Real-time Earthquake Early Warning",
        "authors": ["Chuntao Liang", "Yilin Lin", "Xingli Fan"],
        "journal": "Nature Communications",
        "year": 2024,
        "doi": "10.0000/seislab.eeew.2024",
        "url": "https://example.org/papers/eeew",
        "topics": ["地震预警", "深度学习", "震相识别"],
        "evidenceType": "Claim-ready",
        "abstractPreview": "提出面向实时地震预警的深度学习流程，重点处理低延迟震相识别、震级估计和误报控制。",
        "claim": "深度学习模型可以提升实时地震预警中的早期震相识别稳定性。",
        "evidence": "模型在多台站连续波形上保持低延迟识别，并减少人工阈值规则带来的漏报。",
        "reasoning": "预警任务依赖首波到时和早期振幅特征，深度模型能在噪声背景中学习更稳健的时序表示。",
    },
    {
        "id": "paper-transformer-picking",
        "title": "Seismic Phase Picking using Transformer Networks",
        "authors": ["Xingli Fan", "Yi Lin"],
        "journal": "Geophysical Research Letters",
        "year": 2023,
        "doi": "10.0000/seislab.phase.2023",
        "url": "https://example.org/papers/phase-transformer",
        "topics": ["震相拾取", "Transformer", "自动化处理"],
        "evidenceType": "Method",
        "abstractPreview": "使用 Transformer 编码长程波形上下文，改进 P 波和 S 波到时拾取精度。",
        "claim": "Transformer 结构适合处理长窗地震波形中的震相拾取问题。",
        "evidence": "注意力机制能够同时关注初至附近和背景噪声结构，从而降低局部极值误判。",
        "reasoning": "震相拾取不是孤立峰值检测，长程上下文能帮助模型区分震相、噪声和仪器扰动。",
    },
    {
        "id": "paper-sichuan-tomography",
        "title": "High-resolution Tomography of the Sichuan Basin",
        "authors": ["Yi Lin", "Chuntao Liang"],
        "journal": "JGR: Solid Earth",
        "year": 2023,
        "doi": "10.0000/seislab.tomography.2023",
        "url": "https://example.org/papers/sichuan-tomography",
        "topics": ["四川盆地", "层析成像", "速度结构"],
        "evidenceType": "Region",
        "abstractPreview": "基于区域台网资料反演四川盆地及邻区速度结构，讨论盆山耦合和断裂活动背景。",
        "claim": "四川盆地及邻区地震活动需要结合速度结构和盆山构造耦合解释。",
        "evidence": "高分辨率层析结果显示盆地边界和深部速度异常与主要断裂带空间对应。",
        "reasoning": "速度异常约束介质结构，能帮助解释应力集中、波传播路径和局地震动放大。",
    },
    {
        "id": "paper-fault-3d-cnn",
        "title": "Automated Fault Detection with 3D CNNs",
        "authors": ["Xingye Liu", "Yilin Lin"],
        "journal": "Computers & Geosciences",
        "year": 2022,
        "doi": "10.0000/seislab.fault.2022",
        "url": "https://example.org/papers/fault-3d-cnn",
        "topics": ["断层识别", "三维卷积", "地震解释"],
        "evidenceType": "Graph",
        "abstractPreview": "利用三维卷积网络自动识别地震体中的断层几何形态，并输出可解释的断层概率体。",
        "claim": "三维卷积模型可以作为断层几何识别和知识图谱构建的证据来源。",
        "evidence": "模型输出的断层概率体可与人工解释结果对比，并进一步抽取断层走向和连通性。",
        "reasoning": "断层是地震专业知识图谱中的核心实体，自动识别结果能连接论文、区域和构造关系。",
    },
    {
        "id": "paper-aftershock-sequence",
        "title": "Aftershock Sequence Evolution in Active Intraplate Regions",
        "authors": ["Ming Zhao", "Qiyun Chen"],
        "journal": "Seismological Research Letters",
        "year": 2021,
        "doi": "10.0000/seislab.aftershock.2021",
        "url": "https://example.org/papers/aftershock-sequence",
        "topics": ["余震序列", "活动性分析", "b值"],
        "evidenceType": "Sequence",
        "abstractPreview": "比较板内活动区余震序列的时空迁移和 b 值变化，提出滚动监测指标。",
        "claim": "余震序列演化应作为地震后续研判的重要证据。",
        "evidence": "序列迁移、震级衰减和 b 值变化可反映局部应力调整过程。",
        "reasoning": "单次事件参数不足以支撑完整判断，序列统计能补充时间维度上的危险性线索。",
    },
    {
        "id": "paper-ground-motion-risk",
        "title": "Ground Motion Risk Assessment for Mountainous Seismic Zones",
        "authors": ["Qing Wang", "Xingli Fan"],
        "journal": "Earthquake Engineering & Structural Dynamics",
        "year": 2020,
        "doi": "10.0000/seislab.groundmotion.2020",
        "url": "https://example.org/papers/ground-motion-risk",
        "topics": ["强震动", "危险性评估", "山区地震"],
        "evidenceType": "Hazard",
        "abstractPreview": "结合地形、场地条件和强震动参数，评估山区地震带的局地放大和次生灾害风险。",
        "claim": "山区地震危险性评估需要同时考虑震源、路径、场地和地形因素。",
        "evidence": "局地放大效应和地形相关滑坡易发性会改变近场风险判断。",
        "reasoning": "危险性解释不能只看震级，必须把地震学参数与工程和地貌条件合并分析。",
    },
]


def get_paper_architecture() -> dict[str, Any]:
    return {
        "name": "Paper Knowledge Base",
        "pipeline": PAPER_PIPELINE,
        "parserSlots": PARSER_SLOTS,
        "retrievalModes": RETRIEVAL_MODES,
        "storageUnits": STORAGE_UNITS,
        "structuredFields": STRUCTURED_FIELDS,
        "generationSchema": ["Claim", "Evidence", "Reasoning", "Citation"],
        "validationChecks": ["Grounding Check", "Citation Check", "Safety Check"],
    }


def search_papers(
    *,
    query: str = "",
    topic: str = "",
    year_min: int | None = None,
    year_max: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    _ensure_database()
    normalized_query = _normalize(query)
    normalized_topic = _normalize(topic)
    rewritten_queries = _rewrite_query(query)
    rows = _load_paper_rows()

    scored: list[tuple[float, dict[str, Any]]] = []
    for paper in rows:
        if year_min is not None and int(paper["year"]) < year_min:
            continue
        if year_max is not None and int(paper["year"]) > year_max:
            continue
        if normalized_topic and normalized_topic not in [_normalize(item) for item in paper["topics"]]:
            continue

        prefilter = _metadata_prefilter(paper, normalized_query, year_min, year_max, normalized_topic)
        if not prefilter["accepted"]:
            continue

        breakdown = _score_paper(paper, normalized_query, normalized_topic, rewritten_queries)
        if normalized_query and breakdown["recall"] <= 0:
            continue
        rerank_score = _rerank_score(paper, query, rewritten_queries, breakdown)
        paper = {
            **paper,
            "retrievalScore": round(rerank_score, 4),
            "retrievalBreakdown": {
                "vector": round(breakdown["vector"], 4),
                "keyword": round(breakdown["keyword"], 4),
                "structured": round(breakdown["structured"], 4),
                "graph": round(breakdown["graph"], 4),
                "rerank": round(rerank_score, 4),
            },
            "metadataDecision": prefilter,
        }
        scored.append((rerank_score, paper))

    scored.sort(key=lambda item: (item[0], int(item[1]["year"])), reverse=True)
    items = [_decorate_paper(paper) for _, paper in scored[:limit]]
    topic_counts = Counter(topic for paper in rows for topic in paper["topics"])
    years = [int(paper["year"]) for paper in rows]

    return {
        "query": query,
        "filters": {
            "topic": topic,
            "yearMin": year_min,
            "yearMax": year_max,
            "limit": limit,
        },
        "total": len(scored),
        "items": items,
        "topicCounts": dict(topic_counts),
        "yearRange": {"min": min(years) if years else 0, "max": max(years) if years else 0},
        "architecture": get_paper_architecture(),
        "queryPlan": {
            "original": query,
            "rewritten": rewritten_queries,
            "candidateCount": len(rows),
            "recalledCount": len(scored),
            "rerank": "local-cross-encoder-lite",
            "evidencePolicy": "先构建 Evidence Pack，再生成专业解读。",
        },
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def initialize_paper_database() -> dict[str, Any]:
    _ensure_database()
    rows = _load_paper_rows()
    path = _database_path()
    return {
        "path": str(path),
        "papers": len(rows),
        "topics": len({topic for paper in rows for topic in paper["topics"]}),
        "chunks": _count_rows("paper_chunks"),
        "relations": _count_rows("paper_relations"),
        "sizeBytes": path.stat().st_size if path.exists() else 0,
        "status": "ready",
    }


def get_paper_detail(paper_id: str) -> dict[str, Any] | None:
    _ensure_database()
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT
                id, title, authors_json, journal, year, doi, url, topics_json,
                evidence_type, abstract_preview, claim, evidence, reasoning
            FROM papers
            WHERE id = ?
            """,
            (paper_id,),
        ).fetchone()
        if row is None:
            return None
        paper = _decorate_paper(_paper_from_row(conn, row))
        paper["chunks"] = [
            {
                "type": item["chunk_type"],
                "content": item["content"],
                "ordinal": int(item["ordinal"]),
            }
            for item in conn.execute(
                "SELECT chunk_type, content, ordinal FROM paper_chunks WHERE paper_id = ? ORDER BY ordinal ASC",
                (paper_id,),
            ).fetchall()
        ]
        return paper


def add_paper(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_database()
    paper = _normalize_input_paper(payload)
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        existing = conn.execute("SELECT id FROM papers WHERE id = ?", (paper["id"],)).fetchone()
        if existing is not None:
            raise ValueError(f"Paper already exists: {paper['id']}")
        conn.execute(
            """
            INSERT INTO papers (
                id, title, authors_json, journal, year, doi, url, topics_json,
                evidence_type, abstract_preview, claim, evidence, reasoning,
                source_type, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper["id"],
                paper["title"],
                json.dumps(paper["authors"], ensure_ascii=False),
                paper["journal"],
                paper["year"],
                paper["doi"],
                paper["url"],
                json.dumps(paper["topics"], ensure_ascii=False),
                paper["evidenceType"],
                paper["abstractPreview"],
                paper["claim"],
                paper["evidence"],
                paper["reasoning"],
                "manual",
                now,
                now,
            ),
        )
        _write_derived_records(conn, paper)
    detail = get_paper_detail(paper["id"])
    if detail is None:
        raise RuntimeError("Paper was inserted but could not be loaded")
    return detail


def _ensure_database() -> None:
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors_json TEXT NOT NULL,
                journal TEXT NOT NULL,
                year INTEGER NOT NULL,
                doi TEXT NOT NULL,
                url TEXT NOT NULL,
                topics_json TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                abstract_preview TEXT NOT NULL,
                claim TEXT NOT NULL,
                evidence TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'seed',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS paper_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                content TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS paper_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                target TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS parser_status (
                paper_id TEXT NOT NULL,
                slot TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (paper_id, slot),
                FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
            CREATE INDEX IF NOT EXISTS idx_papers_evidence_type ON papers(evidence_type);
            CREATE INDEX IF NOT EXISTS idx_paper_relations_target ON paper_relations(target);
            """
        )
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        if total == 0:
            _seed_database(conn)


def _seed_database(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for paper in PAPER_CATALOG:
        conn.execute(
            """
            INSERT INTO papers (
                id, title, authors_json, journal, year, doi, url, topics_json,
                evidence_type, abstract_preview, claim, evidence, reasoning,
                source_type, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper["id"],
                paper["title"],
                json.dumps(paper["authors"], ensure_ascii=False),
                paper["journal"],
                paper["year"],
                paper["doi"],
                paper["url"],
                json.dumps(paper["topics"], ensure_ascii=False),
                paper["evidenceType"],
                paper["abstractPreview"],
                paper["claim"],
                paper["evidence"],
                paper["reasoning"],
                "seed",
                now,
                now,
            ),
        )
        _write_derived_records(conn, paper)


def _write_derived_records(conn: sqlite3.Connection, paper: dict[str, Any]) -> None:
    chunk_payloads = [
        ("正文提取", paper["abstractPreview"]),
        ("Claim", paper["claim"]),
        ("Evidence", paper["evidence"]),
        ("Reasoning", paper["reasoning"]),
    ]
    for index, (chunk_type, content) in enumerate(chunk_payloads, start=1):
        conn.execute(
            "INSERT INTO paper_chunks (paper_id, chunk_type, content, ordinal) VALUES (?, ?, ?, ?)",
            (paper["id"], chunk_type, content, index),
        )
    for topic in paper["topics"]:
        conn.execute(
            "INSERT INTO paper_relations (paper_id, relation, target) VALUES (?, ?, ?)",
            (paper["id"], "has-topic", topic),
        )
    for author in paper["authors"]:
        conn.execute(
            "INSERT INTO paper_relations (paper_id, relation, target) VALUES (?, ?, ?)",
            (paper["id"], "has-author", author),
        )
    conn.execute(
        "INSERT INTO paper_relations (paper_id, relation, target) VALUES (?, ?, ?)",
        (paper["id"], "published-in", paper["journal"]),
    )
    for slot in PARSER_SLOTS:
        status = "ready" if slot == "正文提取" else "planned"
        conn.execute(
            "INSERT INTO parser_status (paper_id, slot, status) VALUES (?, ?, ?)",
            (paper["id"], slot, status),
        )


def _load_paper_rows() -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                id, title, authors_json, journal, year, doi, url, topics_json,
                evidence_type, abstract_preview, claim, evidence, reasoning
            FROM papers
            ORDER BY year DESC, title ASC
            """
        ).fetchall()
        return [_paper_from_row(conn, row) for row in rows]


def _paper_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    parser_rows = conn.execute(
        "SELECT slot, status FROM parser_status WHERE paper_id = ? ORDER BY slot ASC",
        (row["id"],),
    ).fetchall()
    relation_rows = conn.execute(
        "SELECT relation, target FROM paper_relations WHERE paper_id = ? ORDER BY id ASC",
        (row["id"],),
    ).fetchall()
    return {
        "id": row["id"],
        "title": row["title"],
        "authors": json.loads(row["authors_json"]),
        "journal": row["journal"],
        "year": int(row["year"]),
        "doi": row["doi"],
        "url": row["url"],
        "topics": json.loads(row["topics_json"]),
        "evidenceType": row["evidence_type"],
        "abstractPreview": row["abstract_preview"],
        "claim": row["claim"],
        "evidence": row["evidence"],
        "reasoning": row["reasoning"],
        "parserStatus": {item["slot"]: item["status"] for item in parser_rows},
        "relations": [
            {"source": row["id"], "relation": item["relation"], "target": item["target"]}
            for item in relation_rows
        ],
    }


def _decorate_paper(paper: dict[str, Any]) -> dict[str, Any]:
    citation = _citation(paper)
    evidence_pack = _build_evidence_pack(paper, citation)
    validation = _validate_evidence_pack(evidence_pack)
    professional_interpretation = _build_professional_interpretation(paper, evidence_pack, validation)
    return {
        **paper,
        "authorsText": ", ".join(paper["authors"]),
        "cer": {
            "claim": paper["claim"],
            "evidence": paper["evidence"],
            "reasoning": paper["reasoning"],
            "citation": citation,
        },
        "parserStatus": paper.get("parserStatus") or {},
        "relations": paper.get("relations") or _relations(paper),
        "retrievalScore": paper.get("retrievalScore", 0.0),
        "retrievalBreakdown": paper.get(
            "retrievalBreakdown",
            {"vector": 0.0, "keyword": 0.0, "structured": 0.0, "graph": 0.0, "rerank": 0.0},
        ),
        "metadataDecision": paper.get("metadataDecision", {"accepted": True, "reasons": ["seeded"]}),
        "evidencePack": evidence_pack,
        "validation": validation,
        "professionalInterpretation": professional_interpretation,
    }


def _score_paper(
    paper: dict[str, Any],
    query: str,
    topic: str,
    rewritten_queries: list[str],
) -> dict[str, float]:
    structured = 0.15
    if topic:
        structured += 0.7 if topic in [_normalize(item) for item in paper["topics"]] else 0.0
    if not query:
        return {"vector": 0.0, "keyword": 0.0, "structured": structured, "graph": 0.0, "recall": 1.0 + structured}
    haystack = _normalize(
        " ".join(
            [
                paper["title"],
                paper["journal"],
                paper["abstractPreview"],
                paper["claim"],
                paper["evidence"],
                " ".join(paper["authors"]),
                " ".join(paper["topics"]),
            ]
        )
    )
    keyword = 0.0
    expanded_tokens = " ".join([query, *rewritten_queries]).split()
    for token in expanded_tokens:
        if token in haystack:
            keyword += 0.4
        if token in _normalize(paper["title"]):
            keyword += 0.6
        if token in [_normalize(topic) for topic in paper["topics"]]:
            keyword += 0.8
    vector = max(_cosine_similarity(_hash_vector(item), _hash_vector(haystack)) for item in [query, *rewritten_queries])
    graph = max(_graph_score(paper, item) for item in [query, *rewritten_queries])
    recall = vector * 1.4 + keyword + structured + graph
    return {"vector": vector, "keyword": keyword, "structured": structured, "graph": graph, "recall": recall}


def _relations(paper: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"source": paper["id"], "relation": "has-topic", "target": topic}
        for topic in paper["topics"]
    ]


def _citation(paper: dict[str, Any]) -> str:
    authors = ", ".join(paper["authors"][:2])
    if len(paper["authors"]) > 2:
        authors = f"{authors}, et al."
    return f"{authors}. {paper['title']}. {paper['journal']}, {paper['year']}. DOI: {paper['doi']}"


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").lower().replace("/", " ").replace("-", " ").split())


def _normalize_input_paper(payload: dict[str, Any]) -> dict[str, Any]:
    title = _clean_required(payload.get("title"), "title")
    authors = payload.get("authors") or []
    if not isinstance(authors, list) or not all(_clean_text(item) for item in authors):
        raise ValueError("authors must be a non-empty list of names")
    topics = payload.get("topics") or []
    if not isinstance(topics, list) or not all(_clean_text(item) for item in topics):
        raise ValueError("topics must be a non-empty list")
    paper_id = _clean_text(payload.get("id")) or _slugify(title)
    return {
        "id": paper_id,
        "title": title,
        "authors": [_clean_text(item) for item in authors],
        "journal": _clean_required(payload.get("journal"), "journal"),
        "year": int(payload.get("year") or datetime.now(timezone.utc).year),
        "doi": _clean_text(payload.get("doi")),
        "url": _clean_text(payload.get("url")),
        "topics": [_clean_text(item) for item in topics],
        "evidenceType": _clean_text(payload.get("evidenceType")) or "Manual",
        "abstractPreview": _clean_required(payload.get("abstractPreview"), "abstractPreview"),
        "claim": _clean_required(payload.get("claim"), "claim"),
        "evidence": _clean_required(payload.get("evidence"), "evidence"),
        "reasoning": _clean_required(payload.get("reasoning"), "reasoning"),
    }


def _metadata_prefilter(
    paper: dict[str, Any],
    query: str,
    year_min: int | None,
    year_max: int | None,
    topic: str,
) -> dict[str, Any]:
    reasons: list[str] = []
    if year_min is not None:
        reasons.append(f"year >= {year_min}")
    if year_max is not None:
        reasons.append(f"year <= {year_max}")
    if topic:
        reasons.append("topic matched")
    if query:
        metadata_text = _normalize(
            " ".join(
                [
                    paper["title"],
                    paper["journal"],
                    paper["abstractPreview"],
                    " ".join(paper["topics"]),
                    paper["evidenceType"],
                ]
            )
        )
        matched = [token for token in query.split() if token in metadata_text]
        if matched:
            reasons.append(f"metadata matched: {', '.join(matched[:4])}")
        elif not topic:
            return {"accepted": True, "quality": "low-prior", "reasons": ["no metadata hit; allowed for semantic recall"]}
    return {"accepted": True, "quality": "candidate", "reasons": reasons or ["default candidate"]}


def _rewrite_query(query: str) -> list[str]:
    normalized = _normalize(query)
    if not normalized:
        return []
    rewrites: list[str] = []
    rules = [
        (("严重", "灾害", "破坏", "risk", "hazard"), "震源深度 灾害影响 地震动强度 场地效应"),
        (("为什么", "成因", "构造", "机制", "mechanism"), "发震构造 断层机制 震源机制 应力释放"),
        (("余震", "aftershock", "序列"), "余震活动 序列迁移 b值 风险评估"),
        (("断层", "fault"), "断层类型 走滑 逆冲 正断层 破裂几何"),
        (("四川", "泸定", "盆地"), "四川盆地 龙门山 速度结构 区域构造"),
    ]
    for keywords, rewrite in rules:
        if any(keyword in normalized for keyword in keywords):
            rewrites.append(rewrite)
    if not rewrites:
        rewrites.append(f"{query} 地震机制 证据 文献")
    return list(dict.fromkeys(rewrites))[:4]


def _rerank_score(
    paper: dict[str, Any],
    query: str,
    rewritten_queries: list[str],
    breakdown: dict[str, float],
) -> float:
    title = _normalize(paper["title"])
    claim = _normalize(paper["claim"])
    query_text = _normalize(" ".join([query, *rewritten_queries]))
    title_overlap = _token_overlap(query_text, title)
    claim_overlap = _token_overlap(query_text, claim)
    evidence_strength = 0.2 if paper.get("evidence") and paper.get("claim") else 0.0
    recency = min(max((int(paper["year"]) - 2015) / 10, 0.0), 1.0) * 0.1
    return breakdown["recall"] + title_overlap * 0.9 + claim_overlap * 0.6 + evidence_strength + recency


def _build_evidence_pack(paper: dict[str, Any], citation: str) -> dict[str, Any]:
    confidence = _confidence_score(paper)
    return {
        "claim": paper["claim"],
        "evidence": [
            {
                "text": paper["evidence"],
                "source": paper["title"],
                "locator": "CER:evidence",
                "confidence": confidence,
            },
            {
                "text": paper["abstractPreview"],
                "source": paper["title"],
                "locator": "abstract",
                "confidence": round(max(confidence - 0.08, 0.0), 2),
            },
        ],
        "citation": citation,
        "confidence": confidence,
        "unsupported": confidence < 0.45,
    }


def _validate_evidence_pack(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    claim = _normalize(evidence_pack.get("claim"))
    evidence_text = _normalize(" ".join(item.get("text", "") for item in evidence_pack.get("evidence", [])))
    grounding = _token_overlap(claim, evidence_text)
    citation_ok = bool(evidence_pack.get("citation"))
    unsafe_terms = ("一定", "必然", "肯定", "绝对", "确定会", "必定")
    over_prediction = any(term in str(evidence_pack.get("claim", "")) for term in unsafe_terms)
    return {
        "grounding": round(grounding, 3),
        "citationRelevant": citation_ok,
        "safety": "review" if over_prediction else "pass",
        "overPrediction": over_prediction,
        "passed": grounding > 0.05 and citation_ok and not over_prediction and not evidence_pack.get("unsupported"),
    }


def _build_professional_interpretation(
    paper: dict[str, Any],
    evidence_pack: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    topics = paper.get("topics", [])
    topic_text = "、".join(topics[:3]) if topics else "地震学研究"
    confidence = evidence_pack.get("confidence", 0.0)
    validation_text = "证据支持度较好" if validation.get("passed") else "仍需人工复核"
    return {
        "headline": f"{paper['title']} 的地震专业解读",
        "summary": (
            f"该文献主要服务于“{topic_text}”方向，可作为论文知识库中用于回答机制解释、"
            f"监测方法或风险研判问题的证据来源。当前 Evidence Pack 置信度为 {confidence:.2f}，"
            f"{validation_text}。"
        ),
        "coreConclusion": paper["claim"],
        "regionalApplicability": (
            f"当前更适合用于 {topic_text} 相关问题的文献 grounding。若用于其他区域或不同构造背景，"
            "应先确认研究区、数据来源和构造环境是否具有可比性。"
        ),
        "citationGuidance": (
            "适合在“已有研究表明”“文献证据支持”“摘要级综述指出”这类表述中引用；"
            "不适合直接写成确定性的灾害预测或短期演化结论。"
        ),
        "methodLimitations": (
            "当前数据库中的解读仍以摘要、手工 CER 和轻量关系抽取为主，尚未完全纳入图表、表格、公式与全文上下文。"
        ),
        "bestForQuestions": _best_for_questions(paper),
        "notSupportedConclusions": _not_supported_conclusions(paper),
        "sections": [
            {
                "title": "研究问题定位",
                "content": (
                    f"从标题、摘要和主题关系看，这篇论文更适合被放入 {topic_text} 的检索分支，"
                    "用于先定位相关研究，再下钻到具体证据块。"
                ),
            },
            {
                "title": "可支撑的专业判断",
                "content": paper["claim"],
            },
            {
                "title": "关键证据",
                "content": paper["evidence"],
            },
            {
                "title": "推理链条",
                "content": paper["reasoning"],
            },
            {
                "title": "适用边界",
                "content": (
                    "该解读只能说明论文证据与问题之间的支持关系，不应被直接扩展为确定性灾害预测。"
                    "涉及强余震、灾害损失或确定性趋势时，需要结合实时台网、震源机制和现场调查。"
                ),
            },
        ],
        "recommendedUse": ["机制解释", "证据引用", "检索扩展", "专业问答 grounding"],
        "uncertainty": "摘要级和手工 CER 证据仍需全文、图表、公式和表格解析结果进一步增强。",
    }


def _best_for_questions(paper: dict[str, Any]) -> list[str]:
    topics = {_normalize(topic) for topic in paper.get("topics", [])}
    questions: list[str] = []
    if {"地震预警", "震相拾取", "自动化处理"} & topics:
        questions.extend(
            [
                "这类方法适合解决什么监测任务？",
                "论文中的方法为什么比传统规则更稳健？",
            ]
        )
    if {"四川盆地", "层析成像", "速度结构"} & topics:
        questions.extend(
            [
                "这个区域的构造背景和速度结构有什么关系？",
                "研究结果如何支撑断层或盆山耦合解释？",
            ]
        )
    if {"余震序列", "活动性分析", "b值"} & topics:
        questions.extend(
            [
                "余震活动最值得关注哪些指标？",
                "序列演化能否为后续风险判断提供支持？",
            ]
        )
    if {"强震动", "危险性评估", "山区地震"} & topics:
        questions.extend(
            [
                "为什么同样震级在不同地区会有不同影响？",
                "场地与地形因素在风险分析里如何进入解释？",
            ]
        )
    if not questions:
        questions.extend(
            [
                "这篇论文最适合支撑哪一类地震学判断？",
                "它的证据更偏向机制解释还是风险分析？",
            ]
        )
    return questions[:4]


def _not_supported_conclusions(paper: dict[str, Any]) -> list[str]:
    statements = [
        "不能仅凭这篇论文直接得出短期一定会发生强余震的结论。",
        "不能把摘要级证据直接外推为确定性的灾害损失预测。",
    ]
    if "地震预警" in paper.get("topics", []):
        statements.append("不能把方法论文的模型效果直接视为所有台网环境下都稳定成立。")
    if "四川盆地" in paper.get("topics", []):
        statements.append("不能把区域结构解释无条件外推到其他构造区。")
    return statements[:4]


def _confidence_score(paper: dict[str, Any]) -> float:
    has_citation = 0.2 if paper.get("doi") or paper.get("url") else 0.0
    has_evidence = 0.35 if paper.get("evidence") else 0.0
    has_reasoning = 0.25 if paper.get("reasoning") else 0.0
    has_relations = min(len(paper.get("relations", [])) * 0.03, 0.15)
    return round(min(0.25 + has_citation + has_evidence + has_reasoning + has_relations, 0.98), 2)


def _token_overlap(left: str, right: str) -> float:
    left_tokens = set(TOKEN_RE.findall(_normalize(left)))
    right_tokens = set(TOKEN_RE.findall(_normalize(right)))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens)


def _clean_required(value: Any, field: str) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        raise ValueError(f"{field} is required")
    return cleaned


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", value.lower()).strip("-")
    digest = sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"paper-{normalized[:48]}-{digest}" if normalized else f"paper-{digest}"


def _hash_vector(text: str) -> list[float]:
    vector = [0.0] * VECTOR_DIMENSIONS
    for token in TOKEN_RE.findall(_normalize(text)):
        bucket = int(sha256(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIMENSIONS
        vector[bucket] += 1.0
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return vector
    return [value / magnitude for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _graph_score(paper: dict[str, Any], query: str) -> float:
    relation_targets = [_normalize(item.get("target")) for item in paper.get("relations", [])]
    if not relation_targets:
        relation_targets = [_normalize(item) for item in paper.get("topics", [])]
    score = 0.0
    for token in query.split():
        if any(token in target for target in relation_targets):
            score += 0.35
    return score


def _count_rows(table: str) -> int:
    with _connect() as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _database_path() -> Path:
    return Path(settings.paper_database_path)
