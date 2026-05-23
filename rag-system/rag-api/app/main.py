# -*- coding: utf-8 -*-

import hashlib
import json
import asyncio
import os
import sqlite3
import uuid
import shutil
import time

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.config import UPLOAD_DIR, env_str
from app.local_db import (
    init_db,
    create_document,
    list_documents,
    get_document,
    delete_document,
    get_document_stats,
    create_task,
    get_task,
    list_tasks,
)
from app.rag_engine import get_rag_engine, get_working_dir
from app.cache import get_cached_graph_stats, set_cached_graph_stats, invalidate_graph_stats
from app.tasks import ingest_document_task, insert_content_list_task, batch_cloud_ingest_task


app = FastAPI(title="RAG-Anything Backend API", version="0.1.0")
STATIC_DIR = Path(__file__).parent / "static"
chatHistory = []

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def frontend_home():
    return FileResponse(STATIC_DIR / "index.html")

class ChatRequest(BaseModel):
    question: str
    mode: str = "hybrid"
    vlm_enhanced: bool = True
    enable_rerank: bool = True
    include_references: bool = True
    top_k: int = 60
    chunk_top_k: int = 30
    history_turns: int = 3
    response_type: str = "Multiple Paragraphs"
    temperature: float = 0.3
    max_tokens: int = 8192
    max_total_tokens: int = 30000
    stream: bool = False
    system_prompt: str | None = None
    hl_keywords: list[str] = []
    image_data: str | None = None
    image_name: str | None = None



# =========================
# Admin file manager helpers
# =========================

METADATA_DB = Path("/opt/rag-system/data/rag_api_metadata.db")

ADMIN_ALLOWED_DIRS = [
    Path("/opt/rag-system/data/inputs").resolve(),
    Path("/opt/rag-system/data/uploads").resolve(),
    Path("/opt/rag-system/RAG-Anything/inputs").resolve(),
]


class DuplicateCheckItem(BaseModel):
    filename: str
    sha256: str | None = None
    file_path: str | None = None


class DuplicateCheckRequest(BaseModel):
    items: list[DuplicateCheckItem]


class BatchReindexRequest(BaseModel):
    document_ids: list[str] | None = None
    model_version: str = "vlm"
    enable_formula: bool = True
    enable_table: bool = True
    is_ocr: bool = False
    language: str = "ch"


class ServerPathIngestRequest(BaseModel):
    file_paths: list[str]
    model_version: str = "vlm"
    enable_formula: bool = True
    enable_table: bool = True
    is_ocr: bool = False
    language: str = "ch"
    skip_duplicates: bool = True


