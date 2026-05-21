# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("/opt/rag-system/data/rag_api_metadata.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # 添加 content_hash 列（用于去重）
        try:
            conn.execute("ALTER TABLE documents ADD COLUMN content_hash TEXT")
        except Exception:
            pass  # 列已存在

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                kb_id TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.commit()


def now():
    return datetime.utcnow().isoformat()


def create_document(document_id, kb_id, filename, file_path):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO documents
            (document_id, kb_id, filename, file_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (document_id, kb_id, filename, file_path, "uploaded", now()),
        )
        conn.commit()


def list_documents(kb_id):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM documents
            WHERE kb_id = ?
            ORDER BY created_at DESC
            """,
            (kb_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_document(document_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE document_id = ?",
            (document_id,),
        ).fetchone()

    return dict(row) if row else None


def update_document_status(document_id, status):
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = ? WHERE document_id = ?",
            (status, document_id),
        )
        conn.commit()


def create_task(task_id, document_id, kb_id, status="queued", message=""):
    t = now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks
            (task_id, document_id, kb_id, status, message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, document_id, kb_id, status, message, t, t),
        )
        conn.commit()


def update_task(task_id, status, message=""):
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET status = ?, message = ?, updated_at = ?
            WHERE task_id = ?
            """,
            (status, message, now(), task_id),
        )
        conn.commit()


def list_tasks(kb_id, limit=50):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM tasks
            WHERE kb_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (kb_id, limit),
        ).fetchall()

    return [dict(row) for row in rows]


def get_task(task_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE task_id = ?",
            (task_id,),
        ).fetchone()

    return dict(row) if row else None


def delete_document(document_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM tasks WHERE document_id = ?", (document_id,))
        conn.commit()


def get_document_stats(kb_id):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) as cnt
            FROM documents
            WHERE kb_id = ?
            GROUP BY status
            """,
            (kb_id,),
        ).fetchall()

    counts = {row["status"]: row["cnt"] for row in rows}
    return {
        "kb_id": kb_id,
        "total_documents": sum(counts.values()),
        "indexed": counts.get("indexed", 0),
        "failed": counts.get("failed", 0),
        "waiting_parser": counts.get("waiting_parser", 0),
        "processing": counts.get("processing", 0),
        "uploaded": counts.get("uploaded", 0),
    }
