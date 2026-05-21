#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import httpx
from functools import partial
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=False)

from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc


def env_str(name, default=""):
    value = os.getenv(name, default)
    if value is None:
        return default
    value = value.strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    return value


def clean_kwargs(kwargs):
    allowed = {"temperature", "top_p", "max_tokens", "stream", "response_format"}
    return {k: v for k, v in kwargs.items() if k in allowed}

async def siliconflow_rerank(query, documents, top_n=None, **kwargs):
    """
    SiliconFlow rerank 函数。
    用于对初步检索出来的 chunk 重新排序。
    """
    api_key = env_str("RERANK_BINDING_API_KEY", env_str("LLM_BINDING_API_KEY"))
    base_url = env_str("RERANK_BINDING_HOST", "https://api.siliconflow.cn/v1").rstrip("/")
    model = env_str("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
    timeout = int(env_str("RERANK_TIMEOUT", "60"))

    text_docs = []
    for doc in documents:
        if isinstance(doc, dict):
            text = (
                doc.get("content")
                or doc.get("text")
                or doc.get("chunk_content")
                or doc.get("description")
                or str(doc)
            )
        else:
            text = str(doc)
        text_docs.append(text)

    if not text_docs:
        return []

    payload = {
        "model": model,
        "query": query,
        "documents": text_docs,
        "top_n": top_n or min(len(text_docs), int(env_str("RERANK_TOP_N", "20"))),
        "return_documents": False,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base_url}/rerank",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "index": item["index"],
            "relevance_score": item.get("relevance_score", item.get("score", 0.0)),
        }
        for item in data.get("results", [])
    ]
    
async def main():
    working_dir = str(PROJECT_ROOT / "rag_storage")

    api_key = env_str("LLM_BINDING_API_KEY")
    base_url = env_str("LLM_BINDING_HOST")
    llm_model = env_str("LLM_MODEL")
    vision_model = env_str("VISION_MODEL", llm_model)

    embedding_api_key = env_str("EMBEDDING_BINDING_API_KEY", api_key)
    embedding_base_url = env_str("EMBEDDING_BINDING_HOST", base_url)
    embedding_model = env_str("EMBEDDING_MODEL")
    embedding_dim = int(env_str("EMBEDDING_DIM", "2560"))

    config = RAGAnythingConfig(
        working_dir=working_dir,
    )

    def llm_model_func(prompt, system_prompt=None, history_messages=None, **kwargs):
        return openai_complete_if_cache(
            llm_model,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            api_key=api_key,
            base_url=base_url,
            **clean_kwargs(kwargs),
        )

    def vision_model_func(prompt, system_prompt=None, history_messages=None, image_data=None, messages=None, **kwargs):
        if messages:
            return openai_complete_if_cache(
                vision_model,
                "",
                system_prompt=None,
                history_messages=[],
                messages=[m for m in messages if m is not None],
                api_key=api_key,
                base_url=base_url,
                **clean_kwargs(kwargs),
            )

        return llm_model_func(
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages or [],
            **kwargs,
        )

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

    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )
    
    # 关键：单独问答脚本必须初始化/加载已有 LightRAG 存储
    init_result = await rag._ensure_lightrag_initialized()
    if not init_result or not init_result.get("success"):
         raise RuntimeError(f"LightRAG 初始化失败: {init_result}")
   
   # 关键：兼容不同版本 LightRAG 的 reranker 注入方式
    rag.lightrag.rerank_model_func = siliconflow_rerank

    if hasattr(rag.lightrag, "global_config") and isinstance(rag.lightrag.global_config, dict):
       rag.lightrag.global_config["rerank_model_func"] = siliconflow_rerank

    if hasattr(rag, "rerank_model_func"):
       rag.rerank_model_func = siliconflow_rerank

    print("Rerank attr:", getattr(rag.lightrag, "rerank_model_func", None))
    print(
       "Rerank global_config:",
       getattr(rag.lightrag, "global_config", {}).get("rerank_model_func")
       if hasattr(rag.lightrag, "global_config")
       else None
    )
    
    print("RAG 问答已启动。输入问题后回车。输入 exit 退出。")
    print("当前知识库目录:", working_dir)

    while True:
        question = input("\n你的问题：").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue

        result = await rag.aquery(
            question,
            mode="hybrid",
            vlm_enhanced=True,
            enable_rerank=True,
        )

        print("\n回答：")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
