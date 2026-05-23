# -*- coding: utf-8 -*-

import os
from pathlib import Path
from dotenv import load_dotenv


def _default_rag_anything_root() -> Path:
    packaged_root = Path(__file__).resolve().parents[2] / "RAG-Anything"
    production_root = Path("/opt/rag-system/RAG-Anything")
    if packaged_root.is_dir():
        return packaged_root
    return production_root


# RAG-Anything 项目根目录。服务器默认仍支持 /opt/rag-system/RAG-Anything；
# 本地开发时自动使用仓库内的 rag-system/RAG-Anything。
RAG_ANYTHING_ROOT = Path(
    os.getenv("RAG_ANYTHING_ROOT", str(_default_rag_anything_root()))
)

# 读取 RAG-Anything 里的 .env
load_dotenv(RAG_ANYTHING_ROOT / ".env", override=True)

# 数据目录
DATA_DIR = Path(os.getenv("RAG_API_DATA_DIR", "/opt/rag-system/data"))
UPLOAD_DIR = DATA_DIR / "uploads"
TASK_DIR = DATA_DIR / "tasks"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TASK_DIR.mkdir(parents=True, exist_ok=True)

# 默认使用你现在已经跑通的 rag_storage
DEFAULT_RAG_WORKING_DIR = Path(
    os.getenv(
        "DEFAULT_RAG_WORKING_DIR",
        str(RAG_ANYTHING_ROOT / "rag_storage"),
    )
)

# 多知识库 workspace 目录，后面正式多用户会用到
WORKSPACES_DIR = Path(os.getenv("RAG_WORKSPACES_DIR", "/opt/rag-system/workspaces"))
WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


def env_str(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    if value is None:
        return default

    value = value.strip()

    # 兼容 .env 行内注释
    if "#" in value:
        value = value.split("#", 1)[0].strip()

    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"true", "1", "yes", "y", "on"}
