# -*- coding: utf-8 -*-

"""
MinerU 云 API 客户端。

职责：
1. 向 MinerU 申请批量上传 URL；
2. PUT 上传本地 PDF 到 MinerU 临时上传地址；
3. 轮询 batch 解析结果；
4. 下载 full_zip_url；
5. 解压 zip；
6. 找到 *_content_list.json，交给后续 RAG-Anything / LightRAG 入库。
"""

import time
import zipfile
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import requests

from app.config import env_str


MINERU_BASE_URL = env_str("MINERU_BASE_URL", "https://mineru.net").rstrip("/")


class MinerUCloudError(RuntimeError):
    pass


def mineru_headers() -> Dict[str, str]:
    token = env_str("MINERU_API_TOKEN")
    if not token:
        raise MinerUCloudError("MINERU_API_TOKEN 未配置。请先在 .env 里配置 MinerU API Token。")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "*/*",
    }


def normalize_upload_url(item: Any) -> str:
    """
    MinerU 返回的 file_urls 通常是字符串列表。
    为了兼容可能的 dict 结构，这里做一层兼容。
    """
    if isinstance(item, str):
        return item

    if isinstance(item, dict):
        for key in ["url", "upload_url", "file_url"]:
            if key in item:
                return item[key]

    raise MinerUCloudError(f"无法识别 MinerU 上传 URL 结构: {item}")


async def submit_batch_local_files_to_mineru(
    files: List[Dict[str, str]],
    *,
    model_version: str = "vlm",
    enable_formula: bool = True,
    enable_table: bool = True,
    is_ocr: bool = False,
    language: str = "ch",
) -> Dict[str, Any]:
    """
    提交本地文件到 MinerU 批量上传解析接口。

    files 格式：
    [
        {
            "document_id": "...",
            "file_path": "/path/to/a.pdf",
            "filename": "a.pdf"
        }
    ]

    返回：
    {
        "batch_id": "...",
        "file_urls": [...],
        "raw": 原始返回
    }
    """
    if not files:
        raise MinerUCloudError("files 不能为空")

    # 官方本地文件批量上传解析单次申请上传链接有数量限制。
    # 我们先限制 50，方便稳定调试。
    if len(files) > 50:
        raise MinerUCloudError("单次批量云解析最多建议 50 个文件。请分批上传。")

    for item in files:
        path = Path(item["file_path"])
        if not path.exists():
            raise MinerUCloudError(f"文件不存在: {path}")

    endpoint = f"{MINERU_BASE_URL}/api/v4/file-urls/batch"

    payload = {
        "model_version": model_version,
        "enable_formula": enable_formula,
        "enable_table": enable_table,
        "language": language,
        "files": [
            {
                "name": item["filename"],
                "data_id": item["document_id"],
                "is_ocr": is_ocr,
            }
            for item in files
        ],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            endpoint,
            headers=mineru_headers(),
            json=payload,
        )

    if resp.status_code >= 400:
        raise MinerUCloudError(
            f"申请 MinerU 上传 URL 失败: HTTP {resp.status_code}, {resp.text[:1000]}"
        )

    result = resp.json()

    if result.get("code") != 0:
        raise MinerUCloudError(f"申请 MinerU 上传 URL 失败: {result}")

    data = result.get("data") or {}
    batch_id = data.get("batch_id")
    file_urls = data.get("file_urls") or []

    if not batch_id:
        raise MinerUCloudError(f"MinerU 返回中没有 batch_id: {result}")

    if len(file_urls) != len(files):
        raise MinerUCloudError(
            f"MinerU 返回上传 URL 数量不匹配: files={len(files)}, urls={len(file_urls)}, raw={result}"
        )

    # 逐个 PUT 上传文件。单个上传失败不中断整体流程。
    upload_failures = {}
    successful_files = []
    successful_urls = []

    for item, url_item in zip(files, file_urls):
        upload_url = normalize_upload_url(url_item)
        file_path = Path(item["file_path"])
        doc_id = item["document_id"]

        try:
            def _upload_file(url=upload_url, path=file_path):
                with path.open("rb") as f:
                    return requests.put(url, data=f, timeout=600)

            put_resp = await asyncio.to_thread(_upload_file)

            if put_resp.status_code not in (200, 201):
                raise MinerUCloudError(
                    f"HTTP {put_resp.status_code}, {put_resp.text[:200]}"
                )

            successful_files.append(item)
            successful_urls.append(url_item)

        except Exception as e:
            upload_failures[doc_id] = f"{type(e).__name__}: {e}"

    return {
        "batch_id": batch_id,
        "successful_files": successful_files,
        "successful_urls": successful_urls,
        "upload_failures": upload_failures,
        "file_urls": file_urls,
        "raw": result,
    }


async def get_mineru_batch_result(batch_id: str) -> Dict[str, Any]:
    """
    查询 MinerU 批量解析结果。
    """
    endpoint = f"{MINERU_BASE_URL}/api/v4/extract-results/batch/{batch_id}"

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(
            endpoint,
            headers=mineru_headers(),
        )

    if resp.status_code >= 400:
        raise MinerUCloudError(
            f"查询 MinerU batch 失败: HTTP {resp.status_code}, {resp.text[:1000]}"
        )

    result = resp.json()

    if result.get("code") != 0:
        raise MinerUCloudError(f"查询 MinerU batch 失败: {result}")

    return result.get("data") or {}


def map_results_by_document_id(
    extract_result: List[Dict[str, Any]],
    files: List[Dict[str, str]],
) -> Dict[str, Dict[str, Any]]:
    """
    MinerU 通常会返回 data_id。
    如果某些情况下没有 data_id，就退回到按顺序匹配。
    """
    mapped: Dict[str, Dict[str, Any]] = {}

    for item in extract_result:
        data_id = item.get("data_id")
        if data_id:
            mapped[data_id] = item

    if mapped:
        return mapped

    for file_item, result_item in zip(files, extract_result):
        mapped[file_item["document_id"]] = result_item

    return mapped


async def download_and_extract_mineru_zip(
    full_zip_url: str,
    *,
    output_root: str,
    document_id: str,
) -> Dict[str, str]:
    """
    下载 MinerU full_zip_url，解压，并找到 content_list.json。

    返回：
    {
        "zip_path": "...",
        "extract_dir": "...",
        "content_list_path": "..."
    }
    """
    out_root = Path(output_root)
    extract_dir = out_root / document_id
    extract_dir.mkdir(parents=True, exist_ok=True)

    zip_path = extract_dir / "mineru_result.zip"

    async with httpx.AsyncClient(timeout=900) as client:
        resp = await client.get(full_zip_url)

    if resp.status_code >= 400:
        raise MinerUCloudError(
            f"下载 MinerU 结果 zip 失败: HTTP {resp.status_code}, {resp.text[:1000]}"
        )

    zip_path.write_bytes(resp.content)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    candidates = list(extract_dir.rglob("*_content_list.json"))

    if not candidates:
        candidates = list(extract_dir.rglob("content_list.json"))

    if not candidates:
        raise MinerUCloudError(f"未在 MinerU zip 中找到 content_list.json: {extract_dir}")

    return {
        "zip_path": str(zip_path),
        "extract_dir": str(extract_dir),
        "content_list_path": str(candidates[0]),
    }


async def wait_seconds(seconds: int) -> None:
    await asyncio.sleep(seconds)


def get_state_text(item: Dict[str, Any]) -> str:
    return str(item.get("state") or item.get("status") or "unknown")
