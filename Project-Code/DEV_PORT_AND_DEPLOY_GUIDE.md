# 开发期本地端口与部署迁移说明

## 1. 本次改动目标

- 移除前端对固定远程 IP 的依赖（不再写死 `43.162.117.155:8001`）。
- 让每位同事可以使用自己的本地端口进行开发。
- 为后续正式服务器/域名上线保留可配置能力，避免重复改代码。

## 2. 本次代码改动

### 2.1 前端接口地址策略

- 新增 `src/config/api.ts`，统一构造 API 地址。
- 默认 `VITE_API_BASE=/api`，前端只请求相对路径（如 `/api/events`）。
- 修改了以下页面：
  - `src/views/DashboardView.vue`
  - `src/views/HistoryData.vue`

结果：

- 开发环境默认走本地代理。
- 生产环境可通过环境变量切换到真实域名，无需改业务代码。

### 2.2 Vite 代理配置

- 修改 `vite.config.ts`，新增 `/api` 代理能力。
- 默认代理目标：`http://127.0.0.1:8001`（可用 `VITE_PROXY_TARGET` 覆盖）。

结果：

- 浏览器访问 `http://127.0.0.1:5173/api/...` 时，自动转发到后端。
- 前端同事无需记忆后端真实地址，统一走 `/api`。

### 2.3 后端 CORS 可配置

- 在 `backend/app/setting.py` 新增配置项：
  - `cors_origins`
- 在 `backend/app/main.py` 中改为从配置解析 CORS 白名单，不再写死远程域名。

结果：

- 开发时默认支持本地前端地址。
- 生产时可通过环境变量精确收敛为正式域名。

### 2.4 一键启动脚本支持自定义端口

- 修改 `dev.py`，支持环境变量：
  - `BACKEND_HOST` / `BACKEND_PORT`
  - `FRONTEND_HOST` / `FRONTEND_PORT`
  - `VITE_API_BASE` / `VITE_PROXY_TARGET`
  - `CORS_ORIGINS`
- 默认值不变（后端 `8001`，前端 `5173`）。

结果：

- 每位同事可以本地自定义端口，不互相冲突。
- 仍可继续使用 `python dev.py` 一键启动。

## 3. 开发阶段使用方式

### 3.1 默认启动（推荐）

```bash
python dev.py
```

### 3.2 自定义本地端口

macOS / Linux:

```bash
BACKEND_PORT=18001 FRONTEND_PORT=15173 python dev.py
```

Windows PowerShell:

```powershell
$env:BACKEND_PORT=18001
$env:FRONTEND_PORT=15173
py dev.py
```

## 4. 有真实服务器和域名后的迁移方案

## 4.1 推荐方案：同域名部署（最成熟）

示例：

- 前端页面：`https://seis.example.com`
- 后端接口：`https://seis.example.com/api/...`

做法：

1. 前端保持 `VITE_API_BASE=/api`（不改业务代码）。
2. 使用 Nginx/网关把 `/api` 反向代理到后端服务（如 `127.0.0.1:8001`）。
3. 后端 `CORS_ORIGINS` 设置为正式前端域名（如 `https://seis.example.com`）。

Nginx 示例（核心片段）：

```nginx
server {
    listen 80;
    server_name seis.example.com;

    location / {
        root /var/www/seis-frontend;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 4.2 备选方案：前后端分域名

示例：

- 前端：`https://app.example.com`
- 后端：`https://api.example.com`

做法：

1. 前端构建时设置：`VITE_API_BASE=https://api.example.com/api`
2. 后端设置：`CORS_ORIGINS=https://app.example.com`
3. 网关层开启 HTTPS 与证书，后端仅暴露必要端口。

## 5. 上线前检查清单

- 前端是否仍有写死 IP（应为 0 个）。
- `CORS_ORIGINS` 是否只包含真实允许域名。
- 是否统一启用 HTTPS。
- 数据库、后端端口是否仅对内网或网关开放。
- 网关是否配置了日志、超时、限流（按运维策略）。
