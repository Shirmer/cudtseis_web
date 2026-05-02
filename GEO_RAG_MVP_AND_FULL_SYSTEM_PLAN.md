# 地质学文献知识库与高级 RAG 系统阶段规划

> 本文档用于指导“地质学文献知识库与高级 RAG 系统”的阶段性开发。  
> 项目分为两个大阶段：  
> - **第一阶段：MVP 最小可行系统**  
> - **第二阶段：完整系统升级**  
>
> 核心目标不是做一个普通问答机器人，而是建设一个面向地质学领域的、可追溯、可审查、可扩展的文献知识库系统。

---

## 0. 项目总目标

本项目的最终目标是建设一个面向地质学领域的高级 RAG 系统，使系统能够提前收集、解析、索引和管理大量地质学文献，并将这些文献作为地震目录分析、论文问答、地质知识问答和证据链展示的基础。

系统最终应支持：

1. 地质学论文 PDF 入库。
2. 多模态文档解析，包括正文、图、表、公式、页码和位置信息。
3. 统一 KnowledgeUnit 知识单元建模。
4. PostgreSQL/PostGIS 管理结构化业务数据。
5. Qdrant 管理向量索引。
6. 基于 Evidence Pack 的证据驱动问答。
7. 地震事件与文献知识库结合分析。
8. 回答引用来源、页码、证据片段和不确定性说明。
9. 后续支持 Claim verification、图表问答、知识图谱和云端部署。

一句话概括：

```text
提前建设地质学文献知识库，让地震目录分析和论文问答都基于统一的向量数据库和证据链完成。
```

---

# 第一部分：第一阶段 MVP 规划

## 1. MVP 阶段定位

第一阶段不追求完整系统，也不追求大规模自动化，而是先完成一条最核心、最小、可展示、可扩展的闭环：

```text
20-50 篇开放获取地质学 PDF
  -> 本地入库
  -> 文本解析
  -> KnowledgeUnit 标准化
  -> PostgreSQL 保存元数据
  -> Qdrant 保存向量
  -> 论文问答
  -> 地震事件分析
  -> 返回引用、页码、证据和不确定性
```

MVP 的核心价值在于证明：

1. 论文可以被解析成可检索知识单元。
2. 知识单元可以进入 Qdrant。
3. 系统可以从文献库召回相关证据。
4. 大模型可以基于证据生成回答。
5. 回答能够返回引用来源，而不是凭空生成。
6. 地震事件分析可以基于文献证据，而不是仅依赖大模型常识。

---

## 2. MVP 不做的事情

为了保证第一阶段能落地，MVP 明确不做以下内容：

```text
1. 不做全网自动大规模论文爬取。
2. 不做完整知识图谱。
3. 不做复杂多模态图像理解。
4. 不做所有地质学方向全覆盖。
5. 不做云端生产级部署。
6. 不做复杂用户权限系统。
7. 不做完整自动科研报告生成。
8. 不做完全自动 Claim verification。
9. 不做实时联网学术搜索。
10. 不要求第一版 PDF 图表解析完全准确。
```

MVP 只做最关键的闭环：

```text
PDF 文本入库
  -> 向量检索
  -> 证据组织
  -> 大模型基于证据回答
  -> 引用返回
  -> 不确定性说明
```

---

## 3. MVP 展示场景

### 3.1 论文问答

用户选择某篇论文后提问：

```text
这篇论文主要研究了哪个断裂带？主要结论是什么？
```

系统应回答：

```text
该论文主要讨论了 XX 区域的 XX 断裂带活动性。
根据第 6 页和第 8 页的证据，作者认为该区域的地震活动可能与晚第四纪断裂活动有关。

证据：
1. Paper A, page 6, Results
2. Paper A, page 8, Figure caption

不确定性：
该论文主要基于地貌和地震目录分析，缺少震源机制约束，因此不能单独确定断层运动方式。
```

---

### 3.2 全库问答

用户提问：

```text
活动断裂和地震危险性之间有什么关系？
```

系统从已经入库的 20-50 篇文献中召回相关证据，并生成带引用的回答。

---

### 3.3 地震事件分析

用户在地震目录中点击某个事件：

```text
震级：M 5.6
深度：10 km
位置：某区域
时间：某日期
```

系统基于事件参数构造检索查询，从文献知识库中召回证据，然后回答：

```text
根据当前知识库，该区域附近研究较多的是 XX 断裂带。
已有文献显示该区域处于 XX 构造背景下，历史上存在中强地震活动。

但仅凭震级、深度和位置，不能确定该事件一定由某条断裂触发。
需要结合震源机制、余震分布、InSAR/GNSS 数据进一步判断。
```

---

## 4. MVP 总体架构

```text
                  PDF 文献
                    |
                    v
              document_ingest.py
                    |
                    v
             PDF 文本解析 / 切分
                    |
                    v
              KnowledgeUnit
                    |
          +---------+----------+
          |                    |
          v                    v
   PostgreSQL/PostGIS        Qdrant
   论文、文档、事件、任务      文本向量、payload
          |                    |
          +---------+----------+
                    |
                    v
              FastAPI RAG 服务
                    |
        +-----------+------------+
        |                        |
        v                        v
    论文问答接口             地震事件分析接口
        |                        |
        +-----------+------------+
                    |
                    v
                  Vue 前端
```

