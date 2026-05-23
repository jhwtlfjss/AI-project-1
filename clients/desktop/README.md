# Desktop Client

电脑端正式可执行客户端是中文原生 Windows Forms 程序，不需要浏览器，也不依赖 Python/Tkinter。界面使用左侧设置栏、顶部会话栏、圆角消息气泡和中文状态文案。源码在：

```text
clients/desktop/winforms/AiProject1Client.cs
```

如果只是开发调试，也可以运行旧的 Python/Tkinter 入口；但正式 exe 不再使用它。

构建正式 exe：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1
```

生成位置：

```text
dist\AI Project 1.exe
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

## 联网搜索设置

桌面客户端左侧设置区可以控制本次聊天请求的联网搜索：

- Live web search: 是否允许这台客户端触发联网搜索。
- Auto lookup triggers: 是否按“查一下、搜索、最新、search、latest”等触发词自动搜索。
- Engine: 支持 `google`、`baidu`、`custom`。
- Custom URL: 当 Engine 为 `custom` 时使用，例如 `https://example.com/search?q={query}`。

这些设置会随 `POST /api/chat` 一起发给主设备 Hub，不需要重启客户端。

## 安装包

如果你想要安装包，先构建 exe，然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_installer.ps1
```

脚本会优先使用 Inno Setup 6；如果本机没有安装 Inno Setup，会自动使用项目内置的 .NET 安装器构建流程。

安装包输出：

```text
dist\AIProject1Setup.exe
```
