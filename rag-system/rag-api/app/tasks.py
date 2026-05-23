# -*- coding: utf-8 -*-

"""
后台任务模块。

现在支持三类任务：
1. 普通 PDF 导入任务 ingest_document_task
   - 如果 PARSER_BACKEND=disabled，只进入 waiting_parser
   - 如果 PARSER_BACKEND=mineru_api，调用 MinerU 云 API 解析后自动入库

2. content_list 直接入库任务 insert_content_list_task
   - 外部已经解析好的 content_list.json 直接入 RAG-Anything / LightRAG

3. 批量云解析入库任务 batch_cloud_ingest_task
   - 多个 PDF 上传到 MinerU 云 API
   - 云端解析完成后下载 zip
   - 找到 content_list.json
   - 自动入库
"""

import os
import json
import time
import asyncio
import inspect
from pathlib import Path
from typing import Any, Dict, List

from app.local_db import get_document, update_document_status, update_task
from app.rag_engine import get_rag_engine
from app.cache import invalidate_graph_stats

from app.mineru_cloud import (
    submit_batch_local_files_to_mineru,
    get_mineru_batch_result,
    map_results_by_document_id,
    download_and_extract_mineru_zip,
    get_state_text,
    MinerUCloudError,
)


def env_str(name: str, default: str = "") -> str:
    """
    读取环境变量。

    这里单独写一份，是为了避免 app.config 里没有 env_str 时出错。
    """
    return os.getenv(name, default).strip()


