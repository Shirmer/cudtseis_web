# 两端 frp 部署与维护

部署日期：2026-10-30。官方版本：0.71.1，Linux amd64。
来源：https://github.com/fatedier/frp/releases/tag/v0.71.1
安装包 SHA-256：`1d9875210972a5d1a62b2dc4c48df45ab0af05d3ca1b5e494a014428259df803`。

## 位置与状态

| 主机 | 登录方式 | 服务 |
| --- | --- | --- |
| 腾讯云 162.14.113.163 | `ssh -i ~/.ssh/deepseek_earth_1.pem ubuntu@162.14.113.163` | `frps`、`frp-ingress` |
| 学校 202.115.129.74 | `ssh -i ~/.ssh/cdutseis-schoolsever root@202.115.129.74` | `frpc`、`frp-health` |

程序位于两台机器 `/opt/frp/0.71.1/`。配置位于 `/etc/frp/frps.toml` 或 `/etc/frp/frpc.toml`。
服务由 systemd 管理，已设为开机启动、失败重启，使用无登录权限的专用 `frp` 用户运行。

## 通道范围

学校 frpc → 腾讯云 TCP 7000。
| 腾讯云本机转发端口 | 学校本机目标 | 用途 |
| --- | --- | --- |
| 18080 | 18080 | `/health` 测试 |
| 18081 | 18081 | GeoCamera 服务 |
| 18082 | 80 | 实验室网站，供 `seis.cdutseis.com` HTTPS 入口转发 |

18080、18081、18082 均不对公网监听。GeoCamera 会话随后另行接入了 `127.0.0.1:18081` 转发，腾讯云 Nginx 通过该端口访问学校 App 服务；未开放数据库或 SSH 转发。

腾讯云控制台入站规则需要：TCP 7000，来源 `202.115.129.74/32`，允许。
主机侧另有 `/etc/frp/ingress.nft` 源地址限制，只允许学校连接 7000，不改变 SSH 规则。

## 验证（腾讯云上执行）

```bash
sudo systemctl status frps --no-pager
curl --connect-timeout 3 --max-time 5 http://127.0.0.1:18080/health
```

预期返回 `status: ok`、`service: frp-link-test`、`location: school-server`。只有收到此结果才确认端到端成功。

学校上执行：

```bash
systemctl status frpc frp-health --no-pager
journalctl -u frpc -n 30 --no-pager
```

腾讯云日志：`sudo journalctl -u frps -n 30 --no-pager`。

## 安全设置

- 私有 CA 签发两端证书，强制 TLS，双向验证证书；学校显式校验服务器身份 `frp-gateway.internal`。该名称仅用于证书校验，不需要公网 DNS。
- 使用随机令牌文件 `/etc/frp/token`，同时认证心跳和工作连接。项目中的示例配置只有文件路径，没有令牌或私钥。
- 配置与证书为 root 所有、frp 组只读；CA 私钥目录为 root 专用。
- 初次部署仅允许测试转发 18080。2026-10-30 GeoCamera 迁移后，服务端随后增加实验室网站转发 18082，目前共三个转发，均限定监听 127.0.0.1。示例已更新为当前端口配置，但不含实际凭据，不要直接覆盖线上配置。
- 系统服务限制写目录、权限提升、可用内存和 CPU。
- 证书约在 2027-10-30 到期；应提前更新证书、分发并重启两端服务。

## 修改与重启

修改前备份 `/etc/frp/` 到仅管理员可访问的位置，不要把实际凭据提交到仓库。

腾讯云：
```bash
sudo /opt/frp/0.71.1/frps verify -c /etc/frp/frps.toml
sudo systemctl restart frps
```

学校：
```bash
/opt/frp/0.71.1/frpc verify -c /etc/frp/frpc.toml
systemctl restart frpc
```

接入真实后端时，调整学校侧 localPort；新增转发须同步调整腾讯云 allowPorts、maxPortsPerClient。
腾讯云 Nginx 后续通过本机转发端口访问后端。测试接口不等于 App 后端。

## 停用

注意：当前 App 和临时实验室域名均依赖 frp，停用会使它们无法访问学校服务。只停止测试服务可以单独停用 frp-health，不应为此停用 frpc/frps。

学校：`systemctl disable --now frpc frp-health`。
腾讯云：`sudo systemctl disable --now frps`。
停用后删除腾讯云控制台的 TCP 7000 放行规则；主机侧源限制可保留。
证书与配置先留存备份。

## 当前验收记录

2026-10-30 15:08（北京时间）端到端验收通过：在腾讯云请求 `http://127.0.0.1:18080/health`，收到学校服务返回的 `{"status": "ok", "service": "frp-link-test", "location": "school-server"}`。

此前 TCP 7000 超时；腾讯云日志显示学校客户端于 14:52:36 成功连接，来源为 `202.115.129.74`。当前连接已放通，主机防火墙允许规则有实际流量。未通过控制台读取云防火墙规则，不能据此确认其来源范围；主机侧限制已核实为仅允许学校 IP。

两端配置语法校验通过，四个相关服务均已启用开机启动且正在运行。核实双向 TLS、令牌文件引用及私钥权限；腾讯云转发端口只监听 `127.0.0.1:18080`，学校测试服务同样只监听本机。15:08 主动重启学校 frpc 后，客户端重新登录、转发重新建立，腾讯云再次取得正常测试响应。

初次验收仅包含 frp 通道及测试服务。后续 GeoCamera 会话已接入真实 App 服务到 18081，并保留阿里云旧地址作为转发入口；本会话于网站部署时核实该转发及安装包查询接口仍正常。域名及网站部署进度另见 `../websites/README.md`。不要对公网开放 18080 或 18081。证书到期时间为 2027-10-30 14:42（北京时间）。

首次启动发现腾讯云程序父目录权限阻止普通用户执行，已修正 `/opt/frp` 为 755，frps 正常运行。临时客户端私钥副本已从腾讯云清理，学校持有客户端私钥；腾讯云 CA 目录仅 root 可访问。

## 实验室网站接入记录

2026-10-30 按用户要求增加 `earthquake-center` 转发：腾讯云 127.0.0.1:18082 → 学校 127.0.0.1:80。两端修改前的配置保存在 `/etc/frp/backups/`（仅管理员访问）。配置验证后重启两端 frp，三个转发均恢复。腾讯云网站入口改为 Nginx 反向代理并删除原静态副本，公网 HTTPS、学校健康接口、页面资源与现有 App 查询均通过验证。无需在腾讯云控制台开放 18082。
