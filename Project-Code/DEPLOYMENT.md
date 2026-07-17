# CDUT SEISLAB 网站部署说明

这个分支是组织网站的干净重启点，当前包含：

- Vue / Vite 前端网站
- FastAPI 后端接口
- PostgreSQL + PostGIS 地震数据存储
- 前端同源 `/api` 调用，方便通过 Nginx 对外发布

## 1. 对外访问还需要什么

你现在已经有服务器 MAC 地址、固定内网 IP、子网掩码、网关。要让网站被公网访问，还需要确认下面这些条件：

- 公网 IP：服务器本身有公网 IP，或者上级路由器/防火墙有公网 IP。
- 端口映射：如果服务器只有内网 IP，需要把公网的 80/443 端口转发到这台服务器的内网 IP。
- 域名：准备一个域名，并把 DNS 的 A 记录指向公网 IP。
- 防火墙放行：云安全组、机房防火墙、系统防火墙都要允许 80 和 443。
- Web 服务：使用 Nginx 或 Caddy 对外提供网站，并把 `/api` 反向代理到后端。
- HTTPS 证书：建议使用 Let's Encrypt 或服务器面板自带证书。
- 运行环境：Node.js 20+、Python 3.10+、PostgreSQL、PostGIS。
- 备案/访问策略：如果使用中国大陆服务器和正式域名，通常需要按服务商要求完成备案。

后端服务建议只监听 `127.0.0.1:8001`，不要直接暴露到公网。

## 2. 前端构建

```bash
cd /opt/cudtseis_web/Project-Code/Frontend/quakes-frontend
npm install
npm run build
```

构建产物会生成在：

```text
/opt/cudtseis_web/Project-Code/Frontend/quakes-frontend/dist
```

## 3. 后端启动

```bash
cd /opt/cudtseis_web/Project-Code/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

启动前需要创建数据库并启用 PostGIS：

```sql
CREATE DATABASE quakes;
\c quakes
CREATE EXTENSION IF NOT EXISTS postgis;
```

后端健康检查：

```bash
curl http://127.0.0.1:8001/health
```

## 4. Nginx 示例

```nginx
server {
    listen 80;
    server_name your-domain.example;

    root /opt/cudtseis_web/Project-Code/Frontend/quakes-frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

## 5. 配置说明

- 前端生产环境默认使用同源 `/api`，不用在代码里写服务器 IP。
- 本地开发时，Vite 会把 `/api` 代理到 `http://127.0.0.1:8001`。
- 数据库账号、密码、域名等配置写进 `.env`，不要提交到 Git。
- 如果服务器只有内网 IP，公网访问的关键不是 MAC 地址，而是公网入口和端口映射。
