# 地质学文献知识库与高级 RAG 系统规划

## 1. 项目定位

本项目当前已经包含两个核心业务模块：

- 地震目录模块：展示、查询和分析地震事件。
- 论文分析模块：管理论文信息、证据链和文献问答能力。

后续目标不是只做一个地震问答机器人，而是建设一个面向地质学领域的可迁移文献知识库系统。系统提前下载、解析和索引大量地质学文献，包括地震学、构造地质学、地球物理、地质灾害、岩土工程、活动断裂、地层、沉积、火山、遥感和地球化学等方向。网站运行时不再主要依赖实时学术检索，而是优先从本地或云端已经构建好的知识库中召回证据，再生成科学、可追溯、可审查的回答。

一句话概括：

```text
提前建设地质学文献知识库，让地震目录分析和论文问答都基于统一的向量数据库和证据链来完成。
```

## 2. 当前项目已经具备的可行基础

### 2.1 协作启动基础

项目已经具备统一的本地开发入口：

```bash
python dev.py
```

当前已有能力：

- 自动创建后端虚拟环境。
- 自动安装后端依赖。
- 自动安装前端依赖。
- 自动准备 PostgreSQL / PostGIS 数据库。
- README 已经补充协作启动、pip 镜像、Windows/macOS 说明。

当前技术：

- 后端：FastAPI、SQLAlchemy、Pydantic。
- 前端：Vue 3、Vite、Naive UI、Leaflet。
- 主数据库：PostgreSQL 17 + PostGIS。
- 本地脚本：`dev.py`。

当前状态：

- `python3 dev.py check` 在当前电脑检查通过。
- 说明项目本地协作运行路径已经基本打通。

### 2.2 地震目录模块基础

项目已经具备地震事件相关能力：

- 地震事件查询 API。
- 地震事件时间、位置、震级、深度等结构化字段。
- 前端地图和仪表盘展示。
- PostgreSQL / PostGIS 支持地理空间数据。

这部分后续可以作为 RAG 问答上下文：

```text
用户点击某个地震事件
  -> 系统读取事件地点、震级、深度、时间、区域
  -> 生成地质学问题上下文
  -> 从文献知识库召回相关证据
  -> 输出构造背景、震源机制、历史相似事件、风险和不确定性说明
```

### 2.3 论文分析模块基础

项目中已经有论文库和证据链雏形，包括：

- 论文元数据。
- 论文检索。
- 论文详情。
- Claim / Evidence / Reasoning / Citation 结构。
- Evidence Pack 的初步概念。
- 论文分析页面和详情页面。

当前这部分更多还是 demo / 原型性质，但方向是正确的：论文不只是被展示，而是被组织成可用于问答和分析的证据单元。

### 2.4 轻量 RAG 基础

项目已经具备轻量 RAG 流程：

```text
用户问题
  -> 构造地震事件和文献摘要上下文
  -> 本地检索相关片段
  -> 生成回答
  -> 返回引用上下文和后续问题
```

当前技术：

- `Project-Code/backend/app/rag.py`
- `Project-Code/backend/app/vector_retrieval.py`
- 可选 OpenAI embedding。
- 无外部向量数据库时可使用轻量本地索引。

当前价值：

- 证明 RAG 业务链路能跑通。
- 后续可以把底层轻量索引替换为 Qdrant。

### 2.5 RAGAnything 参考基础

项目中已经放入 `Agent-RAG` 作为参考项目。它的价值在于：

- PDF 文档解析。
- 图、表、公式解析。
- 多模态 chunk 入库。
- 页码 `page_idx`。
- 坐标框 `bbox`。
- 图片路径。
- LightRAG / 图谱能力。
- 文档问答后返回页码和引用位置。

需要注意：

`Agent-RAG` 当前是完整独立项目目录，里面包含 `.venv`、`node_modules`、运行日志、解析输出、PDF、RAG 存储和自己的 `.git`。它适合作为学习和抽取能力的参考，不适合整体提交到主项目仓库。

