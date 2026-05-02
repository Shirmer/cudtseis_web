#!/usr/bin/env python
"""
CLI 后端：基于 MinerU + RAGAnything 的多模态对话程序

功能：
1. 解析并索引文档（含图片/表格/公式）
2. 在命令行中与文档进行多轮对话
3. 自动使用 VLM（vision_model_func）增强，对图表/图片提问
"""

import numpy as np
import os
import argparse
import asyncio
import logging
import logging.config
from pathlib import Path
import sys
import requests
from dotenv import load_dotenv

# 路径
sys.path.append(str(Path(__file__).parent.parent))

from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc, logger, set_verbose_debug
from raganything import RAGAnything, RAGAnythingConfig

load_dotenv(dotenv_path=".env", override=False)


def configure_logging():
    log_dir = os.getenv("LOG_DIR", os.getcwd())
    log_file_path = os.path.abspath(os.path.join(log_dir, "raganything_cli.log"))

    print(f"\nRAGAnything log file: {log_file_path}\n")
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


async def build_rag(
    file_path: str,
    output_dir: str,
    api_key: str,
    base_url: str | None,
    working_dir: str | None,
    parser: str | None,
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


async def chat_loop(rag: RAGAnything):
    """
    简单命令行对话循环：
    - 默认使用 mode="hybrid"
    - 启用 VLM 增强（自动看图）
    """
    print("\n索引完成，可以开始对话。输入 'exit' 退出。")
    while True:
        try:
            q = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出。")
            break

        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            print("再见。")
            break

        try:
            # 多模态增强：vlm_enhanced=True
            ans = await rag.aquery(q, mode="hybrid", vlm_enhanced=True)
            print("\n助手:", ans)
        except Exception as e:
            print(f"[错误] {e}")


def main():
    parser = argparse.ArgumentParser(description="MinerU RAG CLI Backend")
    parser.add_argument("file_path", help="要处理的文档路径")
    parser.add_argument(
        "--working_dir", "-w", default="./rag_storage", help="工作目录"
    )
    parser.add_argument(
        "--output", "-o", default="./output", help="解析输出目录（可选）"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LLM_BINDING_API_KEY"),
        help="API Key（默认读取 LLM_BINDING_API_KEY 环境变量）",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LLM_BINDING_HOST"),
        help="API Base URL（可选）",
    )
    parser.add_argument(
        "--parser",
        default=os.getenv("PARSER", "mineru"),
        help="解析器（mineru 或 docling），默认 mineru",
    )

    args = parser.parse_args()

    if not args.api_key:
        logger.error("缺少 API Key，请通过环境变量 LLM_BINDING_API_KEY 或 --api-key 提供")
        return

    if args.output:
        os.makedirs(args.output, exist_ok=True)

    async def runner():
        print("正在解析并建立文档索引，请稍等...")
        rag = await build_rag(
            args.file_path,
            args.output,
            args.api_key,
            args.base_url,
            args.working_dir,
            args.parser,
        )
        await chat_loop(rag)

    asyncio.run(runner())


if __name__ == "__main__":
    configure_logging()
    print("RAGAnything CLI Backend")
    print("=" * 30)
    main()