---

## 5. MVP 技术选型

| 模块 | MVP 选择 |
|---|---|
| 后端 | FastAPI |
| 前端 | Vue 3 + Vite + Naive UI |
| 主数据库 | PostgreSQL + PostGIS |
| 向量数据库 | Qdrant |
| 文档解析 | 第一版使用基础 PDF 文本解析，后续替换为 MinerU/RAGAnything |
| Embedding | 大模型 Embedding API |
| 回答生成 | 大模型 Chat API |
| 证据组织 | Evidence Pack |
| 输出控制 | JSON 格式返回 |
| 文件存储 | 本地文件夹，使用 storage_uri 抽象 |
| 初始文献规模 | 20-50 篇开放获取地质学 PDF |

---

## 6. MVP 核心数据模型

### 6.1 Paper

论文元数据。

```python
class Paper:
    paper_id: str
    title: str
    authors: list[str]
    year: int | None
    doi: str | None
    source_url: str | None
    license: str | None
    created_at: datetime
```

`paper_id` 生成优先级：

```text
DOI
  -> arXiv ID
  -> OpenAlex ID
  -> Semantic Scholar ID
  -> title + year + first_author hash
```

示例：

```text
doi_10_1785_0120230012
titlehash_2024_zhang_a8f31c
```

---

### 6.2 Document

每一个 PDF 文件对应一个 Document。

```python
class Document:
    document_id: str
    paper_id: str
    file_uri: str
    file_sha256: str
    parser: str
    parser_version: str | None
    parse_status: str
    parse_error: str | None
    created_at: datetime
```

`parse_status`：

```text
pending
processing
completed
failed
```

---

### 6.3 KnowledgeUnit

KnowledgeUnit 是 MVP 最核心的数据结构。

第一版可以只支持正文 text，但字段要为后续图、表、公式预留。

```python
class KnowledgeUnit:
    unit_id: str
    paper_id: str
    document_id: str
    content_type: str
    title: str
    text: str
    section: str | None
    page: int | None
    bbox: list[float] | None
    doi: str | None
    year: int | None
    authors: list[str]
    topics: list[str]
    region: list[str]
    fault: list[str]
    parser: str
    embedding_model: str
    index_version: str
```

`unit_id` 示例：

```text
doi_10_1785_0120230012:text:p12:c003
doi_10_1785_0120230012:figure:p08:f001
doi_10_1785_0120230012:table:p10:t001
```

MVP 阶段先只生成：

```text
{paper_id}:text:p{page}:c{chunk_index}
```

---

### 6.4 Evidence Pack

Evidence Pack 是 RAG 回答前的证据组织结构。

```json
{
  "question": "该区域构造背景是什么？",
  "mode": "event_analysis",
  "evidence": [
    {
      "unit_id": "doi_xxx:text:p6:c2",
      "paper_id": "doi_xxx",
      "title": "Example Paper",
      "year": 2023,
      "page": 6,
      "section": "Results",
      "text": "The region is located near an active fault zone...",
      "score": 0.86
    }
  ],
  "missing_evidence": [
    "No focal mechanism evidence found."
  ],
  "uncertainty": [
    "Cannot determine fault type based only on magnitude and location."
  ]
}
```

---

## 7. MVP 数据库设计

### 7.1 PostgreSQL 表

MVP 阶段建议建立 6 张核心表：

```text
papers
  id
  paper_id
  title
  authors_json
  year
  doi
  source_url
  license
  created_at

documents
  id
  document_id
  paper_id
  file_uri
  file_sha256
  parser
  parser_version
  parse_status
  parse_error
  created_at

knowledge_units
  id
  unit_id
  paper_id
  document_id
  content_type
  section
  page
  bbox_json
  text_preview
  qdrant_point_id
  embedding_model
  index_version
  created_at

events
  id
  event_id
  time
  magnitude
  depth
  latitude
  longitude
  place
  source

rag_runs
  id
  run_id
  question
  mode
  event_id
  paper_id
  answer_json
  evidence_json
  validation_json
  created_at

ingest_jobs
  id
  job_id
  document_id
  status
  error
  started_at
  finished_at
```

---

### 7.2 Qdrant Collection

MVP collection：

```text
geo_knowledge_v1
```

Qdrant payload：

```json
{
  "unit_id": "doi_xxx:text:p12:c003",
  "paper_id": "doi_xxx",
  "document_id": "doi_xxx_v1",
  "content_type": "text",
  "title": "Example Paper",
  "section": "Results",
  "page": 12,
  "doi": "10.xxxx/xxxx",
  "year": 2024,
  "topics": ["earthquake", "fault"],
  "region": ["Sichuan Basin"],
  "fault": ["Longmenshan Fault"],
  "embedding_model": "text-embedding-3-small",
  "index_version": "geo-rag-v1"
}
```

MVP 建议创建 payload index：

```text
paper_id
document_id
content_type
year
region
fault
index_version
```

---

## 8. MVP 后端目录结构

建议后端扩展为：