async def insert_content_list_task(
    kb_id: str,
    document_id: str,
    task_id: str,
    content_list_path: str,
    original_file_name: str,
):
    """
    直接插入已经解析好的 content_list。

    用途：
    - MinerU 云 API 已经返回 content_list
    - GPU 服务器已经解析好 PDF
    - 其他 parser 已经生成 content_list
    """
    try:
        update_task(task_id, "running", "开始读取 content_list")
        update_document_status(document_id, "inserting")

        path = Path(content_list_path)
        if not path.exists():
            raise FileNotFoundError(f"content_list file not found: {content_list_path}")

        with path.open("r", encoding="utf-8") as f:
            content_list = json.load(f)

        if not isinstance(content_list, list):
            raise ValueError("content_list 必须是 JSON 数组/list")

        # MinerU 的 content_list 里图片通常是相对路径，例如 images/xxx.jpg。
        # 直接传给 RAG-Anything 时，它可能从当前工作目录找 images/xxx.jpg，
        # 导致 Image file not found。
        # 这里统一把相对图片路径改成基于 content_list.json 所在目录的绝对路径。
        content_base_dir = path.parent
        fixed_image_paths = 0

        image_path_keys = {
            "img_path",
            "image_path",
            "table_img_path",
            "equation_img_path",
        }

        for item in content_list:
            if not isinstance(item, dict):
                continue

            for key in image_path_keys:
                value = item.get(key)

                if not value or not isinstance(value, str):
                    continue

                # 跳过网络 URL、base64、绝对路径
                if (
                    value.startswith("http://")
                    or value.startswith("https://")
                    or value.startswith("data:")
                    or value.startswith("/")
                ):
                    continue

                abs_path = content_base_dir / value

                # 如果 content_list 同级目录能找到，就改成绝对路径
                if abs_path.exists():
                    item[key] = str(abs_path)
                    fixed_image_paths += 1
                else:
                    # 兜底：在 content_list 所在目录下递归找同名图片
                    matches = list(content_base_dir.rglob(Path(value).name))
                    if matches:
                        item[key] = str(matches[0])
                        fixed_image_paths += 1

        update_task(
            task_id,
            "inserting",
            f"读取 content_list 成功，共 {len(content_list)} 个内容块；已修正 {fixed_image_paths} 个图片路径，开始入库",
        )

        rag = await get_rag_engine(kb_id)

        # 去重检查：基于 content_list 内容生成 hash，检查是否已入库
        import hashlib
        content_sig_parts = []
        for item in content_list:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    content_sig_parts.append(item["text"].strip()[:200])
                elif item.get("type") == "image" and item.get("img_path"):
                    content_sig_parts.append(f"image:{item['img_path']}")
                elif item.get("type") == "table" and item.get("table_body"):
                    content_sig_parts.append(f"table:{item['table_body'][:200]}")
                elif item.get("type") == "equation" and item.get("text"):
                    content_sig_parts.append(f"equation:{item['text']}")
        content_sig = "\n".join(content_sig_parts)
        content_hash = hashlib.md5(content_sig.encode("utf-8")).hexdigest()

        # 检查本地 DB 中是否已有相同 content_hash 的文档
        from app.local_db import get_conn
        with get_conn() as conn:
            row = conn.execute(
                "SELECT document_id, filename FROM documents WHERE content_hash = ? AND status = 'indexed'",
                (content_hash,),
            ).fetchone()
        if row:
            update_task(
                task_id,
                "duplicate_skipped",
                f"检测到重复文档（hash={content_hash[:8]}），已存在 {row[1][:40]} (id={row[0][:12]})，跳过入库",
            )
            update_document_status(document_id, "indexed")
            return

        insert_func = getattr(rag, "insert_content_list", None)
        if insert_func is None:
            available = [
                x for x in dir(rag)
                if "content" in x.lower() or "insert" in x.lower()
            ]
            raise RuntimeError(
                f"当前 RAGAnything 实例没有 insert_content_list 方法。可用相关方法: {available}"
            )

        kwargs = {
            "content_list": content_list,
            "file_path": original_file_name,
            "doc_id": document_id,
            "display_stats": True,
        }

        # 兼容不同版本 RAG-Anything 的 insert_content_list 参数
        try:
            sig = inspect.signature(insert_func)
            has_kwargs = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in sig.parameters.values()
            )

            if has_kwargs:
                final_kwargs = kwargs
            else:
                final_kwargs = {
                    k: v for k, v in kwargs.items()
                    if k in sig.parameters
                }
        except Exception:
            final_kwargs = kwargs

        result = insert_func(**final_kwargs)

        if inspect.isawaitable(result):
            await result

        update_task(
            task_id,
            "success",
            f"content_list 已成功插入 RAG-Anything / LightRAG 知识库 (hash={content_hash[:8]})",
        )
        update_document_status(document_id, "indexed")
        invalidate_graph_stats()
        # 保存 content_hash 用于后续去重
        try:
            from app.local_db import get_conn
            with get_conn() as conn:
                conn.execute(
                    "UPDATE documents SET content_hash = ? WHERE document_id = ?",
                    (content_hash, document_id),
                )
                conn.commit()
        except Exception:
            pass

    except Exception as e:
        update_task(task_id, "failed", f"{type(e).__name__}: {e}")
        update_document_status(document_id, "failed")

async def ingest_document_task(document_id: str, task_id: str):
    """
    单篇 PDF 一键全流程导入任务。

    根据 PARSER_BACKEND 决定怎么处理：

    PARSER_BACKEND=disabled
    - 只创建任务，不解析，状态进入 waiting_parser

    PARSER_BACKEND=mineru_api
    - 调用 MinerU 云 API
    - 下载解析结果 zip
    - 找 content_list.json
    - 自动插入 RAG-Anything / LightRAG
    """
    doc = get_document(document_id)
    if not doc:
        update_task(task_id, "failed", "document not found")
        return

    kb_id = doc["kb_id"]
    file_path = doc["file_path"]
    filename = doc["filename"]

    parser_backend = env_str("PARSER_BACKEND", "disabled")

    try:
        update_task(task_id, "running", f"任务开始，parser_backend={parser_backend}")
        update_document_status(document_id, "processing")

        if parser_backend == "disabled":
            update_task(
                task_id,
                "waiting_parser",
                "当前 PARSER_BACKEND=disabled。后续可切换 mineru_api / local_mineru。",
            )
            update_document_status(document_id, "waiting_parser")
            return

        if parser_backend == "mineru_api":
            item = {
                "document_id": document_id,
                "task_id": task_id,
                "file_path": file_path,
                "filename": filename,
            }

            options = {
                "model_version": env_str("MINERU_MODEL_VERSION", "vlm"),
                "enable_formula": True,
                "enable_table": True,
                "is_ocr": False,
                "language": "ch",
            }

            await batch_cloud_ingest_task(kb_id, [item], options)
            return

        update_task(task_id, "failed", f"未知 PARSER_BACKEND: {parser_backend}")
        update_document_status(document_id, "failed")

    except Exception as e:
        update_task(task_id, "failed", f"{type(e).__name__}: {e}")
        update_document_status(document_id, "failed")


