# 地质学文献知识库 RAG MVP 协作开发技术文档

## 1. 文档目的

本文档用于指导团队协作开发第一阶段 MVP。

MVP 的目标不是一次性完成完整高级 RAG 系统，而是先跑通最小闭环：

```text
20-50 篇开放获取地质学 PDF
  -> 本地入库
  -> 解析成 KnowledgeUnit
  -> 写入 PostgreSQL + Qdrant
  -> 论文问答
  -> 地震事件分析
  -> 返回证据、引用和不确定性
```

完成 MVP 后，我们应能证明：

- 地质学 PDF 可以被转成可检索知识单元。
- 问答不是凭大模型常识，而是基于知识库证据。
- 地震目录分析可以从文献库召回证据并给出保守解释。
- 系统结构能继续升级到 RAGAnything、多模态、Hybrid Search 和云端部署。

## 2. 当前项目基础

当前项目已经具备：

- 后端：FastAPI + SQLAlchemy。
- 前端：Vue 3 + Vite + Naive UI + Leaflet。
- 数据库：PostgreSQL 17 + PostGIS。
- 本地启动脚本：`python dev.py`。
- 地震目录 API 和前端展示。
- 论文分析模块雏形。
- 轻量 RAG 雏形。
- RAGAnything / Agent-RAG 参考项目。
- ResearchClaw 参考项目。

当前主要相关路径：

```text
README.md
dev.py
Project-Code/backend/app/
Project-Code/backend/app/app_factory.py
Project-Code/backend/app/rag.py
Project-Code/backend/app/raganything_service.py
Project-Code/backend/app/paper_database.py
Project-Code/backend/app/literature_search.py
Project-Code/backend/app/setting.py
Project-Code/backend/app/requirements.txt
Project-Code/Frontend/quakes-frontend/src/
```

重要原则：

```text
MVP 阶段不要大规模重构后端目录。
优先在当前 Project-Code/backend/app/ 下增量新增模块。
```

## 3. MVP 不做什么

为了保证能落地，MVP 暂不做：

- 大规模自动论文爬取。
- 完整知识图谱。
- 图表问答。
- 公式问答。
- 完整 Claim Verification。
- ColBERT / Late Interaction。
- OpenSearch。
- GraphRAG。
- 云端生产部署。
- 复杂权限系统。
- 完整多模态解析。

MVP 只做：

```text
PDF 文本解析
  -> 文本 KnowledgeUnit
  -> Qdrant 检索
  -> Evidence Pack
  -> 论文问答
  -> 地震事件分析
```

## 4. 技术选型

| 模块 | MVP 选择 | 说明 |
| --- | --- | --- |
| 后端 | FastAPI | 沿用当前项目 |
| 前端 | Vue 3 + Vite | 沿用当前项目 |
| 主数据库 | PostgreSQL + PostGIS | 管业务数据、地震目录、论文元数据 |
| 向量数据库 | Qdrant | 管 KnowledgeUnit 向量检索 |
| PDF 文本解析 | Parser Adapter | MVP 可先用 PyMuPDF/text-only，后续接 RAGAnything |
| Embedding | OpenAI-compatible embedding API | 通过 `.env` 配置 |
| 回答生成 | OpenAI-compatible chat API | 通过 `.env` 配置 |
| 证据组织 | Evidence Pack | 回答前必须构建 |
| 文件存储 | 本地文件夹 + `storage_uri` | 后续迁移对象存储 |

## 5. 本地运行要求

所有同事先确保主项目能跑起来：

```bash
python dev.py check
python dev.py setup
python dev.py
```

Windows 使用：

```powershell
py dev.py check
py dev.py setup
py dev.py
```

本地 Qdrant 建议使用 Docker：

```bash
docker run -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/Project-Code/backend/.data/qdrant:/qdrant/storage" \
  qdrant/qdrant
```

如果没有 Docker，可以先由一位同事提供共享 Qdrant 测试实例，其他同事通过 `QDRANT_URL` 连接。

## 6. 环境变量

在 `Project-Code/backend/.env.example` 后续应补充：

