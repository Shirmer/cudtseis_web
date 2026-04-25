# cudtseis_web

CDUT SeisLab Web 项目，包含：

- 后端：FastAPI + SQLAlchemy
- 前端：Vue 3 + Vite
- 数据库：PostgreSQL 17 + PostGIS

本文档的目标是：同事在自己的电脑上 clone 项目后，可以按步骤把项目跑起来。

## 一句话版

如果你已经装好了 Python、Node.js、PostgreSQL 和 PostGIS，在仓库根目录运行：

```bash
python dev.py
```

Windows 如果 `python` 不可用，运行：

```powershell
py dev.py
```

启动成功后访问：

- 前端页面：`http://127.0.0.1:5173`
- 后端接口文档：`http://127.0.0.1:8001/docs`

## 1. 首次准备系统环境

每台电脑只需要做一次。

### macOS

推荐使用 Homebrew 安装：

```bash
brew install python@3.12 node postgresql@17 postgis
brew services start postgresql@17
```

检查命令是否可用：

```bash
python3 --version
node --version
npm --version
psql --version
```

如果 `psql` 找不到，Apple Silicon Mac 通常需要把 PostgreSQL 加入 PATH：

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Intel Mac 常见路径是：

```bash
echo 'export PATH="/usr/local/opt/postgresql@17/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Windows

请安装以下软件：

- Python 3.10+，安装时勾选 `Add python.exe to PATH`
- Node.js 20 LTS
- PostgreSQL 17
- PostGIS for PostgreSQL 17
- Git

PostgreSQL 安装时请记住 `postgres` 用户密码。

安装 PostGIS 最常见方式：

1. 打开 PostgreSQL 安装目录里的 `Stack Builder`
2. 选择本机 PostgreSQL 17
3. 安装 `PostGIS`，版本要匹配 PostgreSQL 17

确认 PostgreSQL bin 目录已加入 PATH：

```text
C:\Program Files\PostgreSQL\17\bin\
```

打开 PowerShell 检查：

```powershell
python --version
node --version
npm --version
psql --version
```

如果 PostgreSQL 服务没有启动：

```powershell
net start postgresql-x64-17
```

如果服务名不同，先查：

```powershell
Get-Service *postgres*
```

## 2. 下载项目代码

```bash
git clone <项目仓库地址>
cd cudtseis_web
```

如果已经 clone 过：

```bash
git pull
```

不要复制别人电脑里的 `.venv`、`.venv-win`、`node_modules`、`.env`。这些都是每台电脑自己的本地文件。

## 3. 检查本机环境

在仓库根目录运行：

```bash
python dev.py check
```

Windows 可用：

```powershell
py dev.py check
```

正常情况下会看到 Python、Node、npm、psql、后端 `.env`、后端 `.venv`、前端 `node_modules` 的检查结果。

第一次运行时 `.env`、`.venv`、`node_modules` 可能显示 missing，这是正常的，下一步会自动创建。

## 4. 初始化项目

在仓库根目录运行：

```bash
python dev.py setup
```

Windows：

```powershell
py dev.py setup
```

这一步会自动做这些事：

- 从 `Project-Code/backend/.env.example` 创建 `Project-Code/backend/.env`
- 创建后端虚拟环境 `Project-Code/backend/.venv`
- 安装后端依赖
- 安装前端依赖
- 尝试创建 `quakes` 数据库
- 尝试启用 PostGIS 扩展

### pip 镜像源说明

国内网络、校园网或公司网经常会在安装 Python 依赖时出现类似错误：

```text
SSLCertVerificationError
CERTIFICATE_VERIFY_FAILED
Could not fetch URL https://pypi.org/simple/...
ERROR: Could not find a version that satisfies the requirement httpx==0.28.1
```

这通常不是代码错误，而是电脑下载 Python 依赖时 SSL 证书校验失败或访问 PyPI 不稳定。

本项目的 `dev.py setup` 已经默认使用清华 pip 镜像源安装后端依赖：

```text
https://pypi.tuna.tsinghua.edu.cn/simple
```

如果团队成员还会手动运行 `pip install`，建议每台电脑统一配置一次全局 pip 镜像。

macOS / Linux：

```bash
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
```

Windows PowerShell：

```powershell
py -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
py -m pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
```

配置后重新运行：

```bash
python dev.py setup
python dev.py
```

Windows：

```powershell
py dev.py setup
py dev.py
```

如果以后需要临时换回官方源，可以在启动前覆盖环境变量：

```bash
PIP_INDEX_URL=https://pypi.org/simple python dev.py setup
```

### Windows 常见数据库配置

如果 `setup` 提示数据库连接失败，编辑：

```text
Project-Code/backend/.env
```

把数据库连接改成你本机 PostgreSQL 的账号密码：

```env
DATABASE_URL=postgresql+psycopg://postgres:你的PostgreSQL密码@127.0.0.1:5432/quakes
```

保存后重新运行：

```powershell
py dev.py setup
```

### 手动确认 PostGIS

如果提示 PostGIS 无法启用，说明 PostgreSQL 装好了，但 PostGIS 没装好或没匹配当前 PostgreSQL 版本。

可以手动检查：

```bash
psql -d quakes -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