async def batch_cloud_ingest_task(
    kb_id: str,
    items: List[Dict[str, str]],
    options: Dict[str, Any],
):
    """
    批量 PDF 云解析并自动入库。

    items 示例：
    [
        {
            "document_id": "...",
            "task_id": "...",
            "file_path": "/opt/rag-system/data/uploads/xxx.pdf",
            "filename": "xxx.pdf"
        }
    ]

    流程：
    1. 向 MinerU 申请批量上传 URL
    2. PUT 上传 PDF 到 MinerU，单个失败不株连
    3. 轮询 MinerU batch 解析状态，每个文档独立超时
    4. 解析完成后并发下载 + 入库（Semaphore 控制并行数）
    5. 下载失败自动重试 3 次
    """
    print(f"[batch_cloud_ingest_task] 开始处理 {len(items)} 个文档")
    if not items:
        print("[batch_cloud_ingest_task] items 为空，退出")
        return

    poll_interval = int(env_str("MINERU_BATCH_POLL_INTERVAL", "10"))
    per_doc_timeout = int(env_str("MINERU_DOC_TIMEOUT", "600"))
    max_concurrent = int(env_str("MAX_CONCURRENT_INSERT", "3"))
    output_root = env_str("MINERU_OUTPUT_DIR", "/opt/rag-system/data/mineru_outputs")

    files = [
        {
            "document_id": x["document_id"],
            "file_path": x["file_path"],
            "filename": x["filename"],
            "task_id": x["task_id"],
        }
        for x in items
    ]

    all_doc_ids = {x["document_id"] for x in items}

    # ===== Phase 0: 提交到 MinerU =====
    print(f"[batch_cloud_ingest_task] 开始提交到 MinerU，{len(files)} 个文件")
    for x in items:
        update_task(x["task_id"], "cloud_requesting", "正在向 MinerU 申请批量上传 URL")
        update_document_status(x["document_id"], "cloud_parsing")

    try:
        submit_result = await submit_batch_local_files_to_mineru(
            files,
            model_version=options.get("model_version", "vlm"),
            enable_formula=bool(options.get("enable_formula", True)),
            enable_table=bool(options.get("enable_table", True)),
            is_ocr=bool(options.get("is_ocr", False)),
            language=options.get("language", "ch"),
        )
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        print(f"[batch_cloud_ingest_task] 提交失败: {err_msg}")
        for x in items:
            update_task(x["task_id"], "failed", f"提交 MinerU 失败: {err_msg}")
            update_document_status(x["document_id"], "failed")
        return

    batch_id = submit_result["batch_id"]

    # 标记上传失败的文件
    upload_failed_ids = set(submit_result.get("upload_failures", {}).keys())
    for doc_id, err_msg in submit_result.get("upload_failures", {}).items():
        for x in items:
            if x["document_id"] == doc_id:
                update_task(x["task_id"], "failed", f"上传到 MinerU 失败: {err_msg}")
                update_document_status(doc_id, "failed")

    successful = submit_result.get("successful_files", [])
    if not successful:
        return

    for x in successful:
        update_task(x["task_id"], "cloud_submitted", f"已上传到 MinerU，batch_id={batch_id}")

    # ===== Phase 1: 轮询 + 并发处理 =====
    doc_start_time = {x["document_id"]: time.time() for x in successful}
    doc_state = {x["document_id"]: "pending" for x in successful}
    semaphore = asyncio.Semaphore(max_concurrent)
    processing_tasks = {}

    def doc_is_final(did: str) -> bool:
        return doc_state.get(did, "done") in ("processed", "failed", "timedout")

    while True:
        # 检查每个文档的独立超时
        for x in successful:
            did = x["document_id"]
            if doc_is_final(did):
                continue
            elapsed = time.time() - doc_start_time.get(did, time.time())
            if elapsed > per_doc_timeout:
                doc_state[did] = "timedout"
                update_task(x["task_id"], "failed", f"文档解析超时 ({per_doc_timeout}s)")
                update_document_status(did, "failed")

        # 全部处理完毕则退出
        if all(doc_is_final(x["document_id"]) for x in successful):
            break

        # 获取 MinerU batch 状态
        try:
            batch_data = await get_mineru_batch_result(batch_id)
        except Exception as e:
            await asyncio.sleep(poll_interval)
            continue

        extract_result = batch_data.get("extract_result") or []
        result_map = map_results_by_document_id(extract_result, successful)

        for x in successful:
            did = x["document_id"]
            tid = x["task_id"]

            if doc_is_final(did):
                continue

            item = result_map.get(did)
            if not item:
                continue

            state = get_state_text(item)

            if state in {"waiting-file", "pending", "running", "converting"}:
                doc_state[did] = "running"
                update_task(tid, f"cloud_{state}", f"MinerU 解析中，state={state}")
                continue

            if state == "failed":
                doc_state[did] = "failed"
                update_task(tid, "failed", f"MinerU 解析失败: {item.get('err_msg') or item}")
                update_document_status(did, "failed")
                continue

            if state == "done":
                doc_state[did] = "downloading"
                task = asyncio.create_task(
                    _process_done_doc(
                        semaphore, kb_id, did, tid, x["filename"],
                        item, output_root,
                    )
                )
                processing_tasks[did] = task
                continue

            update_task(tid, "cloud_unknown_state", f"未知状态: {state}")

        await asyncio.sleep(poll_interval)

    # 等待所有下载+入库任务完成
    if processing_tasks:
        results = await asyncio.gather(*processing_tasks.values(), return_exceptions=True)
        for did, r in zip(processing_tasks.keys(), results):
            if isinstance(r, Exception):
                doc_state[did] = "failed"
            elif doc_state.get(did) != "failed":
                doc_state[did] = "processed"