```text
backend/app/
  main.py

  core/
    config.py
    logging.py

  db/
    session.py
    models.py

  schemas/
    knowledge.py
    rag.py
    document.py
    paper.py

  services/
    paper_service.py
    document_service.py
    ingest_service.py
    embedding_service.py
    qdrant_service.py
    rag_service.py
    evidence_service.py
    event_analysis_service.py

  routers/
    papers.py
    documents.py
    knowledge.py
    rag.py
    events.py

  scripts/
    init_qdrant.py
    ingest_demo_papers.py
    rebuild_index.py
```

---

## 9. MVP API 设计

### 9.1 文献管理

#### POST `/api/papers`

创建论文元数据。

请求：

```json
{
  "title": "Example Paper",
  "authors": ["Author A", "Author B"],
  "year": 2024,
  "doi": "10.xxxx/xxxx",
  "source_url": "https://..."
}
```

返回：

```json
{
  "paper_id": "doi_10_xxxx_xxxx"
}
```

---

#### GET `/api/papers`

获取论文列表。

---

#### GET `/api/papers/{paper_id}`

获取论文详情。

---

### 9.2 文档入库

#### POST `/api/documents/ingest`

上传或指定 PDF 入库。

请求：

```json
{
  "paper_id": "doi_10_xxxx_xxxx",
  "file_uri": "local://papers/example.pdf"
}
```

返回：

```json
{
  "job_id": "job_xxx",
  "document_id": "doi_10_xxxx_xxxx_v1",
  "status": "pending"
}
```

---

#### GET `/api/documents/{document_id}/status`

查看解析状态。

返回：

```json
{
  "document_id": "doi_10_xxxx_xxxx_v1",
  "parse_status": "completed",
  "unit_count": 128,
  "error": null
}
```

---

### 9.3 知识检索

#### POST `/api/knowledge/search`

请求：

```json
{
  "query": "active fault seismicity",
  "filters": {
    "paper_id": "doi_10_xxxx_xxxx",
    "content_type": "text"
  },
  "top_k": 8
}
```

返回：

```json
{
  "results": [
    {
      "unit_id": "doi_xxx:text:p6:c2",
      "paper_id": "doi_xxx",
      "title": "Example Paper",
      "page": 6,
      "section": "Results",
      "text": "...",
      "score": 0.84
    }
  ]
}
```

---

### 9.4 论文问答

#### POST `/api/rag/papers/query`

请求：

```json
{
  "question": "这篇论文的主要结论是什么？",
  "paper_id": "doi_10_xxxx_xxxx",
  "top_k": 8
}
```

返回：

```json
{
  "answer": "...",
  "citations": [
    {
      "unit_id": "doi_xxx:text:p6:c2",
      "paper_id": "doi_xxx",
      "title": "Example Paper",
      "page": 6,
      "section": "Results",
      "text": "..."
    }
  ],
  "uncertainty": [
    "该结论主要来自单篇论文，需要更多研究交叉验证。"
  ]
}
```

---

### 9.5 地震事件分析

#### POST `/api/events/{event_id}/geo-analysis`

请求：

```json
{
  "question": "分析这个地震事件的构造背景和可能相关断裂。"
}
```

返回：

```json
{
  "event": {
    "event_id": "xxx",
    "magnitude": 5.6,
    "depth": 10,
    "place": "xxx"
  },
  "answer": "...",
  "evidence": [],
  "uncertainty": [
    "仅凭震级、深度和位置不能确定发震断层。",
    "当前知识库未找到该事件的震源机制资料。"
  ]
}
```

---

## 10. MVP RAG 流程

```text
用户问题
  -> 判断模式：论文问答 / 全库问答 / 地震事件分析
  -> 构造检索 query
  -> 生成 embedding
  -> Qdrant 检索
  -> PostgreSQL 补充元数据
  -> 组织 Evidence Pack
  -> 调用大模型生成回答
  -> 返回 answer + citations + uncertainty
  -> 记录 rag_runs
```

大模型 Prompt 基本原则：

```text
1. 只能基于给定 Evidence Pack 回答。
2. 如果证据不足，必须说明不足。
3. 不能编造论文、作者、页码、断裂名称。
4. 不能仅凭震级和位置断定发震断层。
5. 所有核心结论必须引用 evidence_id。
6. 地震、灾害和断裂判断必须保持保守。
```

---

## 11. MVP 前端页面

### 11.1 论文列表页

展示字段：

```text
标题
作者
年份
DOI
解析状态
入库状态
问答按钮
```

状态标签：

```text
未入库
解析中
已入库
解析失败
```

---

### 11.2 论文问答页

布局：

```text
左侧：论文信息 / 文献目录
右侧：问答窗口
下方：证据卡片
```

证据卡片显示：

```text
论文标题
年份
页码
章节
相关片段
相似度分数
unit_id
```

---

### 11.3 地震事件分析页

在已有地震事件详情页增加：

```text
AI 地质分析按钮
```

点击后展示：

```text
构造背景
可能相关断裂
历史相似事件
文献证据
不确定性说明
```

---

## 12. MVP 六周开发路线

### 第 1 周：清理项目与确定 schema

目标：把知识库地基定下来。

任务：

