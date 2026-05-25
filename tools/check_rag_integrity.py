#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "Project-Code" / "Frontend" / "quakes-frontend"
RAG_API = ROOT / "rag-system" / "rag-api"
RAG_ENGINE = ROOT / "rag-system" / "RAG-Anything"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def ok(message: str) -> None:
    print(f"ok: {message}")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)
    print(f"FAIL: {message}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_path_state(errors: list[str]) -> None:
    expected_missing = [
        FRONTEND / "src" / "views" / "RAGDashboard.vue",
        FRONTEND / "src" / "api" / "rag.ts",
        ROOT / "RAG-Anything-main",
    ]
    for path in expected_missing:
        if path.exists():
            fail(errors, f"{rel(path)} should not exist")
        else:
            ok(f"{rel(path)} is absent")

    expected_present = [
        FRONTEND / "public" / "cdut_seislab_dino.svg",
        RAG_API / "app" / "static" / "cdut_seislab_dino.svg",
        RAG_ENGINE / "raganything" / "__init__.py",
        FRONTEND / "public" / "rag" / "index.html",
        RAG_API / "app" / "static" / "index.html",
    ]
    for path in expected_present:
        if path.exists():
            ok(f"{rel(path)} exists")
        else:
            fail(errors, f"{rel(path)} is missing")


def check_router(errors: list[str]) -> None:
    router = FRONTEND / "src" / "router" / "index.ts"
    text = read(router)
    if "RAGDashboard" in text:
        fail(errors, f"{rel(router)} still references RAGDashboard")
    else:
        ok("router no longer references RAGDashboard")
    if "/rag/index.html" not in text:
        fail(errors, f"{rel(router)} does not redirect /rag to /rag/index.html")
    else:
        ok("/rag redirects to static workbench")
    for marker in ("path: '/dashboard'", "path: '/history'", "DashboardView", "HistoryData"):
        if marker not in text:
            fail(errors, f"{rel(router)} missing earthquake route marker: {marker}")
        else:
            ok(f"earthquake route marker present: {marker}")


def check_home_entries(errors: list[str]) -> None:
    home = FRONTEND / "src" / "views" / "HomeView.vue"
    text = read(home)
    required_entries = [
        ("地震目录", "router.push('/dashboard')"),
        ("历史数据", "router.push('/history')"),
        ("RAG 工作台", "router.push('/rag')"),
        ("RAG 知识工作台", "router.push('/rag')"),
    ]
    for label, action in required_entries:
        if label not in text or action not in text:
            fail(errors, f"{rel(home)} missing homepage entry: {label} -> {action}")
        else:
            ok(f"homepage entry present: {label}")

    removed_entries = ["文献库", "论文"]
    for label in removed_entries:
        if label in text:
            fail(errors, f"{rel(home)} should not restore removed entry: {label}")
        else:
            ok(f"removed homepage entry remains absent: {label}")

    active_ui_files = [
        home,
        FRONTEND / "src" / "views" / "DashboardView.vue",
        FRONTEND / "public" / "rag" / "index.html",
        RAG_API / "app" / "static" / "index.html",
    ]
    for path in active_ui_files:
        text = read(path)
        if "cdut_logo.png" in text:
            fail(errors, f"{rel(path)} still references the old CDUT logo")
        elif "cdut_seislab_dino.svg" in text:
            ok(f"{rel(path)} uses the dinosaur SEISLAB logo")


def check_workbench(path: Path, errors: list[str]) -> None:
    text = read(path)
    required = [
        "RAG 知识工作台",
        "一、知识库问答",
        "二、上传 PDF",
        "二-B、文献添加管理",
        "三、content_list 直接入库",
        "四、创建导入任务 / 查看状态",
        "五、文档列表",
        "batchProgressPanel",
        "serverFilesList",
        "documentsList",
        "apiPath(",
        'window.location.pathname.startsWith("/rag") ? "/rag-api" : ""',
    ]
    for marker in required:
        if marker not in text:
            fail(errors, f"{rel(path)} missing marker: {marker}")
        else:
            ok(f"{rel(path)} marker present: {marker}")

    direct_fetch = re.findall(r"fetch\(\s*([`'\"])/(?:health|api)", text)
    if direct_fetch:
        fail(errors, f"{rel(path)} has direct root API fetch calls instead of apiPath()")
    else:
        ok(f"{rel(path)} API calls use apiPath()")


def check_workbench_pair(errors: list[str]) -> None:
    frontend_index = FRONTEND / "public" / "rag" / "index.html"
    rag_api_index = RAG_API / "app" / "static" / "index.html"
    check_workbench(frontend_index, errors)
    check_workbench(rag_api_index, errors)
    if frontend_index.read_bytes() == rag_api_index.read_bytes():
        ok("frontend and rag-api workbench HTML files are identical")
    else:
        fail(errors, "frontend and rag-api workbench HTML files differ")


def check_rag_engine_paths(errors: list[str]) -> None:
    checks = [
        ROOT / "Project-Code" / "backend" / "app" / "setting.py",
        ROOT / "Project-Code" / "backend" / "app" / "raganything_service.py",
        ROOT / "Project-Code" / "backend" / "requirements-raganything.txt",
        ROOT / "rag-system" / "rag-api" / "app" / "config.py",
    ]
    for path in checks:
        text = read(path)
        if "RAG-Anything-main" in text:
            fail(errors, f"{rel(path)} still references RAG-Anything-main")
        else:
            ok(f"{rel(path)} does not reference RAG-Anything-main")


def check_frontend_proxy(errors: list[str]) -> None:
    vite_config = FRONTEND / "vite.config.ts"
    text = read(vite_config)
    required = [
        "'/rag-api'",
        "target: 'http://127.0.0.1:8010'",
        "rewrite: (path) => path.replace(/^\\/rag-api/, '')",
    ]
    for marker in required:
        if marker not in text:
            fail(errors, f"{rel(vite_config)} missing RAG API proxy marker: {marker}")
        else:
            ok(f"{rel(vite_config)} RAG API proxy marker present: {marker}")


def check_qdrinx_absent(errors: list[str]) -> None:
    ignored = {".git", "node_modules", ".venv", "dist", "__pycache__"}
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if any(part in ignored for part in path.parts):
            continue
        if "qdrinx" in path.name.lower():
            hits.append(rel(path))
    if hits:
        fail(errors, "qdrinx remnants found: " + ", ".join(hits[:20]))
    else:
        ok("no qdrinx remnants found")


def main() -> int:
    errors: list[str] = []
    check_path_state(errors)
    check_router(errors)
    check_home_entries(errors)
    check_workbench_pair(errors)
    check_rag_engine_paths(errors)
    check_frontend_proxy(errors)
    check_qdrinx_absent(errors)
    if errors:
        print(f"\nRAG integrity check failed: {len(errors)} issue(s).")
        return 1
    print("\nRAG integrity check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
