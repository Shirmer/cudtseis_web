# RAG-Anything & LightRAG 官方 Python API 参考

---

## 一、LightRAG 官方 API

包路径：`from lightrag import LightRAG, QueryParam`

### 1.1 构造函数

```python
rag = LightRAG(
    working_dir="./rag_storage",    # 工作目录
    llm_model_func=...,              # LLM 模型函数
    embedding_func=...,              # 嵌入函数
    kv_storage="JsonKVStorage",      # KV 存储后端
    vector_storage="NanoVectorDBStorage",  # 向量存储后端
    graph_storage="NetworkXStorage", # 图存储后端
    doc_status_storage="JsonDocStatusStorage",  # 文档状态后端
    top_k=40,                        # 查询 top_k
    chunk_token_size=1200,           # 分块大小
    chunk_overlap_token_size=100,    # 分块重叠
    max_entity_tokens=6000,          # 实体 token 上限
    max_relation_tokens=8000,        # 关系 token 上限
    max_tokens=32768,                # LLM token 上限
    llm_model_name="...",            # LLM 模型名
    enable_llm_cache=True,           # LLM 缓存
    enable_llm_cache_for_extract=True,
    cosine_threshold=0.2,            # 向量检索阈值
    embedding_batch_num=10,          # 嵌入批大小
    embedding_func_max_async=8,      # 嵌入最大并发
    max_parallel_insert=2,           # 最大并行插入
    max_async=4,                     # 最大并发 LLM 调用
    rerank_model_func=...,           # 重排序函数
    # 存储后端自定义参数
    kv_storage_cls_kwargs={},
    vector_db_storage_cls_kwargs={},
    graph_storage_cls_kwargs={},
)
```

### 1.2 核心方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `initialize_storages()` | `async () -> None` | 初始化所有存储 |
| `ainsert` | `async (input, file_paths=None, ids=None, ...) -> str` | 插入文档文本，返回 tracking_id |
| `aquery` | `async (query, param=None) -> str` | 完整 RAG 问答 |
| `aquery_data` | `async (query, param=None) -> any` | 仅检索数据，不调用 LLM |
| `aquery_llm` | `async (query, param=None) -> str` | 问答 + 返回结构化响应 |
| `adelete_by_doc_id` | `async (doc_id) -> bool` | 按文档 ID 删除知识库数据 |
| `adelete_by_entity` | `async (entity_name) -> bool` | 按实体名删除 |
| `get_doc_status` | `(doc_id) -> dict` | 获取文档处理状态 |
| `get_doc` | `(doc_id) -> dict` | 获取文档详情 |
| `get_all_documents` | `() -> list` | 获取所有文档列表 |
| `finalize_storages` | `async () -> None` | 关闭存储连接 |

### 1.3 QueryParam（查询参数）

```python
param = QueryParam(
    mode="mix",                # 模式: local/global/hybrid/naive/mix/bypass
    top_k=40,                  # 返回实体/关系数
    chunk_top_k=20,            # 返回 chunk 数
    max_entity_tokens=6000,    # 实体上下文 token 上限
    max_relation_tokens=8000,  # 关系上下文 token 上限
    max_total_tokens=30000,    # 总 token 上限
    cosine_threshold=0.2,      # 向量检索余弦阈值
    enable_rerank=False,       # 是否启用重排序
    stream=False,              # 是否流式输出
    temperature=1.0,           # LLM 温度
    top_p=1.0,                 # LLM top_p
    max_tokens=32768,          # LLM 最大输出 token
)
```

### 1.4 存储后端枚举

| 后端类型 | 文件版（默认） | 生产版可迁移至 |
|----------|--------------|---------------|
| KV 存储 | `JsonKVStorage` | `PGKVStorage`, `RedisKVStorage`, `MongoKVStorage` |
| 向量存储 | `NanoVectorDBStorage` | `MilvusVectorDBStorage`, `QdrantVectorDBStorage`, `FaissVectorDBStorage`, `PGVectorStorage` |
| 图存储 | `NetworkXStorage` | `Neo4JStorage`, `ArangoDBStorage` |
| 文档状态 | `JsonDocStatusStorage` | `PGDocStatusStorage` |

### 1.5 LLM 绑定

`lightrag/llm/` 目录下 15+ 种：

`openai`, `ollama`, `azure_openai`, `anthropic`, `bedrock`, `gemini`, `hf`(HuggingFace), `jina`, `llama_index`, `lmdeploy`, `lollms`, `nvidia_openai`, `voyageai`, `zhipu`

### 1.6 内置 API Server

