# 成都理工大学地震研究中心与深视地球网站

本仓库维护两套独立网站：

| 网站 | 源码 | 当前入口 |
| --- | --- | --- |
| 成都理工大学地震研究中心 | [`lab-site/`](lab-site/README.md)，纯静态 HTML/CSS/JS | <https://seis.cdutseis.com/> |
| 深视地球公司官网（含交互地球） | `Project-Code/Frontend/quakes-frontend/`，Vue 3/Vite | <https://deepseek-earth.cdutseis.com/> |

实验室网站运行在学校服务器，临时域名通过腾讯云 HTTPS 入口与 frp 隧道访问。学校正式域名 `seis.cdut.edu.cn` 的统一反代仍待完成访问验证。公司官网的静态构建产物部署在腾讯云。

地震目录和 Terra 工作台目前为独立静态演示页面，未接入历史后端。`Project-Code/backend/` 为历史科研平台代码；GeoCamera App 的生产后端由独立项目维护。

## 本地运行

实验室网站不需要安装依赖或构建：

```sh
python3 -m http.server 4321 --directory lab-site
```

公司网站：

```sh
cd Project-Code/Frontend/quakes-frontend
npm ci
npm run dev
```

公司网站发布前运行 `npm run type-check` 和 `npm run build`。

## 部署文档

- [网站部署与维护](deployment/websites/README.md)
- [frp 配置与维护](deployment/frp/README.md)

只提交配置模板和证书文件路径，实际令牌、私钥、数据库配置与备份不进入仓库。旧设计稿、截图与提交压缩包保留在本地，不作为源码提交。
