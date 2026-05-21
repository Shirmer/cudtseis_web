# RAGAnything 文献数据库方案

## 1. 从解析文献到生成向量库要多久

当前项目保留轻量 RAG，同时新增真实 RAGAnything 接入。

轻量摘要级流程：检索 OpenAlex、Semantic Scholar、arXiv 摘要，生成事件文档片段，再写入本地向量索引。首次通常 30 秒到 2 分钟，缓存命中后通常几秒。

RAGAnything 全文流程：服务器读取 `RAGANYTHING_DOCUMENT_DIR` 下的 PDF、Office、图片或文本文件，解析正文、图表、表格和公式，再写入 RAGAnything/LightRAG 工作目录。单篇 PDF 通常几分钟起，扫描版、含大量图表或 OCR 的文档会更慢；批量入库建议后台异步跑。

运行方式：后端服务在本机或服务器运行。RAGAnything 解析和索引文件写入在服务器本地执行；LLM、视觉模型和 embedding 默认调用 OpenAI 兼容接口。

启用配置：

```env
RAGANYTHING_ENABLED=true
OPENAI_API_KEY=你的key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RAGANYTHING_WORKING_DIR=/data/cudtseis/raganything
RAGANYTHING_OUTPUT_DIR=/data/cudtseis/raganything_output
RAGANYTHING_DOCUMENT_DIR=/data/cudtseis/documents
```

新增接口：

- `GET /api/raganything/status`
- `POST /api/raganything/events`
- `POST /api/raganything/documents`
- `POST /api/raganything/query`

## 2. 文献太多时速度和准确率怎么处理

文献规模变大后，检索速度会下降，准确率也可能下降。原因是候选 chunk 更多、无关语义噪声更多。

推荐方案：

- 分层库：题录摘要大库 + 精选全文小库。
- 分主题/区域/任务索引：按地震区域、构造类型、余震序列、危险性、InSAR/GNSS/波形反演等分区。
- 元数据过滤优先：先按年份、区域、主题、期刊、开放获取、文献类型过滤，再向量检索。
- 混合检索：向量检索 + BM25 + 元数据过滤 + rerank。
- 生产向量库：小规模可用本地文件；正式系统建议 PostgreSQL + pgvector 或 Qdrant。

本项目推荐路线：

```text
PostgreSQL 元数据
+ pgvector/Qdrant 向量索引
+ RAGAnything 全文多模态解析
+ BM25/关键词检索
+ rerank 重排
```

## 3. 大量下载和筛选优质文献

优先来源：

- OpenAlex：大规模题录、摘要、DOI、引用、期刊和机构元数据。
- Crossref：DOI、出版商、期刊和出版记录校验。
- Semantic Scholar：摘要、引用、相关论文和学科标签。
- Unpaywall、DOAJ、PubMed Central、arXiv、EarthArXiv：开放获取全文。
- 出版社平台：AGU、ScienceDirect、Springer、Wiley、Nature、IEEE 等，只处理授权或开放获取全文。

筛选规则：

- 基础筛选：年份、语言、是否有 DOI、是否有摘要、是否开放获取、文献类型。
- 质量筛选：引用量、期刊/出版社可信度、同行评议、综述/经典高引/方法论文。
- 领域筛选：地震、断层、构造、震源机制、余震、危险性、InSAR、GNSS、波形反演、目标区域关键词。

推荐入库流程：

```text
检索题录
-> DOI/title 去重
-> 元数据质量筛选
-> 开放获取/授权校验
-> 下载 PDF
-> RAGAnything 解析
-> chunk + 图表/表格/公式结构化
-> metadata 入 PostgreSQL
-> embedding 入 pgvector/Qdrant
-> 混合检索和 rerank
```

版权策略：优先下载开放获取全文；非开放获取文献只保存题录、摘要、DOI、链接和机构授权范围内允许保存的内容。
