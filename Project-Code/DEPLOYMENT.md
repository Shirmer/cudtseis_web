# 深视地球官网部署说明

本仓库现为 **深视地球（成都）信息技术有限公司官网**（含 GeoCamera 产品介绍），前端位于
`Project-Code/Frontend/quakes-frontend`（Vue 3 + Vite + TypeScript）。后端目录
`Project-Code/backend`（FastAPI + PostGIS）当前不参与官网部署。

## 1. 站点结构

| 路径 | 说明 |
| --- | --- |
| `/`、`/en` | 官网首页（中/英） |
| `/privacy`、`/en/privacy` | 隐私政策 |
| `/terms`、`/en/terms` | 用户协议 |
| `/contact`、`/en/contact` | 联系我们 |
| `/admin/` | GeoCamera 管理后台（独立构建，部署在服务器） |
| `/api/...` | 移动端 App 与管理后台共用的 Java 后端接口 |

发布前需替换的占位内容：

- `src/config/site.ts`：ICP 备案号、联系邮箱、公司地址；
- `src/content/legal.ts` 与 `src/views/LegalView.vue`：隐私政策/用户协议生效日期。

## 2. 本地开发

```bash
cd Project-Code/Frontend/quakes-frontend
npm install
npm run dev        # http://127.0.0.1:5173
```

开发与预览模式下 `/api` 默认代理到线上后端 `http://8.137.48.168`
（用于获取 App 最新版本信息等只读接口），可通过 `VITE_API_PROXY` 覆盖。

类型检查与构建：

```bash
npm run type-check
npm run build      # 产物在 dist/
```

## 3. 服务器部署（阿里云 8.137.48.168）

```bash
rsync -az --delete --exclude '.DS_Store' \
  -e "ssh -i ~/.ssh/geocamera_ed25519" \
  Project-Code/Frontend/quakes-frontend/dist/ \
  root@8.137.48.168:/opt/geocamera/website/
```

服务器目录：

- `/opt/geocamera/website`：官网静态文件（本仓库产物）；
- `/opt/geocamera/admin-web`：管理后台静态文件（独立仓库构建）；
- `/opt/geocamera/backend.jar`：Java 后端（监听 `127.0.0.1:8080`）。

Nginx 配置 `/etc/nginx/sites-available/geocamera`：

- `/` 返回官网 SPA（`try_files ... /index.html`）；
- `/api/` 反向代理到 `127.0.0.1:8080`（App 与管理后台接口）；
- `/admin/` 静态托管管理后台。

修改配置后：

```bash
nginx -t && systemctl reload nginx
```

域名与备案完成后，将域名 A 记录解析到服务器 IP，并在该配置中补充
`server_name`，再按需配置 HTTPS 证书。

## 4. GeoCamera 下载入口

官网“下载”按钮实时请求 `/api/release/latest` 获取最新版本与 OSS 临时下载地址
（后端每次请求重新签名，有效期约 30 分钟），点击后由浏览器直接下载 APK。
无需在官网侧保存 APK 文件。