```env
# Qdrant
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=geo_knowledge_v1

# Embedding / LLM
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
GEO_RAG_CHAT_MODEL=gpt-4o-mini

# Index
GEO_RAG_INDEX_VERSION=geo-rag-v1
GEO_RAG_EMBEDDING_DIM=1536

# Local file storage
GEO_RAG_STORAGE_ROOT=./.data/geo_rag_files
```

注意：

- `.env` 不提交 Git。
- API Key 不写入代码。
- 向量库数据不提交 Git。
- PDF 大文件不提交 Git，除非是明确的小型 demo 文件。

## 7. 核心数据结构

### 7.1 ID 规则

同一篇论文必须稳定唯一。

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
paper_id    = doi_10_1785_0120230012
document_id = doi_10_1785_0120230012_v1
unit_id     = doi_10_1785_0120230012:text:p012:c003
```

### 7.2 KnowledgeUnit

MVP 阶段只需要 `content_type=text`，但字段要预留给图、表、公式。

```python
class KnowledgeUnit:
    unit_id: str
    paper_id: str
    document_id: str
    content_type: str       # text for MVP
    title: str
    text: str
    section: str | None
    page: int | None
    bbox: list[float] | None
    doi: str | None
    year: int | None
    authors: list[str]
    topics: list[str]
    regions: list[str]
    faults: list[str]
    parser: str
    embedding_model: str
    index_version: str
```

### 7.3 Evidence Pack

回答前必须先构建 Evidence Pack。

```json
{
  "question": "活动断裂和地震危险性之间有什么关系？",
  "mode": "paper_qa",
  "evidence": [
    {
      "evidence_id": "E1",
      "unit_id": "doi_xxx:text:p006:c002",
      "paper_id": "doi_xxx",
      "title": "Example Paper",
      "year": 2024,
      "page": 6,
      "section": "Discussion",
      "text": "Evidence text...",
      "score": 0.84
    }
  ],
  "missing_evidence": [],
  "uncertainty": []
}
```

回答原则：

- 核心结论必须引用 evidence。
- 证据不足时必须说明不足。
- 不编造论文、页码、断裂名称。
- 地震事件分析必须保守。

## 8. PostgreSQL 表设计

MVP 复用现有地震事件和论文模块，不另起一套完整新系统。

建议新增或扩展以下表：

```text
geo_documents
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
  updated_at

geo_knowledge_units
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

geo_ingest_jobs
  id
  job_id
  document_id
  status
  error
  started_at
  finished_at

geo_rag_runs
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
```

说明：

- `papers` 可先复用当前 `paper_database.py` 里的论文库能力。
- `events` 复用当前地震目录数据。
- 新表统一加 `geo_` 前缀，避免和现有表混淆。

## 9. Qdrant 设计

MVP 使用一个 collection：

```text
geo_knowledge_v1
```

point payload：

```json
{
  "unit_id": "doi_xxx:text:p012:c003",
  "paper_id": "doi_xxx",
  "document_id": "doi_xxx_v1",
  "content_type": "text",
  "title": "Example Paper",
  "section": "Results",
  "page": 12,
  "doi": "10.xxxx/xxxx",
  "year": 2024,
  "topics": ["earthquake", "fault"],
  "regions": ["Sichuan Basin"],
  "faults": ["Longmenshan Fault"],
  "embedding_model": "text-embedding-3-small",
  "index_version": "geo-rag-v1"
}
```

MVP 必须支持 filter：

- `paper_id`
- `document_id`
- `content_type`
- `index_version`
- `regions`
- `faults`
- `year`

后期再拆：

```text
geo_paper_index_v1
geo_section_index_v1
geo_chunk_index_v1
```

## 10. 后端新增模块

MVP 阶段建议新增以下文件：

```text
Project-Code/backend/app/geo_ids.py
Project-Code/backend/app/knowledge_schema.py
Project-Code/backend/app/qdrant_service.py
Project-Code/backend/app/embedding_service.py
Project-Code/backend/app/geo_ingest_service.py
Project-Code/backend/app/evidence_service.py
Project-Code/backend/app/geo_rag_service.py
Project-Code/backend/app/geo_rag_models.py
```

### 10.1 `geo_ids.py`

职责：

- 生成 `paper_id`。
- 生成 `document_id`。
- 生成 `unit_id`。
- 规范化 DOI、arXiv ID、title hash。

### 10.2 `knowledge_schema.py`

职责：

- 定义 `KnowledgeUnit`。
- 定义 `EvidenceItem`。
- 定义 `EvidencePack`。
- 定义检索结果结构。

### 10.3 `qdrant_service.py`

职责：

- 初始化 collection。
- 写入 KnowledgeUnit。
- 按 query 检索。
- 支持 payload filter。
- 删除或重建指定 `paper_id` 的索引。

### 10.4 `embedding_service.py`

职责：

- 调用 embedding API。
- 处理 embedding 维度。
- 记录 embedding model。
- 后续增加 embedding cache。

### 10.5 `geo_ingest_service.py`

职责：

- 接收 PDF。
- 计算文件 hash。
- 创建 document。
- 解析 PDF 文本。
- 切分 chunk。
- 生成 KnowledgeUnit。
- 写入 PostgreSQL。
- 写入 Qdrant。
- 更新 ingest status。

MVP parser 要做成 Adapter：

```text
ParserAdapter
  -> TextOnlyPdfParser
  -> FutureRAGAnythingParser
