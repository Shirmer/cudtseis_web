# RAGAnything 主引擎与阿里云轻量服务器部署说明

本文档说明当前项目的最终 RAG 方向：文献 RAG 只保留一个主引擎，即 `RAGAnything + LightRAG + MinerU`。项目自己的 FastAPI/Vue/PostgreSQL 负责产品层、地震目录、文献元数据、PDF 文件管理和问答记录。

## 1. 最终架构

```text
浏览器
  -> Vue 前端
  -> FastAPI 后端
  -> PostgreSQL/PostGIS：地震目录、文献元数据、PDF 路径、问答记录
  -> RAGAnything/LightRAG：文献解析、实体关系、RAG 检索、知识库索引
  -> MinerU：PDF 多模态解析
  -> TEI / BAAI-bge-m3：embedding 服务
  -> 豆包/其他 OpenAI 兼容模型：问答和推理
```

不再采用“双写”：

```text
文献 -> 旧自研 chunk 索引
     -> RAGAnything 镜像索引
```

新的主链路是：

```text
文献上传/导入
  -> 保存原 PDF 到服务器目录
  -> PostgreSQL 记录文献元数据和文件位置
  -> RAGAnything/MinerU/LightRAG 解析与入库
  -> 问答直接走 RAGAnything
```

## 2. 服务器推荐目录

阿里云轻量服务器上建议统一使用：

```bash
/opt/cudtseis_web
/opt/cudtseis_web/storage
/opt/cudtseis_web/storage/geo_rag_documents
/opt/cudtseis_web/storage/geo_rag_upload_stage
/opt/cudtseis_web/storage/raganything
/opt/cudtseis_web/storage/raganything_output
/opt/cudtseis_web/storage/tei-cache
```

含义：

- `geo_rag_documents`：保存原 PDF/TXT/MD。
- `geo_rag_upload_stage`：前端上传的临时文件。
- `raganything`：LightRAG/RAGAnything 工作目录。
- `raganything_output`：MinerU 解析输出。
- `tei-cache`：embedding 模型缓存。

## 3. 后端关键环境变量

服务器上的 `Project-Code/backend/.env.local` 推荐：

```env
DATABASE_URL=postgresql+psycopg://cudtseis:你的强密码@127.0.0.1:5432/quakes

OPENAI_API_KEY=你的豆包或其他模型 API Key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
GEO_RAG_CHAT_MODEL=doubao-seed-2-0-lite-260215
RAGANYTHING_LLM_MODEL=doubao-seed-2-0-lite-260215

GEO_RAG_ENGINE=raganything
RAGANYTHING_ENABLED=true
RAGANYTHING_WORKING_DIR=/opt/cudtseis_web/storage/raganything
RAGANYTHING_OUTPUT_DIR=/opt/cudtseis_web/storage/raganything_output
RAGANYTHING_DOCUMENT_DIR=/opt/cudtseis_web/storage/geo_rag_documents
RAGANYTHING_PARSER=mineru
RAGANYTHING_PARSE_METHOD=auto
RAGANYTHING_QUERY_MODE=hybrid

GEO_RAG_EMBEDDING_PROVIDER=http
GEO_RAG_EMBEDDING_URL=http://127.0.0.1:8080/v1/embeddings
GEO_RAG_EMBEDDING_API_KEY=
GEO_RAG_EMBEDDING_ALLOW_FALLBACK=false
GEO_RAG_EMBEDDING_MODEL=BAAI/bge-m3
GEO_RAG_EMBEDDING_DIM=1024
GEO_RAG_EMBEDDING_BATCH_SIZE=32

GEO_RAG_STORAGE_BACKEND=local
GEO_RAG_STORAGE_ROOT=/opt/cudtseis_web/storage/geo_rag_documents
GEO_RAG_UPLOAD_STAGE_ROOT=/opt/cudtseis_web/storage/geo_rag_upload_stage
GEO_RAG_STORAGE_PUBLIC_BASE_URL=http://服务器公网IP/files/geo_rag_documents
```

注意：这里的 `local` 指服务器本地目录，不是开发者自己的电脑。

## 4. 服务器需要的服务

最低需要：

- PostgreSQL/PostGIS
- FastAPI 后端
- Vue 前端或 Nginx 静态文件
- TEI embedding 服务
- RAGAnything/MinerU 依赖

旧自研向量索引已从文献 RAG 主链路移除。当前最终方向是只维护 RAGAnything/LightRAG 一套文献索引，避免同一篇文献在两套索引中状态不一致。

## 5. 开发原则

后续代码开发遵守以下原则：

1. 文献 RAG 主引擎只走 RAGAnything。
2. PostgreSQL 只保存业务元数据、状态、路径和记录，不再承担主检索 chunk 索引。
3. 原 PDF 必须保存在服务器目录，前端“打开原文”应从服务器 URL 打开。
4. embedding 配置由项目统一管理，RAGAnything 也复用 `GEO_RAG_EMBEDDING_*`。
5. ResearchClaw 式知识卡片作为问答后的审查/结构化层，不替代 RAGAnything 的检索底座。

## 6. 就绪检查

后端启动后先检查：

```bash
curl http://127.0.0.1:8001/api/raganything/status
```

重点看：

- `ready`：是否可以真正执行 RAGAnything 入库和问答。
- `dependencies.missing`：当前虚拟环境缺哪些运行依赖。
- `dependencies.raganythingOrigin`：当前后端实际导入的 RAGAnything 来源，优先应指向 `RAG-Anything-main/raganything/__init__.py`。
- `sourceSnapshot.upstreamSource.complete`：项目根目录的完整 RAGAnything 上游源码是否完整。
- `requiredActions`：下一步应该执行什么。

说明：当前运行时优先使用项目根目录的 `RAG-Anything-main` 完整源码；`.venv` 中通过 `python3 dev.py setup-raganything` 安装的包主要提供运行依赖和兜底。旧 `references/source-snapshots` 快照已清理，不再参与开发或运行。
