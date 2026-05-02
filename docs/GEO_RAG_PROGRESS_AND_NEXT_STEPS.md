# Geo RAG 项目进展与下一步开发说明

更新时间：2026-05-02

本文档用于给团队成员说明当前项目已经做到哪里、现在能运行哪些功能、还存在哪些限制，以及接下来应该如何继续开发。它不是最终论文或最终方案，而是当前阶段的协作开发交接文档。

## 1. 项目当前定位

本项目当前包含三个主要方向：

1. 地震目录模块：查询、展示、分析地震事件。
2. 论文分析模块：围绕文献、证据和问答组织科研分析能力。
3. 地质文献知识库 Geo RAG：提前入库大量地质学文献，让论文问答和地震地质分析都基于统一知识库进行检索、证据组织和回答生成。

当前目标不是马上做成完整高级 RAG 系统，而是先完成一个本地可运行、可协作开发、可继续升级的 MVP：

```text
地质学 PDF/TXT/MD
  -> 文档解析
  -> 文本切块 KnowledgeUnit
  -> 生成 embedding
  -> 写入 Qdrant 向量库
  -> 检索相关证据
  -> 大模型生成带证据的回答
  -> 前端展示检索结果、证据和质量诊断
```

后续完整系统会继续借鉴 RAGAnything 的多模态文档解析，以及 ResearchClaw 的科研分析、证据链和可审查流程。

## 2. 当前总体结论

项目现在已经进入 Geo RAG MVP 阶段，核心链路已经初步打通：

- 本地协作启动方式已经基本统一。
- 前后端可以通过 `python3 dev.py` 启动。
- 已经有地质文献知识库页面。
- 已经支持单篇文献入库、检索、问答和证据展示。
- 已经接入 Qdrant 的本地持久化模式。
- 已经支持 PyMuPDF 解析 PDF 文本。
- 已经加入更合理的混合检索和质量诊断。
- 豆包 Seed 聊天模型配置已完成，可以用于生成回答。
- 真实 bge-m3 embedding 的代码路径已准备好，但火山/VikingDB 权限当前还没有打通。

因此，当前最重要的下一步不是再大改页面，而是把真实 embedding 权限修好，然后做批量文献入库和检索质量评估。

## 3. 当前已实现功能

### 3.1 协作启动

项目根目录下已有统一启动脚本：

```bash
python3 dev.py
```

Windows 可使用：

```powershell
py dev.py
```

脚本已经承担这些工作：

- 创建后端虚拟环境。
- 安装后端依赖。
- 安装前端依赖。
- 准备 PostgreSQL/PostGIS。
- 使用项目内 pip/npm 缓存，减少重复下载。
- 避免把依赖散装到电脑其他位置。
- 依赖未变化时跳过重复安装。

与 Geo RAG 相关的额外依赖可以通过以下命令安装：

```bash
python3 dev.py setup-qdrant
```

当前策略是优先把 Qdrant 作为 Python 客户端的本地持久化库使用，数据放在项目目录内，不默认要求 Docker 或系统级服务。

### 3.2 项目目录轻量化

外部参考项目已经从主目录中清理，只保留有参考价值的快照内容：

```text
references/source-snapshots/
```

这些内容用于后续学习和借鉴，不作为当前系统直接运行依赖。

保留价值：

- RAGAnything / Agent-RAG：参考 PDF、多模态解析、chunk 入库、文档问答流程。
- ResearchClaw / AutoResearchClaw：参考科研分析 pipeline、证据链、人工审查、反幻觉流程。
- literature-review：参考文献综述、检索策略、引用校验等思路。

不建议再把完整外部项目、`.venv`、`node_modules`、运行日志、大文件输出提交进主仓库。

### 3.3 后端 Geo RAG MVP

当前新增或改造的后端能力包括：

```text
Project-Code/backend/app/geo_ids.py
Project-Code/backend/app/embedding_service.py
Project-Code/backend/app/qdrant_service.py
Project-Code/backend/app/geo_ingest_service.py
Project-Code/backend/app/evidence_service.py
Project-Code/backend/app/geo_rag_service.py
```

已经提供的主要 API：

| API | 用途 |
| --- | --- |
| `POST /api/knowledge/init` | 初始化知识库和向量库 |
| `POST /api/documents/ingest` | 单篇文献入库 |
| `GET /api/documents/{document_id}/status` | 查看文献入库状态 |
| `POST /api/knowledge/search` | 检索知识单元 |
| `POST /api/rag/papers/query` | 基于文献证据生成问答 |
| `POST /api/events/{event_id}/geo-analysis` | 基于地震事件做地质分析 |

当前入库支持：

- PDF
- TXT
- MD

当前 PDF 解析策略：