def is_allowed_admin_path(path: Path) -> bool:
    """
    只允许访问白名单目录下的文件，避免管理接口变成任意文件读取接口。
    """
    try:
        resolved = path.expanduser().resolve()
    except Exception:
        return False

    for root in ADMIN_ALLOWED_DIRS:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue

    return False


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_existing_document_records(kb_id: str):
    """
    从 metadata db 里读取已有文档记录。
    当前不改表结构，用 filename / file_path / sha256 组合判断重复。
    """
    if not METADATA_DB.exists():
        return []

    conn = sqlite3.connect(str(METADATA_DB))
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        select document_id, kb_id, filename, file_path, status, created_at
        from documents
        where kb_id = ?
        """,
        (kb_id,),
    ).fetchall()

    conn.close()

    records = []
    for row in rows:
        item = dict(row)
        fp = item.get("file_path")
        item["sha256"] = None

        if fp:
            p = Path(fp)
            if p.exists() and p.is_file():
                try:
                    item["sha256"] = file_sha256(p)
                except Exception:
                    item["sha256"] = None

        records.append(item)

    return records


def check_duplicate_for_item(
    kb_id: str,
    filename: str,
    sha256: str | None = None,
    file_path: str | None = None,
):
    existing = load_existing_document_records(kb_id)

    filename_norm = filename.strip().lower()
    file_path_norm = None
    if file_path:
        try:
            file_path_norm = str(Path(file_path).expanduser().resolve())
        except Exception:
            file_path_norm = str(file_path)

    for doc in existing:
        old_filename = (doc.get("filename") or "").strip().lower()
        old_path = doc.get("file_path")
        old_path_norm = None

        if old_path:
            try:
                old_path_norm = str(Path(old_path).expanduser().resolve())
            except Exception:
                old_path_norm = str(old_path)

        old_sha256 = doc.get("sha256")

        if sha256 and old_sha256 and sha256 == old_sha256:
            return {
                "is_duplicate": True,
                "reason": "sha256",
                "matched_document": doc,
            }

        if file_path_norm and old_path_norm and file_path_norm == old_path_norm:
            return {
                "is_duplicate": True,
                "reason": "file_path",
                "matched_document": doc,
            }

        if filename_norm and old_filename and filename_norm == old_filename:
            return {
                "is_duplicate": True,
                "reason": "filename",
                "matched_document": doc,
            }

    return {
        "is_duplicate": False,
        "reason": None,
        "matched_document": None,
    }

@app.on_event("startup")
async def startup():
    init_db()
    # Pre-warm graph stats cache in background (avoids 8s delay on first request)
    asyncio.create_task(_warm_graph_stats_cache())


async def _warm_graph_stats_cache():
    """Pre-load graph stats into cache during startup."""
    try:
        from app.config import DEFAULT_RAG_WORKING_DIR
        _read_graph_stats(DEFAULT_RAG_WORKING_DIR)
    except Exception:
        pass


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "rag-anything-api",
    }


@app.get("/api/v1/knowledge-bases")
async def list_knowledge_bases():
    """
    第一阶段先只有 default 知识库。
    default 对应你当前已经跑通的：
    /opt/rag-system/RAG-Anything/rag_storage
    """
    return {
        "items": [
            {
                "kb_id": "default",
                "name": "Default Knowledge Base",
                "description": "Current RAG-Anything rag_storage",
            }
        ]
    }


@app.get("/api/v1/knowledge-bases/{kb_id}")
async def get_knowledge_base(kb_id: str):
    return {
        "kb_id": kb_id,
        "status": "available",
    }


def _read_graph_stats(working_dir):
    """Read graph stats from JSON files with in-memory cache."""
    cached = get_cached_graph_stats()
    if cached:
        return cached

    from app.config import DEFAULT_RAG_WORKING_DIR, WORKSPACES_DIR
    if working_dir is None:
        working_dir = DEFAULT_RAG_WORKING_DIR

    def json_count(path):
        try:
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return len(data.get("data", data))
                    return len(data)
        except Exception:
            pass
        return 0

    result = {
        "total_entities": json_count(working_dir / "vdb_entities.json"),
        "total_relations": json_count(working_dir / "vdb_relationships.json"),
        "total_chunks": json_count(working_dir / "kv_store_text_chunks.json"),
    }
    set_cached_graph_stats(result)
    return result


def invalidate_graph_stats():
    """Clear graph stats cache (call after document indexing)."""
    from app.cache import invalidate_graph_stats as _inv
    _inv()


@app.get("/api/v1/knowledge-bases/{kb_id}/stats")
async def knowledge_base_stats(kb_id: str):
    stats = get_document_stats(kb_id)

    try:
        from app.config import DEFAULT_RAG_WORKING_DIR, WORKSPACES_DIR
        if kb_id == "default":
            working_dir = DEFAULT_RAG_WORKING_DIR
        else:
            working_dir = WORKSPACES_DIR / kb_id / "rag_storage"

        g = _read_graph_stats(working_dir)
        stats.update(g)
    except Exception:
        stats["total_entities"] = 0
        stats["total_relations"] = 0
        stats["total_chunks"] = 0

    return stats


@app.get("/api/v1/knowledge-bases/{kb_id}/graph")
async def knowledge_base_graph(kb_id: str, doc_id: str = None):
    from app.config import DEFAULT_RAG_WORKING_DIR, WORKSPACES_DIR
    if kb_id == "default":
        working_dir = DEFAULT_RAG_WORKING_DIR
    else:
        working_dir = WORKSPACES_DIR / kb_id / "rag_storage"

    nodes = []
    edges = []

    entities_path = working_dir / "vdb_entities.json"
    rela_path = working_dir / "vdb_relationships.json"

    if entities_path.exists():
        with open(entities_path) as f:
            data = json.load(f)
        for ent in data.get("data", []):
            nodes.append({
                "id": ent.get("__id__", ""),
                "name": ent.get("entity_name", ""),
                "content": (ent.get("content") or "")[:200],
            })

    if rela_path.exists():
        with open(rela_path) as f:
            data = json.load(f)
        for rel in data.get("data", []):
            edges.append({
                "id": rel.get("__id__", ""),
                "source_id": rel.get("src_id", ""),
                "target_id": rel.get("tgt_id", ""),
                "content": (rel.get("content") or "")[:200],
            })

    if doc_id:
        doc_ent_path = working_dir / "kv_store_full_entities.json"
        if doc_ent_path.exists():
            with open(doc_ent_path) as f:
                doc_entities = json.load(f)
            doc_entity_names = set()
            for doc_key, doc_val in doc_entities.items():
                if doc_key == doc_id:
                    doc_entity_names = set(doc_val.get("entity_names", []))
                    break
            if doc_entity_names:
                nodes = [n for n in nodes if n.get("name") in doc_entity_names]
                valid_ids = {n["id"] for n in nodes}
                edges = [e for e in edges if e.get("source_id") in valid_ids or e.get("target_id") in valid_ids]

    return {"kb_id": kb_id, "nodes": nodes, "edges": edges}


@app.post("/api/v1/knowledge-bases/{kb_id}/documents")
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
):
    """
    上传 PDF。

    第一阶段：
    - 保存文件
    - 写入 SQLite 元数据
    - 不立即解析
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported now.")

    document_id = str(uuid.uuid4())

    kb_dir = UPLOAD_DIR / kb_id
    kb_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    file_path = kb_dir / f"{document_id}_{safe_name}"

    with file_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    create_document(
        document_id=document_id,
        kb_id=kb_id,
        filename=file.filename,
        file_path=str(file_path),
    )

    return {
        "document_id": document_id,
        "kb_id": kb_id,
        "filename": file.filename,
        "file_path": str(file_path),
        "status": "uploaded",
    }