`lightrag/api/lightrag_server.py` — 自带完整的 FastAPI REST 服务 + 认证 + Web UI + Swagger 文档

---

## 二、RAG-Anything 官方 API

包路径：`from raganything import RAGAnything, RAGAnythingConfig`

### 2.1 构造函数

```python
rag = RAGAnything(
    lightrag=None,                # 预初始化的 LightRAG 实例
    llm_model_func=...,            # LLM 模型函数
    vision_model_func=...,          # 视觉模型函数
    embedding_func=...,             # 嵌入函数
    config=RAGAnythingConfig(...),  # 配置
    lightrag_kwargs={},            # 传给 LightRAG 的额外参数
)
```

### 2.2 RAGAnythingConfig（所有配置项）

| 分类 | 字段 | 默认值 | 说明 |
|------|------|--------|------|
| 目录 | `working_dir` | `"./rag_storage"` | 工作目录 |
| | `parser_output_dir` | `"./output"` | 解析输出目录 |
| 解析 | `parse_method` | `"auto"` | 解析方法 |
| | `parser` | `"mineru"` | 解析器: mineru / docling / paddleocr |
| | `display_content_stats` | `True` | 显示内容统计 |
| 多模态 | `enable_image_processing` | `True` | 图片处理 |
| | `enable_table_processing` | `True` | 表格处理 |
| | `enable_equation_processing` | `True` | 公式处理 |
| 批量 | `max_concurrent_files` | `1` | 最大并发文件数 |
| | `recursive_folder_processing` | `True` | 递归处理文件夹 |
| 上下文 | `context_window` | `1` | 上下文窗口大小 |
| | `context_mode` | `"page"` | page / chunk |
| | `max_context_tokens` | `2000` | 上下文 token 上限 |
| | `include_headers` | `True` | 包含页眉 |
| | `include_captions` | `True` | 包含标题 |
| | `content_format` | `"minerU"` | 内容格式 |
| 路径 | `use_full_path` | `False` | 使用完整路径 |

### 2.3 文档处理（ProcessorMixin）

| 方法 | 返回 | 说明 |
|------|------|------|
| `parse_document(file_path, ...)` | `(List[Dict], str)` | 解析文档为 content_list + doc_id |
| `process_document_complete(file_path, ...)` | `None` | 一键全流程：解析→分离→插入文本→处理多模态 |
| `process_document_complete_lightrag_api(file_path, ...)` | `bool` | 供 LightRAG 调用的全流程 API |
| `insert_content_list(content_list, ...)` | `None` | 直接插入已解析的 content_list |
| `is_document_fully_processed(doc_id)` | `bool` | 检查文档是否完全处理（含多模态） |
| `get_document_processing_status(doc_id)` | `Dict` | 获取文档处理状态详情 |
| `finalize_storages()` | `None` | 清理存储 |

### 2.4 查询（QueryMixin）

| 方法 | 返回 | 说明 |
|------|------|------|
| `aquery(query, mode="mix", ...)` | `str` | 文本问答（6种模式） |
| `aquery_with_multimodal(query, multimodal_content, ...)` | `str` | 含多模态内容的问答 |
| `aquery_vlm_enhanced(query, extra_safe_dirs=None, ...)` | `str` | VLM 增强问答（图片自动 base64） |
| `query(query, mode="mix", ...)` | `str` | aquery 同步版本 |
| `query_with_multimodal(query, multimodal_content, ...)` | `str` | aquery_with_multimodal 同步版本 |

### 2.5 批量处理（BatchMixin）

| 方法 | 返回 | 说明 |
|------|------|------|
| `process_folder_complete(folder_path, ...)` | `None` | 递归处理整个文件夹 |
| `process_documents_batch(file_paths, ...)` | `BatchProcessingResult` | 同步批量解析 |
| `process_documents_batch_async(file_paths, ...)` | `BatchProcessingResult` | 异步批量解析 |
| `process_documents_with_rag_batch(file_paths, ...)` | `Dict` | 两步批量：先解析再统一入库 |

**BatchProcessingResult 字段：**
`successful_files`, `failed_files`, `total_files`, `processing_time`, `errors`, `output_dir`, `success_rate`, `summary()`

### 2.6 解析器（Parser）

| 解析器 | 新建值 | 支持格式 |
|--------|--------|----------|
| `MineruParser` | `"mineru"` | PDF, 图片, Office, TXT, MD |
| `DoclingParser` | `"docling"` | PDF, Office, HTML |
| `PaddleOCRParser` | `"paddleocr"` | PDF, 图片, Office, TXT |

