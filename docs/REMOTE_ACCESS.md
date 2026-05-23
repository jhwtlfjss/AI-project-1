# Remote Access

你可以做真正的客户端，不必只靠网页端。整体结构建议保持这样：

```text
家里电脑 RTX 3080
  - 运行模型服务端
  - 保存 memory.json
  - 保存 data/knowledge.jsonl

外面的设备
  - 桌面客户端 / 命令行客户端 / 未来的手机 App
  - 通过安全通道连接家里电脑
```

不要把 `8765` 端口直接转发到公网。这个服务保存你的对话记忆和知识库，应该放在私有网络或有访问控制的隧道后面。

## 服务端

在家里电脑上启动：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

首次启动会自动生成：

```text
data/server_token.txt
```

客户端需要这个 token。服务端 API 会要求请求带：

```text
X-Companion-Token: 你的token
```

只有临时本地测试才使用：

```powershell
python scripts/serve_lan.py --host 127.0.0.1 --port 8765 --no-auth
```

## 推荐方案 A: Tailscale

这是最适合个人私有 AI 的路线。电脑和手机都加入同一个 Tailscale 私有网络后，即使你在外面，也可以访问家里电脑的 Tailscale IP。

使用方式：

1. 家里电脑安装并登录 Tailscale。
2. 手机或笔记本安装并登录同一个 Tailscale 账号。
3. 在 Tailscale 里找到家里电脑的 `100.x.y.z` 地址或 MagicDNS 名称。
4. 客户端连接：

```text
http://100.x.y.z:8765
```

优点：

- 不需要公网 IP。
- 不需要路由器端口转发。
- 只允许你自己的设备访问。
- 很适合私人模型、记忆和知识库。

## 推荐方案 B: Cloudflare Tunnel

如果你想用类似：

```text
https://my-ai.example.com
```

可以用 Cloudflare Tunnel 把公网域名映射到家里电脑的：

```text
http://127.0.0.1:8765
```

建议同时开启 Cloudflare Access，并保留本项目自己的 `X-Companion-Token`。这相当于两层门锁。

## 桌面客户端

启动：

```powershell
python scripts/desktop_client.py
```

填写：

```text
Server: http://100.x.y.z:8765
Token: data/server_token.txt 里的内容
```

如果使用 Cloudflare Tunnel：

```text
Server: https://my-ai.example.com
```

## 命令行客户端

```powershell
python scripts/client_cli.py --server http://100.x.y.z:8765 --token 你的token
```

也可以用环境变量：

```powershell
$env:COMPANION_CLIENT_TOKEN="你的token"
python scripts/client_cli.py --server http://100.x.y.z:8765
```

## 手机 App

当前工程已经有稳定的客户端 API：

```http
GET /api/status
POST /api/chat
X-Companion-Token: 你的token
```

后续可以用 Flutter、React Native、Swift/Kotlin 做真正手机 App。手机 App 只需要保存三个东西：

- 服务端地址
- token
- 本地 UI 设置

模型、记忆和知识库仍保存在家里电脑上。

