# 团队 SSH 入口（2026-11-05）

已在当前 Mac 配置 `ssh cdut-seis`。按用户要求暂时统一使用现有管理员：腾讯云 `ubuntu`（可 sudo）、学校 `root`。每人使用自己的密钥；共享账号无法完整区分操作人员，具有管理员权限。

## 连接路径

电脑 → 腾讯云 SSH 22（ubuntu 公钥认证）→ 腾讯云 127.0.0.1:18083 → frp 双向 TLS → 学校 127.0.0.1:22（root 公钥认证）。学校 SSH 私钥留在电脑，不上传腾讯云，不开启 agent 转发。

- 腾讯云 `frps.toml` 增加 allowPorts 18083；所有转发仍只绑定 127.0.0.1。7000 的主机防火墙仍只允许学校 202.115.129.74。
- `/etc/frp/ingress.nft` 新增 `iifname != "lo" tcp dport 18083 counter drop`；现有 `frp-ingress.service` 随开机加载。不需要在云控制台放行 18083。
- 学校独立配置 `/etc/frp/frpc-ssh.toml`、服务 `frpc-ssh.service`，使用现有 frp 用户及凭据，开机启动、失败重启，内存上限 96M、CPU 配额 20%。不修改原有三条 App/网站代理。
- 学校 sshd 对来源 127.0.0.1、::1 强制 `AuthenticationMethods publickey`，禁用密码和键盘交互，root 仅允许公钥。保留原有校内直连作为回退；这不是对全局密码登录的加固。
- 当前 Mac 已验证登录、命令正常退出、SCP 下载、无公钥时拒绝认证；原三条 HTTP 健康检查均 200。外部尝试 18083 未取得 SSH 响应，服务器侧确认仅 loopback 监听并有额外拦截。尚未在用户手机热点上实测本次快捷配置。

## 当前 Mac

在终端执行：

```sh
ssh cdut-seis
scp ./example.zip cdut-seis:/tmp/
```

`~/.ssh/config` 已添加下面两个专用 Host 条目。原有密钥不变，未修改其他连接配置。

