#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "Project-Code" / "backend"
FRONTEND_DIR = ROOT / "Project-Code" / "Frontend" / "quakes-frontend"
BACKEND_VENV = BACKEND_DIR / ".venv"
BACKEND_ENV = BACKEND_DIR / ".env"
BACKEND_ENV_EXAMPLE = BACKEND_DIR / ".env.example"
BACKEND_REQUIREMENTS = BACKEND_DIR / "requirements.txt"
FRONTEND_LOCK = FRONTEND_DIR / "package-lock.json"
DEFAULT_DATABASE_URL = "postgresql+psycopg://127.0.0.1:5432/quakes"
DEFAULT_PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
DEFAULT_PIP_TRUSTED_HOST = "pypi.tuna.tsinghua.edu.cn"


def is_windows() -> bool:
    return platform.system() == "Windows"


def backend_python() -> Path:
    if is_windows():
        return BACKEND_VENV / "Scripts" / "python.exe"
    return BACKEND_VENV / "bin" / "python"


def command_text(cmd: list[str | Path]) -> str:
    return subprocess.list2cmdline([str(part) for part in cmd])


def log(message: str) -> None:
    print(f"[dev] {message}", flush=True)


def warn(message: str) -> None:
    print(f"[dev][warn] {message}", flush=True)


def error(message: str) -> None:
    print(f"[dev][error] {message}", flush=True)


def run_checked(
    cmd: list[str | Path],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    allow_fail: bool = False,
) -> subprocess.CompletedProcess[str]:
    log(command_text(cmd))
    result = subprocess.run(
        [str(part) for part in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
    )
    if result.returncode != 0 and not allow_fail:
        raise SystemExit(result.returncode)
    return result


def run_capture(
    cmd: list[str | Path],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(part) for part in cmd],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def which_any(names: list[str]) -> str | None:
    for name in names:
        candidate = shutil.which(name)
        if candidate:
            return candidate
    return None


def find_node() -> str | None:
    return which_any(["node.exe", "node"] if is_windows() else ["node"])


def find_npm() -> str | None:
    return which_any(["npm.cmd", "npm.exe", "npm"] if is_windows() else ["npm"])


def find_psql() -> str | None:
    names = ["psql.exe", "psql"] if is_windows() else ["psql"]
    candidate = which_any(names)
    if candidate:
        return candidate

    common_paths = [
        Path("/opt/homebrew/opt/postgresql@17/bin/psql"),
        Path("/usr/local/opt/postgresql@17/bin/psql"),
        Path("/opt/homebrew/bin/psql"),
        Path("/usr/local/bin/psql"),
        Path(r"C:\Program Files\PostgreSQL\17\bin\psql.exe"),
    ]
    for path in common_paths:
        if path.exists():
            return str(path)
    return None


def check_version(cmd: list[str], minimum_major: int | None = None) -> bool:
    result = run_capture(cmd)
    if result.returncode != 0:
        return False
    output = (result.stdout or result.stderr).strip().splitlines()[0]
    print(f"  ok: {command_text(cmd[:1])} {output}", flush=True)
    if minimum_major is None:
        return True
    match = re.search(r"(\d+)", output)
    if not match:
        return False
    return int(match.group(1)) >= minimum_major


def check_environment() -> int:
    log("Checking local development environment")
    ok = True

    python_ok = sys.version_info >= (3, 10)
    print(f"  {'ok' if python_ok else 'missing'}: Python {platform.python_version()}", flush=True)
    ok = ok and python_ok

    node = find_node()
    npm = find_npm()
    if node:
        ok = check_version([node, "--version"], 20) and ok
    else:
        print("  missing: node", flush=True)
        ok = False

    if npm:
        ok = check_version([npm, "--version"], 10) and ok
    else:
        print("  missing: npm", flush=True)
        ok = False

    psql = find_psql()
    if psql:
        check_version([psql, "--version"])
    else:
        warn("psql not found. Install PostgreSQL 17 and add its bin directory to PATH.")

    print(f"  {'ok' if BACKEND_ENV.exists() else 'missing'}: {BACKEND_ENV.relative_to(ROOT)}", flush=True)
    print(f"  {'ok' if backend_python().exists() else 'missing'}: {backend_python().relative_to(ROOT)}", flush=True)
    print(
        f"  {'ok' if (FRONTEND_DIR / 'node_modules').exists() else 'missing'}: "
        f"{(FRONTEND_DIR / 'node_modules').relative_to(ROOT)}",
        flush=True,
    )
    print(f"  info: pip index {pip_index_url()}", flush=True)

    return 0 if ok else 1


def ensure_backend_env() -> None:
    if BACKEND_ENV.exists():
        return
    if not BACKEND_ENV_EXAMPLE.exists():
        warn("Backend .env is missing and no .env.example was found.")
        return
    BACKEND_ENV.write_text(BACKEND_ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    log(f"Created {BACKEND_ENV.relative_to(ROOT)} from .env.example")


def ensure_backend_venv() -> None:
    py = backend_python()
    if not py.exists():
        log(f"Creating backend virtual environment at {BACKEND_VENV.relative_to(ROOT)}")
        run_checked([sys.executable, "-m", "venv", BACKEND_VENV])

    log(f"Using pip index: {pip_index_url()}")
    run_checked(
        [py, "-m", "pip", "install", "--disable-pip-version-check", "-r", BACKEND_REQUIREMENTS],
        env=pip_install_env(),
    )


def pip_index_url() -> str:
    return os.getenv("PIP_INDEX_URL") or DEFAULT_PIP_INDEX_URL


def pip_trusted_host() -> str:
    return os.getenv("PIP_TRUSTED_HOST") or DEFAULT_PIP_TRUSTED_HOST


def pip_install_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PIP_INDEX_URL", DEFAULT_PIP_INDEX_URL)
    env.setdefault("PIP_TRUSTED_HOST", DEFAULT_PIP_TRUSTED_HOST)
    env.setdefault("PIP_DEFAULT_TIMEOUT", "120")
    return env


def ensure_frontend_deps() -> None:
    npm = find_npm()
    if not npm:
        error("npm not found. Install Node.js 20+ first.")
        raise SystemExit(1)

    node_modules = FRONTEND_DIR / "node_modules"
    force = os.getenv("FORCE_INSTALL", "").lower() in {"1", "true", "yes"}
    if node_modules.exists() and not force:
        log("Frontend node_modules already exists; set FORCE_INSTALL=1 to reinstall.")
        return

    install_cmd = "ci" if FRONTEND_LOCK.exists() else "install"
    run_checked([npm, install_cmd], cwd=FRONTEND_DIR)


def read_env_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def configured_database_url() -> str:
    return os.getenv("DATABASE_URL") or read_env_value(BACKEND_ENV, "DATABASE_URL") or DEFAULT_DATABASE_URL


def parse_database_url(url: str) -> dict[str, str | int | None]:
    parsed = urlparse(url)
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username) if parsed.username else None,
        "password": unquote(parsed.password) if parsed.password else None,
        "database": (parsed.path or "/quakes").lstrip("/") or "quakes",
    }


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def psql_base_args(psql: str, db_config: dict[str, str | int | None]) -> list[str]:
    args = [psql, "-v", "ON_ERROR_STOP=1"]
    host = db_config["host"]
    port = db_config["port"]
    user = db_config["user"]
    if host:
        args += ["-h", str(host)]
    if port:
        args += ["-p", str(port)]
    if user:
        args += ["-U", str(user)]
    return args