```

这样后续接 RAGAnything 不会推翻接口。

### 10.6 `evidence_service.py`

职责：

- 将检索结果转换为 Evidence Pack。
- 去重。
- 控制 evidence 数量。
- 截断超长文本。
- 生成 `E1/E2/E3` 编号。
- 添加 `missing_evidence` 和 `uncertainty`。

### 10.7 `geo_rag_service.py`

职责：

- 论文问答。
- 全库问答。
- 地震事件分析。
- 调用 evidence service。
- 调用 LLM。
- 返回结构化结果。

### 10.8 `geo_rag_models.py`

职责：

- SQLAlchemy 表模型。
- 如果不想立刻引入迁移工具，MVP 可先用 `Base.metadata.create_all`。

## 11. API 设计

在 `app_factory.py` 中增量新增 API，不删除现有接口。

### 11.1 初始化 Qdrant

```http
POST /api/knowledge/init
```

用途：

- 创建 Qdrant collection。
- 检查 embedding dim。

### 11.2 知识检索

```http
POST /api/knowledge/search
```

请求：

```json
{
  "query": "active fault seismic hazard",
  "filters": {
    "paper_id": "doi_xxx",
    "content_type": "text"
  },
  "topK": 8
}
```

返回：

```json
{
  "results": [
    {
      "unitId": "doi_xxx:text:p006:c002",
      "paperId": "doi_xxx",
      "title": "Example Paper",
      "page": 6,
      "section": "Results",
      "text": "...",
      "score": 0.84
    }
  ]
}
```

### 11.3 文档入库

```http
POST /api/documents/ingest
```

MVP 可以先支持本地路径或 multipart 上传，二选一即可。

请求：

```json
{
  "paperId": "doi_xxx",
  "fileUri": "local://papers/example.pdf"
}
```

返回：

```json
{
  "jobId": "job_xxx",
  "documentId": "doi_xxx_v1",
  "status": "completed",
  "unitCount": 128
}
```

### 11.4 入库状态

```http
GET /api/documents/{document_id}/status
```

### 11.5 论文问答

```http
POST /api/rag/papers/query
```

请求：

```json
{
  "paperId": "doi_xxx",
  "question": "这篇论文的主要结论是什么？",
  "topK": 8
}
```

返回：

```json
{
  "answer": "...",
  "citations": [
    {
      "evidenceId": "E1",
      "unitId": "doi_xxx:text:p006:c002",
      "paperId": "doi_xxx",
      "title": "Example Paper",
      "page": 6,
      "section": "Results",
      "text": "..."
    }
  ],
  "uncertainty": [
    "该回答仅基于当前入库论文证据。"
  ]
}
```

### 11.6 地震事件分析

```http
POST /api/events/{event_id}/geo-analysis
```

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
    "id": "us7000xxxx",
    "mag": 5.6,
    "depthKm": 10,
    "place": "..."
  },
  "answer": "...",
  "citations": [],
  "uncertainty": [
    "仅凭震级、深度和位置不能确定发震断层。",
    "当前知识库未找到震源机制证据。"
  ]
}
```

## 12. 前端 MVP 改造

优先改现有页面，不新建复杂产品。

