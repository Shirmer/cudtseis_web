#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
process_batch11.py

功能：
1. 自动读取 ./inputs 目录下的 PDF；
2. 使用 RAG-Anything + MinerU 解析文献；
3. 打开图片、表格、公式处理；
4. 调用硅基流动上的 Qwen LLM / Vision / Embedding；
5. 写入默认本地知识库 ./rag_storage；
6. 处理完后自动做一次中文测试查询；
7. 支持 nohup 后台运行，电脑关闭后服务器继续处理。
"""

import os
import sys
import asyncio
import logging
import logging.config
import traceback
import inspect
from functools import partial
from pathlib import Path

# ============================================================
# 1. 项目根目录
# ============================================================

# 当前脚本位置：
# /opt/rag-system/RAG-Anything/scripts/process_batch11.py
#
# 所以 parent.parent 就是：
# /opt/rag-system/RAG-Anything
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# ============================================================
# 2. 读取 .env
# ============================================================

from dotenv import load_dotenv

ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=False)
os.environ["MINERU_MODEL_SOURCE"] = os.getenv("MINERU_MODEL_SOURCE", "modelscope")
print("MINERU_MODEL_SOURCE =", os.environ["MINERU_MODEL_SOURCE"])
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc, logger, set_verbose_debug
from raganything import RAGAnything, RAGAnythingConfig


# ============================================================
# 3. 工具函数
# ============================================================

def env_bool(name: str, default: bool = False) -> bool:
    """
    把 .env 里的 true / false 字符串转成 Python 的 True / False。
    """
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "y", "on"}


def env_str(name: str, default: str = "") -> str:
    """
    读取 .env 字符串，并去掉首尾空格。

    兼容这种写法：
    PARSER=mineru  # Options: mineru, docling, paddleocr

    但更推荐你把注释单独写一行：
    # Options: mineru, docling, paddleocr
    PARSER=mineru
    """
    value = os.getenv(name, default)
    if value is None:
        return default

    value = value.strip()

    # 简单处理行内注释
    if "#" in value:
        value = value.split("#", 1)[0].strip()

    return value


def clean_model_kwargs(kwargs: dict) -> dict:
    """
    过滤模型调用参数。

    目的：
    一些 OpenAI-compatible 平台不支持所有 OpenAI 参数。
    为了减少兼容性问题，只保留常用安全参数。
    """
    allowed = {
        "temperature",
        "top_p",
        "max_tokens",
        "stream",
        "response_format",
    }
    return {k: v for k, v in kwargs.items() if k in allowed}


def remove_none_messages(messages):
    """
    去掉 messages 列表里的 None。

    有些视觉模型接口不接受 None。
    """
    return [m for m in messages if m is not None]


def build_raganything_config(config_kwargs: dict) -> RAGAnythingConfig:
    """
    兼容不同版本的 RAGAnythingConfig。

    如果当前版本不支持某个参数，就自动忽略，避免直接报错。
    """
    sig = inspect.signature(RAGAnythingConfig)
    supported_keys = set(sig.parameters.keys())

    filtered = {
        key: value
        for key, value in config_kwargs.items()
        if key in supported_keys
    }

    ignored = sorted(set(config_kwargs.keys()) - set(filtered.keys()))
    if ignored:
        print(f"[INFO] 当前版本 RAGAnythingConfig 不支持这些参数，已忽略：{ignored}")

    return RAGAnythingConfig(**filtered)


def configure_logging():
    """
    配置日志。
    会同时输出到终端和 ./logs/batch11_runtime.log。
    """
    log_dir = Path(env_str("LOG_DIR", str(PROJECT_ROOT / "logs"))).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "batch11_runtime.log"

    print(f"\n日志文件：{log_file}\n")

    log_max_bytes = int(env_str("LOG_MAX_BYTES", "10485760"))
    log_backup_count = int(env_str("LOG_BACKUP_COUNT", "5"))
    log_level = env_str("LOG_LEVEL", "INFO").upper()

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(levelname)s: %(message)s",
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
                    "filename": str(log_file),
                    "maxBytes": log_max_bytes,
                    "backupCount": log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "loggers": {
                "lightrag": {
                    "handlers": ["console", "file"],
                    "level": log_level,
                    "propagate": False,
                },
            },
        }
    )

    logger.setLevel(log_level)
    set_verbose_debug(env_bool("VERBOSE", False))


# ============================================================
# 4. 单篇文献处理函数
# ============================================================

async def process_one_document(rag: RAGAnything, pdf_path: Path, output_dir: Path):
    """
    处理一篇 PDF。
    parser 已经在 RAGAnythingConfig 里设置，这里不要再传 parser。
    source=modelscope 表示让 MinerU 优先从 ModelScope 下载本地解析模型。
    """
    parse_method = env_str("PARSE_METHOD", "auto")
    mineru_source = env_str("MINERU_SOURCE", "modelscope")

    try:
        await rag.process_document_complete(
            file_path=str(pdf_path),
            output_dir=str(output_dir),
            parse_method=parse_method,
            source=mineru_source,
        )
    except TypeError as e:
        if "unexpected keyword" in str(e) and "source" in str(e):
            print("[WARN] 当前版本 process_document_complete 不支持 source 参数，改用基础参数重试。")
            await rag.process_document_complete(
                file_path=str(pdf_path),
                output_dir=str(output_dir),
                parse_method=parse_method,
            )
        else:
            raise

# ============================================================
# 5. 处理完成后测试查询
# ============================================================

async def query_after_ingest(rag: RAGAnything):
    """
    所有文献处理完成后，自动做一次中文测试查询。
    """
    question = (
        "请用中文总结这批文献的主要研究主题、研究方法、数据类型、"
        "图表信息、公式信息和关键结论。如果包含地质、地震、地球物理内容，"
        "请重点说明。"
    )

    print("\n" + "=" * 80)
    print("开始测试查询：")
    print(question)
    print("=" * 80)

    try:
        result = await rag.aquery(
            question,
            mode="hybrid",
            vlm_enhanced=True,
        )
    except TypeError:
        print("[WARN] 当前版本 aquery 不支持 vlm_enhanced，改用普通 hybrid 查询。")
        result = await rag.aquery(
            question,
            mode="hybrid",
        )

    print("\n" + "=" * 80)
    print("测试查询结果：")
    print("=" * 80)
    print(result)


# ============================================================
# 6. 主流程
# ============================================================

async def main():
    configure_logging()

    print("=" * 80)
    print("RAG-Anything 11 篇文献批处理脚本")
    print("=" * 80)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f".env 路径：{ENV_PATH}")
    print("=" * 80)

    # ------------------------------------------------------------
    # 6.1 默认目录
    # ------------------------------------------------------------
    # 默认使用：
    # ./inputs      放 PDF
    # ./output      放 MinerU 解析输出
    # ./rag_storage 放 RAG 知识库
    # ./logs        放日志
    input_dir = Path(env_str("INPUT_DIR", str(PROJECT_ROOT / "inputs"))).resolve()
    output_dir = Path(env_str("OUTPUT_DIR", str(PROJECT_ROOT / "output"))).resolve()
    working_dir = Path(env_str("WORKING_DIR", str(PROJECT_ROOT / "rag_storage"))).resolve()
    logs_dir = Path(env_str("LOG_DIR", str(PROJECT_ROOT / "logs"))).resolve()

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    working_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(input_dir.glob("*.pdf"))

    print(f"输入目录：{input_dir}")
    print(f"解析输出目录：{output_dir}")
    print(f"知识库存储目录：{working_dir}")
    print(f"日志目录：{logs_dir}")
    print(f"发现 PDF 数量：{len(pdf_files)}")
    print("=" * 80)

    if not pdf_files:
        raise RuntimeError(f"没有在 {input_dir} 找到 PDF。请把文献上传到 ./inputs。")

    # ------------------------------------------------------------
    # 6.2 读取模型配置
    # ------------------------------------------------------------
    api_key = env_str("LLM_BINDING_API_KEY")
    base_url = env_str("LLM_BINDING_HOST")

    llm_model = env_str("LLM_MODEL")
    vision_model = env_str("VISION_MODEL")

    embedding_api_key = env_str("EMBEDDING_BINDING_API_KEY", api_key)
    embedding_base_url = env_str("EMBEDDING_BINDING_HOST", base_url)
    embedding_model = env_str("EMBEDDING_MODEL")
    embedding_dim = int(env_str("EMBEDDING_DIM", "1024"))

    enable_thinking = env_bool("ENABLE_THINKING", False)

    # 基础检查，避免跑半天才发现配置错
    if not api_key or "your" in api_key.lower():
        raise RuntimeError("LLM_BINDING_API_KEY 未正确配置。请填入硅基流动 API Key。")

    if not base_url:
        raise RuntimeError("LLM_BINDING_HOST 未配置。")

    if base_url.startswith("https:https"):
        raise RuntimeError(
            "LLM_BINDING_HOST 写错了。应为 https://api.siliconflow.cn/v1"
        )

    if not llm_model:
        raise RuntimeError("LLM_MODEL 未配置。")

    if not vision_model:
        raise RuntimeError("VISION_MODEL 未配置。")

    if not embedding_model:
        raise RuntimeError("EMBEDDING_MODEL 未配置。")

    if not embedding_api_key or "your" in embedding_api_key.lower():
        raise RuntimeError("EMBEDDING_BINDING_API_KEY 未正确配置。")

    if not embedding_base_url:
        raise RuntimeError("EMBEDDING_BINDING_HOST 未配置。")

    print("模型配置：")
    print(f"LLM_BINDING_HOST：{base_url}")
    print(f"LLM_MODEL：{llm_model}")
    print(f"VISION_MODEL：{vision_model}")
    print(f"EMBEDDING_BINDING_HOST：{embedding_base_url}")
    print(f"EMBEDDING_MODEL：{embedding_model}")
    print(f"EMBEDDING_DIM：{embedding_dim}")
    print(f"ENABLE_THINKING：{enable_thinking}")
    print("=" * 80)

    # ------------------------------------------------------------
    # 6.3 RAGAnything 配置
    # ------------------------------------------------------------
    config_kwargs = {
        "working_dir": str(working_dir),
        "parser": env_str("PARSER", "mineru"),
        "parse_method": env_str("PARSE_METHOD", "auto"),

        # 多模态开关
        "enable_image_processing": env_bool("ENABLE_IMAGE_PROCESSING", True),
        "enable_table_processing": env_bool("ENABLE_TABLE_PROCESSING", True),
        "enable_equation_processing": env_bool("ENABLE_EQUATION_PROCESSING", True),

        # 批处理/上下文配置
        "max_concurrent_files": int(env_str("MAX_CONCURRENT_FILES", "1")),
        "context_window": int(env_str("CONTEXT_WINDOW", "1")),
        "context_mode": env_str("CONTEXT_MODE", "page"),
        "max_context_tokens": int(env_str("MAX_CONTEXT_TOKENS", "2000")),
        "include_headers": env_bool("INCLUDE_HEADERS", True),
        "include_captions": env_bool("INCLUDE_CAPTIONS", True),
        "context_filter_content_types": [
            x.strip()
            for x in env_str("CONTEXT_FILTER_CONTENT_TYPES", "text").split(",")
            if x.strip()
        ],
        "content_format": env_str("CONTENT_FORMAT", "minerU"),
    }

    config = build_raganything_config(config_kwargs)

    print("RAG 配置：")
    print(f"PARSER：{env_str('PARSER', 'mineru')}")
    print(f"PARSE_METHOD：{env_str('PARSE_METHOD', 'auto')}")
    print(f"ENABLE_IMAGE_PROCESSING：{env_bool('ENABLE_IMAGE_PROCESSING', True)}")
    print(f"ENABLE_TABLE_PROCESSING：{env_bool('ENABLE_TABLE_PROCESSING', True)}")
    print(f"ENABLE_EQUATION_PROCESSING：{env_bool('ENABLE_EQUATION_PROCESSING', True)}")
    print("=" * 80)

    # ------------------------------------------------------------
    # 6.4 LLM 函数
    # ------------------------------------------------------------
    # 负责文本理解、实体抽取、关系抽取、总结、最终问答。
    def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        clean_kwargs = clean_model_kwargs(kwargs)

        # Qwen thinking 开关：
        # ENABLE_THINKING=true 时，传 enable_thinking=true；
        # false 时不传，兼容性更好。
        if enable_thinking:
            clean_kwargs["extra_body"] = {"enable_thinking": True}

        return openai_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            api_key=api_key,
            base_url=base_url,
            **clean_kwargs,
        )

    # ------------------------------------------------------------
    # 6.5 Vision 函数
    # ------------------------------------------------------------
    # 负责图片/图表理解。
    # 这里不强行给 Vision 模型传 enable_thinking，减少兼容性风险。
    def vision_model_func(
        prompt,
        system_prompt=None,
        history_messages=None,
        image_data=None,
        messages=None,
        **kwargs,
    ):
        clean_kwargs = clean_model_kwargs(kwargs)

        if messages:
            return openai_complete_if_cache(
                vision_model,
                "",
                system_prompt=None,
                history_messages=[],
                messages=remove_none_messages(messages),
                api_key=api_key,
                base_url=base_url,
                **clean_kwargs,
            )

        if image_data:
            messages_payload = remove_none_messages(
                [
                    {"role": "system", "content": system_prompt}
                    if system_prompt
                    else None,
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
                    },
                ]
            )

            return openai_complete_if_cache(
                vision_model,
                "",
                system_prompt=None,
                history_messages=[],
                messages=messages_payload,
                api_key=api_key,
                base_url=base_url,
                **clean_kwargs,
            )

        # 没有图片时，回退到普通 LLM。
        return llm_model_func(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            **clean_kwargs,
        )

    # ------------------------------------------------------------
    # 6.6 Embedding 函数
    # ------------------------------------------------------------
    # 负责向量化，是检索质量的核心。
    embedding_func = EmbeddingFunc(
        embedding_dim=embedding_dim,
        max_token_size=int(env_str("MAX_EMBED_TOKENS", "8192")),
        func=partial(
            openai_embed.func,
            model=embedding_model,
            api_key=embedding_api_key,
            base_url=embedding_base_url,
        ),
    )

    # ------------------------------------------------------------
    # 6.7 初始化 RAGAnything
    # ------------------------------------------------------------
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )

    # ------------------------------------------------------------
    # 6.8 批量处理 PDF
    # ------------------------------------------------------------
    success_file = logs_dir / "batch11_success.txt"
    failed_file = logs_dir / "batch11_failed.txt"

    # 支持断点续跑：
    # 如果某篇已经成功处理过，下次运行会跳过。
    # 如果你想全部重跑，删除 logs/batch11_success.txt。
    processed_success = set()
    if success_file.exists():
        processed_success = {
            line.strip()
            for line in success_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    print(f"已记录成功处理文件数：{len(processed_success)}")
    print("=" * 80)

    successful = []
    failed = []

    for idx, pdf_path in enumerate(pdf_files, start=1):
        pdf_name = pdf_path.name

        if pdf_name in processed_success:
            print(f"[SKIP] [{idx}/{len(pdf_files)}] 已处理过，跳过：{pdf_name}")
            successful.append(pdf_name)
            continue

        print("\n" + "=" * 80)
        print(f"[START] [{idx}/{len(pdf_files)}] 开始处理：{pdf_name}")
        print("=" * 80)

        try:
            await process_one_document(rag, pdf_path, output_dir)

            successful.append(pdf_name)
            with success_file.open("a", encoding="utf-8") as f:
                f.write(pdf_name + "\n")

            print(f"[SUCCESS] [{idx}/{len(pdf_files)}] 处理成功：{pdf_name}")

        except Exception as e:
            failed.append(pdf_name)

            error_text = (
                f"\n{'=' * 80}\n"
                f"文件：{pdf_name}\n"
                f"错误：{repr(e)}\n"
                f"{traceback.format_exc()}\n"
            )

            with failed_file.open("a", encoding="utf-8") as f:
                f.write(error_text)

            print(f"[FAILED] [{idx}/{len(pdf_files)}] 处理失败：{pdf_name}")
            print(f"错误信息：{repr(e)}")
            logger.exception(f"处理失败：{pdf_name}")

    # ------------------------------------------------------------
    # 6.9 输出统计
    # ------------------------------------------------------------
    print("\n" + "=" * 80)
    print("批处理完成")
    print("=" * 80)
    print(f"总 PDF 数量：{len(pdf_files)}")
    print(f"成功/跳过数量：{len(successful)}")
    print(f"失败数量：{len(failed)}")

    if failed:
        print("失败文件：")
        for name in failed:
            print(f" - {name}")
        print(f"详细失败日志：{failed_file}")

    print("=" * 80)

    # ------------------------------------------------------------
    # 6.10 自动测试查询
    # ------------------------------------------------------------
    if successful:
        await query_after_ingest(rag)
    else:
        print("[WARN] 没有成功处理任何文件，跳过测试查询。")


# ============================================================
# 7. 入口
# ============================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n用户中断。")
    except Exception as e:
        print("\n脚本异常退出：")
        print(repr(e))
        traceback.print_exc()
        raise