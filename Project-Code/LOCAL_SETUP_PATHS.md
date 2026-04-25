# 本地安装与路径说明（macOS / Windows）

从仓库根目录启动：

```bash
python dev.py
```

Windows 可用：

```powershell
py dev.py
```

## 系统级依赖

### macOS（Homebrew）

- Node.js：`/opt/homebrew/opt/node` 或 `/usr/local/opt/node`
- PostgreSQL 17：`/opt/homebrew/opt/postgresql@17` 或 `/usr/local/opt/postgresql@17`
- PostGIS：`/opt/homebrew/opt/postgis` 或 `/usr/local/opt/postgis`

安装示例：

```bash
brew install node postgresql@17 postgis
brew services start postgresql@17
```

### Windows

- Node.js LTS
- Python 3.10+
- PostgreSQL 17
- PostGIS for PostgreSQL 17

常见 PostgreSQL bin 目录：

```text
C:\Program Files\PostgreSQL\17\bin\
```

请把该目录加入 PATH，保证 `psql` 可用。

## 项目内本地目录

以下目录只属于每位开发者自己的电脑，不应提交到 Git：

- 后端虚拟环境：`<repo>/Project-Code/backend/.venv`
- 后端本机配置：`<repo>/Project-Code/backend/.env`
- 后端运行数据：`<repo>/Project-Code/backend/.data`
- 前端依赖目录：`<repo>/Project-Code/Frontend/quakes-frontend/node_modules`
- 前端构建目录：`<repo>/Project-Code/Frontend/quakes-frontend/dist`

可共享的模板文件：

- 后端配置模板：`<repo>/Project-Code/backend/.env.example`
- 前端配置模板：`<repo>/Project-Code/Frontend/quakes-frontend/.env.example`

## 手动调试

推荐优先使用：

```bash
python dev.py check
python dev.py setup
python dev.py up
```

如需手动启动后端：

macOS / Linux:

```bash
cd <repo>/Project-Code/backend
source .venv/bin/activate
python start.py
```

Windows PowerShell:

```powershell
cd <repo>\Project-Code\backend
.venv\Scripts\Activate.ps1
python start.py
```

手动启动前端：

```bash
cd <repo>/Project-Code/Frontend/quakes-frontend
npm run dev
```
