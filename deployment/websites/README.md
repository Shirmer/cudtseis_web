# 网站部署记录（2026-10-30）

## 分工与已部署内容

| 内容 | 主机 | 目录 / 入口 |
| --- | --- | --- |
| 深视地球公司官网（交互地球） | 腾讯云 162.14.113.163 | `/srv/deepseek-earth/current`，正式域名 `deepseek-earth.cdutseis.com` |
| 实验室网站临时公网入口（仅转发） | 腾讯云 162.14.113.163 → frp → 学校 | `https://seis.cdutseis.com/`，腾讯云没有该站静态文件 |
| 成都理工大学地震研究中心官网 | 学校 202.115.129.74 | `/srv/earthquake-center/current`，计划由学校 `seis.cdut.edu.cn` 统一反代访问 |
| GeoCamera 后端、MySQL、管理后台 | 学校（GeoCamera 会话已迁移） | `/srv/geocamera`，本机 `127.0.0.1:18081` |
| App 入口 | 腾讯云 → frp → 学校 | 保留原有转发；阿里云 8.137.48.168 继续作为旧版 App 转发入口 |
| 图片与安装包 | 阿里云 OSS | 保持现有存储与下载地址 |

实验室官网包含主页、地震目录、Terra 工作台、404 页面与实际引用的静态资源；地震目录和 Terra 仍是静态演示，没有接旧后端。没有上传项目源码、内部说明、密钥或本地预览截图。

## 腾讯云公司网站

- 本机构建 Vue/Vite，腾讯云只运行 Nginx 提供构建产物。地球动画在访客浏览器运行，不在服务器执行图形计算。
- 配置：`/etc/nginx/sites-available/deepseek-earth`，软链至 `sites-enabled`；本目录 `company.nginx.conf` 是已部署配置副本。
- 原来的默认站点（GeoCamera 反代）保留。显式 IP 虚拟主机现在展示公司官网，同时继续将 `/api/`、`/admin` 转发到原来的 frp 端口 18081；阿里云旧入口仍可工作。
- 公司域名仅代理安装包查询 `/api/release/latest`；其他 `/api/` 请求返回 404。公司域名没有被设置为 App 全功能 API 域名。
- 假备案号 `蜀ICP备XXXXXXXX号-1` 已从公开页脚移除；未编造真实备案号。公司原有联系邮箱仍沿用既有代码，需要业务方确认。
- 已签发 Let's Encrypt 证书，到期日 2027-01-28；已启用 `certbot.timer` 自动续期，`certbot renew --dry-run` 模拟续期成功。账号未填写联系邮箱，后续可补充维护邮箱。
- 用户放行腾讯云 TCP 443 后，正式域名公网 HTTPS 验证通过（HTTP 200、TLS 证书验证成功），浏览器已打开正式域名。
- DNS 已从 Cloudflare 改为 `elmer.dnspod.net`、`many.dnspod.net`；两台权威服务器均返回 `deepseek-earth.cdutseis.com A 162.14.113.163`，公共解析与浏览器已可解析，个别网络可能仍有旧缓存。

更新：本机构建 `Project-Code/Frontend/quakes-frontend`，上传新 release 目录，切换 `current` 软链。不要覆盖已有 App 反代配置，不要重新运行开发服务器代替静态部署。当前版本目录为 `releases/20261030-website`。

## 学校实验室网站

