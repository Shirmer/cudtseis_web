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

`dev.py` 会把依赖缓存和安装记录放在项目目录里：

- 后端虚拟环境：`Project-Code/backend/.venv`
- pip 下载缓存：`Project-Code/backend/.data/pip-cache`
- pip 安装记录：`Project-Code/backend/.data/pip-stamps`
- 前端依赖：`Project-Code/Frontend/quakes-frontend/node_modules`
- npm 下载缓存：`Project-Code/Frontend/quakes-frontend/.npm-cache`

依赖文件没有变化时，`python dev.py` 会跳过重复安装。只有首次安装、依赖清单变化，或显式设置 `FORCE_INSTALL=1` 时才会重新安装。

### 团队共享云端测试配置

如果团队希望所有成员先共用阿里云上的 PostgreSQL/PostGIS、RAGAnything 工作目录和服务器文献目录，不需要每个人本机都安装数据库和解析服务。先复制团队配置模板：

macOS / Linux：

```bash
cp Project-Code/backend/.env.team.example Project-Code/backend/.env.local
cp Project-Code/Frontend/quakes-frontend/.env.team.example Project-Code/Frontend/quakes-frontend/.env.local
```

Windows PowerShell：

```powershell
Copy-Item Project-Code/backend/.env.team.example Project-Code/backend/.env.local
Copy-Item Project-Code/Frontend/quakes-frontend/.env.team.example Project-Code/Frontend/quakes-frontend/.env.local
```

然后编辑 `Project-Code/backend/.env.local`，把这些占位符换成团队实际值：

```env
REPLACE_WITH_POSTGRES_PASSWORD
REPLACE_WITH_DOUBAO_API_KEY
```

这套配置的运行链路是：

```text
本机浏览器 -> 本机前端 5173 -> 本机后端 8001 -> 云端 PostgreSQL + RAGAnything/LightRAG/MinerU
```

填好后运行：

```bash
python dev.py setup-raganything
python dev.py
```

Windows：

```powershell
py dev.py setup-raganything
py dev.py
```

说明：`.env.team.example` 可以提交给团队共享，里面只放连接方式和占位符；`.env.local` 是每个人本机实际配置，已经被 `.gitignore` 忽略。

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

### 大模型 API 配置说明

普通开发不一定需要大模型 API；没有 API key 时，文献检索会使用本地 hash embedding fallback，问答会使用本地模板 fallback。

如果需要让文献问答和地震地质分析调用大模型，在自己的 `Project-Code/backend/.env` 里配置兼容 OpenAI 的服务：

```env
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=你的 OpenAI 兼容接口地址
GEO_RAG_CHAT_MODEL=你的聊天模型名
```

火山方舟豆包在线推理可参考：

```env
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
GEO_RAG_CHAT_MODEL=doubao-seed-2-0-lite-260215
```

注意：火山方舟的在线推理 API 和 Coding Plan API 地址不同。地质文献问答使用在线推理地址 `api/v3`；如果你在控制台创建的是推理接入点，也可以把 `GEO_RAG_CHAT_MODEL` 改成控制台给出的接入点 ID。

如果该服务只提供聊天/推理模型，不提供 embeddings 接口，可以把 embedding 模型留空：

```env
OPENAI_EMBEDDING_MODEL=
```

现在推荐使用下方独立 TEI embedding 服务；`OPENAI_EMBEDDING_MODEL` 只在同一个服务也提供 OpenAI-compatible embeddings 时才填写。API key 只放在本机 `.env`，不要写入 `.env.example`、README 或源码。

### Embedding 与 RAGAnything

最终文献 RAG 的检索主链路由 RAGAnything/LightRAG 负责。embedding 仍然由项目统一配置，RAGAnything 会复用 `GEO_RAG_EMBEDDING_*`：

```text
embedding 模型：把文本转成向量
RAGAnything/LightRAG：保存文档索引、实体关系和检索工作目录
```

VikingDB 不是必须项。Qdrant 也不再是最终文献 RAG 主链路必需项；它只保留给旧的 builtin fallback 或其他实验索引。负责高级 RAG 的机器需要安装 RAGAnything 依赖：