后续正确做法是：

```text
借鉴 Agent-RAG / RAGAnything 的解析和入库逻辑
  -> 写成我们自己的 adapter
  -> 转换成统一 KnowledgeUnit schema
  -> 存入 PostgreSQL + Qdrant + 文件存储
```

### 2.6 ResearchClaw 参考基础

项目中已有 `AutoResearchClaw` 作为参考。它适合借鉴的不是网站代码，而是科研流程设计：

- 检索规划。
- 文献筛选。
- 知识抽取。
- 多阶段 pipeline。
- Claim / Evidence / Citation。
- 反幻觉校验。
- 人工审核 gate。
- 质量检查和可审查输出。

在本项目中，ResearchClaw 思路适合放在回答流程中：

```text
检索
  -> 筛选
  -> 证据组织
  -> 生成回答
  -> 校验回答
  -> 标注不确定性
```

## 3. 目标系统总架构

推荐架构：

```text
                    +----------------------+
                    |  地质学 PDF / 文献源  |
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

各组件职责：

| 组件 | 职责 |
| --- | --- |
| PostgreSQL + PostGIS | 地震目录、论文元数据、任务状态、用户数据、地理空间查询 |
| Qdrant | 文献 chunk、图表说明、公式说明、Claim/Evidence 的向量检索 |
| 本地文件夹 / 云对象存储 | PDF 原文、图片、解析文件、图表截图 |
| RAGAnything / MinerU | PDF、多模态内容解析 |
| ResearchClaw 思路 | 科学分析流程、证据链、反幻觉校验 |
| FastAPI | 统一 API、入库任务、RAG 查询、证据校验 |
| Vue 前端 | 地震目录分析、论文问答、证据链展示、PDF 定位 |

## 4. 数据库是否必须使用 PostgreSQL + PostGIS

不是所有数据都必须放进 PostgreSQL，但 PostgreSQL + PostGIS 很适合作为主业务数据库。

它适合管理：

- 地震事件。
- 经纬度、震级、深度、时间。
- 地理范围查询。
- 论文标题、作者、年份、DOI、来源。
- 文献入库状态。
- 用户问答记录。
- 任务状态和错误日志。

它不适合单独承担全部大规模向量检索。因此推荐组合：

```text
PostgreSQL + PostGIS：主业务数据库
Qdrant：向量数据库
对象存储：PDF 和图片文件
```

这样本地和云端都容易迁移：

```text
本地 PostgreSQL -> 云 PostgreSQL
本地 Qdrant     -> 云 Qdrant
本地文件夹       -> S3 / OSS / COS / MinIO
```

## 5. 文献提前下载和入库策略

新的方向是提前下载大量地质学文献，而不是每次根据地震事件实时检索文献。

推荐文献范围：

- 地震学。
- 构造地质学。
- 活动断裂。
- 地球物理。
- 地质灾害。
- 工程地质。
- 地层与沉积。
- 遥感地质。
- 火山与岩浆活动。
- 地球化学。
- 区域地质。
- 地质建模与数值模拟。

推荐来源：

- OpenAlex 元数据。
- Semantic Scholar 元数据。
- arXiv / EarthArXiv。
- Crossref DOI 元数据。
- 开放获取期刊。
- 机构知识库。
- 团队手动上传的 PDF。

需要注意版权：

- 优先收集开放获取文献。
- 对非开放获取文献，只存团队合法获取的本地 PDF。
- 云端部署时要区分公开可用文件和内部授权文件。

## 6. 核心数据模型设计

### 6.1 论文唯一 ID

同一篇论文必须有稳定唯一标签，不能完全依赖解析器自动生成。

推荐生成优先级：

```text
DOI
  -> arXiv ID
  -> OpenAlex ID
  -> Semantic Scholar ID
  -> title + year + first_author hash
