# Android Client

这是 AI Project 1 的原生 Android 客户端工程。它不运行模型，只连接你的主设备 Hub：

```text
Android APK
  -> /api/status
  -> /api/chat
  -> 主设备 Hub
  -> 模型、记忆、知识库、实时工具
```

## 功能

- 保存 Server URL
- 保存访问 token
- 设置 client id
- 支持 HTTP
- 支持 HTTPS
- 支持自签 HTTPS 证书开关
- 支持选择联网搜索引擎：google / baidu / custom
- 支持自定义搜索页 URL
- 使用气泡式聊天界面
- 聊天消息发送到主设备 Hub

## 构建 APK

当前这台机器没有 Android SDK / Java / Gradle，所以我无法在这里直接产出 APK 文件。你可以用 Android Studio 构建：

1. 安装 Android Studio。
2. 打开 `clients/android`。
3. 等待 Gradle Sync 完成。
4. 菜单选择 `Build > Build APK(s)`。
5. APK 位于：

```text
clients/android/app/build/outputs/apk/debug/app-debug.apk
```

如果你的电脑有 Gradle 或 Android Studio 生成了 Gradle Wrapper，也可以运行：

```powershell
powershell -ExecutionPolicy Bypass -File clients\android\build_apk.ps1
```

## 连接主设备

在 App 中填写：

```text
Server: http://主设备IP:8765
Token: data/server_token.txt 里的内容
Client: android-phone
```

如果主设备使用自签 HTTPS：

```text
Server: https://主设备IP或域名:8765
Trust self-signed HTTPS: on
```

公网直连时请优先使用 HTTPS。HTTP 适合局域网调试。