@app.post("/api/v1/knowledge-bases/{kb_id}/content-list/insert")
async def insert_content_list(
    kb_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    original_file_name: str = Form("external_document.pdf"),
):
    """
    上传已经解析好的 content_list.json，并创建直接入库任务。

    适用场景：
    - MinerU 云 API 已经解析好 PDF
    - GPU 服务器已经解析好 PDF
    - 外部 parser 已经生成 content_list

    注意：
    - 这个接口不会再调用 MinerU 解析 PDF
    - 它会直接把 content_list 插入 RAG-Anything / LightRAG
    """
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON content_list files are supported.")

    document_id = str(uuid.uuid4())
    task_id = str(uuid.uuid4())

    kb_dir = UPLOAD_DIR / kb_id / "content_lists"
    kb_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    content_list_path = kb_dir / f"{document_id}_{safe_name}"

    with content_list_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # 这里 filename 记录原始 PDF 名称，file_path 暂时记录 content_list 路径
    create_document(
        document_id=document_id,
        kb_id=kb_id,
        filename=original_file_name,
        file_path=str(content_list_path),
    )

    create_task(
        task_id=task_id,
        document_id=document_id,
        kb_id=kb_id,
        status="queued",
        message="content_list insert queued",
    )

    background_tasks.add_task(
        insert_content_list_task,
        kb_id,
        document_id,
        task_id,
        str(content_list_path),
        original_file_name,
    )

    return {
        "task_id": task_id,
        "document_id": document_id,
        "kb_id": kb_id,
        "content_list_path": str(content_list_path),
        "original_file_name": original_file_name,
        "status": "queued",
    }
    