```

示例：

```text
paper_id    = doi_10.1785_0120230012
document_id = doi_10.1785_0120230012_v1
chunk_id    = doi_10.1785_0120230012:text:p12:c003
figure_id   = doi_10.1785_0120230012:figure:p08:f001
table_id    = doi_10.1785_0120230012:table:p10:t001
equation_id = doi_10.1785_0120230012:equation:p06:e002
```

### 6.2 KnowledgeUnit

`KnowledgeUnit` 是统一入库的最小知识单元。无论正文、图、表、公式、Claim，最终都转换成这种结构。

示例：

```json
{
  "unit_id": "doi_10.1785_0120230012:text:p12:c003",
  "paper_id": "doi_10.1785_0120230012",
  "document_id": "doi_10.1785_0120230012_v1",
  "source_type": "paper",
  "content_type": "text",
  "title": "Example Paper Title",
  "text": "This paragraph discusses the fault geometry and seismicity...",
  "section": "Results",
  "page": 12,
  "bbox": [120.5, 233.0, 480.2, 310.6],
  "doi": "10.1785/0120230012",
  "year": 2024,
  "authors": ["Author A", "Author B"],
  "topics": ["earthquake", "fault", "seismicity"],
  "geo_terms": {
    "region": ["Sichuan Basin"],
    "fault": ["Longmenshan Fault"],
    "tectonic_setting": ["active fault zone"]
  },
  "parser": "mineru",
  "parser_version": "unknown",
  "embedding_model": "text-embedding-3-small",
  "index_version": "geo-rag-v1"
}
```

图表单元示例：

```json
{
  "unit_id": "doi_10.1785_0120230012:figure:p08:f001",
  "paper_id": "doi_10.1785_0120230012",
  "content_type": "figure",
  "text": "Figure 3 shows focal mechanism solutions near the active fault...",
  "caption": "Figure 3. Focal mechanisms...",
  "image_uri": "local://papers/doi_10.1785_0120230012/images/fig_003.jpg",
  "page": 8,
  "bbox": [80, 120, 520, 420],
  "related_unit_ids": [
    "doi_10.1785_0120230012:text:p08:c002"
  ]
}
```

### 6.3 PostgreSQL 建议表

第一阶段建议至少有这些表：

```text
papers
  paper_id
  title
  authors
  year
  doi
  arxiv_id
  openalex_id
  semantic_scholar_id
  source_url
  license
  created_at

documents
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
  unit_id
  paper_id
  document_id
  content_type
  section
  page
  bbox
  text_preview
  qdrant_point_id
  created_at

claims
  claim_id
  paper_id
  unit_id
  claim
  evidence
  citation
  confidence
  validation_status

events
  event_id
  time
  magnitude
  depth
  latitude
  longitude
  place
  source

rag_runs
  run_id
  question
  mode
  event_id
  selected_paper_id
  answer
  evidence_json
  validation_json
  created_at
```

### 6.4 Qdrant payload 建议

Qdrant collection：

```text
collection: geo_knowledge
```

每个 point payload：

```json
{
  "unit_id": "doi_10.1785_0120230012:text:p12:c003",
  "paper_id": "doi_10.1785_0120230012",
  "document_id": "doi_10.1785_0120230012_v1",
  "source_type": "paper",
  "content_type": "text",
  "title": "Example Paper Title",
  "section": "Results",
  "page": 12,
  "bbox": [120.5, 233.0, 480.2, 310.6],
  "doi": "10.1785/0120230012",
  "year": 2024,
  "topics": ["earthquake", "fault"],
  "region": ["Sichuan Basin"],
  "fault": ["Longmenshan Fault"],
  "index_version": "geo-rag-v1"
}
```

## 7. 完整处理工作流

### 7.1 文献采集工作流

```text
1. 输入主题范围
   例如：earthquake, active fault, tectonics, landslide, geophysics

