# Main Device Hub

你可以先不搭建外部服务器，而是把自己的主设备当作私人中转中枢。

这里的“中转”不是第三方转发，而是：

```text
手机 / 笔记本 / 桌面客户端
  -> 连接你的主设备 Hub
  -> 主设备运行模型
  -> 主设备保存 memory.json
  -> 主设备保存 data/knowledge.jsonl
  -> 主设备调用实时网络、地址和天气工具
```

也就是说，主设备就是这个 AI 的家。

## 适合的阶段

这个模式适合现在：

- 不急着搭公网服务器。
- 不想依赖第三方隧道。
- 想先把模型、记忆、知识库、客户端协议稳定下来。
- 主要在家里、宿舍、办公室内网，或者后续自己配置公网直连。

## Hub 启动

调试时可以先不加载模型：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_hub.ps1 -NoModel
```

训练好模型后：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_hub.ps1 -Checkpoint runs\tiny-lover\ckpt.pt
```

如果想用 HTTPS：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_hub.ps1 -Checkpoint runs\tiny-lover\ckpt.pt -Https
```

Hub 会保存：

```text
data/hub_profile.json
data/server_token.txt
memory.json
data/knowledge.jsonl
```

## 客户端配对

Hub 启动过一次后，生成客户端配置：

```powershell
python scripts/pair_client.py --port 8765
```

这会输出并保存：

```text
data/client_profile.json
```

里面包含：

- Hub 地址
- token
- hub_id
- hub_name

你可以把其中的 `server` 和 `token` 填到桌面客户端里。

## 桌面客户端

```powershell
python scripts/desktop_client.py
```

填写：

```text
Server: http://主设备IP:8765
Token: data/server_token.txt 里的内容
Client: 这台客户端设备的名字
```

如果 Hub 用自签 HTTPS，勾选：

```text
Self-signed HTTPS
```

## 命令行客户端

```powershell
python scripts/client_cli.py --server http://主设备IP:8765 --token 你的token --client-id 我的笔记本
```

## 和“外面也能用”的关系

主设备 Hub 是核心。你在外面要访问它时，仍然需要一种网络入口：

```text
客户端 -> 你的公网 IP/域名 -> 路由器端口转发 -> 主设备 Hub
```

如果没有公网 IP 或入站 IPv6，外面设备无法直接找到你的主设备。这个限制来自网络，不是客户端或模型代码。

现在先把 Hub 做好是对的：以后不管你选择公网直连、自己的中转服务器、还是只在局域网用，客户端协议都不用推倒重来。