@app.post("/api/v1/knowledge-bases/{kb_id}/documents/batch-cloud-ingest")
async def batch_cloud_ingest_documents(
    kb_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    model_version: str = Form("vlm"),
    enable_formula: bool = Form(True),
    enable_table: bool = Form(True),
    is_ocr: bool = Form(False),
    language: str = Form("ch"),
):
    """
    批量上传 PDF，并调用 MinerU 云 API 解析，解析完成后自动入库。
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if len(files) > 50:
        raise HTTPException(status_code=400, detail="最多一次上传 50 个文件，请分批上传。")

    items = []

    kb_dir = UPLOAD_DIR / kb_id / "cloud_batch"
    kb_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Only PDF files are supported now: {file.filename}",
            )

        document_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        safe_name = file.filename.replace("/", "_").replace("\\", "_")
        file_path = kb_dir / f"{document_id}_{safe_name}"

        with file_path.open("wb") as f:
            shutil.copyfileobj(file.file, f)

        create_document(
            document_id=document_id,
            kb_id=kb_id,
            filename=file.filename,
            file_path=str(file_path),
        )

        create_task(
            task_id=task_id,
            document_id=document_id,
            kb_id=kb_id,
            status="queued",
            message="cloud batch ingest queued",
        )

        items.append(
            {
                "document_id": document_id,
                "task_id": task_id,
                "file_path": str(file_path),
                "filename": file.filename,
            }
        )

    options = {
        "model_version": model_version,
        "enable_formula": enable_formula,
        "enable_table": enable_table,
        "is_ocr": is_ocr,
        "language": language,
    }

    background_tasks.add_task(
        batch_cloud_ingest_task,
        kb_id,
        items,
        options,
    )

    return {
        "kb_id": kb_id,
        "status": "queued",
        "parser": "mineru_api",
        "model_version": model_version,
        "items": items,
    }


@app.post("/api/v1/knowledge-bases/{kb_id}/documents/check-duplicates")
async def check_document_duplicates(
    kb_id: str,
    req: DuplicateCheckRequest,
):
    """
    检查文献是否可能重复。

    支持：
    - 本机上传前：前端计算 sha256 后传来检查；
    - 服务器已有文件：传 file_path 后检查；
    - 兜底：filename 检查。
    """
    results = []

    for item in req.items:
        duplicate = check_duplicate_for_item(
            kb_id=kb_id,
            filename=item.filename,
            sha256=item.sha256,
            file_path=item.file_path,
        )

        results.append(
            {
                "filename": item.filename,
                "sha256": item.sha256,
                "file_path": item.file_path,
                **duplicate,
            }
        )

    return {
        "kb_id": kb_id,
        "count": len(results),
        "items": results,
    }


@app.get("/api/v1/admin/server-files")
async def list_server_pdf_files(
    dir: str,
    kb_id: str = "default",
):
    """
    管理员查看服务器已有 PDF。

    安全限制：
    只允许访问 ADMIN_ALLOWED_DIRS 白名单目录。
    """
    base_dir = Path(dir).expanduser()

    if not is_allowed_admin_path(base_dir):
        raise HTTPException(
            status_code=403,
            detail=f"Directory not allowed: {dir}",
        )

    if not base_dir.exists() or not base_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail=f"Directory not found: {dir}",
        )

    files = []

    for p in sorted(base_dir.glob("*.pdf")):
        if not p.is_file():
            continue

        try:
            sha = file_sha256(p)
        except Exception:
            sha = None

        duplicate = check_duplicate_for_item(
            kb_id=kb_id,
            filename=p.name,
            sha256=sha,
            file_path=str(p),
        )

        files.append(
            {
                "filename": p.name,
                "file_path": str(p),
                "size_bytes": p.stat().st_size,
                "sha256": sha,
                **duplicate,
            }
        )

    return {
        "kb_id": kb_id,
        "dir": str(base_dir),
        "count": len(files),
        "items": files,
    }


@app.post("/api/v1/knowledge-bases/{kb_id}/documents/server-paths-cloud-ingest")
async def server_paths_cloud_ingest(
    kb_id: str,
    req: ServerPathIngestRequest,
    background_tasks: BackgroundTasks,
):
    """
    从服务器已有 PDF 路径创建 MinerU 云解析 + LightRAG 入库任务。

    适合：
    - /opt/rag-system/data/inputs/batch100 这种已经在服务器上的文献。
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="file_paths is empty")

    if len(req.file_paths) > 50:
        raise HTTPException(status_code=400, detail="一次最多提交 50 个文件，建议 20 个一批。")

    items = []
    skipped_duplicates = []

    for file_path in req.file_paths:
        p = Path(file_path).expanduser()

        if not is_allowed_admin_path(p):
            raise HTTPException(status_code=403, detail=f"File path not allowed: {file_path}")

        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        if p.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail=f"Only PDF supported: {file_path}")

        sha = file_sha256(p)

        duplicate = check_duplicate_for_item(
            kb_id=kb_id,
            filename=p.name,
            sha256=sha,
            file_path=str(p),
        )

        if req.skip_duplicates and duplicate["is_duplicate"]:
            skipped_duplicates.append(
                {
                    "filename": p.name,
                    "file_path": str(p),
                    "sha256": sha,
                    "duplicate_reason": duplicate["reason"],
                    "matched_document": duplicate["matched_document"],
                }
            )
            continue

        document_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())

        create_document(
            document_id=document_id,
            kb_id=kb_id,
            filename=p.name,
            file_path=str(p),
        )

        create_task(
            task_id=task_id,
            document_id=document_id,
            kb_id=kb_id,
            status="queued",
            message="服务器已有 PDF 已加入 MinerU 云解析队列",
        )

        items.append(
            {
                "document_id": document_id,
                "task_id": task_id,
                "file_path": str(p),
                "filename": p.name,
            }
        )

    if not items:
        return {
            "kb_id": kb_id,
            "status": "skipped",
            "message": "没有需要提交的新文件，可能全部重复。",
            "count": 0,
            "items": [],
            "skipped_duplicates": skipped_duplicates,
        }

    options = {
        "model_version": req.model_version,
        "enable_formula": req.enable_formula,
        "enable_table": req.enable_table,
        "is_ocr": req.is_ocr,
        "language": req.language,
    }

    background_tasks.add_task(
        batch_cloud_ingest_task,
        kb_id,
        items,
        options,
    )

    return {
        "kb_id": kb_id,
        "status": "queued",
        "parser": "mineru_api",
        "count": len(items),
        "items": items,
        "skipped_duplicates": skipped_duplicates,
    }