Parser 基类方法：`parse_pdf()`, `parse_image()`, `parse_document()`, `check_installation()`, `convert_office_to_pdf()`, `convert_text_to_pdf()`

Parser 注册系统：`register_parser()`, `unregister_parser()`, `list_parsers()`, `get_parser()`

### 2.7 多模态处理器（ModalProcessor）

| 处理器 | 处理类型 | 功能 |
|--------|----------|------|
| `ImageModalProcessor` | `"image"` | VLM 分析图片 → 描述 + 实体 + 关系 |
| `TableModalProcessor` | `"table"` | LLM 分析表格 → 结构化描述 + 实体 + 关系 |
| `EquationModalProcessor` | `"equation"` | LLM 分析公式 → LaTeX + 描述 + 实体 + 关系 |
| `GenericModalProcessor` | 其他 | LLM 分析通用内容 |

每个处理器提供：`generate_description_only()` / `process_multimodal_content()`

### 2.8 上下文提取（ContextExtractor）

| 方法 | 说明 |
|------|------|
| `extract_context(content_source, current_item_info)` | 提取多模态项周围的上下文 |
| `_extract_from_content_list()` | MinerU 风格提取 |
| `_extract_page_context()` | 基于页面的上下文窗口 |
| `_extract_chunk_context()` | 基于 chunk 的上下文窗口 |

### 2.9 回调系统（Callback）

**17 个钩子覆盖全流程：**

| 阶段 | 钩子 |
|------|------|
| 解析 | `on_parse_start` / `on_parse_complete` / `on_parse_error` |
| 文本插入 | `on_text_insert_start` / `on_text_insert_complete` |
| 多模态 | `on_multimodal_start` / `on_multimodal_item_complete` / `on_multimodal_complete` |
| 查询 | `on_query_start` / `on_query_complete` / `on_query_error` |
| 文档 | `on_document_complete` / `on_document_error` |
| 批量 | `on_batch_start` / `on_batch_complete` |

**内置实现：**
- `ProcessingCallback` — 抽象基类
- `MetricsCallback` — 指标收集（文档数/耗时/错误/查询数）
- `CallbackManager` — 注册/分发/事件日志

### 2.10 韧性工具

```python
from raganything import retry, async_retry, CircuitBreaker

@retry(max_attempts=3, base_delay=1.0, max_delay=60.0,
       exponential_base=2.0, jitter=True)
def sync_func(): ...

@async_retry(max_attempts=3, ...)
async def async_func(): ...

cb = CircuitBreaker(failure_threshold=5, reset_timeout=60.0)
```

默认自动重试：ConnectionError, TimeoutError, httpx.*, openai.* 等

### 2.11 Prompt 系统

```python
from raganything import set_prompt_language, get_prompt_language

set_prompt_language("zh")   # 切换到中文 Prompt
set_prompt_language("en")   # 切回英文
```

内置中英文 Prompt 模板，覆盖：实体提取、图片/表格/公式分析、查询增强

### 2.12 支持的文件格式

```
PDF / JPG / JPEG / PNG / BMP / TIFF / GIF / WebP
DOC / DOCX / PPT / PPTX / XLS / XLSX / TXT / MD
```

---

## 三、当前 rag-api 覆盖度

| 功能 | 开发者的 REST 接口 | 使用的官方 API |
|------|------------------|---------------|
| 文档上传 | `POST /documents` | 无，仅存文件 |
| 文档列表 | `GET /documents` | 无，走 SQLite |
| 文档删除 | `DELETE /documents/{id}` | 无，仅删 SQLite + 文件 |
| 云解析 | `POST /documents/batch-cloud-ingest` | 无，自己调 MinerU API |
| content_list 入库 | `POST /content-list/insert` | `rag.insert_content_list()` |
| 问答 | `POST /chat` | `rag.aquery()` |
| 知识库统计 | `GET /stats` | 无，SQLite 查询 |

**未使用的官方功能：**
- `rag.process_document_complete()` — 一键全流程
- `rag.aquery_with_multimodal()` — 多模态问答
- `rag.aquery_vlm_enhanced()` — VLM 增强
- `rag.is_document_fully_processed()` — 处理状态
- `rag.get_document_processing_status()` — 详细状态
- `rag.process_folder_complete()` — 批量文件夹
- LightRAG `adelete_by_doc_id()` — 知识库删除
- LightRAG `aquery_data()` — 纯检索
- LightRAG `get_doc_status()` — 文档状态
- Callback 系统 / CircuitBreaker / Prompt 切换
- 所有 Parser 绑定
- 所有存储后端切换
