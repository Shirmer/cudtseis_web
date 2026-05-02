#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, urlunparse
import getpass
import os
import platform
import re
import shutil
import socket
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
BACKEND_QDRANT_REQUIREMENTS = BACKEND_DIR / "requirements-qdrant.txt"
BACKEND_RAGANYTHING_REQUIREMENTS = BACKEND_DIR / "requirements-raganything.txt"
FRONTEND_LOCK = FRONTEND_DIR / "package-lock.json"
DEFAULT_DATABASE_URL = "postgresql+psycopg:///quakes"
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


def pip_install(
    requirements: Path,
    *,
    label: str,
) -> None:
    py = backend_python()
    digest = requirements_digest(requirements)
    stamp = pip_stamp_path(requirements)
    if not force_install_enabled() and stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
        log(f"{label} dependencies are already installed; set FORCE_INSTALL=1 to reinstall.")
        return

    log(f"Using pip index: {pip_index_url()} for {label}")
    run_checked(
        [
            py,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--retries",
            "10",
            "--timeout",
            "120",
            "-r",
            requirements,
        ],
        env=pip_install_env(),
    )
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(digest + "\n", encoding="utf-8")


def ensure_backend_venv(*, extras: set[str] | None = None) -> None:
    py = backend_python()
    if not py.exists():
        log(f"Creating backend virtual environment at {BACKEND_VENV.relative_to(ROOT)}")
        run_checked([sys.executable, "-m", "venv", BACKEND_VENV])

    selected_extras = extras or set()
    pip_install(BACKEND_REQUIREMENTS, label="base backend")
    if "qdrant" in selected_extras:
        pip_install(BACKEND_QDRANT_REQUIREMENTS, label="optional qdrant")
    if "raganything" in selected_extras:
        pip_install(BACKEND_RAGANYTHING_REQUIREMENTS, label="optional raganything")


def pip_index_url() -> str:
    return os.getenv("PIP_INDEX_URL") or DEFAULT_PIP_INDEX_URL


def pip_trusted_host() -> str:
    return os.getenv("PIP_TRUSTED_HOST") or DEFAULT_PIP_TRUSTED_HOST


def pip_install_env() -> dict[str, str]:
    env = os.environ.copy()
    pip_cache = BACKEND_DIR / ".data" / "pip-cache"
    pip_cache.mkdir(parents=True, exist_ok=True)
    env.setdefault("PIP_INDEX_URL", DEFAULT_PIP_INDEX_URL)
    env.setdefault("PIP_TRUSTED_HOST", DEFAULT_PIP_TRUSTED_HOST)
    env.setdefault("PIP_DEFAULT_TIMEOUT", "120")
    env.setdefault("PIP_CACHE_DIR", str(pip_cache))
    return env


def force_install_enabled() -> bool:
    return os.getenv("FORCE_INSTALL", "").lower() in {"1", "true", "yes"}


def pip_stamp_path(requirements: Path) -> Path:
    return BACKEND_DIR / ".data" / "pip-stamps" / f"{requirements.name}.sha256"


