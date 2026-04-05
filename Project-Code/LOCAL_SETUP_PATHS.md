# Local Setup Paths (macOS / Windows)

Quick start from repo root:

```bash
python dev.py
```

## System-level installs (Homebrew)

- Node.js: `/opt/homebrew/opt/node`
- npm binary: `/opt/homebrew/bin/npm`
- PostgreSQL 17: `/opt/homebrew/opt/postgresql@17`
- PostGIS: `/opt/homebrew/opt/postgis`
- PostgreSQL data directory: `/opt/homebrew/var/postgresql@17`

## System-level installs (Windows reference)

- Node.js (default): `C:\Program Files\nodejs\`
- Python launcher: `py` (from Python official installer)
- PostgreSQL 17 binary (default): `C:\Program Files\PostgreSQL\17\bin\`
- PostgreSQL data directory (common default): `C:\Program Files\PostgreSQL\17\data\`
- PostGIS SQL extension files (common default): `C:\Program Files\PostgreSQL\17\share\extension\`

## Project-local installs (inside repo)

- Backend virtualenv: `/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend/.venv`
- Backend deps source list: `/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend/requirements.txt`
- Frontend node modules: `/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend/node_modules`
- Frontend npm cache: `/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend/.npm-cache`
- Frontend static placeholders: `/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend/public`

Windows equivalent project-local directories:

- Backend virtualenv: `<repo>\Project-Code\backend\.venv`
- Frontend node modules: `<repo>\Project-Code\Frontend\quakes-frontend\node_modules`
- Frontend npm cache: `<repo>\Project-Code\Frontend\quakes-frontend\.npm-cache`

## Run and debug

### 1) Start database service

```bash
brew services start postgresql@17
```

### 2) Start backend

```bash
cd /Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Check:

```bash
curl 'http://127.0.0.1:8001/api/events?hours=1&minMag=3&limit=2'
```

### 3) Start frontend

```bash
cd /Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open: `http://127.0.0.1:5173`

## Run and debug (Windows PowerShell)

### 1) Start PostgreSQL service

```powershell
net start postgresql-x64-17
```

If your service name differs, check:

```powershell
Get-Service *postgres*
```

### 2) One-command startup (recommended)

```powershell
cd <repo-root>
py dev.py
```

### 3) Manual mode (optional)

Backend:

```powershell
cd <repo-root>\Project-Code\backend
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Frontend:

```powershell
cd <repo-root>\Project-Code\Frontend\quakes-frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
