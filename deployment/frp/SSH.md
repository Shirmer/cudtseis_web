# SSH 跳板通用示例

以下全部为示例值。正式入口、用户名、本人密钥文件名及服务器主机指纹，请通过团队内部渠道向管理员获取。

连接路径：电脑 → SSH 跳板 → 跳板本地转发端口 → 目标服务器 SSH。

## 客户端配置

Mac / Linux 使用 `~/.ssh/config`；Windows OpenSSH 使用 `%USERPROFILE%\.ssh\config`。将专用条目放在通用 `Host *` 前，不覆盖其他连接。

```sshconfig
Host example-jump
    HostName 203.0.113.10
    User developer
    IdentityFile ~/.ssh/example_ed25519
    IdentitiesOnly yes
    ForwardAgent no
    StrictHostKeyChecking ask

Host example-target
    HostName 127.0.0.1
    Port 22022
    User developer
    IdentityFile ~/.ssh/example_ed25519
    ProxyJump example-jump
    HostKeyAlias example-target-host
    IdentitiesOnly yes
    ForwardAgent no
    StrictHostKeyChecking ask
    ServerAliveInterval 30
    ServerAliveCountMax 3
```

`example_ed25519` 不是随仓库分发的文件，每位成员应使用自己的密钥。首次连接时通过可信的内部渠道核对主机指纹，确认一致后接受；不要关闭主机身份校验。

在终端或 PowerShell 运行 `ssh example-target`。电脑无需安装 frp。

## 管理要求

- 管理员登记成员公钥，成员自行保管私钥；公钥登记列表和访问权限记录不公开发布。
- 目标账号权限按实际工作分配；退出团队时撤销对应授权。
- 隧道目标使用公钥认证，不开放新的公网 SSH 转发端口。
- 私钥权限仅限本人和必要管理主体。

参考：[OpenSSH ProxyJump](https://man.openbsd.org/ssh_config#ProxyJump)。