- 独立 Compose 项目 `earthquake-center`，目录 `/srv/earthquake-center`，容器 `cdut-earthquake-center-web`，与 `/srv/geocamera` 分开管理。
- 使用已有官方 Nginx 镜像的本地标签 `geocamera/nginx:1.28`，无需重新拉取或构建 App 镜像。
- Nginx 监听学校主机 TCP 80，使用 host 网络，让主机 firewalld 继续控制端口；新增的主机防火墙规则仅为 HTTP 服务。
- 容器只读文件系统、静态资源只读挂载、工作进程使用 nginx 用户；设置内存上限 96 MiB、CPU 上限 0.5 核、日志轮转和自动重启。
- 校园网内 `http://202.115.129.74/` 可访问，主页、目录、Terra 及所有实际资源均核实与本地一致；`/health` 返回 `earthquake-center ok`。
- 校外腾讯云访问学校 IP 的 HTTP 端口超时，因此不能把校园网内访问成功当成校外可访问。
- `seis.cdut.edu.cn` 指向学校反代是预期设计，不修改该 DNS。当前 HTTP/HTTPS 请求返回防护校验页（412），浏览器未显示官网，尚未验证学校反代到本站的完整链路。
- 需由学校管理员核实 `seis.cdut.edu.cn` 的后端目标为 `http://202.115.129.74:80`，反代节点到此地址的访问权限，以及网站防护策略。反代的实际回源地址不一定等于其域名解析 IP。

更新配置与静态文件后执行：

```sh
cd /srv/earthquake-center
docker compose run --rm --no-deps --entrypoint nginx web -t
docker compose up -d --force-recreate
curl -f http://127.0.0.1/health
```

静态资源使用 `current` 软链只读挂载；切换 release 后要重建此网站容器以重新解析挂载目标，不要仅重启 Nginx 工作进程。无需重建 App、重启 Docker 或修改数据库。

## 验证与剩余工作

- 公司站通过 TypeScript 检查和生产构建；Vite 提示地球模块体积较大，属于下载体积提示，构建成功。
- 25 项 HTTP/内容比对及 HTTPS 检查通过，本地记录见 `verification-20261030.json`（生成产物，不提交仓库）；浏览器中公司地球与版本查询正常，实验室主页正常。
- 现有腾讯云 IP 和阿里云旧 IP 的 `/api/release/latest` 均正常返回版本 1.0.25；学校容器正常，MySQL healthy。没有修改 App 后端、数据库、OSS 或 frp 配置。
- 还需完成：学校正式域名的反代访问验证。公司域名 DNS、HTTPS 及公网访问已完成。
- 未进行数据库写入业务测试；GeoCamera 会话此前已完成登录、同步和账号隔离测试，本次网站部署只复查只读接口。

## 当前临时公网入口：seis.cdutseis.com → frp → 学校

用户明确要求腾讯云不保存实验室网站文件，已将先前静态副本方式替换为反向代理。

- 访问路径：访客 HTTPS → 腾讯云 Nginx → 127.0.0.1:18082 → frp 双向 TLS 隧道 → 学校 127.0.0.1:80 → 学校网站容器。
- DNS 仍为 `seis.cdutseis.com A 162.14.113.163`；腾讯云继续负责该域名的 HTTPS 证书和自动续期。
- 入口配置：`/etc/nginx/sites-available/earthquake-center`，本地副本 `lab-tencent.nginx.conf`；没有静态 root、缓存或备用静态内容。
- 腾讯云的 `/srv/earthquake-center` 静态副本及上传压缩包已移除。页面源文件只在学校网站目录管理；本地项目保留开发源码。
- 原公司网站、GeoCamera、数据库、管理后台与 OSS 保持原有分工。frp 仅增加独立网站转发；端口 18082 只监听腾讯云 127.0.0.1，无需新增公网规则。
- 完整页面、目录、Terra 和学校 `/health` 均已通过公网 HTTPS 验证，并核实删除腾讯云静态文件后仍可访问。现有公司及 App 入口同时复查通过，本地记录见 `lab-frp-verification-20261030.json`（生成产物，不提交仓库）。
- `seis.cdutseis.com` 证书模拟续期已成功；HTTP 自动跳转 HTTPS。证书到期日 2027-01-28。
- 后续只更新学校 `/srv/earthquake-center`；无需再同步实验室网页到腾讯云。学校正式域名可用后，再决定是否设置临时域名重定向。
- 临时域名依赖学校网站和 frp 均正常；它不是学校正式域名的反代修复，`seis.cdut.edu.cn` 的入口仍需学校管理员核实。

本地生成的 `lab-mirror-verification-20261030.json`（不提交仓库）记录的是此前短暂使用的静态副本方案，仅供历史参考；当前以 frp 验证记录为准。