### 12.1 论文分析页

当前路径参考：

```text
Project-Code/Frontend/quakes-frontend/src/views/PapersView.vue
Project-Code/Frontend/quakes-frontend/src/views/PaperDetailView.vue
```

新增：

- 解析状态。
- 入库按钮。
- 论文问答入口。
- 证据卡片。

最小 UI：

```text
论文信息
问题输入框
回答区域
证据卡片列表
```

### 12.2 地震事件分析

当前路径参考：

```text
Project-Code/Frontend/quakes-frontend/src/views/DashboardView.vue
```

新增：

- “生成地质分析”按钮。
- 回答区域。
- 文献证据卡片。
- 不确定性提示。

### 12.3 TerraChat 可选接入

当前路径：

```text
Project-Code/Frontend/quakes-frontend/src/views/TerraChat.vue
```

MVP 可暂时不改 TerraChat，避免影响已有聊天体验。后续可以让 TerraChat 调用 `/api/rag/geo/query`。

## 13. MVP 开发流程

### 过程 1：准备数据

负责人任务：

- 准备 20-50 篇开放获取地质学 PDF。
- 建立 `demo_papers.csv`。
- 记录 title、authors、year、doi、source_url、license。

验收：

- 文献可合法用于 demo。
- 每篇 PDF 可在本地访问。

### 过程 2：定义 schema 和 ID

负责人任务：

- 实现 `geo_ids.py`。
- 实现 `knowledge_schema.py`。
- 实现 SQLAlchemy 模型。

验收：

- 输入 DOI 能生成稳定 `paper_id`。
- 输入 PDF 能生成 `document_id`。
- chunk 能生成稳定 `unit_id`。

### 过程 3：接入 Qdrant

负责人任务：

- 添加 `qdrant-client` 依赖。
- 实现 collection 初始化。
- 手写 10 条 KnowledgeUnit 写入 Qdrant。
- 实现 `/api/knowledge/search`。

验收：

- 可以检索 demo unit。
- 可以按 `paper_id` 过滤。

### 过程 4：PDF 文本入库

负责人任务：

- 添加 PDF text parser adapter。
- 实现 chunk 切分。
- 生成 KnowledgeUnit。
- 写 PostgreSQL。
- 写 Qdrant。

验收：

- 1 篇 PDF 能生成多个 KnowledgeUnit。
- parse status 能正确更新。
- 可以按 paper_id 搜到这篇论文内容。

### 过程 5：Evidence Pack

负责人任务：

- 实现 `evidence_service.py`。
- 从检索结果生成 Evidence Pack。
- 控制 evidence topK。
- 添加 uncertainty。

验收：

- 每次回答前有清晰 evidence 列表。
- evidence 有 `E1/E2` 编号。
- evidence 有 `unit_id/paper_id/page`。

### 过程 6：论文问答

负责人任务：

- 实现 `/api/rag/papers/query`。
- 后端生成结构化回答。
- 前端显示回答和证据卡片。

验收：

- 选择一篇论文后提问。
- 系统只从该论文召回证据。
- 回答包含引用。
- 证据不足时明确说明不足。

### 过程 7：地震事件分析

负责人任务：

- 实现 `/api/events/{event_id}/geo-analysis`。
- 读取当前地震事件。
- 构造 query。
- 检索地质文献知识库。
- 输出保守分析和不确定性。

验收：

- 点击地震事件可以生成分析。
- 回答包含文献证据。
- 不会断言“必然由某断裂造成”。

### 过程 8：评估和演示

负责人任务：

- 准备 30 个测试问题。
- 记录每个问题预期证据。
- 测试论文问答和地震分析。
- 写 README MVP 使用说明。

验收：

- 演示流程稳定。
- 不编造论文和页码。
- 错误状态可见。
- 同事可按 README 跑起来。

## 14. 分工建议

### 后端 A：Schema + PostgreSQL

负责：

- `geo_ids.py`
- `knowledge_schema.py`
- `geo_rag_models.py`
- 数据表创建。

### 后端 B：Qdrant + Embedding

负责：

- `qdrant_service.py`
- `embedding_service.py`
- `/api/knowledge/search`

### 后端 C：Ingest + Parser

负责：