def requirements_digest(requirements: Path) -> str:
    seen: set[Path] = set()
    hasher = hashlib.sha256()

    def add_file(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        content = resolved.read_text(encoding="utf-8")
        hasher.update(str(resolved.relative_to(ROOT)).encode("utf-8", errors="ignore"))
        hasher.update(b"\0")
        hasher.update(content.encode("utf-8"))
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            referenced = None
            if line.startswith("-r "):
                referenced = line[3:].strip()
            elif line.startswith("--requirement "):
                referenced = line.removeprefix("--requirement ").strip()
            if referenced:
                add_file((resolved.parent / referenced).resolve())

    add_file(requirements)
    return hasher.hexdigest()


def ensure_frontend_deps() -> None:
    npm = find_npm()
    if not npm:
        error("npm not found. Install Node.js 20+ first.")
        raise SystemExit(1)

    node_modules = FRONTEND_DIR / "node_modules"
    if node_modules.exists() and not force_install_enabled():
        log("Frontend node_modules already exists; set FORCE_INSTALL=1 to reinstall.")
        return

    install_cmd = "ci" if FRONTEND_LOCK.exists() else "install"
    npm_cache = FRONTEND_DIR / ".npm-cache"
    npm_cache.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("npm_config_cache", str(npm_cache))
    run_checked([npm, install_cmd], cwd=FRONTEND_DIR, env=env)


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


def write_env_value(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    replacement = f"{key}={value}"
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _ = line.split("=", 1)
        if name.strip() == key:
            lines[index] = replacement
            break
    else:
        lines.append(replacement)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def configured_database_url() -> str:
    return os.getenv("DATABASE_URL") or read_env_value(BACKEND_ENV, "DATABASE_URL") or DEFAULT_DATABASE_URL


def mask_database_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.password is None:
        return url
    username = quote(unquote(parsed.username or ""), safe="")
    host = parsed.hostname or "127.0.0.1"
    netloc = f"{username}:***@{host}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def persist_database_url(url: str) -> None:
    if os.getenv("DATABASE_URL"):
        return
    if read_env_value(BACKEND_ENV, "DATABASE_URL") == url:
        return
    write_env_value(BACKEND_ENV, "DATABASE_URL", url)
    log(f"Saved DATABASE_URL to {BACKEND_ENV.relative_to(ROOT)}: {mask_database_url(url)}")


def prompt_database_credentials(url: str, *, force: bool = False) -> str:
    parsed = urlparse(url)
    if not parsed.scheme.startswith("postgresql"):
        return url
    if not force:
        return url
    if not sys.stdin.isatty():
        return url

    print("本机 PostgreSQL 免密连接失败。请输入你自己电脑的 PostgreSQL 用户名/密码。", flush=True)
    print("如果你的 PostgreSQL 允许免密，密码可以直接回车。", flush=True)
    default_user = unquote(parsed.username) if parsed.username else ("postgres" if is_windows() else getpass.getuser())
    username = input("postgresql用户名 : ").strip() or default_user
    password = getpass.getpass("postgresql密码（可直接回车尝试免密）: ")

    netloc = quote(username, safe="")
    if password:
        netloc += f":{quote(password, safe='')}"

    host = parsed.hostname or ("127.0.0.1" if is_windows() else "")
    if host:
        netloc += f"@{host}"
    elif netloc:
        netloc += "@"
    if host and parsed.port:
        netloc += f":{parsed.port}"

    return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))


def database_url_candidates(url: str) -> list[str]:
    candidates = [url]
    parsed = urlparse(url)
    if is_windows() or not parsed.scheme.startswith("postgresql"):
        return candidates
    if parsed.username or parsed.password:
        return candidates
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return candidates

    database = (parsed.path or "/quakes").lstrip("/") or "quakes"
    socket_url = urlunparse((parsed.scheme, "", f"/{database}", parsed.params, parsed.query, parsed.fragment))
    if socket_url not in candidates:
        candidates.append(socket_url)
    return candidates


def parse_database_url(url: str) -> dict[str, str | int | None]:
    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": parsed.port,
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
    if password is not None:
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

    database_url = configured_database_url()
    db_config: dict[str, str | int | None] | None = None
    exists: subprocess.CompletedProcess[str] | None = None
    postgres_start_attempted = False
    prompt_count = 0
    while True:
        for candidate_url in database_url_candidates(database_url):
            candidate_config = parse_database_url(candidate_url)
            base_args = psql_base_args(psql, candidate_config)
            env = psql_env(candidate_config)
            database = str(candidate_config["database"])
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]{0,62}", database):
                warn(f"Skipping automatic database creation for unsupported database name: {database}")
                return False

            exists_sql = f"SELECT 1 FROM pg_database WHERE datname = {sql_literal(database)}"
            exists = run_capture(base_args + ["-d", "postgres", "-tAc", exists_sql], env=env)
            if exists.returncode != 0 and not postgres_start_attempted:
                try_start_postgres()
                postgres_start_attempted = True
                exists = run_capture(base_args + ["-d", "postgres", "-tAc", exists_sql], env=env)
            if exists.returncode == 0:
                database_url = candidate_url
                db_config = candidate_config
                os.environ["DATABASE_URL"] = database_url
                persist_database_url(database_url)
                break

        if db_config is not None:
            break

        warn("Could not connect to PostgreSQL with the configured DATABASE_URL.")
        if exists is not None and exists.stderr.strip():
            warn(exists.stderr.strip().splitlines()[-1])
        if not sys.stdin.isatty() or prompt_count >= 2:
            warn("Set Project-Code/backend/.env DATABASE_URL for your own local PostgreSQL user/password, or configure local passwordless access.")
            return False
        database_url = prompt_database_credentials(database_url, force=True)
        prompt_count += 1

    if db_config is None or exists is None:
        return False
    database = str(db_config["database"])
    base_args = psql_base_args(psql, db_config)
    env = psql_env(db_config)

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