def psql_env(db_config: dict[str, str | int | None]) -> dict[str, str]:
    env = os.environ.copy()
    password = db_config["password"]
    if password:
        env["PGPASSWORD"] = str(password)
    return env


def try_start_postgres() -> None:
    if platform.system() != "Darwin":
        return
    brew = shutil.which("brew")
    if not brew:
        return
    run_checked([brew, "services", "start", "postgresql@17"], allow_fail=True)


def ensure_database() -> bool:
    if os.getenv("SKIP_DB_SETUP", "").lower() in {"1", "true", "yes"}:
        warn("Skipping database setup because SKIP_DB_SETUP is set.")
        return True

    psql = find_psql()
    if not psql:
        warn("Skipping database setup because psql was not found.")
        warn("After installing PostgreSQL/PostGIS, run `python dev.py setup` again.")
        return False

    try_start_postgres()
    db_config = parse_database_url(configured_database_url())
    database = str(db_config["database"])
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", database):
        warn(f"Skipping automatic database creation for unsupported database name: {database}")
        return False

    base_args = psql_base_args(psql, db_config)
    env = psql_env(db_config)
    exists_sql = f"SELECT 1 FROM pg_database WHERE datname = {sql_literal(database)}"
    exists = run_capture(base_args + ["-d", "postgres", "-tAc", exists_sql], env=env)
    if exists.returncode != 0:
        warn("Could not connect to PostgreSQL with the configured DATABASE_URL.")
        warn("Set Project-Code/backend/.env DATABASE_URL for your local PostgreSQL user/password.")
        if exists.stderr.strip():
            warn(exists.stderr.strip().splitlines()[-1])
        return False

    if exists.stdout.strip() != "1":
        create_sql = f"CREATE DATABASE {sql_identifier(database)}"
        create = run_capture(base_args + ["-d", "postgres", "-c", create_sql], env=env)
        if create.returncode != 0:
            warn(f"Could not create database {database}.")
            if create.stderr.strip():
                warn(create.stderr.strip().splitlines()[-1])
            return False
        log(f"Created PostgreSQL database {database}")

    extension = run_capture(base_args + ["-d", database, "-c", "CREATE EXTENSION IF NOT EXISTS postgis;"], env=env)
    if extension.returncode != 0:
        warn("Database is reachable, but PostGIS extension could not be enabled.")
        warn("Install PostGIS for PostgreSQL 17, then rerun `python dev.py setup`.")
        if extension.stderr.strip():
            warn(extension.stderr.strip().splitlines()[-1])
        return False

    log("PostgreSQL database is ready")
    return True