2. 从开放数据源收集元数据
   OpenAlex / Semantic Scholar / Crossref / arXiv

3. 去重
   DOI -> arXiv ID -> OpenAlex ID -> title hash

4. 判断是否有全文
   开放获取 PDF / 本地上传 PDF / 仅元数据

5. 保存论文元数据到 PostgreSQL

6. 保存 PDF 到本地文件夹或对象存储

7. 创建解析任务
```

### 7.2 文档解析工作流

```text
1. 读取 documents 中 parse_status=pending 的 PDF

2. 调用 RAGAnything / MinerU

3. 得到 content_list
   - text
   - image
   - table
   - equation
   - page_idx
   - bbox
   - image_path

4. 转换成 KnowledgeUnit

5. 抽取地质专业字段
   - region
   - fault
   - tectonic setting
   - magnitude
   - depth
   - focal mechanism
   - hazard
   - monitoring method

6. 写入 PostgreSQL

7. 生成 embedding

8. 写入 Qdrant

9. 更新 parse_status=completed
```

### 7.3 地震目录分析工作流

```text
1. 用户在地震目录中点击事件

2. 系统读取事件信息
   - 位置
   - 震级
   - 深度
   - 时间
   - 区域

3. 构造 RAG 查询
   例如：
   - 该区域构造背景
   - 相似震级和深度事件
   - 活动断裂相关研究
   - 地震危险性和余震研究

4. 从 Qdrant 召回相关 KnowledgeUnit
   过滤条件：
   - 地质领域
   - 区域相近
   - 主题相关
   - 文献可靠

5. 生成 Evidence Pack

6. 基于 Evidence Pack 生成回答

7. 校验回答
   - 是否每个核心结论都有证据
   - 是否引用真实
   - 是否过度推断
   - 是否应该提示不确定性

8. 前端展示
   - 分析结论
   - 证据来源
   - 相关论文
   - 不确定性
```

### 7.4 论文问答工作流

```text
1. 用户进入论文分析模块

2. 用户选择：
   - 全库问答
   - 某篇论文问答
   - 某个主题问答
   - 某个区域问答

3. 系统根据范围设置 Qdrant filter
   - paper_id
   - topic
   - region
   - content_type

4. 召回正文、图、表、公式相关 KnowledgeUnit

5. 组织 Evidence Pack

6. 生成回答

7. 返回：
   - answer
   - citations
   - page
   - bbox
   - related figures/tables
   - confidence

8. 前端支持跳转到 PDF 对应页码和框选区域
```

### 7.5 科学校验工作流

借鉴 ResearchClaw，回答生成后增加验证层：

```text
1. 从回答中抽取关键 Claim

2. 对每个 Claim 寻找支持 Evidence

3. 判断 Evidence 是否真的支持 Claim

4. 检查 Citation 是否存在

5. 检查是否存在过度预测
   例如：
   - 没有证据却判断必然发生余震
   - 仅凭震级判断灾害严重
   - 把某篇论文的局部结论推广到所有区域

6. 输出 validation report
   - passed
   - warning
   - unsupported_claims
   - confidence
```

## 8. RAGAnything 在本系统中的角色

RAGAnything 负责：

- PDF 解析。
- 章节和正文提取。
- 图片、表格、公式提取。
- 生成图表和公式说明。
- 保留页码和坐标。
- 输出可用于入库的 content list。

RAGAnything 不负责：

- 统一论文 ID。
- 统一知识库 schema。
- 云端迁移。
- 科学结论校验。
- 地质专业字段标准化。
- 业务 API 和前端展示。

因此需要我们写：

```text
RAGAnything Output
  -> KnowledgeUnit Adapter
  -> PostgreSQL + Qdrant
