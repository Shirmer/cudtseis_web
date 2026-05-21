# RAG-Anything + LightRAG 功能清单

> 当前环境：RAG-Anything v1.3.0 / LightRAG v1.4.16
> 安装位置：`/opt/rag-system/RAG-Anything/`

---

## 目录

- [一、LightRAG（底层引擎）](#一lightrag底层引擎)
  - [1.1 查询模式](#11-查询模式)
  - [1.2 存储后端](#12-存储后端)
  - [1.3 核心 API](#13-核心-api)
  - [1.4 查询参数（QueryParam）](#14-查询参数queryparam)
  - [1.5 内置 API Server](#15-内置-api-server)
  - [1.6 LLM 绑定支持](#16-llm-绑定支持)
  - [1.7 默认常量](#17-默认常量)
- [二、RAG-Anything（上层封装）](#二rag-anything上层封装)
  - [2.1 文档处理全流程](#21-文档处理全流程)
  - [2.2 核心类 RAGAnything](#22-核心类-raganything)
  - [2.3 RAGAnythingConfig 配置](#23-raganythingconfig-配置)
  - [2.4 ProcessorMixin（文档处理）](#24-processormixin文档处理)
  - [2.5 QueryMixin（查询）](#25-querymixin查询)
  - [2.6 BatchMixin（批量处理）](#26-batchmixin批量处理)
  - [2.7 解析器 Parser](#27-解析器-parser)
  - [2.8 多模态处理器 ModalProcessor](#28-多模态处理器-modalprocessor)
  - [2.9 上下文提取 ContextExtractor](#29-上下文提取-contextextractor)
  - [2.10 回调系统 Callback](#210-回调系统-callback)
  - [2.11 韧性工具（Retry / CircuitBreaker）](#211-韧性工具retry--circuitbreaker)
  - [2.12 Prompt 系统](#212-prompt-系统)
  - [2.13 工具函数](#213-工具函数)
  - [2.14 EnhancedMarkdown 转换](#214-enhancedmarkdown-转换)
  - [2.15 OMML 公式提取](#215-omml-公式提取)
  - [2.16 支持的文件格式](#216-支持的文件格式)
- [三、Content List 数据格式](#三content-list-数据格式)
- [四、当前 rag-api 覆盖度对比](#四当前-rag-api-覆盖度对比)

---

## 一、LightRAG（底层引擎）

### 1.1 查询模式

| 模式 | 值 | 说明 |
|------|-----|------|
| Local | `"local"` | 本地检索：基于实体/向量匹配，响应快、精确度高 |
| Global | `"global"` | 全局检索：基于知识图谱关系遍历，宏观概括能力强 |
| Hybrid | `"hybrid"` | 混合检索：local + global 组合 |
| Naive | `"naive"` | 朴素检索：纯 chunk 向量检索，不构建知识图谱 |
| Mix | `"mix"` | 混合模式（默认）：自动融合多路检索结果 |
| Bypass | `"bypass"` | 绕过检索：直接调用 LLM，不做 RAG |

### 1.2 存储后端

| 层级 | 可用后端 | 当前使用 |
|------|----------|----------|
| **KV 存储** | `JsonKVStorage`, `PGKVStorage`, `RedisKVStorage`, `MongoKVStorage` | `JsonKVStorage`（JSON 文件） |
| **向量存储** | `NanoVectorDBStorage`, `MilvusVectorDBStorage`, `QdrantVectorDBStorage`, `FaissVectorDBStorage`, `PGVectorStorage` | `NanoVectorDBStorage`（JSON 文件） |
| **图存储** | `NetworkXStorage`, `Neo4JStorage`, `ArangoDBStorage` | `NetworkXStorage`（GraphML 文件） |
| **文档状态** | `JsonDocStatusStorage`, `PGDocStatusStorage` | `JsonDocStatusStorage`（JSON 文件） |

### 1.3 核心 API

| 方法 | 用途 |
|------|------|
| `rag.initialize_storages()` | 初始化所有存储（必调） |
| `rag.ainsert(text, file_paths=..., ids=...)` | 插入文档文本，返回 tracking_id |
| `rag.aquery(query, param=QueryParam(...))` | 完整 RAG 问答 |
| `rag.aquery_data(query, param)` | 仅检索数据，不调 LLM |
| `rag.aquery_llm(query, param)` | 问答 + 返回结构化响应 |
| `rag.adelete_by_doc_id(doc_id)` | 按文档 ID 删除 |
| `rag.adelete_by_entity(entity_name)` | 按实体名删除 |
| `rag.get_doc_status(doc_id)` | 获取文档处理状态 |
| `rag.get_doc(doc_id)` | 获取文档详情 |
| `rag.get_all_documents()` | 获取所有文档列表 |
| `rag.finalize_storages()` | 关闭所有存储连接（清理用） |

### 1.4 查询参数（QueryParam）

```python
from lightrag import QueryParam

param = QueryParam(
    mode="mix",                # 查询模式
    top_k=40,                  # 返回的实体/关系数
    chunk_top_k=20,            # 返回的 chunk 数
    max_entity_tokens=6000,    # 实体上下文 token 上限
    max_relation_tokens=8000,  # 关系上下文 token 上限
    max_total_tokens=30000,    # 总上下文 token 上限
    cosine_threshold=0.2,      # 向量检索余弦阈值
    enable_rerank=False,       # 是否启用重排序
    stream=False,              # 是否流式输出
    temperature=1.0,           # LLM 温度
    top_p=1.0,                 # LLM top_p
    max_tokens=32768,          # LLM 最大输出 token
)
```

### 1.5 内置 API Server

位于 `lightrag/api/lightrag_server.py`，自带：

- **路由**：文档管理、查询、图谱可视化、Ollama 代理
- **认证**：JWT / Auth 账号体系
- **Web UI**：React/Vite 前端
- **部署**：支持 Gunicorn 生产部署
- **Swagger**：自动生成 API 文档

### 1.6 LLM 绑定支持

支持 15+ 种 LLM 后端：

| 模块 | 提供者 |
|------|--------|
| `openai.py` | OpenAI / 兼容 API |
| `ollama.py` | Ollama 本地模型 |
| `anthropic.py` | Anthropic Claude |
| `bedrock.py` | AWS Bedrock |
| `gemini.py` | Google Gemini |
| `hf.py` | HuggingFace 模型 |
| `jina.py` | Jina AI（嵌入） |
| `lmdeploy.py` | LMDeploy |
| `lollms.py` | LOLLMs |
| `nvidia_openai.py` | NVIDIA |
| `voyageai.py` | Voyage AI（嵌入） |
| `zhipu.py` | 智谱 AI |
| `azure_openai.py` | Azure OpenAI |
| `llama_index_impl.py` | LlamaIndex |

### 1.7 默认常量

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_TOP_K` | 40 | 查询返回实体/关系数 |
| `DEFAULT_CHUNK_TOP_K` | 20 | 查询返回 chunk 数 |
| `DEFAULT_COSINE_THRESHOLD` | 0.2 | 向量检索阈值 |
| `DEFAULT_MAX_GLEANING` | 1 | 实体提取重新扫描次数 |
| `DEFAULT_MAX_GRAPH_NODES` | 1000 | 图谱返回最大节点数 |
| `DEFAULT_SUMMARY_LANGUAGE` | `"English"` | 摘要语言 |
| `DEFAULT_CHUNK_SIZE` | 1200 | 文本分块大小 |
| `DEFAULT_CHUNK_OVERLAP` | 100 | 分块重叠 |
| `DEFAULT_MAX_ASYNC` | 4 | 最大并发 LLM 调用数 |
| `DEFAULT_MAX_PARALLEL_INSERT` | 2 | 最大并行插入数 |
| `DEFAULT_LLM_TIMEOUT` | 180 | LLM 超时（秒） |
| `DEFAULT_TEMPERATURE` | 1.0 | LLM 温度 |

---

## 二、RAG-Anything（上层封装）

### 2.1 文档处理全流程

```
输入文件（PDF/TXT/MD/图片/Office）
        │
        ▼
  Parser（MinerU / Docling / PaddleOCR）
        │
        ▼
  ┌─ content_list（JSON 数组，含文本 + 图片 + 表格 + 公式）
  │
  ├──→ 文本内容 → LightRAG ainsert（分块 → 向量化 → 实体/关系提取 → 知识图谱）
  │
  └──→ 多模态内容 → ModalProcessor（逐项分析，生成实体/关系/chunk）
           ├── ImageModalProcessor    （视觉模型分析图片）
           ├── TableModalProcessor    （LLM 分析表格结构）
           ├── EquationModalProcessor （LLM 分析公式）
           └── GenericModalProcessor  （LLM 分析通用内容）
```

### 2.2 核心类 RAGAnything

继承自三个 Mixin：`QueryMixin` + `ProcessorMixin` + `BatchMixin`

#### 构造参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lightrag` | `Optional[LightRAG]` | `None` | 预初始化的 LightRAG 实例 |
| `llm_model_func` | `Optional[Callable]` | `None` | LLM 模型函数 |
| `vision_model_func` | `Optional[Callable]` | `None` | 视觉模型函数 |
| `embedding_func` | `Optional[Callable]` | `None` | 嵌入函数 |
| `config` | `Optional[RAGAnythingConfig]` | `None` | 配置对象（自动创建） |
| `lightrag_kwargs` | `Dict[str, Any]` | `{}` | 透传给 LightRAG 的额外参数 |

#### 实例方法

| 方法 | 用途 |
|------|------|
| `parse_document(file_path)` | 仅解析文档，返回 `(content_list, doc_id)` |
| `process_document_complete(file_path)` | 一键全流程：解析 → 分离 → 插入文本 → 处理多模态 |
| `insert_content_list(content_list, ...)` | 直接插入已解析的 content_list（不重复解析） |
| `aquery(query, mode="mix")` | 文本问答 |
| `aquery_with_multimodal(query, multimodal_content)` | 含多模态内容的问答 |
| `aquery_vlm_enhanced(query, extra_safe_dirs=None)` | VLM 增强问答（图片自动 base64 编码） |
| `process_folder_complete(folder_path)` | 批量处理整个文件夹 |
| `process_documents_batch(file_paths)` | 同步批量处理多文件 |
| `process_documents_batch_async(file_paths)` | 异步批量处理多文件 |
| `process_documents_with_rag_batch(file_paths)` | 两步批量：先解析再统一入库 |
| `is_document_fully_processed(doc_id)` | 检查文档是否完全处理（文本+多模态） |
| `get_document_processing_status(doc_id)` | 获取文档详细处理状态 |
| `finalize_storages()` | 清理所有存储资源 |
| `close()` | 清理资源（处理异步上下文） |
| `check_parser_installation()` | 检查解析器是否安装 |
| `get_config_info()` | 获取完整配置信息 |
| `get_processor_info()` | 获取处理器状态信息 |
| `update_config(**kwargs)` | 动态更新配置 |
| `update_context_config(**kwargs)` | 动态更新上下文提取配置 |
| `set_content_source_for_context(content_source)` | 设置上下文提取的内容源 |
| `get_supported_file_extensions()` | 获取支持的文件扩展名列表 |
| `filter_supported_files(file_paths)` | 过滤出支持的文件 |

### 2.3 RAGAnythingConfig 配置

| 分类 | 字段 | 默认值 | 环境变量 |
|------|------|--------|----------|
| **目录** | `working_dir` | `"./rag_storage"` | `WORKING_DIR` |
| | `parser_output_dir` | `"./output"` | `OUTPUT_DIR` |
| **解析** | `parse_method` | `"auto"` | `PARSE_METHOD` |
| | `parser` | `"mineru"` | `PARSER` |
| | `display_content_stats` | `True` | `DISPLAY_CONTENT_STATS` |
| **多模态** | `enable_image_processing` | `True` | `ENABLE_IMAGE_PROCESSING` |
| | `enable_table_processing` | `True` | `ENABLE_TABLE_PROCESSING` |
| | `enable_equation_processing` | `True` | `ENABLE_EQUATION_PROCESSING` |
| **批量** | `max_concurrent_files` | `1` | `MAX_CONCURRENT_FILES` |
| | `supported_file_extensions` | 18 种扩展名 | `SUPPORTED_FILE_EXTENSIONS` |
| | `recursive_folder_processing` | `True` | `RECURSIVE_FOLDER_PROCESSING` |
| **上下文** | `context_window` | `1` | `CONTEXT_WINDOW` |
| | `context_mode` | `"page"` | `CONTEXT_MODE` |
| | `max_context_tokens` | `2000` | `MAX_CONTEXT_TOKENS` |
| | `include_headers` | `True` | `INCLUDE_HEADERS` |
| | `include_captions` | `True` | `INCLUDE_CAPTIONS` |
| | `context_filter_content_types` | `["text"]` | `CONTEXT_FILTER_CONTENT_TYPES` |
| | `content_format` | `"minerU"` | `CONTENT_FORMAT` |
| **路径** | `use_full_path` | `False` | `USE_FULL_PATH` |

### 2.4 ProcessorMixin（文档处理）

公共方法：

| 方法 | 签名 | 返回 | 说明 |
|------|------|------|------|
| `parse_document` | `async (file_path, ...)` | `(List[Dict], str)` | 解析文档，返回 content_list + doc_id |
| `process_document_complete` | `async (file_path, ...)` | `None` | 一键全流程处理 |
| `process_document_complete_lightrag_api` | `async (file_path, ...)` | `bool` | 供 LightRAG 调用的全流程 API |
| `insert_content_list` | `async (content_list, ...)` | `None` | 直接插入已解析的 content_list |
| `is_document_fully_processed` | `async (doc_id)` | `bool` | 检查文档是否完全处理 |
| `get_document_processing_status` | `async (doc_id)` | `Dict` | 获取文档处理状态详情 |

### 2.5 QueryMixin（查询）

| 方法 | 签名 | 返回 | 说明 |
|------|------|------|------|
| `aquery` | `async (query, mode="mix", ...)` | `str` | 纯文本问答（通过 LightRAG） |
| `aquery_with_multimodal` | `async (query, multimodal_content, ...)` | `str` | 含多模态内容的问答 |
| `aquery_vlm_enhanced` | `async (query, extra_safe_dirs=None, ...)` | `str` | VLM 增强问答（自动编码图片为 base64） |
| `query` | `(query, mode="mix", ...)` | `str` | aquery 的同步版本 |
| `query_with_multimodal` | `(query, multimodal_content, ...)` | `str` | aquery_with_multimodal 的同步版本 |

### 2.6 BatchMixin（批量处理）

| 方法 | 返回 | 说明 |
|------|------|------|
| `process_folder_complete(folder_path, ...)` | `None` | 递归处理整个文件夹 |
| `process_documents_batch(file_paths, ...)` | `BatchProcessingResult` | 同步批量解析 |
| `process_documents_batch_async(file_paths, ...)` | `BatchProcessingResult` | 异步批量解析 |
| `process_documents_with_rag_batch(file_paths, ...)` | `Dict` | 两步批量：解析 + 统一 RAG 入库 |

**BatchProcessingResult 字段：**
`successful_files`, `failed_files`, `total_files`, `processing_time`, `errors`, `output_dir`, `success_rate`, `summary()`

### 2.7 解析器 Parser

| 解析器 | 配置值 | 说明 |
|--------|--------|------|
| `MineruParser` | `"mineru"` | MinerU 2.0，最高质量，支持 PDF/图片/Office/文本，可用云端 API |
| `DoclingParser` | `"docling"` | IBM Docling，Python 原生，支持 PDF/Office/HTML |
| `PaddleOCRParser` | `"paddleocr"` | 百度 PaddleOCR，适合扫描件和 OCR |

**Parser 基类方法：**

| 方法 | 返回 | 说明 |
|------|------|------|
| `parse_pdf(pdf_path, ...)` | `List[Dict]` | 解析 PDF |
| `parse_image(image_path, ...)` | `List[Dict]` | 解析图片 |
| `parse_document(file_path, ...)` | `List[Dict]` | 自动识别类型并解析 |
| `check_installation()` | `bool` | 检查是否已安装 |
| `convert_office_to_pdf(doc_path)` | `Path` | 通过 LibreOffice 转换 Office 为 PDF |
| `convert_text_to_pdf(text_path)` | `Path` | 通过 ReportLab 转换 MD/TXT 为 PDF |

**MineruParser 特有参数：**
`backend`, `start_page`, `end_page`, `formula`, `table`, `device`, `source`, `vlm_url`, `timeout`, `env`

**Parser 注册系统：**
`register_parser(name, class)`, `unregister_parser(name)`, `list_parsers()`, `get_parser(name)`

### 2.8 多模态处理器 ModalProcessor

| 处理器 | 处理类型 | 功能 |
|--------|----------|------|
| `ImageModalProcessor` | `"image"` | 视觉模型(VLM)分析图片 → 生成描述、实体、关系 |
| `TableModalProcessor` | `"table"` | LLM 分析表格结构 → 结构化描述 + 实体 + 关系 |
| `EquationModalProcessor` | `"equation"` | LLM 分析公式 → LaTeX 描述 + 实体 + 关系 |
| `GenericModalProcessor` | 其他 | LLM 分析通用内容 → 描述 + 实体 + 关系 |

每个处理器提供：

| 方法 | 说明 |
|------|------|
| `generate_description_only(modal_content, content_type)` | 仅生成描述，不做入库 |
| `process_multimodal_content(modal_content, content_type, ...)` | 全流程：生成描述 → 创建实体 → 创建 chunk → 提取关系 |

### 2.9 上下文提取 ContextExtractor

**ContextConfig 字段：** `context_window`, `context_mode` (`"page"`/`"chunk"`), `max_context_tokens`, `include_headers`, `include_captions`, `filter_content_types`, `content_format`

**ContextExtractor 方法：**

| 方法 | 说明 |
|------|------|
| `extract_context(content_source, current_item_info)` | 提取当前多模态项周围的上下文文本 |
| `_extract_from_content_list()` | MineralU 风格 content_list 提取 |
| `_extract_page_context()` | 基于页面的上下文窗口 |
| `_extract_chunk_context()` | 基于 chunk 的上下文窗口 |

### 2.10 回调系统 Callback

#### ProcessingEvent（事件数据）

```python
@dataclass
class ProcessingEvent:
    event_type: str
    timestamp: float            # 自动生成
    file_path: Optional[str]
    doc_id: Optional[str]
    stage: Optional[str]
    details: Dict[str, Any]
    duration_seconds: Optional[float]
    error: Optional[str]
```

#### ProcessingCallback（抽象基类，17个钩子）

**解析阶段：**
- `on_parse_start(file_path, parser, ...)`
- `on_parse_complete(file_path, content_blocks, doc_id, duration, ...)`
- `on_parse_error(file_path, error, ...)`

**文本插入阶段：**
- `on_text_insert_start(file_path, text_length, ...)`
- `on_text_insert_complete(file_path, duration, ...)`

**多模态处理阶段：**
- `on_multimodal_start(file_path, item_count, ...)`
- `on_multimodal_item_complete(file_path, item_index, item_type, ...)`
- `on_multimodal_complete(file_path, processed_count, duration, ...)`

**查询阶段：**
- `on_query_start(query, mode, ...)`
- `on_query_complete(query, mode, duration, result_length, ...)`
- `on_query_error(query, mode, error, ...)`

**文档级别：**
- `on_document_complete(file_path, doc_id, duration, ...)`
- `on_document_error(file_path, error, stage, ...)`

**批量阶段：**
- `on_batch_start(file_count, ...)`
- `on_batch_complete(total_files, successful, failed, duration, ...)`

#### MetricsCallback（内置指标收集）

| 方法/属性 | 说明 |
|-----------|------|
| `metrics` | 原始指标数据字典 |
| `summary()` | 可读的指标摘要 |
| `reset()` | 重置所有指标 |

追踪的指标：`documents_processed`, `documents_failed`, `total_content_blocks`, `total_multimodal_items`, `total_parse_time`, `total_insert_time`, `total_multimodal_time`, `queries_executed`, `total_query_time`, `errors`

#### CallbackManager（回调管理器）

| 方法 | 说明 |
|------|------|
| `register(callback)` | 注册回调 |
| `unregister(callback)` | 注销回调 |
| `dispatch(event_name, **kwargs)` | 分发事件到所有回调 |
| `enable_event_log(enabled)` | 开启/关闭事件日志 |
| `clear_event_log()` | 清空事件日志 |
| `event_log` | 只读事件日志列表 |

### 2.11 韧性工具（Retry / CircuitBreaker）

#### retry / async_retry（重试装饰器）

```python
from raganything import retry, async_retry

@retry(max_attempts=3, base_delay=1.0, max_delay=60.0,
       exponential_base=2.0, jitter=True)
def sync_func(): ...

@async_retry(max_attempts=3, base_delay=1.0, max_delay=60.0,
             exponential_base=2.0, jitter=True)
async def async_func(): ...
```

默认自动重试的异常：`ConnectionError`, `TimeoutError`, `httpx.ConnectError`, `httpx.ReadTimeout`, `httpx.WriteTimeout`, `httpx.PoolTimeout`, `openai.APIConnectionError`, `openai.APITimeoutError`, `openai.RateLimitError`, `openai.InternalServerError`

#### CircuitBreaker（熔断器）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `failure_threshold` | `5` | 连续失败次数阈值 |
| `reset_timeout` | `60.0` | 熔断后自动恢复时间(秒) |
| `name` | `"default"` | 熔断器名称 |

| 方法/属性 | 说明 |
|-----------|------|
| `record_success()` | 记录成功（复位） |
| `record_failure()` | 记录失败 |
| `state` | 当前状态：`"closed"` / `"open"` / `"half-open"` |
| `__call__(func)` | 作为同步装饰器使用 |
| `async_call(func)` | 作为异步装饰器使用 |

### 2.12 Prompt 系统

#### PromptRegistry（全局单例）

| 方法 | 说明 |
|------|------|
| `swap(prompts)` | 原子替换所有 prompt 模板 |
| `snapshot()` | 返回当前 prompt 副本 |
| `get(key, default)` | 获取特定 prompt |
| `keys()`, `items()`, `values()` | 字典兼容接口 |

#### 内置语言

- 英文：`prompt.py` — 默认
- 中文：`prompts_zh.py`

#### Prompt 语言切换

```python
from raganything import set_prompt_language, get_prompt_language

set_prompt_language("zh")   # 切换到中文
set_prompt_language("en")   # 切换回英文
get_prompt_language()       # 获取当前语言
get_available_languages()   # 列出所有已注册的语言
```

#### LightRAG Prompt 模板（英文）

| Key | 用途 |
|-----|------|
| `entity_extraction_system_prompt` | 实体/关系提取系统提示 |
| `entity_extraction_user_prompt` | 提取用户提示 |
| `summarize_entity_descriptions` | 实体描述摘要 |
| `rag_response` | 标准 RAG 响应模板 |
| `naive_rag_response` | 朴素 RAG 响应模板 |
| `keywords_extraction` | 关键词提取提示 |

#### RAG-Anything 多模态 Prompt 模板

| Key | 用途 |
|-----|------|
| `IMAGE_ANALYSIS_SYSTEM` | 图片分析系统提示 |
| `TABLE_ANALYSIS_SYSTEM` | 表格分析系统提示 |
| `EQUATION_ANALYSIS_SYSTEM` | 公式分析系统提示 |
| `GENERIC_ANALYSIS_SYSTEM` | 通用内容分析系统提示 |
| `vision_prompt` / `vision_prompt_with_context` | 图片分析用户提示 |
| `table_prompt` / `table_prompt_with_context` | 表格分析用户提示 |
| `equation_prompt` / `equation_prompt_with_context` | 公式分析用户提示 |
| `generic_prompt` / `generic_prompt_with_context` | 通用内容分析用户提示 |
| `image_chunk` | 图片 chunk 模板 |
| `table_chunk` | 表格 chunk 模板 |
| `equation_chunk` | 公式 chunk 模板 |
| `generic_chunk` | 通用 chunk 模板 |
| `QUERY_IMAGE_DESCRIPTION` | 查询时图片描述提示 |

### 2.13 工具函数

`ragapi/app/utils.py`（RAG-Anything 内置）：

| 函数 | 返回 | 说明 |
|------|------|------|
| `normalize_caption_list(value)` | `List[str]` | 标准化 caption/footnote 为字符串列表 |
| `get_table_body(item)` | `Any` | 读取表格内容（支持多别名） |
| `format_table_body(table_body)` | `str` | 格式化表格为 Markdown |
| `get_equation_text_and_format(item)` | `(str, str)` | 读取公式文本和格式 |
| `separate_content(content_list)` | `(str, List[Dict])` | 分离文本和多模态内容 |
| `encode_image_to_base64(image_path)` | `str` | 编码图片为 base64 |
| `validate_image_file(image_path, max_size_mb=50)` | `bool` | 验证图片文件（存在性/扩展名/大小/符号链接） |
| `insert_text_content(lightrag, input, ...)` | `None` | 插入文本到 LightRAG |
| `insert_text_content_with_multimodal_content(lightrag, input, ...)` | `None` | 插入文本+多模态到 LightRAG |
| `get_processor_for_type(modal_processors, content_type)` | `processor or None` | 根据类型获取处理器 |
| `get_processor_supports(proc_type)` | `List[str]` | 处理器支持的特性列表 |

### 2.14 EnhancedMarkdown 转换

**MarkdownConfig 字段：** `css_file`, `template_file`, `page_size`(A4), `margin`, `font_size`, `line_height`, `include_toc`, `syntax_highlighting`, `image_max_width`, `table_style`, `output_format`(pdf), `output_dir`, `custom_css`, `metadata`

**EnhancedMarkdownConverter 方法：**

| 方法 | 说明 |
|------|------|
| `convert_with_weasyprint(md, output_path)` | 通过 WeasyPrint 转换 |
| `convert_with_pandoc(md, output_path)` | 通过 Pandoc 转换 |
| `convert_markdown_to_pdf(md, output_path)` | 自动选择后端转换 |
| `convert_file_to_pdf(input_path, output_path)` | 转换文件 |
| `get_backend_info()` | 可用后端信息 |

### 2.15 OMML 公式提取

位于 `omml_extractor.py`，专为 DOCX 文件设计：

| 函数 | 返回 | 说明 |
|------|------|------|
| `extract_omml_equations(docx_path)` | `List[Dict]` | 从 DOCX 提取所有 OMML 公式 |
| `enrich_content_list_with_docx_equations(content_list, docx_path)` | `List[Dict]` | 将提取的公式合并到 content_list |
| `omml_to_latex(element)` | `str` | 将 OMML 元素转换为 LaTeX |

### 2.16 支持的文件格式

```
.pdf, .jpg, .jpeg, .png, .bmp, .tiff, .tif,
.gif, .webp, .doc, .docx, .ppt, .pptx,
.xls, .xlsx, .txt, .md
```

---

## 三、Content List 数据格式

MinerU 解析后返回 `List[Dict]`：

| 类型 | 键字段 |
|------|--------|
| `"text"` | `type=text`, `text`, `text_level` |
| `"image"` | `type=image`, `img_path`, `image_caption`/`img_caption`, `image_footnote`/`img_footnote` |
| `"table"` | `type=table`, `table_body`/`table_data`, `table_caption`, `table_footnote`, `img_path` |
| `"equation"` | `type=equation`, `text`/`latex`/`equation`, `text_format` |
| 通用 | `content` |

---

## 四、当前 rag-api 覆盖度对比

| RAG-Anything 功能 | 当前是否使用 | 说明 |
|-------------------|:----------:|------|
| `parse_document` | ❌ | 没用，走了自己的 MinerU 云 API |
| `process_document_complete` | ❌ | 没用，自己拆成了多个步骤 |
| `insert_content_list` | ✅ | 在用 |
| `aquery` | ✅ | 在用 |
| `aquery_with_multimodal` | ❌ | 未暴露，前端未支持 |
| `aquery_vlm_enhanced` | ⚠️ | 在用，但图片路径有 bug |
| `process_folder_complete` | ❌ | 未暴露 API |
| `get_document_processing_status` | ❌ | 未暴露 API |
| `is_document_fully_processed` | ❌ | 未暴露 |
| `get_config_info` | ❌ | 未暴露 |
| `update_config` | ❌ | 未暴露 |
| `Callback 系统` | ❌ | 完全没用 |
| `CircuitBreaker` / `retry` | ❌ | 完全没用 |
| `Prompt 语言切换` | ❌ | 未用 |
| `文档删除` | ❌ | 未暴露 API |
| `aquery_data`（纯检索） | ❌ | 未暴露 |
| `QueryParam` 自定义 | ❌ | 全部使用默认值 |
| `MineruParser` 本地解析 | ❌ | 走了云 API |
| `DoclingParser` / `PaddleOCR` | ❌ | 未启用 |
| `多模态查询` | ❌ | 前端问答无多模态输入 |
| `批量文件夹处理` | ❌ | 仅单文件上传 |
| `Markdown 转 PDF` | ❌ | 未用 |
| `OMML 公式提取` | ❌ | 未用（DOCX 支持） |
| `EnhancedMarkdown` | ❌ | 未用 |
| `storage.get_all_documents()` | ❌ | 走 SQLite 而非 LightRAG |
| `storage.adelete_by_doc_id()` | ❌ | 无删除功能 |
