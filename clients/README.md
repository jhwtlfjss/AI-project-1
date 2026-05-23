# Clients

AI Project 1 的客户端分两类：

```text
clients/desktop  电脑端客户端入口
clients/android  安卓 APK 工程
```

所有客户端都只连接主设备 Hub。模型权重、记忆、知识库和实时工具都保存在主设备上。

## API

客户端使用同一套 HTTP API：

```http
GET /api/status
POST /api/chat
X-Companion-Token: <token>
X-Companion-Client: <client-id>
```

`POST /api/chat` body：

```json
{"message":"今天有点累。"}
```

## 安全

- 局域网调试可以使用 HTTP。
- 外网直连建议使用 HTTPS。
- 自签 HTTPS 只适合你自己的设备。
- 不要把 `data/server_token.txt` 发给别人。