```bash
python dev.py setup-raganything
```

这会把 RAGAnything、LightRAG、MinerU 等依赖安装到 `Project-Code/backend/.venv`，不会安装系统服务，也不会写到项目目录外。

服务器后端推荐配置示例：

```env
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8001
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,http://8.137.179.31,http://8.137.179.31:5173

DATABASE_URL=postgresql+psycopg://cudtseis:你的密码@127.0.0.1:5432/quakes

GEO_RAG_ENGINE=raganything
RAGANYTHING_ENABLED=true
RAGANYTHING_WORKING_DIR=/opt/cudtseis_web/storage/raganything
RAGANYTHING_OUTPUT_DIR=/opt/cudtseis_web/storage/raganything_output
RAGANYTHING_DOCUMENT_DIR=/opt/cudtseis_web/storage/geo_rag_documents
RAGANYTHING_PARSER=mineru
RAGANYTHING_PARSE_METHOD=auto
RAGANYTHING_QUERY_MODE=hybrid

GEO_RAG_EMBEDDING_PROVIDER=http
GEO_RAG_EMBEDDING_URL=http://127.0.0.1:8080/v1/embeddings
GEO_RAG_EMBEDDING_API_KEY=
GEO_RAG_EMBEDDING_ALLOW_FALLBACK=false
GEO_RAG_EMBEDDING_MODEL=BAAI/bge-m3
GEO_RAG_EMBEDDING_DIM=1024
GEO_RAG_EMBEDDING_BATCH_SIZE=32
GEO_RAG_INDEX_VERSION=geo-rag-bge-m3-v1

# 文献原文件存储。
# 服务器后端模式下，local 指云服务器本机目录。
GEO_RAG_STORAGE_BACKEND=local
GEO_RAG_STORAGE_ROOT=/opt/cudtseis_web/storage/geo_rag_documents
GEO_RAG_UPLOAD_STAGE_ROOT=/opt/cudtseis_web/storage/geo_rag_upload_stage
GEO_RAG_STORAGE_REMOTE_ROOT=/opt/cudtseis_web/storage/geo_rag_documents
GEO_RAG_STORAGE_PUBLIC_BASE_URL=http://8.137.179.31/files/geo_rag_documents
GEO_RAG_STORAGE_SSH_HOST=
GEO_RAG_STORAGE_SSH_USER=root
GEO_RAG_STORAGE_SSH_PORT=22
GEO_RAG_STORAGE_SSH_KEY_PATH=
```

`GEO_RAG_EMBEDDING_ALLOW_FALLBACK=false` 用来防止正式导入时污染知识库：如果 TEI 没启动，入库会直接失败，而不是悄悄使用 hash embedding。

从导入页上传文献时，文件会先写入后端配置的暂存目录，再保存到服务器文献目录，并由 RAGAnything/MinerU/LightRAG 解析和入库。我们当前推荐“服务器跑后端”：后端在云服务器上，所以 `GEO_RAG_STORAGE_BACKEND=local` 表示文件保存到云服务器目录，不再需要本机 SSH 密钥来上传 PDF。

如果只在个人电脑跑前端，把前端 `.env.local` 配成：

```env
VITE_API_BASE=http://8.137.179.31:8001/api
```

其中 PostgreSQL 存地震目录、文献元数据、PDF 路径和问答记录；RAGAnything/LightRAG 存文献 RAG 索引；PDF 原文存云服务器目录；embedding 在服务器上先跑 TEI，后续可以迁到云 GPU 或统一 embedding 服务。

服务器只启动后端时，在仓库根目录运行：

```bash
python3 dev.py setup-raganything
python3 dev.py backend
```

当前最终文献 RAG 链路采用 `RAGAnything + MinerU + LightRAG`：MinerU 负责 PDF 版面和多模态解析，RAGAnything 负责把正文、图、表、公式等内容组织进 LightRAG 索引，LightRAG 负责混合检索、实体关系和上下文组织。项目自己的 PostgreSQL 不再重复保存每一个 LightRAG chunk，而是保存文献元数据、原文路径、解析统计、知识卡片和问答记录，方便前端展示、审查和云端迁移。

