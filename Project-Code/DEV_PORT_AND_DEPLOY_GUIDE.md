# 开发端口与部署迁移说明

## 本地开发端口

默认端口：

- 后端：`127.0.0.1:8001`
- 前端：`127.0.0.1:5173`

一条命令启动：

```bash
python dev.py
```

自定义端口：

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

## 前端 API 策略

前端业务代码通过 `src/config/api.ts` 统一生成接口地址：

- 默认 `VITE_API_BASE=/api`
- 开发环境由 Vite 把 `/api` 代理到后端
- 默认代理目标为 `http://127.0.0.1:8001`
- 可用 `VITE_PROXY_TARGET` 覆盖代理目标

因此本地开发不需要在页面代码里写死任何后端 IP。

## 后端 CORS

后端读取 `CORS_ORIGINS` 配置，默认支持：

- `http://127.0.0.1:5173`
- `http://localhost:5173`

使用 `dev.py` 启动时，会根据 `FRONTEND_HOST` / `FRONTEND_PORT` 自动设置本次开发服务所需的 CORS 来源。

## 可用环境变量

- `BACKEND_HOST`，默认 `127.0.0.1`
- `BACKEND_PORT`，默认 `8001`
- `FRONTEND_HOST`，默认 `127.0.0.1`
- `FRONTEND_PORT`，默认 `5173`
- `VITE_API_BASE`，默认 `/api`
- `VITE_PROXY_TARGET`，默认 `http://<BACKEND_HOST>:<BACKEND_PORT>`
- `CORS_ORIGINS`，逗号分隔
- `DATABASE_URL`，后端数据库连接串

## 推荐部署方式：同域名反向代理

示例：

- 前端页面：`https://seis.example.com`
- 后端接口：`https://seis.example.com/api/...`

做法：

1. 前端保持 `VITE_API_BASE=/api`。
2. Nginx 或网关把 `/api` 反向代理到后端服务。
3. 后端 `CORS_ORIGINS` 设置为正式前端域名。

Nginx 核心片段：

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

## 备选部署方式：前后端分域名

示例：

- 前端：`https://app.example.com`
- 后端：`https://api.example.com`

配置：

```bash
VITE_API_BASE=https://api.example.com/api
CORS_ORIGINS=https://app.example.com
```

## 上线前检查清单

- 前端没有写死公网 IP 或本机 IP。
- `.env` 没有提交到 Git。
- 生产 `CORS_ORIGINS` 只包含真实允许域名。
- 数据库和后端端口只对内网或网关开放。
- 网关启用 HTTPS、日志、超时和必要限流。