- 优先使用 PyMuPDF。
- 按页读取文本 block。
- 尝试保留页码。
- 清理页眉、页脚、断行、连字符和异常空白。
- 按段落和句子进行语义近似切块。
- 每个 chunk 形成一个 KnowledgeUnit。

当前检索策略：

- dense vector 候选召回。
- keyword 候选召回。
- metadata boost。
- 文档多样性选择。
- 返回质量诊断信息。

当前问答策略：

- 先检索证据。
- 再构建 Evidence Pack。
- 再调用聊天模型生成回答。
- 如果大模型不可用，则使用本地模板 fallback。

### 3.4 前端知识库页面

前端已经新增页面：

```text
Project-Code/Frontend/quakes-frontend/src/views/KnowledgeView.vue
```

访问路径：

```text
/knowledge
```

当前页面能力：

- 初始化知识库。
- 单篇文献入库。
- 输入检索问题并查看检索结果。
- 生成文献问答。
- 查看证据包。
- 查看检索质量诊断。
- 查看回答证据诊断。

当前页面已经能帮助团队判断：

- 文献是否成功入库。
- Qdrant 是否可用。
- 当前使用真实 embedding 还是 fallback。
- 检索结果是否过度集中在同一篇文献。
- 回答是否基于证据。

### 3.5 Qdrant 当前状态

当前已经支持 Qdrant 本地持久化模式：

```env
QDRANT_USE_LOCAL=true
QDRANT_LOCAL_PATH=./.data/qdrant-local
QDRANT_COLLECTION=geo_knowledge_v2
```

这种方式的优点：

- 不需要同事额外安装 Docker。
- 不需要系统后台服务。
- 数据保存在项目目录的 `.data/qdrant-local`。
- 将来删除项目时可以一起清理。
- 后续迁移云端 Qdrant 时，接口层不需要大改。

如果页面显示：

```text
qdrant-client is not available
```

通常说明当前后端虚拟环境还没有安装 Qdrant 依赖，或安装后没有重启服务。处理方式：

```bash
python3 dev.py setup-qdrant
python3 dev.py
```

### 3.6 大模型与 embedding 当前状态

聊天模型：

- 豆包 Seed 聊天模型的配置路径已经接入。
- 用于 `POST /api/rag/papers/query` 的回答生成。
- API key 应只放在本机 `.env` 或 `.env.local`，不要提交 Git。

Embedding：

- 目标方案：火山 / VikingDB 的 `bge-m3`。
- 目标向量维度：1024。
- 当前代码已经支持调用路径。
- 但当前账号权限仍然报错，真实 bge-m3 暂时不可用。

当前 fallback：

- 如果 VikingDB 或 OpenAI-compatible embedding 不可用，系统会退回本地 hash embedding。
- hash embedding 可以用于开发流程验证，但不适合作为最终科研问答质量依据。

团队需要特别注意：

```text
在真实 bge-m3 权限修复前，不建议大规模重建正式知识库。
否则大量文献会被 fallback hash embedding 索引，后续仍然需要重建。
```

## 4. 当前数据与文件位置

后端本地数据主要放在：

```text
Project-Code/backend/.data/
```

常见子目录：

| 路径 | 用途 |
| --- | --- |
| `.data/geo_rag_documents` | 本地文献文件 |
| `.data/qdrant-local` | Qdrant 本地向量库 |
| `.data/pip-cache` | pip 下载缓存 |
| `.data/pip-stamps` | pip 安装记录 |
| `.data/geo_rag_vector_fallback.json` | fallback 向量索引 |

这些目录属于本机运行数据，不应该提交 Git。

环境变量文件：

| 文件 | 说明 |
| --- | --- |
| `Project-Code/backend/.env.example` | 可提交的配置模板，不放真实密钥 |
| `Project-Code/backend/.env` | 每个同事自己的本地配置 |
| `Project-Code/backend/.env.local` | 本地覆盖配置，可用于团队测试，但不提交 Git |

## 5. 当前验证情况

最近一次已验证：

```bash
Project-Code/backend/.venv/bin/python -m unittest discover -s tests
npm run type-check
npm run build
```

结果：

- 后端单元测试通过。
- 前端类型检查通过。
- 前端构建通过。
- Qdrant local 初始化通过。
- 单篇 PDF 入库、检索、问答链路可以跑通。

需要注意：

- 这些验证说明 MVP 链路可运行。
- 不代表真实科研问答质量已经达标。
- 当前最大质量短板仍是 embedding 没有真正切到 bge-m3。

## 6. 当前主要限制

### 6.1 真实 embedding 权限未打通

当前 VikingDB/bge-m3 调用返回权限错误。需要在火山控制台确认：

- AK/SK 是否有效。
- 是否开通 VikingDB / 向量化服务。
- IAM 用户是否有对应服务权限。
- region 是否为 `cn-beijing`。
- host 是否为 `api-vikingdb.volces.com`。

权限打通后，运行下面的最小验证：

