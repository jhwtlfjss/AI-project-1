# Fully Owned Direct Access

如果你不想依赖 Tailscale、Cloudflare、Telegram、Discord 或任何第三方中转，可以使用直连模式：

```text
外面的客户端
  -> 你的公网 IP 或你自己的域名
  -> 家里路由器端口转发
  -> 家里电脑上的 My Companion AI 服务端
```

这条路线的代码、模型、记忆、知识库和客户端都在你自己手里。它唯一依赖的是互联网本身、你的 ISP、路由器和操作系统网络栈。

## 必要条件

1. 你家的网络必须有真实公网 IPv4 或可入站访问的 IPv6。
2. 如果是 IPv4，路由器需要做端口转发，例如 `WAN:8765 -> 电脑LAN_IP:8765`。
3. Windows 防火墙需要允许入站 TCP `8765`。
4. 客户端连接你的公网 IP 或自己的域名。

如果 ISP 给你的是 CGNAT，外面无法直接连进你家网络。你需要向 ISP 申请公网 IP，或者使用你自己控制的服务器做中转。没有公网入口时，纯代码无法让外网设备直接找到你的家里电脑。

## 启动服务端

HTTP 直连：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

首次启动会自动生成访问令牌：

```text
data/server_token.txt
```

客户端必须带这个 token。

## HTTPS

公网使用时建议启用 HTTPS，否则 token 会以明文经过网络。

生成自签证书：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/generate_self_signed_cert.ps1 -DnsName my-companion-ai.local
```

启动 HTTPS 服务：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web --ssl-cert data/certs/server.crt.pem --ssl-key data/certs/server.key.pem
```

自签证书不会被普通系统自动信任，所以你自己的客户端需要允许 self-signed HTTPS。

桌面客户端里勾选：

```text
Self-signed HTTPS
```

命令行客户端：

```powershell
python scripts/client_cli.py --server https://你的公网IP或域名:8765 --token 你的token --insecure
```

## 客户端

桌面客户端：

```powershell
python scripts/desktop_client.py
```

命令行客户端：

```powershell
python scripts/client_cli.py --server http://你的公网IP或域名:8765 --token 你的token
```

## 网络诊断

```powershell
python scripts/network_probe.py --host 127.0.0.1 --port 8765
```

这个脚本只检查本机和局域网信息。公网 IP、CGNAT 和端口转发状态需要在你的路由器或 ISP 侧确认。

## 安全建议

- 不要使用 `--no-auth` 暴露到公网。
- token 要足够长，默认自动生成的就可以。
- 能用 HTTPS 就用 HTTPS。
- 如果你只给自己使用，路由器可以限制来源 IP 或只开放临时端口。
- 定期备份 `memory.json` 和 `data/knowledge.jsonl`。