- `geo_ingest_service.py`
- PDF parser adapter。
- `/api/documents/ingest`
- `/api/documents/{document_id}/status`

### 后端 D：RAG + Evidence

负责：

- `evidence_service.py`
- `geo_rag_service.py`
- `/api/rag/papers/query`
- `/api/events/{event_id}/geo-analysis`

### 前端 A：论文问答

负责：

- 论文详情页问答入口。
- 证据卡片。
- 入库状态展示。

### 前端 B：地震事件分析

负责：

- 地震事件详情分析按钮。
- AI 分析结果展示。
- 不确定性提示。

### 测试/资料负责人

负责：

- demo PDF 清单。
- 测试问题。
- 期望证据。
- MVP 演示流程。

## 15. 开发约定

### 15.1 Git

不要提交：

- `.env`
- `.venv/`
- `node_modules/`
- Qdrant 数据目录。
- PDF 大文件。
- 解析输出大文件。
- `Agent-RAG/.venv`
- `Agent-RAG/node_modules`
- `Agent-RAG/output`
- `Agent-RAG/rag_storage`

### 15.2 分支

建议分支命名：

```text
feature/geo-rag-schema
feature/geo-rag-qdrant
feature/geo-rag-ingest
feature/geo-rag-paper-qa
feature/geo-rag-event-analysis
```

### 15.3 API 返回格式

统一使用 camelCase 给前端：

```json
{
  "paperId": "...",
  "unitId": "...",
  "documentId": "..."
}
```

后端内部 Python 可使用 snake_case。

### 15.4 错误处理

所有入库任务必须有状态：

```text
pending
processing
completed
failed
```

失败时必须保存错误信息。

### 15.5 回答安全规则

地震事件分析必须遵守：

```text
1. 不能仅凭震级和位置断定发震断层。
2. 没有震源机制时必须说明不能确定断层运动性质。
3. 没有余震、InSAR、GNSS 或灾害观测时，不能断言破裂过程和灾害等级。
4. 所有地质解释都要基于 evidence。
```

## 16. 测试清单

### 后端测试

至少覆盖：

- ID 生成稳定。
- KnowledgeUnit 序列化。
- Qdrant 写入和检索。
- paper_id filter 生效。
- PDF 入库成功。
- PDF 入库失败可记录状态。
- Evidence Pack 生成。
- 论文问答只使用指定 paper_id。
- 地震事件分析返回 uncertainty。

### 前端测试

至少检查：

- 论文入库状态显示。
- 论文问答请求成功。
- 证据卡片显示。
- 地震事件分析按钮可用。
- 加载状态、失败状态可见。

### 人工评估

准备 30 个问题：

```text
10 个单篇论文问题
10 个全库地质概念问题
10 个地震事件分析问题
```

人工检查：

- 证据是否相关。
- 引用是否真实。
- 回答是否基于证据。
- 是否编造论文、页码、断裂名。
- 是否过度推断地震风险。

## 17. MVP 验收标准

MVP 完成时应满足：

```text
1. 同事能按 README 启动项目。
2. 本地 Qdrant 能启动。
3. 能入库至少 20 篇开放获取地质 PDF。
4. 每篇 PDF 能生成 KnowledgeUnit。
5. KnowledgeUnit 能写入 PostgreSQL。
6. 向量能写入 Qdrant。
7. 能按 paper_id 检索。
8. 能全库检索。
9. 论文问答能返回答案和引用。
10. 地震事件分析能返回文献证据。
11. 回答包含 uncertainty。
12. 不编造论文、页码和断裂结论。
13. 解析失败有状态。
14. 前端能展示回答和证据卡片。
```

## 18. MVP 后再做的增强

MVP 完成后再考虑：

- RAGAnything / MinerU 深度接入。
- bbox 高亮。
- 图表问答。
- 公式问答。
- Paper / Section / Chunk 三层索引。
- Hybrid Search。
- Reranker。
- Claim Verification。
- 流式输出。
- 缓存。
- 云端对象存储。
- 大规模文献采集。

## 19. 一句话总结

```text
MVP 的核心不是做最强 RAG，而是先证明：
地质 PDF 可以稳定入库，
知识块可以被检索，
回答可以被证据支撑，
地震分析可以保守、可追溯、可审查。
```