```

## 9. ResearchClaw 在本系统中的角色

ResearchClaw 适合借鉴到以下模块：

### 9.1 文献筛选

对入库文献按主题、质量、来源、年份、引用量、开放性做筛选。

### 9.2 知识抽取

从论文 chunk 中抽取：

- Claim。
- Evidence。
- Method。
- Dataset。
- Limitation。
- Citation。

### 9.3 回答前证据组织

先构建 Evidence Pack，再回答。

```json
{
  "claim": "该区域地震活动可能与活动断裂带有关",
  "evidence": [
    {
      "unit_id": "xxx",
      "text": "论文第 6 页指出该区域断裂带活动性显著...",
      "citation": "Author et al., 2023",
      "confidence": 0.84
    }
  ],
  "uncertainty": "该结论需要结合震源机制和余震序列进一步确认"
}
```

### 9.4 反幻觉校验

回答后检查：

- 是否有无证据结论。
- 是否有不存在的引用。
- 是否把局部结论泛化。
- 是否对灾害风险表述过度确定。

### 9.5 人工审核

重要问题可以加入人工审核：

- 震源机制判断。
- 灾害风险判断。
- 区域构造解释。
- 学术报告导出。

## 10. 前端产品形态

### 10.1 地震目录页

目标能力：

- 地图展示事件。
- 点击事件查看基础参数。
- 自动给出相关地质背景。
- 展示相关文献证据。
- 展示不确定性。

建议展示结构：

```text
事件参数
构造背景
相关断裂 / 区域
历史相似事件
文献证据
AI 分析
不确定性说明
```

### 10.2 论文分析页

目标能力：

- 全库论文检索。
- 单篇论文问答。
- 多篇论文对比。
- 图表/公式问答。
- 页码和 bbox 定位。

建议展示结构：

```text
论文列表
论文详情
文档问答
证据链
图表/公式
PDF 定位
知识图谱
```

### 10.3 地质学通用问答

长期可以加入全库问答：

```text
为什么四川盆地边缘地震活动频繁？
活动断裂和地震危险性之间有什么关系？
震源机制解如何用于判断断层类型？
滑坡灾害与地震动参数之间有什么关系？
```

## 11. 云端迁移设计

从一开始就要避免本地路径写死。

文件 URI 应采用抽象格式：

```text
local://papers/xxx.pdf
s3://bucket/papers/xxx.pdf
oss://bucket/papers/xxx.pdf
minio://geo-rag/papers/xxx.pdf
```

环境变量建议：

```env
DATABASE_URL=postgresql+psycopg://...
QDRANT_URL=http://127.0.0.1:6333
QDRANT_API_KEY=
OBJECT_STORAGE_PROVIDER=local
OBJECT_STORAGE_ROOT=./.data/files
EMBEDDING_MODEL=text-embedding-3-small
INDEX_VERSION=geo-rag-v1
```

迁移原则：

- Git 只存源码、schema、脚本、文档。
- 不提交向量库数据。
- 不提交 PDF 大文件。
- 不提交本地解析输出。
- 云端通过入库脚本重建或同步数据库。

## 12. 当前主要缺口

### 12.1 缺少统一向量数据库

当前项目还没有真正接入 Qdrant。轻量 RAG 已经能证明流程，但不适合未来大规模地质文献库。

需要做：

- 新增 Qdrant 本地部署说明。
- 新增 Qdrant Python client。
- 新增 collection 初始化脚本。
- 新增入库、检索、删除、重建接口。

### 12.2 缺少统一 KnowledgeUnit schema

当前论文库和 RAGAnything 输出还没有统一起来。

需要做：

- 定义 `KnowledgeUnit`。
- 定义 PostgreSQL 表结构。
- 定义 Qdrant payload。
- 定义 ID 规则。

### 12.3 缺少 RAGAnything adapter

现在 RAGAnything 只是可用依赖和参考项目，还没有稳定转换层。

需要做：

```text
process_document_complete()
  -> content_list
  -> normalize
  -> KnowledgeUnit
  -> embedding
  -> Qdrant