### 文献入库不变量

Geo RAG 入库必须遵守文献边界不变量：

```text
每个入库任务只处理一篇文献。
每个 chunk 只能属于一个 document_id。
overlap 只允许发生在同一篇文献内部。
批量入库只是逐篇调用单篇入库流程，不能把两篇文献拼接后再切块。
```

在 RAGAnything 主引擎模式下，具体 chunk、实体和关系由 RAGAnything/LightRAG 管理；项目层仍然坚持上面的“每篇文献独立入库”不变量，保证一个文献任务不会把另一篇文献的内容混进同一个 `document_id`。旧的 builtin fallback 才会使用项目内置的 role-aware overlap 和 Qdrant chunk 索引。

批量导入目录中的 PDF/TXT/MD：

```bash
curl -s -X POST http://127.0.0.1:8001/api/documents/batch-ingest \
  -H 'Content-Type: application/json' \
  -d '{"directoryPath":"Project-Code/backend/.data/geo_rag_documents","limit":3,"force":true}'
```

建议先用 `limit=3` 或 `limit=5` 小批量验证检索质量，再扩大到完整文献库。

### RAG-Anything / 高级 RAG 说明

本项目最终文献 RAG 主链路已经切到 RAGAnything。只做前端、地震目录或普通页面开发时，可以先运行默认 `python dev.py setup`；只要你要导入文献、解析 PDF、检索文献或调试 RAG 问答，就必须安装完整 RAG 依赖。

安装完整 RAG 依赖：

```bash
python dev.py setup-raganything
```

Windows：

```powershell
py dev.py setup-raganything
```

要实际启用 RAGAnything 运行时，还需要在 `Project-Code/backend/.env.local` 中配置：

```env
GEO_RAG_ENGINE=raganything
RAGANYTHING_ENABLED=true
RAGANYTHING_SOURCE_DIR=/Users/teki/Downloads/my_project/cudtseis_web/RAG-Anything-main
OPENAI_API_KEY=你的 API Key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
```

当前代码已经把 RAGAnything 作为主 RAG 引擎层接入，而不是把它的源码拆散复制到业务代码里。最终目标是：RAGAnything/LightRAG/MinerU 负责通用多模态 RAG，项目自己的后端负责用户入口、文献元数据、PDF 文件管理、地震目录、问答记录和科研审查层。相关配置：

```env
# 正式方向：只使用 RAGAnything 作为文献 RAG 引擎。
# builtin 只保留作本地轻量调试/遗留测试，不作为最终系统主链路。
GEO_RAG_ENGINE=raganything

RAGANYTHING_WORKING_DIR=Project-Code/backend/.data/raganything
RAGANYTHING_OUTPUT_DIR=Project-Code/backend/.data/raganything_output
RAGANYTHING_DOCUMENT_DIR=Project-Code/backend/.data/geo_rag_documents
RAGANYTHING_SOURCE_DIR=RAG-Anything-main
RAGANYTHING_PARSER=mineru
RAGANYTHING_PARSE_METHOD=auto
RAGANYTHING_QUERY_MODE=hybrid
```

`RAGANYTHING_SOURCE_DIR` 指向项目根目录下的完整上游源码 `RAG-Anything-main`。后端启动时会优先从这里导入 `raganything`，如果该目录不存在，才回退到虚拟环境里通过 pip 安装的包。这样团队可以直接跟随完整 RAGAnything 源码升级，而不是把核心 RAG 逻辑拆碎复制进业务代码。

`GEO_RAG_ENGINE=raganything` 后，文献导入不再同时写入我们自研 Qdrant chunk 索引；PDF/TXT/MD 会先进入项目的文件存储目录，然后由 RAGAnything/MinerU/LightRAG 完成解析、入库和检索。PostgreSQL 仍然保存文献元数据、原文路径、地震目录和问答记录。

