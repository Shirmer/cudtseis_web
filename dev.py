#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "Project-Code" / "backend"
FRONTEND_DIR = ROOT / "Project-Code" / "Frontend" / "quakes-frontend"
BACKEND_REQUIREMENTS = BACKEND_DIR / "requirements.txt"
VENV_DIR = BACKEND_DIR / ".venv"
DEFAULT_DB_URL = "postgresql+psycopg://127.0.0.1:5432/quakes"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8001
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 5173


def info(message: str) -> None:
    print(f"[dev] {message}")


def fail(message: str, code: int = 1) -> None:
    print(f"[dev][error] {message}", file=sys.stderr)
    raise SystemExit(code)


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    info(" ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=check,
        text=True,
        capture_output=capture,
    )


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def find_executable(name: str) -> str | None:
    path = shutil.which(name)
    if path:
        return path
    if platform.system() == "Darwin":
        candidates = [
            f"/opt/homebrew/opt/postgresql@17/bin/{name}",
            f"/opt/homebrew/opt/postgresql@16/bin/{name}",
            f"/usr/local/opt/postgresql@17/bin/{name}",
            f"/usr/local/opt/postgresql@16/bin/{name}",
        ]
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
    return None


def npm_command() -> str:
    npm = shutil.which("npm")
    if npm:
        return npm
    fail("未找到 npm。请先安装 Node.js（会自带 npm）。")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def parse_db_url() -> tuple[str, int, str | None, str | None]:
    db_url = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
    parsed = urlparse(db_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432
    user = parsed.username
    password = parsed.password
    return host, port, user, password


def is_local_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def can_connect(host: str, port: int, timeout: float = 0.8) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def ensure_backend_venv() -> None:
    python_path = venv_python()
    if python_path.exists():
        return
    info("创建后端虚拟环境 (.venv)")
    run([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT)


def ensure_backend_deps() -> None:
    ensure_backend_venv()
    python_path = str(venv_python())
    check_cmd = [
        python_path,
        "-c",
        "import fastapi,uvicorn,sqlalchemy,psycopg,geoalchemy2,shapely",
    ]
    res = subprocess.run(
        check_cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
    )
    if res.returncode == 0:
        info("后端依赖已就绪")
        return
    info("安装后端依赖")
    install_cmd = [python_path, "-m", "pip", "install", "-r", str(BACKEND_REQUIREMENTS)]
    first_try = run(install_cmd, cwd=ROOT, check=False)
    if first_try.returncode == 0:
        return

    info("pip 安装失败，尝试 trusted-host 回退方案")
    fallback_cmd = [
        python_path,
        "-m",
        "pip",
        "install",
        "--index-url",
        "https://pypi.org/simple",
        "--trusted-host",
        "pypi.org",
        "--trusted-host",
        "files.pythonhosted.org",
        "-r",
        str(BACKEND_REQUIREMENTS),
    ]
    fallback_try = run(fallback_cmd, cwd=ROOT, check=False)
    if fallback_try.returncode != 0:
        fail("后端依赖安装失败，请检查网络或证书配置后重试。")


def ensure_frontend_deps() -> None:
    if not command_exists("node"):
        fail("未找到 node。请先安装 Node.js。")
    npm = npm_command()
    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists():
        info("前端依赖已就绪")
        return
    info("安装前端依赖")
    npm_cache = FRONTEND_DIR / ".npm-cache"
    npm_cache.mkdir(parents=True, exist_ok=True)
    install_cmd = [npm, "install", "--cache", str(npm_cache)]
    first_try = run(install_cmd, cwd=FRONTEND_DIR, check=False)
    if first_try.returncode == 0:
        return

    info("npm 安装失败，尝试 strict-ssl=false 回退方案")
    fallback_cmd = [
        npm,
        "install",
        "--cache",
        str(npm_cache),
        "--strict-ssl=false",
        "--registry=https://registry.npmjs.org/",
    ]
    fallback_try = run(fallback_cmd, cwd=FRONTEND_DIR, check=False)
    if fallback_try.returncode != 0:
        fail("前端依赖安装失败，请检查网络或 npm 证书配置后重试。")


def try_start_local_postgres() -> None:
    host, port, _, _ = parse_db_url()
    if not is_local_host(host):
        info("DATABASE_URL 指向远程数据库，跳过本地 PostgreSQL 启动检查")
        return
    if can_connect(host, port):
        info(f"本地数据库端口可用: {host}:{port}")
        return

    if platform.system() == "Darwin" and command_exists("brew"):
        info("尝试通过 Homebrew 启动 PostgreSQL 17")
        run(["brew", "services", "start", "postgresql@17"], cwd=ROOT, check=False)
        for _ in range(20):
            if can_connect(host, port):
                info(f"PostgreSQL 已启动: {host}:{port}")
                return
            time.sleep(0.5)

    if platform.system() == "Windows":
        fail(
            "本地数据库未启动。请先在 PowerShell 执行: net start postgresql-x64-17，"
            "然后重新运行 python dev.py"
        )
    fail(
        f"本地数据库未启动（{host}:{port} 无法连接）。"
        "请先启动 PostgreSQL 服务后重试。"
    )


def pg_env() -> dict[str, str]:
    host, port, user, password = parse_db_url()
    env = os.environ.copy()
    env["PGHOST"] = host
    env["PGPORT"] = str(port)
    if user:
        env["PGUSER"] = user
    if password:
        env["PGPASSWORD"] = password
    return env


def ensure_database_initialized() -> None:
    host, _, _, _ = parse_db_url()
    if not is_local_host(host):
        info("远程数据库场景下，跳过自动建库")
        return
    psql = find_executable("psql")
    createdb = find_executable("createdb")
    if not psql:
        info("未找到 psql，跳过自动建库步骤")
        return

    env = pg_env()
    check_db = run(
        [psql, "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='quakes'"],
        env=env,
        capture=True,
        check=False,
    )
    if check_db.returncode != 0:
        fail("无法连接 PostgreSQL。请确认数据库服务已启动。")

    if check_db.stdout.strip() != "1":
        info("创建数据库 quakes")
        if createdb:
            run([createdb, "quakes"], env=env)
        else:
            run([psql, "-d", "postgres", "-c", "CREATE DATABASE quakes;"], env=env)

    ext = run(
        [psql, "-d", "quakes", "-tAc", "SELECT 1 FROM pg_extension WHERE extname='postgis'"],
        env=env,
        capture=True,
        check=False,
    )
    if ext.stdout.strip() == "1":
        info("PostGIS 扩展已就绪")
        return

    info("启用 PostGIS 扩展")
    create_ext = run(
        [psql, "-d", "quakes", "-c", "CREATE EXTENSION IF NOT EXISTS postgis;"],
        env=env,
        check=False,
        capture=True,
    )
    if create_ext.returncode != 0:
        fail(
            "创建 PostGIS 扩展失败。请确认你的 PostgreSQL 版本与 PostGIS 安装匹配。"
        )


def print_status() -> None:
    psql = find_executable("psql")
    info(f"Python: {sys.version.split()[0]}")
    info(f"Node: {shutil.which('node') or '未安装'}")
    info(f"npm: {shutil.which('npm') or '未安装'}")
    info(f"psql: {psql or '未安装'}")
    info(f"Backend dir: {BACKEND_DIR}")
    info(f"Frontend dir: {FRONTEND_DIR}")


def terminate_process(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        return
    info(f"停止 {name} ...")
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        info(f"{name} 未及时退出，执行强制结束")
        proc.kill()


def start_services() -> int:
    backend_env = os.environ.copy()
    backend_env.setdefault("DATABASE_URL", DEFAULT_DB_URL)

    backend_cmd = [
        str(venv_python()),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
        "--reload",
    ]
    frontend_cmd = [
        npm_command(),
        "run",
        "dev",
        "--",
        "--host",
        FRONTEND_HOST,
        "--port",
        str(FRONTEND_PORT),
    ]

    info("启动后端服务")
    backend_proc = subprocess.Popen(backend_cmd, cwd=str(BACKEND_DIR), env=backend_env)
    info("启动前端服务")
    frontend_proc = subprocess.Popen(frontend_cmd, cwd=str(FRONTEND_DIR))

    info(f"后端地址: http://{BACKEND_HOST}:{BACKEND_PORT}")
    info(f"前端地址: http://{FRONTEND_HOST}:{FRONTEND_PORT}")
    info("按 Ctrl+C 可同时停止前后端")

    procs = [("backend", backend_proc), ("frontend", frontend_proc)]
    try:
        while True:
            for name, proc in procs:
                code = proc.poll()
                if code is not None:
                    info(f"{name} 进程已退出 (code={code})，准备停止其余进程")
                    for other_name, other_proc in procs:
                        if other_proc is not proc:
                            terminate_process(other_proc, other_name)
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        for name, proc in procs:
            terminate_process(proc, name)
        return 0


def do_setup() -> None:
    print_status()
    ensure_backend_deps()
    ensure_frontend_deps()
    try_start_local_postgres()
    ensure_database_initialized()
    info("setup 完成")


def do_up() -> int:
    do_setup()
    return start_services()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-platform one-command dev runner")
    parser.add_argument(
        "command",
        nargs="?",
        default="up",
        choices=["up", "setup", "check"],
        help="up: 启动项目, setup: 仅安装与初始化, check: 仅检查环境",
    )
    args = parser.parse_args()

    if args.command == "check":
        print_status()
        return
    if args.command == "setup":
        do_setup()
        return

    code = do_up()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