Windows 如果需要密码：

```powershell
psql -U postgres -d quakes -c "CREATE EXTENSION IF NOT EXISTS postgis;"
```

## 5. 启动项目

在仓库根目录运行：

```bash
python dev.py
```

Windows：

```powershell
py dev.py
```

启动成功后终端会显示类似：

```text
[dev] backend  http://127.0.0.1:8001
[dev] frontend http://127.0.0.1:5173
```

浏览器打开：

```text
http://127.0.0.1:5173
```

停止项目：

```text
Ctrl+C
```

## 6. 常用开发命令

```bash
python dev.py check   # 检查环境，不安装
python dev.py setup   # 安装依赖、初始化数据库，不启动
python dev.py up      # 初始化后启动，等同 python dev.py
python dev.py test    # 后端测试 + 前端类型检查 + 前端构建
```

Windows 把 `python` 换成 `py` 即可。

## 7. 自定义端口

默认端口：

- 后端：`8001`
- 前端：`5173`

如果端口被占用，可以临时换端口。

macOS / Linux：

```bash
BACKEND_PORT=18001 FRONTEND_PORT=15173 python dev.py
```

Windows PowerShell：

```powershell
$env:BACKEND_PORT=18001
$env:FRONTEND_PORT=15173
py dev.py
```

可用变量：

- `BACKEND_HOST`，默认 `127.0.0.1`
- `BACKEND_PORT`，默认 `8001`
- `FRONTEND_HOST`，默认 `127.0.0.1`
- `FRONTEND_PORT`，默认 `5173`
- `VITE_API_BASE`，默认 `/api`
- `VITE_PROXY_TARGET`，默认 `http://<BACKEND_HOST>:<BACKEND_PORT>`
- `CORS_ORIGINS`，默认自动包含当前前端地址
- `DATABASE_URL`，数据库连接串
- `PIP_INDEX_URL`，默认 `https://pypi.tuna.tsinghua.edu.cn/simple`
- `PIP_TRUSTED_HOST`，默认 `pypi.tuna.tsinghua.edu.cn`
- `SKIP_DB_SETUP=1`，跳过数据库自动初始化
- `FORCE_INSTALL=1`，强制重新安装前端依赖

## 8. 常见问题

### 找不到 node 或 npm

重新安装 Node.js 20 LTS，然后重开终端：

```bash
node --version
npm --version
```

### 找不到 psql

说明 PostgreSQL 的 bin 目录没有加入 PATH。Windows 常见路径：

```text
C:\Program Files\PostgreSQL\17\bin\
```

macOS Homebrew 常见路径：

```text
/opt/homebrew/opt/postgresql@17/bin
```

### 数据库密码错误

编辑：

```text
Project-Code/backend/.env
```

改成正确密码后重新运行：

```bash
python dev.py setup
```

### 端口被占用

换一组本地端口：

```bash
BACKEND_PORT=18001 FRONTEND_PORT=15173 python dev.py
```

Windows PowerShell：

```powershell
$env:BACKEND_PORT=18001
$env:FRONTEND_PORT=15173
py dev.py
```

### Python 报 ModuleNotFoundError

通常是后端依赖没装完整，重新运行：

```bash
python dev.py setup
```

如果还不行，强制重装依赖：

```bash
FORCE_INSTALL=1 python dev.py setup
```

### pip 安装 httpx 或其他依赖时报 SSL 错误

如果看到：

```text
CERTIFICATE_VERIFY_FAILED
Could not fetch URL https://pypi.org/simple/httpx/
```

先配置清华 pip 镜像源：

```bash
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
python -m pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
```

Windows：

```powershell
py -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
py -m pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn
```

然后重新跑：

```bash
python dev.py setup
python dev.py
```

### 前端页面能打开，但接口失败

先确认后端文档能打开：

```text
http://127.0.0.1:8001/docs
```

如果后端端口不是 `8001`，启动时同步设置后端和前端代理：

```bash
BACKEND_PORT=18001 FRONTEND_PORT=15173 python dev.py
```

## 9. 协作约定

不要提交本机生成物或个人配置：

- `.env`
- `.venv/`
- `.venv-win/`
- `node_modules/`
- `dist/`
- `__pycache__/`
- `*.log`

这些已经写入 `.gitignore`。如果仓库历史里已经跟踪过这些文件，需要从 Git 索引移除，但保留本机文件：

```bash
git rm -r --cached .venv-win __pycache__ Project-Code/backend/.env Project-Code/backend/__pycache__ Project-Code/backend/tests/__pycache__ Project-Code/Frontend/quakes-frontend/dist dev-out.log dev-err.log .DS_Store
```

以后每位同事只提交源码、配置模板和文档，不提交自己电脑生成的依赖目录或数据库配置。