RAGAnything 的 embedding 会复用项目里的 `GEO_RAG_EMBEDDING_*` 配置。因此服务器上可以统一启动 TEI / `BAAI/bge-m3`，不需要再给 RAGAnything 单独配置一套 embedding API。

说明：`raganything[text]` 依赖 MinerU、Lightrag、OpenCV、ONNX、Gradio 等较大的包，首次安装会明显慢一些。如果遇到 `incomplete-download` 或网络中断，重新运行 `python dev.py setup-raganything`。

如果看到类似：

```text
Cannot install mineru[core,pipeline]==3.1.6 and shapely==2.0.6
ResolutionImpossible
```

这不是业务代码错误，而是解析依赖之间的版本约束冲突。请使用项目提供的 `Project-Code/backend/requirements-raganything.txt`，其中只启用 `mineru[core]`，避免默认开发环境被 `pipeline` 依赖拖垮。

### 外部方案参考快照

项目根目录的 `RAG-Anything-main/` 是当前优先使用的完整上游 RAGAnything 源码。`references/source-snapshots/` 仍作为旧方案和 ResearchClaw / literature-review 的技术参考，不再作为运行时主来源。

可以通过这个接口检查当前环境是否真正就绪：

```bash
curl http://127.0.0.1:8001/api/raganything/status
```

如果返回 `ready=false`，优先看 `requiredActions` 和 `dependencies.missing`。如果要确认当前是否真的使用完整源码，看 `dependencies.raganythingOrigin`，它应该指向项目根目录下的 `RAG-Anything-main/raganything/__init__.py`。

不要把完整的外部仓库、它们自己的 `.venv`、`node_modules`、解析输出、样例 PDF 或缓存提交进本项目。完整导入目录 `Agent-RAG/`、`AutoResearchClaw/`、`literature-review/` 已经加入 `.gitignore`；协作开发只需要保留 `references/` 里的轻量快照。

### 地质文献知识库说明

当前已经提供“先建库，再基于库做问答/分析”的后端接口。最终文献 RAG 主引擎是 RAGAnything：

- `POST /api/knowledge/init`：查看知识库和 RAG 引擎状态
- `POST /api/documents/ingest`：导入本地 PDF/TXT/Markdown 文献
- `POST /api/knowledge/search`：通过 RAGAnything/LightRAG 检索上下文
- `POST /api/rag/papers/query`：论文/文献知识库问答
- `POST /api/events/{event_id}/geo-analysis`：结合地震事件和文献证据做地质分析

`builtin` 旧链路仍保留在代码里，主要用于本地轻量调试和测试；正式协作与服务器部署不再依赖 Qdrant 双写。

导入一篇本地文献示例：

前端“文献入库”的文件路径要填写具体文件，不能只填目录。比如已经把 PDF 放到 `Project-Code/backend/.data/geo_rag_documents/` 后，应填写：

```text
Project-Code/backend/.data/geo_rag_documents/2604.27126v1.pdf
```

```bash
curl -X POST http://127.0.0.1:8001/api/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "filePath": "Project-Code/backend/.data/geo_rag_documents/example.pdf",
    "title": "Example Geology Paper",
    "authors": ["Author A"],
    "year": 2024,
    "force": true
  }'
```

检索/问答示例：

```bash
curl -X POST http://127.0.0.1:8001/api/rag/papers/query \
  -H "Content-Type: application/json" \
  -d '{"question":"这批文献中关于断层破裂和构造背景有哪些证据？","topK":6}'
```

### PostgreSQL 账号密码说明

默认配置尽量不写账号密码：

```env
DATABASE_URL=postgresql+psycopg:///quakes
```

这个写法会优先使用本机 PostgreSQL 的本地连接方式和当前系统用户，适合 macOS/Homebrew 这类常见开发环境。`dev.py` 会先尝试免密连接；只有本机 PostgreSQL 明确要求密码时，才会提示输入你自己电脑的 PostgreSQL 用户名和密码。

每位同事的数据库账号密码只应该存在于自己的：

```text
Project-Code/backend/.env
```