def setup() -> int:
    ensure_backend_env()
    ensure_backend_venv()
    ensure_frontend_deps()
    ensure_database()
    return 0


def with_dev_env() -> tuple[dict[str, str], dict[str, str], str, str]:
    backend_host = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port = os.getenv("BACKEND_PORT", "8001")
    frontend_host = os.getenv("FRONTEND_HOST", "127.0.0.1")
    frontend_port = os.getenv("FRONTEND_PORT", "5173")

    backend_origin = f"http://{backend_host}:{backend_port}"
    frontend_origin = f"http://{frontend_host}:{frontend_port}"
    proxy_target = os.getenv("VITE_PROXY_TARGET", backend_origin)
    api_base = os.getenv("VITE_API_BASE", "/api")

    cors_origins = os.getenv(
        "CORS_ORIGINS",
        ",".join(
            dict.fromkeys(
                [
                    frontend_origin,
                    f"http://127.0.0.1:{frontend_port}",
                    f"http://localhost:{frontend_port}",
                ]
            )
        ),
    )

    backend_env = os.environ.copy()
    frontend_env = os.environ.copy()
    backend_env.update(
        {
            "BACKEND_HOST": backend_host,
            "BACKEND_PORT": backend_port,
            "CORS_ORIGINS": cors_origins,
            "PYTHONUNBUFFERED": "1",
        }
    )
    frontend_env.update(
        {
            "FRONTEND_HOST": frontend_host,
            "FRONTEND_PORT": frontend_port,
            "VITE_API_BASE": api_base,
            "VITE_PROXY_TARGET": proxy_target,
        }
    )
    return backend_env, frontend_env, f"http://{backend_host}:{backend_port}", f"http://{frontend_host}:{frontend_port}"


def terminate(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        return
    log(f"Stopping {name}")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def up() -> int:
    setup()
    npm = find_npm()
    if not npm:
        error("npm not found. Install Node.js 20+ first.")
        return 1

    backend_env, frontend_env, backend_url, frontend_url = with_dev_env()
    backend_cmd = [backend_python(), "start.py"]
    frontend_cmd = [npm, "run", "dev"]

    log(command_text(backend_cmd))
    backend_proc = subprocess.Popen([str(part) for part in backend_cmd], cwd=str(BACKEND_DIR), env=backend_env)
    log(command_text(frontend_cmd))
    frontend_proc = subprocess.Popen([str(part) for part in frontend_cmd], cwd=str(FRONTEND_DIR), env=frontend_env)

    print("", flush=True)
    log(f"backend  {backend_url}")
    log(f"frontend {frontend_url}")
    log("Press Ctrl+C to stop both processes.")

    try:
        while True:
            backend_code = backend_proc.poll()
            frontend_code = frontend_proc.poll()
            if backend_code is not None or frontend_code is not None:
                if backend_code is not None:
                    warn(f"backend exited with code {backend_code}")
                    terminate(frontend_proc, "frontend")
                    return backend_code
                if frontend_code is not None:
                    warn(f"frontend exited with code {frontend_code}")
                    terminate(backend_proc, "backend")
                    return frontend_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("", flush=True)
        terminate(backend_proc, "backend")
        terminate(frontend_proc, "frontend")
        return 0


def test() -> int:
    setup()
    run_checked([backend_python(), "-m", "unittest", "discover", "-s", "tests"], cwd=BACKEND_DIR)
    npm = find_npm()
    if not npm:
        error("npm not found. Install Node.js 20+ first.")
        return 1
    run_checked([npm, "run", "type-check"], cwd=FRONTEND_DIR)
    run_checked([npm, "run", "build"], cwd=FRONTEND_DIR)
    return 0


def print_help() -> None:
    print(
        """Usage:
  python dev.py             setup dependencies and start backend/frontend
  python dev.py check       inspect local tools without installing
  python dev.py setup       create .env, install dependencies, prepare database
  python dev.py up          same as default
  python dev.py test        run backend unit tests and frontend checks

Useful environment variables:
  BACKEND_HOST=127.0.0.1
  BACKEND_PORT=8001
  FRONTEND_HOST=127.0.0.1
  FRONTEND_PORT=5173
  VITE_API_BASE=/api
  VITE_PROXY_TARGET=http://127.0.0.1:8001
  CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
  DATABASE_URL=postgresql+psycopg://user:password@127.0.0.1:5432/quakes
  PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
  PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
  SKIP_DB_SETUP=1
  FORCE_INSTALL=1
""",
        flush=True,
    )


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "up"
    if command in {"-h", "--help", "help"}:
        print_help()
        return 0
    if command == "check":
        return check_environment()
    if command == "setup":
        return setup()
    if command == "up":
        return up()
    if command == "test":
        return test()
    error(f"Unknown command: {command}")
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
