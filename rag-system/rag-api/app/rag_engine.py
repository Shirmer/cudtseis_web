# -*- coding: utf-8 -*-

import sys
import time
import os
import xml.etree.ElementTree as ET
from contextvars import ContextVar
from functools import partial
from pathlib import Path

from app.config import (
    RAG_ANYTHING_ROOT,
    DEFAULT_RAG_WORKING_DIR,
    WORKSPACES_DIR,
    env_str,
)

# 确保能 import RAG-Anything 源码包
sys.path.append(str(RAG_ANYTHING_ROOT))

from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from typing import List, Tuple


RAG_CACHE = {}


def clean_kwargs(kwargs):
    """
    过滤部分 OpenAI-compatible API 不支持的参数。
    """
    allowed = {
        "temperature",
        "top_p",
        "max_tokens",
        "stream",
        "response_format",
    }
    return {k: v for k, v in kwargs.items() if k in allowed}


# Context variable for chat-specific API key
_chat_api_key: ContextVar[str | None] = ContextVar("chat_api_key", default=None)


def set_chat_api_key(key: str | None):
    _chat_api_key.set(key)


def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
    api_key = _chat_api_key.get() or env_str("LLM_BINDING_API_KEY")
    return openai_complete_if_cache(
        env_str("LLM_MODEL"),
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        api_key=api_key,
        base_url=env_str("LLM_BINDING_HOST"),
        **clean_kwargs(kwargs),
    )


def vision_model_func(
    prompt,
    system_prompt=None,
    history_messages=None,
    image_data=None,
    messages=None,
    **kwargs,
):
    """
    视觉模型函数。
    RAG-Anything 处理图片/图表时会调用。
    """
    if messages:
        return openai_complete_if_cache(
            env_str("VISION_MODEL", env_str("LLM_MODEL")),
            "",
            system_prompt=None,
            history_messages=[],
            messages=[m for m in messages if m is not None],
            api_key=env_str("LLM_BINDING_API_KEY"),
            base_url=env_str("LLM_BINDING_HOST"),
            **clean_kwargs(kwargs),
        )

    return llm_model_func(
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages or [],
        **kwargs,
    )


def rerank_model_func(query: str, chunks: List[Tuple[str, int, str]], **kwargs) -> List[Tuple[int, float]]:
    """
    通过 SiliconFlow API 进行重排序。
    chunks: [(chunk_id, doc_id, content), ...]
    返回: [(index_in_input, score), ...]
    """
    import httpx
    import asyncio

    api_key = env_str("RERANK_BINDING_API_KEY", env_str("LLM_BINDING_API_KEY"))
    base_url = env_str("RERANK_BINDING_HOST", "https://api.siliconflow.cn/v1")
    model = env_str("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")

    if not chunks:
        return []

    texts = [c[2] for c in chunks]
    try:
        resp = httpx.post(
            f"{base_url}/rerank",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "query": query, "documents": texts, "top_n": len(texts)},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            return [(r["index"], r.get("relevance_score", 0)) for r in results]
    except Exception as e:
        print(f"[WARN] Rerank failed, falling back: {e}")

    return [(i, 1.0) for i in range(len(chunks))]


def get_working_dir(kb_id: str) -> Path:
    """
    default 知识库使用已经跑通的 RAG-Anything/rag_storage。
    其他知识库使用 /opt/rag-system/workspaces/{kb_id}/rag_storage。
    """
    if kb_id == "default":
        return DEFAULT_RAG_WORKING_DIR

    return WORKSPACES_DIR / kb_id / "rag_storage"


def repair_lightrag_graph_if_needed(working_dir: Path):
    """
    修复 LightRAG 的 graphml 文件。

    解决：
    - graph_chunk_entity_relation.graphml 空文件
    - graphml 写坏导致 no element found: line 1, column 0
    - XML 解析失败

    做法：
    - 不直接覆盖；
    - 把坏文件改名为 .bad.xxx；
    - 让 LightRAG 下次初始化时重新创建。
    """
    graph_path = working_dir / "graph_chunk_entity_relation.graphml"

    if not graph_path.exists():
        return

    try:
        if graph_path.stat().st_size == 0:
            bad_path = graph_path.with_suffix(f".graphml.bad.{int(time.time())}")
            graph_path.rename(bad_path)
            print(f"[WARN] graphml 为空，已备份: {bad_path}")
            return

        ET.parse(graph_path)

    except Exception as e:
        bad_path = graph_path.with_suffix(f".graphml.bad.{int(time.time())}")
        graph_path.rename(bad_path)
        print(f"[WARN] graphml 损坏，已备份: {bad_path}, error={e}")


async def get_rag_engine(kb_id: str = "default") -> RAGAnything:
    """
    获取或初始化 RAGAnything 实例。
    """
    if kb_id in RAG_CACHE:
        return RAG_CACHE[kb_id]

    working_dir = get_working_dir(kb_id)
    working_dir.mkdir(parents=True, exist_ok=True)

    # 关键：初始化前先检查 graphml 是否为空或损坏
    repair_lightrag_graph_if_needed(working_dir)

    embedding_func = EmbeddingFunc(
        embedding_dim=int(env_str("EMBEDDING_DIM", "2560")),
        max_token_size=int(env_str("MAX_EMBED_TOKENS", "8192")),
        func=partial(
            openai_embed.func,
            model=env_str("EMBEDDING_MODEL"),
            api_key=env_str(
                "EMBEDDING_BINDING_API_KEY",
                env_str("LLM_BINDING_API_KEY"),
            ),
            base_url=env_str(
                "EMBEDDING_BINDING_HOST",
                env_str("LLM_BINDING_HOST"),
            ),
        ),
    )

    config = RAGAnythingConfig(
        working_dir=str(working_dir),
    )

    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
        lightrag_kwargs={
            "rerank_model_func": rerank_model_func,
        },
    )

    # 关键：云解析 / content_list 直接入库时，不需要本地 MinerU parser。
    # MinerU 云 API 已经负责解析 PDF，这里只负责把 content_list 插入 LightRAG。
    if env_str("SKIP_LOCAL_PARSER_CHECK", "true").lower() in {"1", "true", "yes", "on"}:
        rag._parser_installation_checked = True

    init_result = await rag._ensure_lightrag_initialized()
    if not init_result or not init_result.get("success"):
        raise RuntimeError(f"LightRAG 初始化失败: {init_result}")

    RAG_CACHE[kb_id] = rag
    return rag
