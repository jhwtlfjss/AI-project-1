# Desktop Client

电脑端正式可执行客户端是原生 Windows Forms 程序，不需要浏览器，也不依赖 Python/Tkinter。界面使用左侧设置栏、顶部会话栏、圆角消息气泡，并支持中文 / 日本語 / English 三种界面语言。源码在：

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

电脑端会保存连接配置。默认连接 `127.0.0.1` 时，它会自动启动本机 Hub，并使用本机的记忆、知识库和模型权重。

## 如果显示未连接

这个 exe 是聊天界面，但现在可以自动启动本机 Hub。打开软件后，如果左侧勾选了“打开软件时自动启动本机 Hub”，并且服务地址是 `http://127.0.0.1:8765` 或 `http://localhost:8765`，它会自动在后台启动：

```text
python scripts\serve_lan.py --host 0.0.0.0 --port 8765 --live-web
```

然后自动读取 `data/server_token.txt` 并连接。

真正聊天需要先训练出：

```text
runs\tiny-lover\ckpt.pt
```

然后启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_hub.ps1 -Checkpoint runs\tiny-lover\ckpt.pt
```

客户端里填写：

```text
Server: http://主设备IP:8765
Token: data/server_token.txt 里的内容
```

如果没有 `ckpt.pt`，说明现在还只有软件框架和客户端，实际语言模型还没有训练出来。

如果你想连接别的电脑或外出访问家里的主设备，请取消勾选“打开软件时自动启动本机 Hub”，再填写远程地址和 token。

## 打包内容

安装包会把下面这些内容放进同一个安装目录：

```text
AI Project 1.exe
companion_ai/
scripts/
configs/
web/
docs/
data/raw/
assets/
```

如果构建安装包时本机已有 `runs\tiny-lover\ckpt.pt`，也会一起打进去。Python/PyTorch/CUDA 仍然使用系统已安装环境，不会塞进 exe 本体。

## 语言设置

左侧设置栏提供 `界面语言 / 表示言語 / Interface language` 选项：

- 中文
- 日本語
- English

切换后会自动保存，并刷新主要界面文案。

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