```

### 12.4 缺少大规模文献采集和去重流程

需要做：

- 文献元数据采集。
- DOI 去重。
- PDF 下载策略。
- 版权和授权字段。
- 解析任务队列。

### 12.5 缺少科学验证层

当前还没有完整的 Claim 验证流程。

需要做：

- 回答后抽取 Claim。
- 对 Claim 匹配 Evidence。
- 对 unsupported claim 给 warning。
- 对高风险地质解释降低确定性。

### 12.6 缺少索引版本管理

需要记录：

- parser 版本。
- chunk 策略版本。
- embedding 模型。
- embedding 维度。
- collection 名称。
- index_version。

否则以后换模型或换 chunk 策略，会导致新旧向量混在一起。

### 12.7 缺少云端文件存储抽象

当前本地路径适合开发，但不适合云端。

需要做：

- `storage_uri` 字段。
- 本地存储实现。
- 后续 S3 / OSS / COS / MinIO 实现。

## 13. 分阶段实施计划

### 阶段 0：稳定协作运行

目标：

- 所有同事能本地跑起来。
- 文档清晰。
- 不提交本地生成物。

已基本完成：

- `dev.py`
- README 协作说明。
- pip 镜像说明。

还需要：

- 清理或忽略 `Agent-RAG` 中的 `.venv`、`node_modules`、输出文件。
- 决定 `Agent-RAG` 是作为外部参考、submodule，还是只抽取必要代码。

### 阶段 1：统一知识库 schema

目标：

- 定义 `paper_id`、`document_id`、`unit_id`。
- 定义 PostgreSQL 表。
- 定义 Qdrant payload。
- 定义 KnowledgeUnit Python model。

交付：

- `knowledge_schema.py`
- 数据库迁移或建表脚本。
- schema 文档。

### 阶段 2：本地 Qdrant 接入

目标：

- 本地启动 Qdrant。
- 创建 `geo_knowledge` collection。
- 写入 demo KnowledgeUnit。
- 支持向量检索和 metadata filter。

交付：

- `qdrant_service.py`
- `python dev.py index-demo`
- `/api/knowledge/search`

### 阶段 3：RAGAnything 文档入库

目标：

- 上传或指定 PDF。
- 使用 RAGAnything 解析。
- 转换成 KnowledgeUnit。
- 写入 PostgreSQL + Qdrant。

交付：

- `/api/documents/ingest`
- `/api/documents/{id}/status`
- 入库日志和错误信息。

### 阶段 4：论文问答升级

目标：

- 论文问答从 Qdrant 召回。
- 支持按 `paper_id` 过滤。
- 返回引用页码和 bbox。

交付：

- `/api/rag/papers/query`
- 前端论文问答页面升级。

### 阶段 5：地震目录分析升级

目标：

- 地震分析从统一地质文献库召回。
- 不再依赖实时文献检索作为主要路径。
- 输出证据链和不确定性。

交付：

- `/api/events/{event_id}/geo-analysis`
- 地震目录页证据卡片。

### 阶段 6：科学验证层

目标：

- 回答生成后做 Claim 检查。
- 标注 unsupported claim。
- 输出 confidence。

交付：

- `claim_verifier.py`
- `Evidence Pack`
- `Validation Report`

### 阶段 7：云端迁移

目标：

- PostgreSQL 云端化。
- Qdrant 云端化。
- PDF / 图片对象存储。
- 本地和云端共用 schema。

交付：

- 云端部署文档。
- 环境变量模板。
- 数据同步或重建脚本。

## 14. MVP 建议

第一版不要追求全功能。建议 MVP 目标：

```text
给定 20-50 篇开放获取地质学 PDF
  -> 本地解析
  -> 写入 Qdrant
  -> 论文问答能返回页码和证据
  -> 地震事件能基于知识库生成解释