```text
1. 清理 Agent-RAG 目录。
2. 增加 .gitignore。
3. 定义 KnowledgeUnit schema。
4. 定义 paper_id / document_id / unit_id 规则。
5. 建 PostgreSQL 表。
6. 写 schema 文档。
```

交付物：

```text
backend/app/schemas/knowledge.py
backend/app/db/models.py
docs/knowledge_schema.md
docs/id_rules.md
```

验收标准：

```text
能创建 paper。
能创建 document。
能创建 knowledge_unit 记录。
ID 规则稳定。
```

---

### 第 2 周：接入 Qdrant 与 demo 检索

目标：先不管 PDF，手动写入 demo 知识块，证明检索可用。

任务：

```text
1. 增加 Qdrant docker-compose。
2. 写 init_qdrant.py。
3. 写 qdrant_service.py。
4. 写 embedding_service.py。
5. 准备 10 条 demo KnowledgeUnit。
6. 写入 Qdrant。
7. 实现 /api/knowledge/search。
```

交付物：

```text
docker-compose.qdrant.yml
backend/app/services/qdrant_service.py
backend/app/services/embedding_service.py
backend/app/scripts/init_qdrant.py
backend/app/routers/knowledge.py
```

验收标准：

```text
Qdrant 可启动。
collection 可创建。
demo 知识块可写入。
输入 query 能返回相关片段。
支持 paper_id filter。
```

---

### 第 3 周：PDF 入库闭环

目标：让 1 篇 PDF 能完整入库。

任务：

```text
1. 准备 3-5 篇开放获取 PDF。
2. 写 document_ingest.py。
3. 提取 PDF 文本。
4. 切分 chunk。
5. 生成 KnowledgeUnit。
6. 写 PostgreSQL。
7. 写 Qdrant。
8. 记录 parse_status。
```

交付物：

```text
backend/app/services/ingest_service.py
backend/app/routers/documents.py
backend/app/scripts/ingest_demo_papers.py
```

验收标准：

```text
指定一个 PDF：
  -> documents 记录 created
  -> parse_status 从 pending 到 completed
  -> knowledge_units 生成
  -> Qdrant 有对应 point
  -> 可以按 paper_id 搜到内容
```

---

### 第 4 周：论文问答

目标：完成第一个真正 RAG 功能。

任务：

```text
1. 实现 /api/rag/papers/query。
2. 检索 Qdrant。
3. 组织 Evidence Pack。
4. 调用大模型生成 answer。
5. 返回 citations。
6. 前端做论文问答页面。
7. 保存 rag_runs。
```

交付物：

```text
backend/app/services/rag_service.py
backend/app/services/evidence_service.py
backend/app/routers/rag.py
frontend paper QA 页面
```

验收标准：

```text
选择一篇论文。
输入问题。
系统只基于该论文回答。
回答包含引用片段。
引用包含 page / section / unit_id。
证据不足时能说明不足。
```

---

### 第 5 周：地震事件分析

目标：把 RAG 和已有地震目录模块连接起来。

任务：

```text
1. 实现 /api/events/{event_id}/geo-analysis。
2. 从事件读取地点、震级、深度、时间。
3. 构造地质学检索 query。
4. 检索相关 KnowledgeUnit。
5. 生成分析回答。
6. 返回 evidence 和 uncertainty。
7. 前端地震详情页增加 AI 分析区。
```

交付物：

```text
backend/app/services/event_analysis_service.py
backend/app/routers/events.py
frontend event detail analysis panel
```

验收标准：

```text
点击地震事件。
点击“生成地质分析”。
返回构造背景。
返回相关证据。
返回不确定性。
不会断言“必然由某断裂造成”。
```

---

### 第 6 周：质量评估与演示打磨

目标：让项目能稳定演示。

任务：

```text
1. 准备 30 个测试问题。
2. 手工标注期望证据。
3. 测试论文问答。
4. 测试地震事件分析。
5. 加错误处理。
6. 加 loading / failed / retry 状态。
7. 写 README MVP 使用说明。
8. 录制演示流程。
```

验收指标：

```text
能否召回相关文献。
回答是否基于证据。
引用是否真实。
是否出现编造论文。
是否过度推断地震风险。
页面是否能顺畅演示。
```

---

## 13. MVP 最终验收清单

MVP 完成时，至少满足：

```text
1. 能启动后端、前端、PostgreSQL、Qdrant。
2. 能录入 20 篇左右地质学 PDF。
3. 每篇 PDF 能生成 KnowledgeUnit。
4. KnowledgeUnit 能写入 PostgreSQL。
5. 向量能写入 Qdrant。
6. 可以按 paper_id 检索。
7. 可以全库检索。
8. 论文问答能返回答案。
9. 答案包含引用证据。
10. 引用包含 page / unit_id / paper_id。
11. 地震事件详情页能生成地质分析。
12. 分析包含不确定性。
13. 系统不会编造论文和页码。
14. 解析失败有错误状态。
15. README 能让别人跑起来。
```

---

# 第二部分：第二阶段完整系统规划

## 14. 第二阶段定位

第二阶段是在 MVP 成功之后，将系统升级为真正可扩展、可维护、可审查的地质学文献知识库与高级 RAG 平台。

