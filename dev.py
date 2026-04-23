#!/usr/bin/env python3
from pathlib import Path
import subprocess
import shutil
import sys
import os

ROOT = Path(__file__).resolve().parent

BACKEND_DIR = ROOT / "Project-Code" / "backend"
FRONTEND_DIR = ROOT / "Project-Code" / "Frontend" / "quakes-frontend"


def pick_python():
    candidates = [
        ROOT / ".venv-win" / "Scripts" / "python.exe",
        ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def pick_node():
    candidates = [
        shutil.which("node"),
        shutil.which("node.exe"),
        str(Path(r"I:\node\node.exe")),
        str(Path(r"C:\Program Files\nodejs\node.exe")),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def pick_npm():
    candidates = [
        shutil.which("npm"),
        shutil.which("npm.cmd"),
        str(Path(r"I:\node\npm.cmd")),
        str(Path(r"C:\Program Files\nodejs\npm.cmd")),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def run(cmd, cwd=None, env=None):
    print("[dev]", " ".join(cmd))
    return subprocess.Popen(cmd, cwd=cwd, env=env)


def check(cmd):
    return shutil.which(cmd) is not None


def main():
    print("[dev] 启动标准开发环境")
    python_executable = pick_python()
    node_executable = pick_node()
    npm_executable = pick_npm()

    # --- check ---
    if not node_executable:
        print("[dev][error] node 未安装")
        sys.exit(1)

    if not npm_executable:
        print("[dev][error] npm 未安装")
        sys.exit(1)

    # --- env ---
    backend_env = os.environ.copy()
    frontend_env = os.environ.copy()
    node_dir = str(Path(node_executable).parent)
    backend_env["PATH"] = node_dir + os.pathsep + backend_env.get("PATH", "")
    frontend_env["PATH"] = node_dir + os.pathsep + frontend_env.get("PATH", "")

    # --- start backend ---
    backend_proc = run(
        [python_executable, "start.py"],
        cwd=str(BACKEND_DIR),
        env=backend_env,
    )

    # --- start frontend ---
    frontend_proc = run(
        [npm_executable, "run", "dev"],
        cwd=str(FRONTEND_DIR),
        env=frontend_env,
    )

    print("\n[dev] backend http://127.0.0.1:8001")
    print("[dev] frontend http://127.0.0.1:5173")

    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\n[dev] stopping...")
        backend_proc.terminate()
        frontend_proc.terminate()


if __name__ == "__main__":
    main()
