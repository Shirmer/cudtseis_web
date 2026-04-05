# cudtseis_web

CDUT SeisLab Web 项目（前端 + 后端 + 数据库）。

## 一条命令启动（macOS / Windows）

在仓库根目录运行：

```bash
python dev.py
```

Windows 也可以用：

```powershell
py dev.py
```

该命令会自动执行：

- 检查 Node/npm/Python/PostgreSQL 工具是否可用
- 准备后端虚拟环境与依赖
- 准备前端依赖
- 尝试启动本机 PostgreSQL 服务（macOS + Homebrew）
- 自动创建 `quakes` 数据库，并尽可能启用 `postgis`
- 同时启动后端（`8001`）和前端（`5173`）

按 `Ctrl+C` 可同时停止两个服务。

## 可选命令

```bash
python dev.py check
python dev.py setup
python dev.py up
```

- `check`：仅检查环境状态
- `setup`：仅安装/初始化，不启动开发服务
- `up`：初始化 + 启动（与默认行为一致）

## 跨平台前置依赖

- Python 3.10+
- Node.js 20+
- PostgreSQL 17 + PostGIS

### macOS（Homebrew）

```bash
brew install node postgresql@17 postgis
brew services start postgresql@17
```

### Windows

请先安装：

- Node.js LTS
- PostgreSQL 17
- PostGIS（Stack Builder 或其他包管理方式）
- Python 3.10+

安装建议：

- 安装 PostgreSQL 时请记住超级用户密码。
- PostGIS 版本要与 PostgreSQL 主版本一致（`17`）。
- 确保 `C:\Program Files\PostgreSQL\17\bin\` 已加入 PATH（保证 `psql` 可用）。

然后启动 PostgreSQL 服务（通常是）：

```powershell
net start postgresql-x64-17
```

之后运行：

```powershell
python dev.py
```

也可以直接双击仓库根目录的 `dev.bat`。

如果系统不识别 `python`，请改用：

```powershell
py dev.py
```

如果 PostgreSQL 服务名不同，可用以下命令查询：

```powershell
Get-Service *postgres*
```

## 访问地址

- 前端：`http://127.0.0.1:5173`
- 后端文档：`http://127.0.0.1:8001/docs`