第二阶段的目标是：

```text
从“小规模文本 RAG demo”
升级为
“可扩展的地质学多模态知识库系统”
```

第二阶段重点包括：

1. 大规模文献采集。
2. 更可靠的 PDF 多模态解析。
3. 图、表、公式入库。
4. Hybrid Search。
5. Reranker。
6. Evidence Pack 强化。
7. Claim verification。
8. 地质专业字段抽取。
9. PDF 页码和 bbox 定位。
10. 云端迁移。
11. 权限与版权管理。
12. 自动评估体系。
13. 前端证据链与知识图谱展示。

---

## 15. 完整系统总体架构

```text
                    +----------------------+
                    |  地质学 PDF / 文献源  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | 文献采集与去重系统    |
                    | OpenAlex/Crossref等  |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | RAGAnything / MinerU |
                    | 文档、多模态解析       |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | KnowledgeUnit Adapter|
                    | 统一数据结构转换       |
                    +----------+-----------+
                               |
        +----------------------+----------------------+
        |                                             |
        v                                             v
+-------------------+                       +-------------------+
| PostgreSQL/PostGIS|                       |      Qdrant        |
| 结构化元数据       |                       | 向量检索知识块      |
+-------------------+                       +-------------------+
        |                                             |
        +----------------------+----------------------+
                               |
                               v
                    +----------------------+
                    |      FastAPI         |
                    | 检索、证据、回答、校验 |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    |      Vue 前端        |
                    | 地震目录 / 论文问答   |
                    +----------------------+
```

---

## 16. 第二阶段核心升级模块

## 16.1 文献采集系统

第二阶段需要从手动上传 PDF，升级为半自动文献采集。

推荐来源：

```text
OpenAlex
Crossref
Semantic Scholar
arXiv
EarthArXiv
开放获取期刊
机构知识库
团队手动上传 PDF
```

文献采集流程：

```text
输入主题范围
  -> 检索元数据
  -> 去重
  -> 判断是否开放获取
  -> 下载 PDF 或仅保存元数据
  -> 保存 Paper 记录
  -> 创建 Document 记录
  -> 创建解析任务
```

需要注意：

```text
1. 优先收集开放获取文献。
2. 非开放获取文献只存团队合法获取的本地 PDF。
3. 云端部署时必须区分公开可用文件和内部授权文件。
4. 每篇文献必须保存 license 和 access_level。
```

---

## 16.2 多模态文档解析系统

MVP 阶段只做文本解析，第二阶段要接入 RAGAnything / MinerU / Docling 等能力。

目标支持：

```text
正文
章节标题
图像
图注
表格
公式
页码
bbox
图片路径
表格结构
公式 LaTeX
附近正文关联
```

解析输出需要转换为统一 KnowledgeUnit。

不同内容类型：

```text
text
figure
table
equation
claim
method
dataset
limitation
```

图表 KnowledgeUnit 示例：

```json
{
  "unit_id": "doi_xxx:figure:p08:f001",
  "paper_id": "doi_xxx",
  "content_type": "figure",
  "text": "Figure 3 shows focal mechanism solutions near the active fault...",
  "caption": "Figure 3. Focal mechanisms...",
  "image_uri": "local://papers/doi_xxx/images/fig_003.jpg",
  "page": 8,
  "bbox": [80, 120, 520, 420],
  "related_unit_ids": [
    "doi_xxx:text:p08:c002"
  ]
}
```

表格 KnowledgeUnit 示例：

```json
{
  "unit_id": "doi_xxx:table:p10:t001",
  "paper_id": "doi_xxx",
  "content_type": "table",
  "text": "This table summarizes earthquake parameters...",
  "caption": "Table 2. Earthquake catalog used in this study.",
  "table_markdown": "| Event | Magnitude | Depth | ... |",
  "page": 10,
  "bbox": [72, 130, 520, 430]
}
```

公式 KnowledgeUnit 示例：

```json
{
  "unit_id": "doi_xxx:equation:p06:e002",
  "paper_id": "doi_xxx",
  "content_type": "equation",
  "text": "The equation describes seismic moment magnitude relation.",
  "latex": "M_w = \\frac{2}{3}\\log_{10}(M_0) - 6.07",
  "page": 6,
  "bbox": [100, 200, 480, 240]
}
```

---

## 16.3 KnowledgeUnit Adapter

第二阶段应重点建设：

```text
RAGAnything / MinerU Output
  -> normalize
  -> enrich
  -> validate
  -> KnowledgeUnit
  -> PostgreSQL
  -> Qdrant
```

Adapter 需要完成：

```text
1. 内容类型识别。
2. 页码转换。
3. bbox 标准化。
4. 图片路径转换。
5. 表格结构保存。
6. 图表与附近正文关联。
7. 地质专业字段抽取。
8. ID 生成。
9. parser_version 记录。
10. 解析质量检查。
```

---

## 16.4 地质专业字段抽取

第二阶段需要从 KnowledgeUnit 中抽取地质领域字段。

建议字段：

```text
region
fault
tectonic_setting
earthquake_name
magnitude
depth
focal_mechanism
hazard_type
monitoring_method
geological_period
stratigraphy
lithology
geochemistry
remote_sensing_method
```

