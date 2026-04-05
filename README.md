# cudtseis_web

CDUT SeisLab web project (frontend + backend + database).

## One-command start (macOS / Windows)

Run in repo root:

```bash
python dev.py
```

Windows can also use:

```powershell
py dev.py
```

This command will:

- check Node/npm/Python/PostgreSQL tools
- prepare backend venv and dependencies
- prepare frontend dependencies
- try to start local PostgreSQL service (macOS with Homebrew)
- auto-create `quakes` database and enable `postgis` when possible
- start backend (`8001`) and frontend (`5173`) together

Stop both services with `Ctrl+C`.

## Optional commands

```bash
python dev.py check
python dev.py setup
python dev.py up
```

- `check`: only print environment status
- `setup`: install/init only, do not start dev servers
- `up`: setup + start (same as default)

## Cross-platform prerequisites

- Python 3.10+
- Node.js 20+
- PostgreSQL 17 + PostGIS

### macOS (Homebrew)

```bash
brew install node postgresql@17 postgis
brew services start postgresql@17
```

### Windows

Install:

- Node.js LTS
- PostgreSQL 17
- PostGIS (Stack Builder or package manager)
- Python 3.10+

Recommended install notes:

- During PostgreSQL install, remember the superuser password.
- Install PostGIS into the same PostgreSQL major version (`17`).
- Make sure `C:\Program Files\PostgreSQL\17\bin\` is in PATH (so `psql` is available).

Then start PostgreSQL service, usually:

```powershell
net start postgresql-x64-17
```

After that run:

```powershell
python dev.py
```

Or double-click `dev.bat` in repo root.

If `python` is not recognized, use:

```powershell
py dev.py
```

If PostgreSQL service name is different, find it with:

```powershell
Get-Service *postgres*
```

## URLs

- Frontend: `http://127.0.0.1:5173`
- Backend docs: `http://127.0.0.1:8001/docs`