`.env` 已经被 `.gitignore` 忽略，不应该提交到 Git。不要把某一个人的 PostgreSQL 用户名或密码写进 README、`.env.example` 或源码。

如果你的本机 PostgreSQL 需要账号密码，可以在 `.env` 里使用：

```env
DATABASE_URL=postgresql+psycopg://postgres:你的PostgreSQL密码@127.0.0.1:5432/quakes
```

如果你的 PostgreSQL 允许指定用户但不需要密码，也可以写：

```env
DATABASE_URL=postgresql+psycopg://你的用户名@127.0.0.1:5432/quakes
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

也可以按终端提示直接输入 PostgreSQL 用户名和密码；如果本机允许免密，密码处可以直接回车。连接成功后，`dev.py` 会把可用的 `DATABASE_URL` 保存到 `Project-Code/backend/.env`，下次启动不用重复输入。

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
python dev.py clean   # 删除本项目内的依赖目录和下载缓存
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
- `DATABASE_URL`，数据库连接串；默认 `postgresql+psycopg:///quakes`，尽量使用本机免密连接
- `PIP_INDEX_URL`，默认 `https://pypi.tuna.tsinghua.edu.cn/simple`
- `PIP_TRUSTED_HOST`，默认 `pypi.tuna.tsinghua.edu.cn`
- `PIP_CACHE_DIR`，默认 `Project-Code/backend/.data/pip-cache`
- `GEO_RAG_ENGINE`，文献 RAG 引擎；最终推荐 `raganything`
- `RAGANYTHING_ENABLED`，是否启用 RAGAnything/LightRAG/MinerU
- `RAGANYTHING_WORKING_DIR`，RAGAnything/LightRAG 工作目录
- `RAGANYTHING_OUTPUT_DIR`，MinerU 解析输出目录
- `RAGANYTHING_DOCUMENT_DIR`，RAGAnything 允许读取的文献目录
- `QDRANT_URL` / `QDRANT_COLLECTION`，仅用于 legacy builtin fallback 或实验索引
- `GEO_RAG_STORAGE_BACKEND`，PDF/TXT/MD 原文存储方式；服务器后端模式推荐 `local`
- `GEO_RAG_STORAGE_ROOT`，原文目录；服务器后端模式建议 `/opt/cudtseis_web/storage/geo_rag_documents`
- `GEO_RAG_UPLOAD_STAGE_ROOT`，上传暂存目录；服务器后端模式建议 `/opt/cudtseis_web/storage/geo_rag_upload_stage`
- `GEO_RAG_STORAGE_REMOTE_ROOT`，云服务器原文目录；`ssh` 模式使用
- `GEO_RAG_STORAGE_PUBLIC_BASE_URL`，原文公开访问前缀，用于“打开原文”
- `GEO_RAG_STORAGE_SSH_HOST` / `GEO_RAG_STORAGE_SSH_USER` / `GEO_RAG_STORAGE_SSH_KEY_PATH`，仅在个人电脑后端通过 SSH 上传原文时使用
- `SKIP_DB_SETUP=1`，跳过数据库自动初始化
- `FORCE_INSTALL=1`，强制重新安装后端和前端依赖

## 8. 清理本机依赖

如果以后要卸载本项目的本地依赖，或者想重新安装一个干净环境，在仓库根目录运行：

```bash
python dev.py clean
```

Windows：

```powershell
py dev.py clean
```

这只会删除项目目录里的依赖和下载缓存，不会删除源码、`.env`、数据库或文献数据：

- `Project-Code/backend/.venv`
- `Project-Code/backend/.data/pip-cache`
- `Project-Code/backend/.data/pip-stamps`
- `Project-Code/Frontend/quakes-frontend/node_modules`
- `Project-Code/Frontend/quakes-frontend/.npm-cache`

## 9. 常见问题

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

### 数据库连接失败或密码错误

编辑：

```text
Project-Code/backend/.env
```

如果本机不能免密连接，改成你自己电脑的 PostgreSQL 用户名和密码后重新运行：

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

## 10. 协作约定

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