抽取方式：

```text
规则词典
  + NER 模型
  + LLM 信息抽取
  + 人工校验
```

字段用途：

```text
1. 用于 Qdrant metadata filter。
2. 用于地震事件分析。
3. 用于文献筛选。
4. 用于前端标签展示。
5. 用于知识图谱建设。
```

---

## 16.5 Hybrid Search

MVP 阶段使用 dense vector + metadata filter。第二阶段应升级为 Hybrid Search。

推荐检索组合：

```text
Dense semantic search
  + Sparse keyword search
  + Metadata filter
  + Reranker
  + Diversity control
```

原因：

地质学中有大量专有名词和地名：

```text
Longmenshan Fault
Wenchuan earthquake
Sichuan Basin
focal mechanism
strike-slip fault
normal fault
thrust fault
```

只靠 dense embedding 可能漏召回，所以需要加入 sparse keyword search。

第二阶段检索流程：

```text
用户问题
  -> query rewrite
  -> 领域实体抽取
  -> metadata filter 生成
  -> dense search top 50
  -> sparse search top 50
  -> RRF 融合
  -> rerank top 20
  -> 去重
  -> Evidence Pack top 8-12
```

---

## 16.6 Reranker

Reranker 用于提高最终进入 Evidence Pack 的证据质量。

第一版可用 LLM rerank。

第二阶段建议改为：

```text
bge-reranker
jina-reranker
cohere-rerank
自部署 cross-encoder reranker
```

Reranker 输入：

```json
{
  "query": "该区域构造背景是什么？",
  "candidates": [
    {
      "unit_id": "...",
      "text": "..."
    }
  ]
}
```

输出：

```json
{
  "ranked_results": [
    {
      "unit_id": "...",
      "rerank_score": 0.92
    }
  ]
}
```

---

## 16.7 Evidence Pack 强化

第二阶段 Evidence Pack 不只保存 chunk，还要保存 claim 与 evidence 的关系。

结构示例：

```json
{
  "question": "该区域地震活动与活动断裂有什么关系？",
  "claims": [
    {
      "claim_id": "claim_001",
      "claim": "该区域地震活动可能与活动断裂带有关。",
      "evidence": [
        {
          "unit_id": "doi_xxx:text:p6:c2",
          "support_type": "direct",
          "confidence": 0.86
        }
      ],
      "uncertainty": "需要结合震源机制和余震序列进一步确认。"
    }
  ],
  "missing_evidence": [
    "No focal mechanism data found."
  ]
}
```

---

## 16.8 Claim Verification

第二阶段必须加入回答后校验。

流程：

```text
生成回答
  -> 抽取核心 Claim
  -> 对每个 Claim 寻找证据
  -> 判断 Evidence 是否支持 Claim
  -> 检查 Citation 是否存在
  -> 检查是否存在过度推断
  -> 输出 Validation Report
```

Validation Report：

```json
{
  "passed": false,
  "warnings": [
    "Claim about fault type is weakly supported."
  ],
  "unsupported_claims": [
    {
      "claim": "该地震一定由 XX 断裂触发。",
      "reason": "No focal mechanism or rupture evidence found."
    }
  ],
  "confidence": 0.67
}
```

特别需要检查：

```text
1. 是否没有证据却判断发震断层。
2. 是否仅凭震级判断灾害严重性。
3. 是否把某篇论文局部结论推广到所有区域。
4. 是否编造不存在的引用。
5. 是否对未来地震趋势做过度预测。
```

---

## 16.9 前端证据链升级

第二阶段前端应支持：

```text
1. 回答正文。
2. 引用卡片。
3. 点击证据跳转 PDF 页码。
4. bbox 高亮。
5. 图表预览。
6. 表格预览。
7. 公式展示。
8. Evidence Pack 展开。
9. Validation Report 展示。
10. 不确定性标签。
```

论文问答页面升级为：

```text
左侧：PDF 阅读器
中间：问答区
右侧：证据链 / 图表 / 验证报告
```

地震事件分析页面升级为：

```text
地图 + 事件参数
构造背景
相关断裂
历史相似事件
文献证据
不确定性说明
验证报告
```

---

## 16.10 云端迁移

第二阶段需要将本地系统迁移到云端。

推荐抽象：

```text
PostgreSQL 本地 -> 云 PostgreSQL
Qdrant 本地 -> Qdrant Cloud / 自部署 Qdrant
本地文件夹 -> MinIO / S3 / OSS / COS
```

环境变量：

```env
DATABASE_URL=postgresql+psycopg://...
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=
OBJECT_STORAGE_PROVIDER=local
OBJECT_STORAGE_ROOT=./.data/files
EMBEDDING_MODEL=text-embedding-3-small
INDEX_VERSION=geo-rag-v1
```

文件 URI 抽象：

```text
local://papers/xxx.pdf
s3://bucket/papers/xxx.pdf
oss://bucket/papers/xxx.pdf
minio://geo-rag/papers/xxx.pdf
```

迁移原则：

```text
1. Git 只存源码、schema、脚本和文档。
2. 不提交向量库数据。
3. 不提交 PDF 大文件。
4. 不提交本地解析输出。
5. 云端通过入库脚本重建或同步数据库。
```

