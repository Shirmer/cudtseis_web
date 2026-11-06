# 网站发布通用说明

本目录只保留公开的部署示例，不记录生产主机、登录方式、内部转发端口、成员信息、备份位置或实际运维日志。正式配置和维护记录由管理员在团队内部保存。

## 网站源码

- 公司与产品官网：`Project-Code/Frontend/quakes-frontend`。
- 研究中心官网：`lab-site`。
- 公司与产品官网按域名选择入口，正式公开网址在前端站点配置中维护。

## 检查与构建

在 Vue 项目目录执行：

```sh
npm ci
npm run type-check
npm run build
```

仅发布 `dist/` 内的公开构建产物。不要将源码、环境变量文件、部署记录、数据库或私钥上传静态网站目录。

## 发布原则

1. 使用内部维护的真实配置替换示例域名、目录及上游端口。
2. 上传到新的版本目录，校验公开文件后切换当前版本，保留回退版本。
3. 检查网站、静态资源、HTTPS 和必要的公开只读接口。
4. 生产环境使用静态文件服务，不暴露开发服务器。
5. HTTPS 私钥保存在受限目录，定期验证自动续期。

本目录的 Nginx / Compose 文件均为示例，不能直接覆盖线上配置。`renew-nginx-certificate.sh` 是证书续期后的通用配置检查与平滑重载脚本。

## 文件说明

- `company.nginx.conf`：公司 SPA 静态站点示例。
- `geocamera.nginx.conf`：独立产品站点示例。
- `lab.nginx.conf`：研究网站静态服务示例。
- `lab-tencent.nginx.conf`：HTTPS 入口转发到本地上游的示例。
- `lab.compose.yaml`：只读静态网站容器示例。
