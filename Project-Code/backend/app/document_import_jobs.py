from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import threading
import uuid
from typing import Any

from sqlalchemy.orm import Session

from .db import SessionLocal
from .geo_ingest_service import SUPPORTED_DOCUMENT_SUFFIXES, ingest_geo_document
from .models import DocumentImportItem, DocumentImportJob
from .settings import settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
_IMPORT_LOCK = threading.Lock()


def create_document_import_job(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    directory = _resolve_batch_directory(str(payload.get("directoryPath") or ""))
    recursive = bool(payload.get("recursive", False))
    force = bool(payload.get("force", False))
    limit = max(1, min(int(payload.get("limit") or 100), 1000))
    extensions = _normalize_extensions(payload.get("extensions") or list(SUPPORTED_DOCUMENT_SUFFIXES))

    iterator = directory.rglob("*") if recursive else directory.glob("*")
    files = sorted(path for path in iterator if path.is_file() and path.suffix.lower() in extensions)[:limit]

    job = DocumentImportJob(
        id=str(uuid.uuid4()),
        directory_path=str(directory),
        recursive=recursive,
        force=force,
        limit=limit,
        extensions_json=sorted(extensions),
        status="queued" if files else "completed",
        total=len(files),
        queued=len(files),
        message="Import job queued." if files else "No supported documents found.",
        finished_at=None if files else datetime.now(timezone.utc),
    )
    db.add(job)
    for index, path in enumerate(files):
        db.add(
            DocumentImportItem(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{job.id}:{index}:{path}")),
                job_id=job.id,
                file_path=str(path),
                title=path.stem,
                status="queued",
            )
        )
    db.commit()
    return get_document_import_job(db, job.id)


def get_document_import_job(db: Session, job_id: str) -> dict[str, Any]:
    job = db.get(DocumentImportJob, job_id)
    if job is None:
        raise ValueError("Import job not found")
    _refresh_job_counts(db, job)
    db.commit()
    return _job_to_dict(db, job)


def list_document_import_jobs(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit or 20), 100))
    jobs = (
        db.query(DocumentImportJob)
        .order_by(DocumentImportJob.created_at.desc())
        .limit(limit)
        .all()
    )
    for job in jobs:
        _refresh_job_counts(db, job)
    db.commit()
    return [_job_to_dict(db, job, item_limit=20) for job in jobs]


def process_next_import_item() -> dict[str, Any]:
    if not _IMPORT_LOCK.acquire(blocking=False):
        return {"processed": False, "reason": "worker-busy"}
    try:
        with SessionLocal() as db:
            _recover_stale_running_items(db)
            item = (
                db.query(DocumentImportItem)
                .filter(DocumentImportItem.status == "queued")
                .order_by(DocumentImportItem.created_at.asc())
                .first()
            )
            if item is None:
                _finalize_open_jobs(db)
                db.commit()
                return {"processed": False, "reason": "queue-empty"}

            job = db.get(DocumentImportJob, item.job_id)
            if job is None:
                item.status = "failed"
                item.error = "Parent import job was not found."
                item.finished_at = datetime.now(timezone.utc)
                db.commit()
                return {"processed": True, "reason": "missing-job"}

            now = datetime.now(timezone.utc)
            item_id = item.id
            job_id = item.job_id
            job.status = "running"
            job.started_at = job.started_at or now
            job.message = f"Indexing {Path(item.file_path).name}"
            item.status = "running"
            item.started_at = now
            item.error = ""
            _refresh_job_counts(db, job)
            db.commit()

            try:
                result = ingest_geo_document(
                    db,
                    {
                        "filePath": item.file_path,
                        "title": item.title or Path(item.file_path).stem,
                        "force": job.force,
                    },
                )
                skipped = "already exists" in str(result.get("message", "")).lower()
                item = db.get(DocumentImportItem, item_id)
                if item is not None:
                    item.status = "skipped" if skipped else str(result.get("status") or "indexed")
                    item.document_id = str(result.get("documentId") or "")
                    item.paper_id = str(result.get("paperId") or "")
                    item.title = str(result.get("title") or item.title or Path(item.file_path).stem)
                    item.pages = int(result.get("pages") or 0)
                    item.units = int(result.get("units") or 0)
                    item.multimodal_units = int(result.get("multimodalUnits") or 0)
                    item.storage_uri = str(result.get("storageUri") or "")
                    item.embedding_backend = str(result.get("embeddingBackend") or "")
                    item.message = str(result.get("message") or "")
                    item.error = ""
                    item.finished_at = datetime.now(timezone.utc)
            except Exception as exc:
                db.rollback()
                item = db.get(DocumentImportItem, item_id)
                if item is not None:
                    item.status = "failed"
                    item.error = str(exc)
                    item.finished_at = datetime.now(timezone.utc)

            job = db.get(DocumentImportJob, job_id)
            if job is not None:
                _refresh_job_counts(db, job)
            db.commit()
            return {"processed": True, "jobId": job_id}
    finally:
        _IMPORT_LOCK.release()