def setup(*, extras: set[str] | None = None) -> int:
    ensure_backend_env()
    ensure_backend_venv(extras=extras)
    ensure_frontend_deps()
    return 0 if ensure_database() else 1


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def available_port(host: str, preferred: int) -> int:
    port = preferred
    while port < preferred + 100:
        if is_port_available(host, port):
            return port
        port += 1
    raise RuntimeError(f"No available port found near {preferred}")


def configured_port(name: str, default: int, host: str) -> str:
    raw_value = os.getenv(name)
    if raw_value:
        return raw_value
    port = available_port(host, default)
    if port != default:
        warn(f"{name} default port {default} is already in use; using {port}.")
    return str(port)


def wait_for_port(host: str, port: int, proc: subprocess.Popen[str], name: str, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        code = proc.poll()
        if code is not None:
            warn(f"{name} exited with code {code}")
            return False
        if not is_port_available(host, port):
            return True
        time.sleep(0.2)
    warn(f"Timed out waiting for {name} to listen on {host}:{port}.")
    return False


def with_dev_env() -> tuple[dict[str, str], dict[str, str], str, str]:
    backend_host = os.getenv("BACKEND_HOST", "127.0.0.1")
    frontend_host = os.getenv("FRONTEND_HOST", "127.0.0.1")
    backend_port = configured_port("BACKEND_PORT", 8001, backend_host)
    frontend_port = configured_port("FRONTEND_PORT", 5173, frontend_host)

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
    setup_result = setup()
    if setup_result != 0:
        return setup_result
    npm = find_npm()
    if not npm:
        error("npm not found. Install Node.js 20+ first.")
        return 1

    backend_env, frontend_env, backend_url, frontend_url = with_dev_env()
    backend_cmd = [backend_python(), "start.py"]
    frontend_cmd = [npm, "run", "dev"]

    log(command_text(backend_cmd))
    backend_proc = subprocess.Popen([str(part) for part in backend_cmd], cwd=str(BACKEND_DIR), env=backend_env)
    backend_host = backend_env["BACKEND_HOST"]
    backend_port = int(backend_env["BACKEND_PORT"])
    if not wait_for_port(backend_host, backend_port, backend_proc, "backend"):
        terminate(backend_proc, "backend")
        return 1

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
    setup_result = setup()
    if setup_result != 0:
        return setup_result
    run_checked([backend_python(), "-m", "unittest", "discover", "-s", "tests"], cwd=BACKEND_DIR)
    npm = find_npm()
    if not npm:
        error("npm not found. Install Node.js 20+ first.")
        return 1
    run_checked([npm, "run", "type-check"], cwd=FRONTEND_DIR)
    run_checked([npm, "run", "build"], cwd=FRONTEND_DIR)
    return 0


def clean() -> int:
    targets = [
        BACKEND_VENV,
        BACKEND_DIR / ".data" / "pip-cache",
        BACKEND_DIR / ".data" / "pip-stamps",
        FRONTEND_DIR / "node_modules",
        FRONTEND_DIR / ".npm-cache",
    ]
    for target in targets:
        if not target.exists():
            continue
        log(f"Removing {target.relative_to(ROOT)}")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    log("Local dependency folders and caches were removed.")
    return 0


def print_help() -> None:
    print(
        """Usage:
  python dev.py             setup dependencies and start backend/frontend
  python dev.py check       inspect local tools without installing
  python dev.py setup       create .env, install dependencies, prepare database
  python dev.py setup-qdrant       install base dependencies plus Qdrant client
  python dev.py setup-raganything  install base dependencies plus optional RAGAnything stack
  python dev.py up          same as default
  python dev.py test        run backend unit tests and frontend checks
  python dev.py clean       remove local dependency folders and caches

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
  PIP_CACHE_DIR=Project-Code/backend/.data/pip-cache
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
    if command == "setup-qdrant":
        return setup(extras={"qdrant"})
    if command == "setup-raganything":
        return setup(extras={"raganything"})
    if command == "setup-all":
        return setup(extras={"qdrant", "raganything"})
    if command == "up":
        return up()
    if command == "test":
        return test()
    if command == "clean":
        return clean()
    error(f"Unknown command: {command}")
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