async def _process_done_doc(
    semaphore: asyncio.Semaphore,
    kb_id: str,
    doc_id: str,
    task_id: str,
    filename: str,
    result_item: dict,
    output_root: str,
):
    """并发处理单个已完成文档：下载 → 解压 → 入库，含重试"""
    async with semaphore:
        full_zip_url = result_item.get("full_zip_url")
        if not full_zip_url:
            update_task(task_id, "failed", "MinerU done 但无 full_zip_url")
            update_document_status(doc_id, "failed")
            return

        update_task(task_id, "cloud_downloading", "正在下载 MinerU 解析结果...")

        # 下载重试（最多 3 次）
        last_exc = None
        for attempt in range(3):
            try:
                extracted = await download_and_extract_mineru_zip(
                    full_zip_url,
                    output_root=output_root,
                    document_id=doc_id,
                )
                last_exc = None
                break
            except Exception as e:
                last_exc = e
                if attempt < 2:
                    wait = 2 ** attempt
                    update_task(task_id, "cloud_download_retry", f"下载失败，{wait}s 后重试 ({attempt+1}/3): {type(e).__name__}")
                    await asyncio.sleep(wait)

        if last_exc:
            update_task(task_id, "failed", f"下载 MinerU 结果失败 (3次均失败): {type(last_exc).__name__}: {last_exc}")
            update_document_status(doc_id, "failed")
            return

        update_task(task_id, "cloud_result_ready", "下载完成，开始入库")
        await insert_content_list_task(
            kb_id=kb_id,
            document_id=doc_id,
            task_id=task_id,
            content_list_path=extracted["content_list_path"],
            original_file_name=filename,
        )
