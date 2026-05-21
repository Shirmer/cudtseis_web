# RAGAnything-main 源码分析与项目接入说明

本文说明项目根目录 `RAG-Anything-main/` 的作用，以及它如何接入当前网站。

## 1. 结论

`RAG-Anything-main/` 是完整上游源码，当前版本为 `1.3.0`。它应作为本项目文献 RAG 的核心引擎层使用。

本项目不再复制或重写 RAGAnything 的核心解析、图文表公式处理和 LightRAG 检索逻辑，而是在后端做一层适配：

1. 用户在网页上传或选择 PDF/TXT/MD。
2. 后端把文件保存到项目配置的文献目录。
3. 后端调用 `RAGAnything.process_document_complete()`。
4. RAGAnything 调用 MinerU 解析文献，并将正文、图片、表格、公式等内容交给 LightRAG 入库。
5. 用户检索或问答时，后端调用 `RAGAnything.aquery()`。
6. 项目自己的 PostgreSQL 仍保存文献元数据、原文路径、地震目录、问答记录和产品侧状态。

## 2. RAGAnything-main 的核心结构

- `raganything/raganything.py`  
  总入口，组合配置、Parser、LightRAG、上下文抽取器、多模态处理器和回调机制。

- `raganything/config.py`  
  配置中心，包括工作目录、解析器、解析方式、解析输出目录、多模态开关、上下文窗口等。

- `raganything/processor.py`  
  文献处理主流程。核心方法是 `process_document_complete()`，流程包括解析文献、拆分正文和多模态内容、写入 LightRAG、处理图表公式、更新文档状态。

- `raganything/parser.py`  
  解析器入口，支持 MinerU 等解析方式。PDF 的正文、标题、图、表、公式、图注、表注等结构化结果主要从这里产生。

- `raganything/modalprocessors.py`  
  多模态处理器。包含图片、表格、公式、通用内容处理，并通过 `ContextExtractor` 为图表公式补充上下文。

- `raganything/query.py`  
  查询入口。核心方法是 `aquery()`，支持 `local/global/hybrid/naive/mix` 等 LightRAG 查询模式，也支持 VLM 增强查询。

- `raganything/callbacks.py`  
  处理过程回调，可用于后续做导入进度、耗时统计、失败诊断。

- `raganything/resilience.py`  
  重试、熔断等可靠性工具，后续可用于增强批量导入稳定性。

- `raganything/prompt_manager.py` 和 `prompts_zh.py`  
  多语言 Prompt 管理，后续可用于中文科研问答提示词。

## 3. 当前项目如何接入

后端配置项：

```env
GEO_RAG_ENGINE=raganything
RAGANYTHING_ENABLED=true
RAGANYTHING_SOURCE_DIR=RAG-Anything-main
RAGANYTHING_WORKING_DIR=Project-Code/backend/.data/raganything
RAGANYTHING_OUTPUT_DIR=Project-Code/backend/.data/raganything_output
RAGANYTHING_DOCUMENT_DIR=Project-Code/backend/.data/geo_rag_documents
RAGANYTHING_PARSER=mineru
RAGANYTHING_PARSE_METHOD=auto
RAGANYTHING_QUERY_MODE=hybrid
```

后端启动时会优先把 `RAGANYTHING_SOURCE_DIR` 加入 Python import 路径，因此实际导入的是项目里的完整源码。如果该目录不存在，会回退到 `.venv` 中 pip 安装的 `raganything`。

检查接口：

```bash
curl http://127.0.0.1:8001/api/raganything/status
```

重点看：

- `ready` 是否为 `true`
- `dependencies.raganythingOrigin` 是否指向 `RAG-Anything-main/raganything/__init__.py`
- `dependencies.version` 是否为 `1.3.0`
- `sourceSnapshot.upstreamSource.complete` 是否为 `true`

## 4. 网页功能对应关系

- `知识库导入` 页面  
  对应后端 `/api/documents/upload` 和 `/api/documents/ingest`。上传后的文献会进入 RAGAnything 解析和入库流程。

- `论文检索` 页面  
  对应后端 `/api/knowledge/search`。最终应以 RAGAnything/LightRAG 的混合检索结果为主。

- `证据问答 / 工作台问答`  
  对应 RAG 问答链路。最终应基于 RAGAnything 返回的证据上下文，再由项目自己的科研审查层组织回答。

## 5. 仍需继续完善的部分

1. 批量导入任务需要做后台任务队列，避免大 PDF 解析时阻塞网页请求。
2. 导入进度需要接入 RAGAnything callbacks，显示当前处于解析、正文入库、多模态处理还是完成阶段。
3. 检索结果需要统一映射回项目自己的文献 ID、页码、原文 URL，保证“查看上下文”和“打开原文”稳定。
4. 中文问答可以接入 `prompt_manager.py` 和 `prompts_zh.py`，让回答更贴合中文科研场景。
5. 云端部署时，`RAG-Anything-main/`、PDF 原文目录、RAGAnything 工作目录都应放在服务器同一个项目目录或持久化存储目录下。