@app.get("/api/v1/knowledge-bases/{kb_id}/documents")
async def get_documents(kb_id: str):
    return {
        "kb_id": kb_id,
        "items": list_documents(kb_id),
    }


@app.get("/api/v1/documents/{document_id}")
async def get_document_detail(document_id: str):
    doc = get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    return doc


@app.delete("/api/v1/documents/{document_id}")
async def delete_document_endpoint(document_id: str):
    doc = get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    file_path = doc.get("file_path")
    if file_path:
        p = Path(file_path)
        try:
            if p.exists() and p.is_file():
                p.unlink()
        except Exception:
            pass

    delete_document(document_id)

    return {"status": "deleted", "document_id": document_id}


@app.get("/api/v1/documents/{document_id}/pdf")
async def get_document_pdf(document_id: str, filename: str = None):
    """
    获取文档原始 PDF 文件。
    支持 UUID document_id、或直接通过 filename 参数搜索。
    """
    from fastapi.responses import FileResponse

    # 先尝试从 DB 查找
    doc = get_document(document_id)
    if doc:
        file_path = doc.get("file_path", "")
        p = Path(file_path)
        candidates = [p]
        # inputs/batch100 目录
        batch100 = Path("/opt/rag-system/data/inputs/batch100")
        if batch100.exists():
            for f in batch100.iterdir():
                if doc.get("filename", "") in str(f):
                    candidates.append(f)
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return FileResponse(str(candidate), media_type="application/pdf", filename=doc.get("filename", "document.pdf"))

    # 使用 filename 参数搜索
    search_name = filename or document_id
    if not search_name or search_name.startswith("doc-"):
        # 如果是 content-based ID，尝试从 doc_status 找文件名
        doc_status_path = Path("/opt/rag-system/RAG-Anything/rag_storage/kv_store_doc_status.json")
        if doc_status_path.exists():
            with open(doc_status_path) as f:
                doc_status = json.load(f)
            # 尝试匹配 document_id
            info = doc_status.get(document_id)
            if info and info.get("file_path"):
                search_name = info["file_path"]

    if not search_name:
        raise HTTPException(status_code=404, detail="PDF file not found")

    # 在已知位置搜索 PDF
    search_dirs = [
        Path("/opt/rag-system/data/inputs/batch100"),
        Path("/opt/rag-system/data/inputs/batch11"),
        Path("/opt/rag-system/data/uploads/default/cloud_batch"),
        Path("/opt/rag-system/data/uploads"),
        Path("/opt/rag-system/RAG-Anything/inputs"),
    ]
    for sd in search_dirs:
        if sd.exists():
            for f in sd.rglob("*.pdf"):
                if search_name and search_name in str(f):
                    return FileResponse(str(f), media_type="application/pdf", filename=f.name)

    raise HTTPException(status_code=404, detail=f"PDF file not found. Searched for: {search_name}")


class ReindexOptions(BaseModel):
    model_version: str = "vlm"
    enable_formula: bool = True
    enable_table: bool = True
    is_ocr: bool = False
    language: str = "ch"