---

## 17. 第二阶段数据库扩展

在 MVP 表基础上扩展：

```text
paper_sources
  source_id
  paper_id
  source_type
  source_url
  license
  is_open_access

figures
  figure_id
  paper_id
  document_id
  unit_id
  image_uri
  caption
  page
  bbox

tables
  table_id
  paper_id
  document_id
  unit_id
  caption
  table_markdown
  page
  bbox

equations
  equation_id
  paper_id
  document_id
  unit_id
  latex
  description
  page
  bbox

claims
  claim_id
  paper_id
  unit_id
  claim
  evidence
  confidence
  validation_status

evidence_packs
  pack_id
  run_id
  question
  evidence_json
  missing_evidence_json
  created_at

validation_reports
  report_id
  run_id
  passed
  warnings_json
  unsupported_claims_json
  confidence
  created_at

index_versions
  index_version
  parser
  parser_version
  chunk_strategy
  embedding_model
  embedding_dimension
  qdrant_collection
  created_at
```

---

## 18. 第二阶段 API 扩展

### 文献采集

```text
POST /api/literature/search
POST /api/literature/import
POST /api/literature/deduplicate
GET  /api/literature/jobs/{job_id}
```

### 多模态解析

```text
POST /api/documents/{document_id}/parse
POST /api/documents/{document_id}/reparse
GET  /api/documents/{document_id}/units
GET  /api/documents/{document_id}/figures
GET  /api/documents/{document_id}/tables
GET  /api/documents/{document_id}/equations
```

### 高级检索

```text
POST /api/knowledge/hybrid-search
POST /api/knowledge/rerank
POST /api/knowledge/search-by-region
POST /api/knowledge/search-by-fault
```

### 高级问答

```text
POST /api/rag/global/query
POST /api/rag/papers/compare
POST /api/rag/figures/query
POST /api/rag/tables/query
POST /api/rag/events/{event_id}/analysis
```

### 验证与评估

```text
POST /api/rag/claims/extract
POST /api/rag/claims/verify
GET  /api/rag/runs/{run_id}/validation
POST /api/eval/rag/run
GET  /api/eval/rag/report
```

---

## 19. 第二阶段实施路线

### 阶段 2.1：文献采集与去重

目标：

```text
从手动上传升级为半自动收集元数据和开放获取 PDF。
```

任务：

```text
1. 接 OpenAlex / Crossref / Semantic Scholar。
2. 设计 literature_search_service。
3. 实现 DOI 去重。
4. 保存 license 和 access_level。
5. 支持批量导入文献。
```

验收：

```text
能按主题搜索 100 篇候选论文。
能识别重复 DOI。
能筛选开放获取 PDF。
能创建批量解析任务。
```

---

### 阶段 2.2：RAGAnything / MinerU Adapter

目标：

```text
从简单文本解析升级为多模态解析。
```

任务：

```text
1. 接入 MinerU 或 RAGAnything。
2. 提取 text / figure / table / equation。
3. 保留 page / bbox / image_uri。
4. 转换成 KnowledgeUnit。
5. 支持解析失败重试。
```

验收：

```text
能解析复杂双栏 PDF。
能保存图表和页码。
能返回 bbox。
能将图表 caption 入库。
```

---

### 阶段 2.3：Hybrid Search 与 Rerank

目标：

```text
提升召回质量和最终证据质量。
```

任务：

```text
1. 增加 sparse search。
2. 增加 RRF 融合。
3. 增加 reranker。
4. 增加文献去重和多样性控制。
5. 增加 region/fault/topic filter。
```

验收：

```text
专业术语查询召回更稳定。
同一论文不会刷屏。
最终证据相关性明显提升。
```

---

### 阶段 2.4：Claim Verification

目标：

```text
让回答从“看起来像”升级为“可校验”。
```

任务：

```text
1. 回答后抽取核心 claims。
2. 对每个 claim 匹配 evidence。
3. 判断支持强度。
4. 输出 unsupported_claims。
5. 在前端展示验证报告。
```

验收：

```text
系统能发现无证据结论。
系统能标注弱支持结论。
地震风险回答更加保守。
```

---

### 阶段 2.5：前端证据链与 PDF 定位

目标：

```text
让用户能够审查回答来源。
```

任务：

```text
1. PDF 阅读器集成。
2. 页码跳转。
3. bbox 高亮。
4. 图表预览。
5. Evidence Pack 展示。
6. Validation Report 展示。
```

验收：

```text
点击引用能跳转到原文页。
用户能看到证据片段。
用户能看到不确定性和校验结果。
```

---

### 阶段 2.6：云端部署与数据迁移

目标：

```text
系统从本地 demo 升级为可部署服务。
```

任务：

```text
1. PostgreSQL 云端化。
2. Qdrant 云端化。
3. 文件存储迁移到 MinIO/S3/OSS/COS。
4. 环境变量统一。
5. 增加数据重建脚本。
6. 增加备份和恢复流程。
```

验收：

```text
本地和云端共用 schema。
云端可以重建索引。
PDF 不写死本地路径。
```

---

## 20. 第二阶段完整系统验收标准

