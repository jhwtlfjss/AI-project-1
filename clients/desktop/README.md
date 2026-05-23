# Desktop Client

电脑端客户端使用项目里的 Tkinter 桌面程序，不需要浏览器。新版入口在：

```text
clients/desktop/app/ai_project1_client.py
```

启动：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\start_desktop_client.ps1
```

或者直接：

```powershell
python clients\desktop\app\ai_project1_client.py
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

## 打包为 exe

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1 -InstallPyInstaller
```

生成位置：

```text
dist\AI Project 1.exe
```

如果已经在项目里创建 `.venv` 并安装了 PyInstaller：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1 -Python .\.venv\Scripts\python.exe
```

## 安装包

如果你想要安装包，先构建 exe，再安装 Inno Setup，然后运行：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_installer.ps1
```

安装包输出：

```text
dist\AIProject1Setup.exe
```