@app.post("/api/v1/knowledge-bases/{kb_id}/documents/batch-reindex")
async def batch_reindex_documents(kb_id: str, req: BatchReindexRequest):
    """
    批量重新入库文档。
    
    如果 document_ids 为空，则自动选择所有 failed 和 waiting_parser 状态的文档。
    所有文档作为一个 MinerU batch 提交，后台异步执行。
    """
    from app.tasks import batch_cloud_ingest_task

    docs = list_documents(kb_id)
    if not docs:
        raise HTTPException(status_code=404, detail="知识库为空")

    if req.document_ids:
        target_docs = [d for d in docs if d["document_id"] in req.document_ids]
    else:
        target_docs = [d for d in docs if d["status"] in ("failed", "waiting_parser", "uploaded")]

    if not target_docs:
        return {"kb_id": kb_id, "total": 0, "message": "没有需要重新入库的文档", "tasks": []}

    # 创建新任务
    items = []
    for doc in target_docs:
        task_id = str(uuid.uuid4())
        create_task(
            task_id=task_id,
            document_id=doc["document_id"],
            kb_id=kb_id,
            status="queued",
            message="批量重新入库",
        )
        items.append({
            "document_id": doc["document_id"],
            "task_id": task_id,
            "file_path": doc["file_path"],
            "filename": doc["filename"],
        })

    options = {
        "model_version": req.model_version,
        "enable_formula": req.enable_formula,
        "enable_table": req.enable_table,
        "is_ocr": req.is_ocr,
        "language": req.language,
    }

    # 按 20 个一批拆分（MinerU 限制 50 files/min）
    BATCH_SIZE = 20
    batches = [items[i:i+BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]

    async def _run_with_logging():
        try:
            print(f"[batch-reindex] 开始处理 {len(items)} 个文档，分 {len(batches)} 批", flush=True)
            for idx, batch in enumerate(batches):
                print(f"[batch-reindex] 第 {idx+1}/{len(batches)} 批，{len(batch)} 个文档", flush=True)
                await batch_cloud_ingest_task(kb_id, batch, options)
                if idx < len(batches) - 1:
                    print(f"[batch-reindex] 等待 70s 避免 MinerU 429 限流", flush=True)
                    await asyncio.sleep(70)
            print(f"[batch-reindex] 全部处理完成", flush=True)
        except Exception as e:
            print(f"[batch-reindex] 异常: {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()

    import threading
    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_run_with_logging())
        loop.close()

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    print(f"[batch-reindex] 后台线程已启动", flush=True)

    return {
        "kb_id": kb_id,
        "total": len(items),
        "message": f"已提交 {len(items)} 个文档到批量入库队列",
        "tasks": [{"task_id": t["task_id"], "document_id": t["document_id"], "filename": t["filename"]} for t in items],
    }


@app.post("/api/v1/documents/{document_id}/ingest")
async def create_ingest_task(
    document_id: str,
    background_tasks: BackgroundTasks,
):
    """
    创建导入任务。

    第一阶段：
    只创建任务骨架，不默认跑本地 MinerU。
    """
    doc = get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")

    task_id = str(uuid.uuid4())

    create_task(
        task_id=task_id,
        document_id=document_id,
        kb_id=doc["kb_id"],
        status="queued",
        message="queued",
    )

    background_tasks.add_task(
        ingest_document_task,
        document_id,
        task_id,
    )

    return {
        "task_id": task_id,
        "document_id": document_id,
        "kb_id": doc["kb_id"],
        "status": "queued",
    }


@app.get("/api/v1/knowledge-bases/{kb_id}/tasks")
async def list_kb_tasks(kb_id: str, limit: int = 50):
    return {
        "kb_id": kb_id,
        "items": list_tasks(kb_id, limit),
    }


@app.get("/api/v1/knowledge-bases/{kb_id}/tasks/summary")
async def kb_tasks_summary(kb_id: str):
    all_tasks = list_tasks(kb_id, 1000)
    total = len(all_tasks)
    failed = sum(1 for t in all_tasks if t["status"] == "failed")
    active = sum(1 for t in all_tasks if t["status"] in ("cloud_requesting", "inserting", "queued", "waiting_parser"))
    return {
        "kb_id": kb_id,
        "total": total,
        "failed": failed,
        "active": active,
        "failure_rate": round(failed / total * 100) if total > 0 else 0,
    }


@app.get("/api/v1/documents/{document_id}/tasks")
async def list_document_tasks(document_id: str):
    doc = get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    tasks = list_tasks(doc["kb_id"], 100)
    return {
        "document_id": document_id,
        "items": [t for t in tasks if t["document_id"] == document_id],
    }


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    return task


@app.post("/api/v1/knowledge-bases/{kb_id}/chat")
async def chat_with_knowledge_base(
    kb_id: str,
    req: ChatRequest,
):
    rag = await get_rag_engine(kb_id)
    from lightrag import QueryParam

    param = QueryParam(
        mode=req.mode,
        top_k=req.top_k,
        chunk_top_k=req.chunk_top_k,
        enable_rerank=req.enable_rerank,
        include_references=req.include_references,
        response_type=req.response_type,
        history_turns=req.history_turns,
        conversation_history=chatHistory,
        max_total_tokens=req.max_total_tokens,
        hl_keywords=req.hl_keywords or [],
        ll_keywords=[],
        stream=req.stream,
    )
    from app.rag_engine import set_chat_api_key
    chat_api_key = env_str("CHAT_LLM_BINDING_API_KEY", env_str("LLM_BINDING_API_KEY"))
    set_chat_api_key(chat_api_key)

    question = req.question

    # 如果用户上传了图片：先直接调视觉模型描述（不走 RAG），再用描述作为检索 query
    if req.image_data:
        try:
            mime = 'image/png' if (req.image_name or '').lower().endswith('.png') else 'image/jpeg'
            data_url = f"data:{mime};base64,{req.image_data}"
            vlm_messages = [
                {"role": "user", "content": [
                    {"type": "text", "text": "请详细描述这张图片的所有可见内容：文字、图表、数据、纹理、颜色、布局等。"},
                    {"type": "image_url", "image_url": {"url": data_url}}
                ]}
            ]
            desc = await rag.vision_model_func(messages=vlm_messages)
            question = f"[用户上传了一张图片，AI 分析如下: {desc}]\n\n{req.question}"
        except Exception as e:
            question = f"[用户上传图片但分析失败: {e}]\n\n{req.question}"

    if req.vlm_enhanced and rag.vision_model_func:
        result = await rag.aquery_vlm_enhanced(question, mode=req.mode)
    else:
        result = await rag.lightrag.aquery(question, param=param, system_prompt=req.system_prompt)

    # 保存对话历史
    chatHistory.append({"role": "user", "content": question})
    chatHistory.append({"role": "assistant", "content": result})
    if len(chatHistory) > 20:
        chatHistory[:] = chatHistory[-20:]

    # 查找图片
    from app.config import DEFAULT_RAG_WORKING_DIR
    images = []
    chunk_path = DEFAULT_RAG_WORKING_DIR / "vdb_chunks.json"
    if chunk_path.exists():
        try:
            with open(chunk_path) as f:
                chunk_data = json.load(f)
            for chunk in chunk_data.get("data", []):
                content = str(chunk.get("content", ""))
                for line in content.split("\n"):
                    if "Image Path:" in line or line.strip().startswith("/"):
                        path = line.split("Image Path:", 1)[-1].strip() if "Image Path:" in line else line.strip()
                        if path.startswith("/") and any(path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]):
                            p = Path(path)
                            if p.exists():
                                if "mineru_outputs" in str(p):
                                    rel = str(p.relative_to("/opt/rag-system/data/mineru_outputs"))
                                    url = f"/rag-images/{rel}"
                                elif str(p).startswith("/opt/rag-system/RAG-Anything/output/"):
                                    rel = str(p.relative_to("/opt/rag-system/RAG-Anything/output"))
                                    url = f"/rag-output/{rel}"
                                else:
                                    continue
                                if url not in images:
                                    images.append(url)
                                    if len(images) >= 6:
                                        break
        except Exception:
            pass

    return {
        "kb_id": kb_id,
        "question": req.question,
        "answer": result,
        "mode": req.mode,
        "vlm_enhanced": req.vlm_enhanced,
        "enable_rerank": req.enable_rerank,
        "has_image": bool(req.image_data),
        "images": images,
    }