async def import_worker_loop() -> None:
    import asyncio

    while True:
        try:
            result = await asyncio.to_thread(process_next_import_item)
            delay = 0.1 if result.get("processed") else settings.geo_rag_import_worker_poll_seconds
        except Exception as exc:
            print(f"[import-worker] {exc}", flush=True)
            delay = max(1.0, settings.geo_rag_import_worker_poll_seconds)
        await asyncio.sleep(delay)


def _refresh_job_counts(db: Session, job: DocumentImportJob) -> None:
    counts = Counter(
        status
        for (status,) in db.query(DocumentImportItem.status).filter(DocumentImportItem.job_id == job.id).all()
    )
    job.total = sum(counts.values())
    job.queued = counts.get("queued", 0)
    job.running = counts.get("running", 0)
    job.succeeded = counts.get("indexed", 0) + counts.get("ready", 0)
    job.skipped = counts.get("skipped", 0)
    job.failed = counts.get("failed", 0)
    if job.total == 0:
        job.status = "completed"
        job.finished_at = job.finished_at or datetime.now(timezone.utc)
    elif job.queued or job.running:
        if job.running:
            job.status = "running"
        elif job.status not in {"running", "queued"}:
            job.status = "queued"
        job.finished_at = None
    else:
        job.status = "completed" if job.failed == 0 else "completed_with_errors"
        job.finished_at = job.finished_at or datetime.now(timezone.utc)
        job.message = "Import job completed." if job.failed == 0 else "Import job completed with failed items."


def _finalize_open_jobs(db: Session) -> None:
    jobs = db.query(DocumentImportJob).filter(DocumentImportJob.status.in_(["queued", "running"])).all()
    for job in jobs:
        _refresh_job_counts(db, job)


def _recover_stale_running_items(db: Session) -> None:
    # The worker is intentionally single-writer. If the backend process was
    # interrupted while an item was running, recover it to queued so server
    # restart can continue instead of leaving the import half-stuck forever.
    stale_items = db.query(DocumentImportItem).filter(DocumentImportItem.status == "running").all()
    for item in stale_items:
        item.status = "queued"
        item.message = "Recovered after worker restart; queued for retry."
        item.error = ""
        item.started_at = None
    if stale_items:
        jobs = db.query(DocumentImportJob).filter(DocumentImportJob.status == "running").all()
        for job in jobs:
            job.status = "queued"
            job.message = "Recovered after worker restart."
        db.commit()


def _job_to_dict(db: Session, job: DocumentImportJob, *, item_limit: int = 100) -> dict[str, Any]:
    items = (
        db.query(DocumentImportItem)
        .filter(DocumentImportItem.job_id == job.id)
        .order_by(DocumentImportItem.created_at.asc())
        .limit(item_limit)
        .all()
    )
    processed = job.succeeded + job.skipped + job.failed
    progress = 1.0 if job.total == 0 else processed / max(job.total, 1)
    return {
        "jobId": job.id,
        "directoryPath": job.directory_path,
        "recursive": job.recursive,
        "force": job.force,
        "limit": job.limit,
        "status": job.status,
        "progress": round(progress, 4),
        "total": job.total,
        "queued": job.queued,
        "running": job.running,
        "succeeded": job.succeeded,
        "skipped": job.skipped,
        "failed": job.failed,
        "message": job.message,
        "items": [_item_to_dict(item) for item in items],
        "createdAt": _iso(job.created_at),
        "startedAt": _iso(job.started_at),
        "finishedAt": _iso(job.finished_at),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _item_to_dict(item: DocumentImportItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "filePath": item.file_path,
        "status": item.status,
        "documentId": item.document_id,
        "paperId": item.paper_id,
        "title": item.title,
        "pages": item.pages,
        "units": item.units,
        "multimodalUnits": item.multimodal_units,
        "storageUri": item.storage_uri,
        "embeddingBackend": item.embedding_backend,
        "message": item.message,
        "error": item.error,
        "startedAt": _iso(item.started_at),
        "finishedAt": _iso(item.finished_at),
    }


def _resolve_batch_directory(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("directoryPath is required")
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    resolved = candidate.expanduser().resolve()
    if not resolved.exists():
        raise ValueError(f"Batch directory does not exist: {resolved}")
    if not resolved.is_dir():
        raise ValueError(f"Batch path is not a directory: {resolved}")
    return resolved


def _normalize_extensions(raw_extensions: Any) -> set[str]:
    values = {
        str(item).lower().strip()
        for item in raw_extensions
        if str(item).strip()
    }
    values = {item if item.startswith(".") else f".{item}" for item in values}
    return values.intersection(SUPPORTED_DOCUMENT_SUFFIXES) or SUPPORTED_DOCUMENT_SUFFIXES


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""