```sshconfig
Host cdut-seis-jump
    HostName 162.14.113.163
    User ubuntu
    IdentityFile ~/.ssh/deepseek_earth_1.pem
    IdentitiesOnly yes
    ForwardAgent no
    StrictHostKeyChecking yes

Host cdut-seis
    HostName 127.0.0.1
    Port 18083
    User root
    IdentityFile ~/.ssh/cdutseis-schoolsever
    ProxyJump cdut-seis-jump
    HostKeyAlias 202.115.129.74
    IdentitiesOnly yes
    ForwardAgent no
    StrictHostKeyChecking yes
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

## 其他同事 / Windows

同事电脑需有 OpenSSH 客户端及自己的密钥，管理员分别把公钥登记到腾讯云 ubuntu、学校 root；可以每台服务器一对密钥，也可同一公钥登记两端。不要复制别人的私钥或整个 config，不需要在电脑安装 frp、Docker。

Mac 配置在 `~/.ssh/config`，Windows 在 `%USERPROFILE%\.ssh\config`（无 `.txt` 后缀），PowerShell 同样运行 `ssh cdut-seis`。在已有 config 的通用 `Host *` 规则前添加这两个专用条目，并将 IdentityFile 改为本人密钥路径；不要覆盖原文件或重用已有同名 Host。Windows 私钥访问权限只给本人及必要的系统管理主体。

先由管理员核对并登记主机身份，再保留 `StrictHostKeyChecking yes` 使用；不要通过关闭校验解决首次连接错误。已核实的 ED25519 主机指纹：

- 腾讯云：`SHA256:3NZXI+O1uR1g/lG77KdUZzTAvWbb1TELaGvZE36AgLs`
- 学校：`SHA256:qBjeoojvhWSCalkJ+cNPb08D4rb2Ne0acUb8/3cCHMc`

离职或撤销访问时移除对应公钥；共享账号的其他人仍有权限重新添加公钥。需要可靠审计和撤权时应改成独立账号。

## 维护与回退

本次变更前备份在两端 `/var/backups/cdut-seis/20261105-admin-ssh/`，仅管理员访问。学校原 sshd_config 与 frpc 配置、腾讯云原 frps 与防火墙配置均有备份。

- 仅停止新 SSH 通道：学校执行 `systemctl disable --now frpc-ssh`，原 App 和网站通道继续运行。校内直连学校 SSH 保留。
- 要撤回 sshd 规则，先通过校内直连登录，核对变更后恢复该 Match 块，执行 `sshd -t` 后平滑重载；不要覆盖其他人后续修改。
- 要移除腾讯云 allowPorts 18083，验证配置后需重启 frps，原通道会短暂重连。仅停用 SSH 无需做这一步。防火墙的 18083 拦截可保留。
- 故障先检查学校 `systemctl status frpc-ssh`、腾讯云 `sudo systemctl status frps frp-ingress`。日志可用 `journalctl -u frpc-ssh`；不要把含凭据的配置发进聊天或仓库。
- 当前学校 SSH 版本会让较新的 Mac 客户端提示未使用后量子密钥交换，普通 SSH 加密与身份校验仍启用。此任务未升级系统 OpenSSH；后续可安排维护升级。

参考：[frp SSH 转发](https://gofrp.org/en/docs/examples/ssh/)、[OpenSSH ProxyJump](https://man.openbsd.org/ssh_config#ProxyJump)。

## 2026-11-05 三位同事接入

用户提供腾讯云截图：`deepseek_earth_1` 为本人，`deepseek_earth_xdd`、`deepseek_earth_ljf`、`deepseek_earth_LiLe` 为同事，四把均绑定同一实例 ubuntu。

实际核实腾讯云恰有四把不同公钥，以本机现有私钥导出公钥识别本人密钥，排除后将其余三把原公钥追加到学校 `/root/.ssh/authorized_keys`；未修改腾讯云公钥或移除学校原有 ED25519 公钥。学校原文件备份于 `/var/backups/cdut-seis/20261105-team-keys/authorized_keys`，仅管理员可访问，更新无需重启 sshd。

两端均已核对三把同事公钥存在、各自总数为四把；原管理员通过 `ssh cdut-seis` 登录仍正常，密码认证仍关闭，RSA SHA-2 认证受学校 sshd 支持。App 与官网健康检查均 200。已为三个私钥文件名生成独立客户端配置片段并验证语法；未持有同事私钥，三人实际登录尚需各自电脑验证。

腾讯云 authorized_keys 仅保留内部 `skey-*` 标识，未凭顺序猜测公钥指纹与同事姓名的对应关系。以后撤销某一位权限，先用他持有的对应公钥指纹准确识别，再从两端删除该公钥。

## 2026-11-05 两位新同事接入

用户新增 `deepseek_earth_blj.pem`、`deepseek_earth_qlh.pem`。腾讯云 ubuntu 当前有六把公钥；排除本人及学校已有公钥后，准确识别出两把新增 RSA 公钥，追加至学校 root。两把指纹分别为 `SHA256:dVd00UHM74VY30qnr66gsX/pi8jDLw5DDP7EJ8h7onQ`、`SHA256:YEBh9HyG3ff8aYfv109Se0WbYBOK3OIzDRv8IwoQKoE`；云端只有内部 skey 标识，未猜测其与姓名的对应顺序。

学校修改前备份为 `/var/backups/cdut-seis/20261105-team-blj-qlh/authorized_keys.before`，目录 700、文件 600。写入前按原始字节校验文件未被其他会话修改，通过临时文件原子替换；确认原文件全部字节（含已有 Windows 换行）保持不变，旧成员授权全部保留。未修改腾讯云授权、sshd 配置或 frp，也未重启服务。

已验证原管理员仍可通过 `ssh cdut-seis` 登录，SSH 隧道 active、授权文件 root:root 600，loopback 入口仍只允许公钥认证。为 blj / qlh 分别生成并检查客户端配置；未持有其私钥，二人实际登录需各自在电脑验证。

## 2026-11-06 wrq 接入

用户新增腾讯云密钥 `deepseek_earth_wrq`。核实腾讯云 ubuntu 当前七把公钥，排除本人与学校已有授权后仅有一把新增公钥：`skey-9tr03s45`，指纹 `SHA256:mWZF+zxZaIghauV1nMF7blflol6gphYCAGyA6Wc9dhg`。已将此公钥追加至学校 root；未读取同事私钥。

修改前按原始字节哈希确认授权文件未改变，备份于 `/var/backups/cdut-seis/20261106-team-wrq/authorized_keys.before`；在文件锁内原子替换，验证原有文件内容全部保留。当前授权文件权限 root:root 600，原管理员 SSH 登录正常、frpc-ssh active，loopback 入口仍仅允许公钥认证。未修改防火墙、sshd、frp 或重启服务。

已生成并校验 wrq 专用 SSH 配置：腾讯云 ubuntu、学校 root，私钥路径 `~/.ssh/deepseek_earth_wrq.pem`；同事仍需在自己的电脑执行首次实际登录验证。