@app.post("/api/v1/knowledge-bases/{kb_id}/retrieve")
async def retrieve_evidence(
    kb_id: str,
    req: ChatRequest,
):
    """
    纯检索，不调用 LLM。返回检索到的实体、关系和 chunks。
    """
    from app.config import DEFAULT_RAG_WORKING_DIR, WORKSPACES_DIR
    wd = DEFAULT_RAG_WORKING_DIR if kb_id == "default" else WORKSPACES_DIR / kb_id / "rag_storage"

    rag = await get_rag_engine(kb_id)
    from lightrag import QueryParam

    param = QueryParam(
        mode=req.mode,
        top_k=req.top_k,
        chunk_top_k=30,
        enable_rerank=req.enable_rerank,
    )
    if hasattr(rag, "lightrag") and rag.lightrag:
        result = await rag.lightrag.aquery_data(req.question, param=param)
    else:
        result = {}

    evidence = []
    raw_text = str(result)
    try:
        data = result if isinstance(result, dict) else {}
        # aquery_data 返回 {status, message, data: {entities, relationships, chunks}}
        inner = data.get("data", data)
        # 预加载 text chunks 用于查找 page_idx 和 full_doc_id
        text_chunks_map = {}
        try:
            tc_path = wd / "kv_store_text_chunks.json" if 'wd' in dir() else None
            if not tc_path or not tc_path.exists():
                tc_path = Path("/opt/rag-system/RAG-Anything/rag_storage/kv_store_text_chunks.json")
            if tc_path.exists():
                with open(tc_path) as f:
                    tc_data = json.load(f)
                for cid, cinfo in tc_data.items():
                    if isinstance(cinfo, dict):
                        text_chunks_map[cid] = cinfo
        except Exception:
            pass

        for key in inner:
            items = inner[key] if isinstance(inner[key], list) else []
            for item in items[:10]:
                if isinstance(item, dict):
                    ev_item = {
                        "type": item.get("entity_type", item.get("type", key)),
                        "source": item.get("entity_name", item.get("source", "")),
                        "content": (item.get("description") or item.get("content") or str(item))[:300],
                        "score": item.get("rank", item.get("score", 0)),
                    }
                    # chunk 特有字段：用于定位原文
                    if key == "chunks":
                        if item.get("file_path"):
                            ev_item["file_path"] = item["file_path"]
                        if item.get("reference_id"):
                            ev_item["reference_id"] = item["reference_id"]
                            # 通过 reference_id 查找 page_idx 和 full_doc_id
                            ref_id = item["reference_id"]
                            # reference_id 可能是 "4" 这样的序号，需要匹配 chunk_order_index
                            try:
                                ref_idx = int(ref_id)
                                for cid, cinfo in text_chunks_map.items():
                                    if cinfo.get("chunk_order_index") == ref_idx:
                                        if cinfo.get("page_idx") is not None:
                                            ev_item["page_idx"] = cinfo["page_idx"]
                                        if cinfo.get("full_doc_id"):
                                            ev_item["full_doc_id"] = cinfo["full_doc_id"]
                                        break
                            except (ValueError, TypeError):
                                pass
                        # 如果上面没找到，尝试直接从 item 中获取
                        if "page_idx" not in ev_item and item.get("page_idx") is not None:
                            ev_item["page_idx"] = item["page_idx"]
                        if "full_doc_id" not in ev_item and item.get("full_doc_id"):
                            ev_item["full_doc_id"] = item["full_doc_id"]
                    evidence.append(ev_item)
    except Exception:
        pass

    if not evidence:
        evidence = [{"type": "info", "source": "LightRAG 检索完成", "content": raw_text[:300]}]

    # 扫描 vdb_chunks.json 查找图片引用（仅返回与证据相关的图片）
    images_with_captions = []
    
    # 先从 MinerU content_list.json 构建 caption 映射
    mineru_caption_map = {}
    try:
        mineru_dir = Path("/opt/rag-system/data/mineru_outputs")
        if mineru_dir.exists():
            for root, dirs, files in os.walk(mineru_dir):
                for f in files:
                    if f.endswith("content_list.json"):
                        with open(os.path.join(root, f)) as fp:
                            cl_data = json.load(fp)
                        for item in cl_data:
                            if isinstance(item, dict) and item.get("type") == "image":
                                img_path = item.get("img_path", "")
                                captions = item.get("image_caption", [])
                                if img_path and captions:
                                    mineru_caption_map[os.path.basename(img_path)] = captions[0]
    except Exception:
        pass

    chunk_path = wd / "vdb_chunks.json"
    if chunk_path.exists():
        try:
            with open(chunk_path) as f:
                chunk_data = json.load(f)
            # 收集证据中提到的文件
            evidence_files = set()
            for ev in evidence:
                if ev.get("file_path"):
                    evidence_files.add(ev["file_path"])
            
            for chunk in chunk_data.get("data", []):
                content = str(chunk.get("content", ""))
                # 只返回与证据相关的图片
                chunk_file = chunk.get("file_path", "")
                if evidence_files and chunk_file not in evidence_files:
                    continue
                    
                for line in content.split("\n"):
                    if "Image Path:" in line:
                        path = line.split("Image Path:", 1)[-1].strip()
                        if path.startswith("/") and any(path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]):
                            p = Path(path)
                            if p.exists():
                                if "mineru_outputs" in str(p):
                                    rel = str(p.relative_to("/opt/rag-system/data/mineru_outputs"))
                                    url = f"/rag-images/{rel}"
                                elif str(p).startswith("/opt/rag-system/RAG-Anything/output/"):
                                    rel = str(p.relative_to("/opt/rag-system/RAG-Anything/output"))
                                    url = f"/rag-output/{rel}"
                                else:
                                    continue
                                
                                # 查找 caption：优先 MinerU，其次 chunk 内容
                                caption = ""
                                img_basename = os.path.basename(path)
                                if img_basename in mineru_caption_map:
                                    caption = mineru_caption_map[img_basename]
                                else:
                                    for cap_line in content.split("\n"):
                                        if cap_line.startswith("Caption:"):
                                            cap_val = cap_line.split("Caption:", 1)[-1].strip()
                                            if cap_val and cap_val != "None":
                                                caption = cap_val
                                            break
                                
                                img_obj = {"url": url, "caption": caption}
                                if img_obj not in images_with_captions:
                                    images_with_captions.append(img_obj)
                                    if len(images_with_captions) >= 4:
                                        break
                if len(images_with_captions) >= 4:
                    break
        except Exception:
            pass

    return {
        "kb_id": kb_id,
        "question": req.question,
        "mode": req.mode,
        "evidence": evidence,
        "images": images_with_captions,
    }
