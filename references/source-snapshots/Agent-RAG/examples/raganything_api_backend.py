#!/usr/bin/env python
"""
FastAPI 后端：基于 MinerU + RAGAnything 的多模态对话服务

路径约定：
- 本文件：/home/projects/RAG-Anything/examples/raganything_api_backend.py
- working_dir 默认：/home/projects/RAG-Anything/rag_storage
- output 默认：/home/projects/RAG-Anything/output

功能：
1. 启动时解析并索引指定文档（含图片/表格/公式）
2. 提供 /chat 接口进行多轮对话
3. 使用 VLM（vision_model_func）增强，对图表/图片提问
4. 从回答文本中提取 Image Path，并转换成 /static/... 形式的图片 URL
"""

import os
import sys
import re
import asyncio
from pathlib import Path
from typing import Optional, List

import numpy as np
import requests
from dotenv import load_dotenv

import logging
import logging.config

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 保证能 import raganything / lightrag
# 当前文件在 /home/projects/RAG-Anything/examples
# 父目录就是项目根：/home/projects/RAG-Anything
sys.path.append(str(Path(__file__).parent.parent))

from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc, logger, set_verbose_debug
from raganything import RAGAnything, RAGAnythingConfig

load_dotenv(dotenv_path=".env", override=False)

# ========= 日志配置，与 CLI 基本一致 =========
def configure_logging():
    # 默认日志放在项目根目录
    project_root = Path(__file__).parent.parent
    log_dir = os.getenv("LOG_DIR", str(project_root))
    log_file_path = os.path.abspath(os.path.join(log_dir, "raganything_api.log"))

    print(f"\nRAGAnything API log file: {log_file_path}\n")
    os.makedirs(os.path.dirname(log_dir), exist_ok=True)

    log_max_bytes = int(os.getenv("LOG_MAX_BYTES", 10485760))
    log_backup_count = int(os.getenv("LOG_BACKUP_COUNT", 5))

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(levelname)s: %(message)s"},
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
            },
            "handlers": {
                "console": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stderr",
                },
                "file": {
                    "formatter": "detailed",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": log_file_path,
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "lightrag": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }
    )
    logger.setLevel(logging.INFO)
    set_verbose_debug(os.getenv("VERBOSE", "false").lower() == "true")


# ========= 复用你 CLI 里的 build_rag 函数逻辑 =========
async def build_rag(
    file_path: str,
    output_dir: str,
    api_key: str,
    base_url: Optional[str],
    working_dir: Optional[str],
    parser: Optional[str],
) -> RAGAnything:
    """
    初始化 RAGAnything，并对文档完成解析和插入，返回 rag 实例
    """
    # 1. 配置
    config = RAGAnythingConfig(
        working_dir=working_dir or "./rag_storage",
        parser=parser,
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )

    # 2. LLM 函数
    def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        if history_messages is None:
            history_messages = []
        return openai_complete_if_cache(
            "qwen-max",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

    # 3. 视觉多模态函数（给 VLM 增强用）
    def vision_model_func(
        prompt,
        system_prompt=None,
        history_messages=None,
        image_data=None,
        messages=None,
        **kwargs,
    ):
        if history_messages is None:
            history_messages = []

        # OpenAI/Qwen 多模态格式：直接传 messages
        if messages:
            return openai_complete_if_cache(
                "qwen-max",
                "",
                system_prompt=None,
                history_messages=[],
                messages=messages,
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )

        # 单张图形式
        if image_data:
            mm = []
            if system_prompt:
                mm.append({"role": "system", "content": system_prompt})
            mm.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            },
                        },
                    ],
                }
            )
            return openai_complete_if_cache(
                "qwen-max",
                "",
                system_prompt=None,
                history_messages=[],
                messages=mm,
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )

        # 纯文本退化为普通 LLM
        return llm_model_func(prompt, system_prompt, history_messages, **kwargs)

    # 4. Embedding 函数（保持你原来的写法）
    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")

    def _embed_raw_sync(texts):
        root = (base_url or "https://api.openai.com").rstrip("/")
        if root.endswith("/v1"):
            url = root + "/embeddings"
        else:
            url = root + "/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": embedding_model, "input": texts}
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()["data"]
        emb = [item["embedding"] for item in data]
        return np.asarray(emb, dtype=np.float32)

    async def embed_raw(texts):
        return await asyncio.to_thread(_embed_raw_sync, texts)

    probe = await embed_raw(["dim probe"])
    real_dim = len(probe[0])
    logger.info(f"[Embedding Probe] model={embedding_model} returned dim={real_dim}")

    embedding_func = EmbeddingFunc(
        embedding_dim=real_dim,
        max_token_size=8192,
        func=embed_raw,
    )

    # 5. 构建 RAGAnything
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )

    # 6. 解析并插入文档
    await rag.process_document_complete(
        file_path=file_path, output_dir=output_dir, parse_method="auto"
    )

    return rag


