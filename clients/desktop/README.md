# Desktop Client

电脑端客户端使用项目里的 Tkinter 桌面程序，不需要浏览器。

启动：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\start_desktop_client.ps1
```

或者直接：

```powershell
python scripts\desktop_client.py
```

填写：

```text
Server: http://主设备IP:8765
Token: data/server_token.txt 里的内容
Client: 这台电脑的名字
```

如果主设备 Hub 使用自签 HTTPS，勾选：

```text
Self-signed HTTPS
```

电脑端只保存连接配置，不保存模型权重、记忆或知识库。核心数据仍在主设备 Hub 上。