```bash
cd /Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend
.venv/bin/python -c "from app.embedding_service import embed_texts; r=embed_texts(['active fault rupture']); print(r.backend, r.model, len(r.vectors[0]))"
```

期望输出类似：

```text
vikingdb bge-m3 1024
```

如果仍然输出 fallback 或 hashing，说明还没有真正使用 bge-m3。

### 6.2 目前还没有批量入库

当前页面主要支持单篇文献路径入库。用户已经准备了大量文献后，下一步应该开发批量入库能力：

```text
扫描文件夹
  -> 识别 PDF/TXT/MD
  -> 计算 sha256 去重
  -> 判断是否已入库
  -> 批量解析
  -> 批量 embedding
  -> 批量写入 Qdrant
  -> 显示进度和失败原因
```

### 6.3 PDF 解析仍是文本 MVP

当前 PyMuPDF 解析已经比初始方案更可靠，但还不是完整 RAGAnything/MinerU 级别。

还缺少：

- 扫描版 PDF OCR。
- 表格结构化提取。
- 图像、图注和图表关联。
- 公式识别。
- 页内坐标精确定位。
- 引用文献区过滤。
- 章节结构识别。

MVP 阶段可以先把文本问答做好，后续再接多模态解析 adapter。

### 6.4 检索质量还需要评估集

当前有质量诊断字段，但还没有正式评测集。后续需要人工准备 20-50 个地质学问题，用于评估：

- 检索到的证据是否相关。
- 证据是否来自合适文献。
- 回答是否引用证据。
- 回答是否承认不确定性。
- 是否出现无证据推断。

### 6.5 云端迁移还没开始

当前方案是 local-first：

- 本地 PostgreSQL。
- 本地 Qdrant。
- 本地文献文件。

云端迁移还没完成。后续需要确定：

- 云端 PostgreSQL/PostGIS。
- 云端 Qdrant 或托管向量库。
- 对象存储。
- 后端部署方式。
- API key 和团队权限管理。

## 7. 下一步开发路线

### 阶段 A：先修正真实 embedding

优先级最高。

目标：

- 让 `bge-m3` 真正返回 1024 维向量。
- 页面顶部不再显示 `local-fallback` 或 `hashing` 作为主要检索后端。
- 新入库文献使用真实语义向量。

任务：

1. 在火山控制台修复 VikingDB / bge-m3 权限。
2. 用最小脚本验证 embedding。
3. 清理旧的 fallback 索引数据。
4. 重新初始化 Qdrant collection。
5. 重新入库少量测试文献。

完成标准：

```text
embedding backend = vikingdb
embedding model = bge-m3
vector size = 1024
Qdrant backend = qdrant-local
```

### 阶段 B：开发批量文献入库

目标：

- 支持把一个文件夹中的文献批量导入知识库。
- 能看到进度、成功数、失败数和失败原因。
- 支持 force rebuild。
- 支持 dry run。

建议新增 API：

| API | 用途 |
| --- | --- |
| `POST /api/documents/batch-ingest` | 批量启动入库 |
| `GET /api/documents/batch-jobs/{job_id}` | 查询入库任务状态 |
| `POST /api/documents/reindex` | 重建索引 |

前端新增能力：

- 文件夹路径输入。
- 批量入库按钮。
- 入库进度条。
- 文献列表。
- 失败详情。
- 一键重建当前知识库。

完成标准：

- 至少能批量入库 10 篇 PDF。
- 单篇失败不影响整体任务。
- 同一文件重复导入不会产生重复文档。
- 页面能显示当前文献数和知识单元数。

### 阶段 C：提升 PDF 解析质量

目标：

- 让中英文 PDF 都能更稳定地生成可检索片段。
- 减少乱码、页眉页脚、参考文献、跨栏粘连带来的干扰。

建议优化：

- 自动识别中文/英文。
- 针对中文避免不合理空格。
- 针对英文处理断词和跨行。
- 识别 Abstract、Introduction、Conclusion 等章节。
- 弱化 References 区域权重。
- 对扫描 PDF 给出明确提示：需要 OCR。

完成标准：

- 检索结果片段可读。
- 不再大量出现无空格粘连文本。
- 文献标题、页码、片段位置基本可追踪。

### 阶段 D：提升检索策略

目标：

- 从“能搜到”升级到“搜得准、证据多样、可解释”。

建议优化：

- 中英文地质术语 query expansion。
- metadata filter：年份、主题、断裂、区域、文献 ID。
- MMR 或类似多样性选择。
- reranker。
- score threshold。
- top document share 过高时自动补充其他文献。

完成标准：

- 同一问题不会只返回同一篇文献的重复片段。
- 回答证据至少覆盖 2-3 个独立来源。
- 页面能解释本次检索为什么可靠或不可靠。

### 阶段 E：加强科研问答可靠性