# ========= 全局 RAG 实例 & 路径设定 =========
configure_logging()

project_root = Path(__file__).parent.parent  # /home/projects/RAG-Anything

# 你可以通过环境变量 DOC_PATH 配置文档，也可以直接写死
DOCUMENT_PATH = os.getenv(
    "DOC_PATH",
    str(project_root / "examples" / "example.pdf"),  # 默认一个示例路径，建议改掉
)

WORKING_DIR = os.getenv("WORKING_DIR", str(project_root / "rag_storage"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(project_root / "output"))

API_KEY = os.getenv("LLM_BINDING_API_KEY")
BASE_URL = os.getenv("LLM_BINDING_HOST")
PARSER = os.getenv("PARSER", "mineru")

# 静态文件根目录：使用 OUTPUT_DIR（和 CLI 默认的 --output 一致）
STATIC_ROOT = os.path.abspath(OUTPUT_DIR)

rag: Optional[RAGAnything] = None


# ========= 工具：从答案中提取 Image Path 并转成 /static URL =========
IMAGE_PATH_PATTERN = re.compile(
    r"Image Path:\s*([^\r\n]*?\.(?:jpg|jpeg|png|gif|bmp|webp|tiff|tif))",
    re.IGNORECASE,
)


def extract_image_paths_from_answer(answer: str) -> List[str]:
    return IMAGE_PATH_PATTERN.findall(answer)


def local_path_to_static_url(local_path: str) -> str:
    """
    将本地文件路径（在 STATIC_ROOT 内）转换成 /static/... URL
    """
    local_path = os.path.abspath(local_path)
    root = os.path.abspath(STATIC_ROOT)
    if not local_path.startswith(root):
        return ""
    rel = os.path.relpath(local_path, root)
    return f"/static/{rel.replace(os.sep, '/')}"


# ========= FastAPI 应用 =========
app = FastAPI(title="RAGAnything FastAPI Backend")

# 跨域：开发阶段先放开，生产环境建议限定前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态目录为 /static，用于访问图片
os.makedirs(STATIC_ROOT, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


# ========= Pydantic 模型 =========
class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    images: List[str] = []


# ========= 启动时构建 RAG =========
@app.on_event("startup")
async def startup_event():
    global rag

    if not API_KEY:
        logger.error("缺少 API Key，请设置环境变量 LLM_BINDING_API_KEY")
        return

    if not os.path.exists(DOCUMENT_PATH):
        logger.error(f"文档不存在: {DOCUMENT_PATH}")
        return

    logger.info(f"使用文档: {DOCUMENT_PATH}")
    logger.info("正在启动时解析并建立文档索引，请稍等...")

    rag = await build_rag(
        file_path=DOCUMENT_PATH,
        output_dir=OUTPUT_DIR,
        api_key=API_KEY,
        base_url=BASE_URL,
        working_dir=WORKING_DIR,
        parser=PARSER,
    )

    logger.info("文档索引构建完成。")


# ========= 对话接口 =========
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    global rag
    if rag is None:
        raise HTTPException(status_code=503, detail="RAG 引擎尚未就绪或初始化失败")

    try:
        # 和 CLI 一样：mode="hybrid" + vlm_enhanced=True
        raw_res = await rag.aquery(req.query, mode="hybrid", vlm_enhanced=True)

        if isinstance(raw_res, dict) and "answer" in raw_res:
            answer = raw_res["answer"]
        else:
            answer = str(raw_res)

        # 从答案文本中抽取 Image Path 行
        raw_paths = extract_image_paths_from_answer(answer)
        image_urls: List[str] = []
        for p in raw_paths:
            url = local_path_to_static_url(p)
            if url:
                image_urls.append(url)

        return ChatResponse(answer=answer, images=image_urls)

    except Exception as e:
        logger.exception("对话处理失败")
        raise HTTPException(status_code=500, detail=str(e))

        