```

MVP 验收标准：

- 能跑 `python dev.py`。
- 能启动 Qdrant。
- 能入库至少 20 篇 PDF。
- 能在论文问答中按 `paper_id` 限定范围。
- 能在全库问答中按主题召回。
- 回答包含引用文献和页码。
- 地震事件分析不依赖实时网络检索。
- 回答中明确说明不确定性。

## 15. 风险和注意事项

### 15.1 文献版权

不要默认把所有 PDF 都上传云端。需要区分：

- 开放获取文献。
- 团队内部合法获取文献。
- 仅元数据文献。

### 15.2 RAGAnything 解析质量

PDF 解析不是百分百稳定。复杂双栏、扫描件、图表、公式可能失败。

需要：

- 保存解析状态。
- 保存解析错误。
- 支持重新解析。
- 支持人工修正关键文献。

### 15.3 向量召回不等于正确答案

向量库只能找相似内容，不能保证结论科学正确。

必须增加：

- Evidence Pack。
- Claim verification。
- Citation check。
- Uncertainty statement。

### 15.4 地质解释不能过度确定

地质学和地震学分析常有不确定性。系统回答时应避免：

- 只凭震级判断灾害风险。
- 没有震源机制却断定断层类型。
- 把某区域研究结论套到所有区域。
- 把模型推测说成事实。

### 15.5 Agent-RAG 不能整体提交

当前 `Agent-RAG` 目录包含大量运行产物和环境目录。建议只作为本地参考，后续抽取：

- RAGAnything 后端构建逻辑。
- page / bbox citation 逻辑。
- graph_data 思路。
- 前端图文问答展示思路。

## 16. 推荐下一步任务

优先级从高到低：

1. 决定 Qdrant 作为向量数据库，并补本地启动说明。
2. 定义 `KnowledgeUnit` schema。
3. 定义 `paper_id/document_id/unit_id` 规则。
4. 写 RAGAnything adapter。
5. 做 20 篇 PDF 的本地入库 demo。
6. 改论文问答走 Qdrant。
7. 改地震目录分析走 Qdrant。
8. 加 Evidence Pack。
9. 加 Claim verification。
10. 设计云端迁移环境变量和存储 URI。

## 17. 可以继续问 ChatGPT 的问题

可以把下面问题发给 ChatGPT 或用于后续方案深化：

```text
我正在设计一个地质学文献知识库 RAG 系统。
技术栈计划是 FastAPI + Vue + PostgreSQL/PostGIS + Qdrant + RAGAnything。
系统需要提前下载大量地质学论文，解析 PDF、图表、公式，并支持地震目录分析和论文问答。

请帮我详细设计：
1. KnowledgeUnit schema
2. PostgreSQL 表结构
3. Qdrant collection 和 payload
4. paper_id/document_id/unit_id 生成规则
5. RAGAnything 输出到 KnowledgeUnit 的 adapter
6. Evidence Pack 结构
7. Claim verification 流程
8. 本地到云端迁移方案
9. MVP 开发路线
```

## 18. 总结

目前项目已经具备以下基础：

- 网站前后端可运行。
- 地震目录模块已有数据和展示基础。
- 论文分析模块已有结构雏形。
- 轻量 RAG 已经证明业务链路可行。
- RAGAnything 可作为文献、多模态解析参考。
- ResearchClaw 可作为科学分析和校验流程参考。

目前还缺少：

- 统一向量数据库。
- 统一 KnowledgeUnit schema。
- RAGAnything adapter。
- 大规模文献采集和去重流程。
- 证据优先的回答流程。
- 反幻觉校验。
- 云端迁移设计。

最终系统应当形成：

```text
地质学大文献库
  -> 多模态解析
  -> 统一知识单元
  -> PostgreSQL + Qdrant
  -> 证据驱动 RAG
  -> 地震目录分析 + 论文问答
  -> 可审查、可追溯、可迁移
```