完整系统完成后，应满足：

```text
1. 能管理数百到数千篇地质学文献。
2. 能自动或半自动采集开放获取文献。
3. 能解析正文、图、表、公式。
4. 能保留页码、bbox 和图片路径。
5. 能将所有内容转换成 KnowledgeUnit。
6. 能进行 dense + sparse hybrid search。
7. 能进行 rerank。
8. 能构建 Evidence Pack。
9. 能基于证据生成回答。
10. 能进行 Claim verification。
11. 能标注 unsupported claims。
12. 能在前端展示引用和验证结果。
13. 能跳转 PDF 页码并高亮证据区域。
14. 能支持地震事件分析。
15. 能支持论文问答、全库问答、多篇论文对比。
16. 能迁移到云端。
17. 能区分开放文献和内部授权文献。
18. 能记录 index_version，支持重建索引。
19. 能评估 RAG 检索和回答质量。
20. 能作为后续科研辅助平台继续扩展。
```

---

# 第三部分：整体优先级建议

## 21. 最高优先级

```text
1. KnowledgeUnit schema
2. PostgreSQL 表结构
3. Qdrant 接入
4. PDF 文本入库
5. 论文问答
6. 引用页码返回
7. 地震事件分析
```

这些是 MVP 必须完成的核心。

---

## 22. 中优先级

```text
1. 前端证据卡片
2. ingest 状态展示
3. rag_runs 记录
4. 不确定性说明
5. 简单评估集
6. 错误处理和重试
```

这些决定演示效果和系统稳定性。

---

## 23. 后续优先级

```text
1. RAGAnything / MinerU 深度接入
2. bbox 高亮
3. 图表问答
4. Hybrid Search
5. Reranker
6. Claim verification
7. 云端对象存储
8. 自动文献采集
9. 知识图谱
```

这些属于第二阶段完整系统。

---

# 第四部分：关键风险与控制

## 24. 文献版权风险

风险：

```text
非开放获取 PDF 被错误上传云端或公开使用。
```

控制：

```text
1. 每篇论文保存 license。
2. 每个 document 保存 access_level。
3. 云端部署区分 public / internal。
4. 非开放获取文献只允许内部合法使用。
```

---

## 25. PDF 解析质量风险

风险：

```text
双栏论文、扫描件、图表和公式解析错误。
```

控制：

```text
1. 保存 parse_status。
2. 保存 parse_error。
3. 支持 reparse。
4. 关键文献支持人工修正。
5. 第二阶段接 RAGAnything / MinerU。
```

---

## 26. 向量召回错误风险

风险：

```text
检索到相似但不支持结论的片段。
```

控制：

```text
1. Evidence Pack 不直接等于 top-k。
2. 第二阶段加入 reranker。
3. 每个结论必须绑定证据。
4. 加入 Claim verification。
```

---

## 27. 大模型幻觉风险

风险：

```text
大模型编造论文、页码、断裂名称或地震结论。
```

控制：

```text
1. 大模型只能引用 Evidence Pack 中已有来源。
2. 输出必须包含 citations。
3. 证据不足时必须说明不足。
4. 地震分析必须保守。
5. 回答后进行 Claim verification。
```

---

## 28. 地质解释过度确定风险

风险：

```text
系统仅凭震级、深度和位置判断发震断层、灾害严重性或未来余震趋势。
```

控制：

```text
1. Prompt 明确禁止过度推断。
2. 地震事件回答必须输出 uncertainty。
3. 缺少震源机制时必须说明不能确定断层类型。
4. 缺少灾害观测时不能断言灾害等级。
```

---

## 29. 索引版本混乱风险

风险：

```text
不同 parser、chunk 策略、embedding 模型生成的向量混在一起。
```

控制：

```text
1. 从第一天记录 index_version。
2. 记录 parser_version。
3. 记录 chunk_strategy。
4. 记录 embedding_model 和 dimension。
5. 换模型时新建 collection 或新 index_version。
```

---

# 第五部分：最终建议

## 30. 当前最应该立刻开始的 10 件事

```text
1. 确定 MVP 范围为 20-50 篇开放获取地质 PDF。
2. 写 KnowledgeUnit schema。
3. 建 PostgreSQL 表。
4. 接入 Qdrant。
5. 手写 demo KnowledgeUnit 测试检索。
6. 实现 PDF 文本入库。
7. 实现 /api/knowledge/search。
8. 实现 /api/rag/papers/query。
9. 实现 /api/events/{event_id}/geo-analysis。
10. 做前端证据卡片和不确定性展示。
```

---

## 31. 最重要的工程原则

```text
先做闭环，再做高级功能。
先做文本，再做图表公式。
先做本地，再做云端。
先做证据链，再做漂亮回答。
先做可追溯，再做智能化。
```

---

## 32. 项目一句话总结

```text
第一阶段 MVP：
用 20-50 篇地质学 PDF 跑通 PDF 入库、Qdrant 检索、证据驱动问答和地震事件分析。

第二阶段完整系统：
升级为支持大规模文献、多模态解析、Hybrid Search、Claim Verification、PDF 定位和云端迁移的地质学知识库与高级 RAG 平台。
```
