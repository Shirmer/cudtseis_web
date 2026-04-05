# 本地安装与路径说明（macOS / Windows）

从仓库根目录快速启动：

```bash
python dev.py
```

## 系统级安装位置（Homebrew）

- Node.js：`/opt/homebrew/opt/node`
- npm 可执行文件：`/opt/homebrew/bin/npm`
- PostgreSQL 17：`/opt/homebrew/opt/postgresql@17`
- PostGIS：`/opt/homebrew/opt/postgis`
- PostgreSQL 数据目录：`/opt/homebrew/var/postgresql@17`

## 系统级安装位置（Windows 参考）

- Node.js（默认）：`C:\Program Files\nodejs\`
- Python 启动器：`py`（官方安装器提供）
- PostgreSQL 17 可执行文件（默认）：`C:\Program Files\PostgreSQL\17\bin\`
- PostgreSQL 数据目录（常见默认）：`C:\Program Files\PostgreSQL\17\data\`
- PostGIS SQL 扩展文件（常见默认）：`C:\Program Files\PostgreSQL\17\share\extension\`

## 项目内安装位置（仓库内部）

- 后端虚拟环境：`/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend/.venv`
- 后端依赖清单：`/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend/requirements.txt`
- 前端依赖目录：`/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend/node_modules`
- 前端 npm 缓存：`/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend/.npm-cache`
- 前端静态占位资源：`/Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend/public`

Windows 对应的项目内目录：

- 后端虚拟环境：`<repo>\Project-Code\backend\.venv`
- 前端依赖目录：`<repo>\Project-Code\Frontend\quakes-frontend\node_modules`
- 前端 npm 缓存：`<repo>\Project-Code\Frontend\quakes-frontend\.npm-cache`

## 运行与调试（macOS）

### 1）启动数据库服务

```bash
brew services start postgresql@17
```

### 2）启动后端

```bash
cd /Users/teki/Downloads/my_project/cudtseis_web/Project-Code/backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

接口检查：

```bash
curl 'http://127.0.0.1:8001/api/events?hours=1&minMag=3&limit=2'
```

### 3）启动前端

```bash
cd /Users/teki/Downloads/my_project/cudtseis_web/Project-Code/Frontend/quakes-frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：`http://127.0.0.1:5173`

## 运行与调试（Windows PowerShell）

### 1）启动 PostgreSQL 服务

```powershell
net start postgresql-x64-17
```

如果服务名不同，可先查询：

```powershell
Get-Service *postgres*
```

### 2）一条命令启动（推荐）

```powershell
cd <repo-root>
py dev.py
```

### 3）手动模式（可选）

后端：

```powershell
cd <repo-root>\Project-Code\backend
.venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

前端：

```powershell
cd <repo-root>\Project-Code\Frontend\quakes-frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