目标：

- 让回答更像科研辅助，而不是普通聊天。

建议流程：

```text
用户问题
  -> 查询理解
  -> 检索证据
  -> 证据筛选
  -> 生成回答
  -> 回答-证据一致性检查
  -> 输出不确定性和后续建议
```

借鉴 ResearchClaw 的位置：

- 检索规划。
- 证据筛选。
- Claim/Evidence/Citation 结构。
- 回答后校验。
- 人工审核 gate。
- 质量评分。

完成标准：

- 回答明确引用 E1、E2、E3 等证据。
- 没有证据时明确说“不足以判断”。
- 对争议性结论给出不确定性。
- 能列出还需要补充哪些文献或数据。

### 阶段 F：地震目录与文献知识库融合

目标：

- 用户点击地震事件后，系统自动基于事件信息召回地质学文献并生成解释。

建议流程：

```text
地震事件
  -> 经纬度 / 震级 / 深度 / 时间 / 区域
  -> 生成地质分析查询
  -> 检索活动断裂、构造背景、历史地震、危险性相关文献
  -> 组织 Evidence Pack
  -> 输出地质解释和不确定性
```

完成标准：

- 每个地震分析回答都带证据。
- 回答不把文献中不存在的信息说成事实。
- 能明确区分“事件数据本身”和“文献推断”。

## 8. 建议团队分工

| 角色 | 负责内容 |
| --- | --- |
| 后端 A | 批量入库、任务状态、reindex |
| 后端 B | embedding、Qdrant、云端迁移准备 |
| 后端 C | 检索策略、reranker、质量诊断 |
| 前端 | 知识库页面、批量入库 UI、证据展示 |
| 科研/算法 | 地质 schema、术语表、评测集、问题集 |
| 文档维护 | README、开发手册、接口说明 |

开发时建议遵守：

- 不直接提交 `.env`、`.env.local`、`.data`、`.venv`、`node_modules`。
- 不把外部完整项目重新塞回主目录。
- 大规模依赖安装前先确认是否真的需要。
- 能放项目目录的数据就不要放到系统目录。
- 先小批量测试，再批量入库。
- 真实 embedding 未修复前，不做正式大规模索引。

## 9. 当前同事如何继续开发

### 9.1 普通启动

```bash
cd /Users/teki/Downloads/my_project/cudtseis_web
python3 dev.py
```

启动后访问：

```text
http://127.0.0.1:5173
```

知识库页面：

```text
http://127.0.0.1:5173/knowledge
```

### 9.2 安装 Geo RAG 额外依赖

```bash
python3 dev.py setup-qdrant
```

安装后重新启动：

```bash
python3 dev.py
```

### 9.3 放置测试文献

建议放到：

```text
Project-Code/backend/.data/geo_rag_documents
```

页面目前填写的是具体文件路径，不是文件夹路径，例如：

```text
Project-Code/backend/.data/geo_rag_documents/example.pdf
```

### 9.4 入库后应该观察什么

入库后看这些信息：

- 状态是否为 `indexed`。
- parser 是否为 `pymupdf-blocks`。
- 页数是否合理。
- 知识单元数是否合理。
- embedding backend 是否为真实模型。
- vector backend 是否为 `qdrant-local`。

检索后看这些信息：

- 命中内容是否和问题相关。
- 是否来自多篇文献。
- 是否出现大段乱码。
- `qualityFlags` 是否提示结果过度集中。
- 证据包是否能支撑回答。

## 10. 下一个里程碑验收标准

下一个阶段完成后，建议用以下标准验收：

1. `bge-m3` embedding 调用成功，返回 1024 维向量。
2. Qdrant local 正常写入和检索。
3. 能批量入库至少 10 篇 PDF。
4. 中英文文献片段可读性明显提升。
5. 文献问答能引用证据 ID。
6. 回答能说明不确定性，不无证据下结论。
7. 前端能显示批量入库进度和质量诊断。
8. 后端测试通过。
9. 前端 type-check 和 build 通过。
10. 新同事按 README 和本文档可以在自己电脑上跑起来。

## 11. 近期最推荐的开发顺序

建议不要同时铺开太多方向。当前最稳的顺序是：

```text
1. 修复 bge-m3 / VikingDB 权限
2. 验证真实 embedding
3. 清理并重建 Qdrant v2 collection
4. 开发批量入库
5. 小批量导入 10-20 篇文献
6. 做检索质量评估
7. 优化 PDF 解析和 query expansion
8. 再扩大文献规模
9. 再接 RAGAnything 多模态解析
10. 再引入 ResearchClaw 式审查流程
```

一句话总结：

```text
现在项目已经能跑通 Geo RAG MVP 的基础链路，但还不能说已经达到高质量科研 RAG。下一步应先修复真实 embedding，再做批量入库、检索评估和证据可靠性增强。
```
