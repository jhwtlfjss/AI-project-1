# My Companion AI

这是一个从零训练的私人三语恋人陪伴模型工程。它不加载任何现有大模型权重，不使用现成 tokenizer；模型从随机初始化开始学习，支持中文、日语和英语文本。

任意支持 CUDA 的 NVIDIA 显卡都可以用。建议先训练 `tiny_nvidia.json`，稳定后再按显存尝试 `small_nvidia.json`。

## 这个版本的边界

- 它会先很笨，需要数据慢慢养。
- 它适合短句陪伴、倾听、温柔回应，不适合百科、推理或复杂任务。
- 如果你要求“完全属于自己”，训练数据也应该尽量使用你自己写的、授权的、或明确可用的数据。
- 手机连接建议只开在家庭局域网，不要直接暴露到公网。

## 安装

创建 Python 环境后安装 PyTorch。PyTorch 的 CUDA 安装命令会随版本变化，建议使用 PyTorch 官网安装选择器生成 Windows + pip + CUDA 的命令。

安装好后，在项目根目录检查：

```powershell
python scripts/check_env.py
```

## 准备数据

把你自己的训练文本放进：

```text
data/raw/
```

支持 `.txt` 和 `.jsonl`。格式示例见 [data/raw/README.md](data/raw/README.md)。

然后构建训练数据：

```powershell
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
```

## 训练

先跑一个小配置验证：

```powershell
python scripts/train.py --config configs/micro_cpu.json
```

确认流程正常后用 NVIDIA 显卡：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json
```

训练脚本会自动使用可用的 CUDA 显卡；多显卡机器会优先选择空闲显存最多的一张。你也可以手动指定：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json --device cuda:0
python scripts/train.py --config configs/tiny_nvidia.json --device cuda:1
```

如果显存够、数据够多，再尝试：

```powershell
python scripts/train.py --config configs/small_nvidia.json
```

如果显存较小，可以临时降低每步显存占用：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json --batch-size 8 --grad-accum-steps 8
```

## 本地聊天

```powershell
python scripts/chat_cli.py --checkpoint runs/tiny-lover/ckpt.pt
```

正常模式会保存：

- `memory.json`: 你们之间的偏好、称呼、事实和最近对话
- `data/knowledge.jsonl`: 自主学习、实时网络和实时工具查到的资料

如果只是临时调试、不想保存网络资料，可以关闭知识缓存：

```powershell
python scripts/chat_cli.py --checkpoint runs/tiny-lover/ckpt.pt --live-web --no-knowledge-cache
```

## 手机局域网聊天

电脑和手机连同一个 Wi-Fi，然后启动：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765
```

带实时网络、地址和天气工具，并保存到知识库：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

如果只是临时调试、不读取也不写入 `data/knowledge.jsonl`：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web --no-knowledge-cache
```

在手机浏览器打开：

```text
http://你的电脑局域网IP:8765
```

可以用下面命令查看电脑 IP：

```powershell
ipconfig
```

## 外出访问和客户端

现在服务端支持访问令牌，首次启动会自动生成：

```text
data/server_token.txt
```

如果你接受私有网络工具，推荐用 Tailscale 把家里电脑和手机/笔记本放进同一个私有网络，然后从外面连接：

```text
http://家里电脑的Tailscale-IP:8765
```

桌面客户端：

```powershell
python clients\desktop\app\ai_project1_client.py
```

或者：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\start_desktop_client.ps1
```

打包为 Windows 可执行文件：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1 -Python .\.venv\Scripts\python.exe
```

生成后直接运行：

```text
dist\AI Project 1.exe
```

安装包脚本也已提供：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_installer.ps1
```

构建安装包需要本机安装 Inno Setup。

命令行客户端：

```powershell
python scripts/client_cli.py --server http://100.x.y.z:8765 --token 你的token
```

详细说明见 [docs/REMOTE_ACCESS.md](docs/REMOTE_ACCESS.md)。

安卓客户端源码在：

```text
clients/android
```

用 Android Studio 打开后可以构建 APK。详细说明见 [clients/android/README.md](clients/android/README.md)。

如果暂时不搭外部服务器，而是让自己的主设备作为私人中转 Hub：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_hub.ps1 -NoModel
python scripts/pair_client.py --port 8765
python clients\desktop\app\ai_project1_client.py
```

详细说明见 [docs/MAIN_DEVICE_HUB.md](docs/MAIN_DEVICE_HUB.md)。

如果你希望完全不依赖第三方隧道，走你自己的公网 IP/域名 + 路由器端口转发：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

直连方案说明见 [docs/OWNED_DIRECT_ACCESS.md](docs/OWNED_DIRECT_ACCESS.md)。

## Lv3 自主学习

这个工程现在支持可控的 Lv3 自主学习：它可以按你设定的主题联网读取网页、RSS/Atom 或 Wikipedia 页面，整理成 `data/knowledge.jsonl`，聊天时再从本地知识库检索相关内容作为参考。

手动学习一次：

```powershell
python scripts/autolearn.py --force
```

后台守护运行：

```powershell
python scripts/autolearn.py --daemon --sleep-minutes 30
```

注册 Windows 计划任务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_autolearn_task.ps1 -IntervalMinutes 720
```

学习主题和来源在：

```text
configs/learning_sources.json
```

实时网络触发词和缓存开关在：

```text
configs/network_access.json
```

地址、坐标、天气等实时数据工具在：

```text
configs/realtime_data.json
```

详细说明见 [docs/AUTONOMOUS_LEARNING.md](docs/AUTONOMOUS_LEARNING.md)。

如果你不想提前准备本地知识库，可以跳过 `autolearn.py`。只要聊天服务使用 `--live-web`，它会在你提到“查一下、搜索、最新、ニュース、調べて、search、latest”等触发词，或直接发送 URL 时实时联网，并把有用结果写入 `data/knowledge.jsonl`。

地址、坐标、天气等实时数据会自动触发，例如：

```text
东京站地址在哪里？
东京站天气怎么样？
35.6811505, 139.7659765 这个位置是哪？
```

## 建议训练路线

1. 用 `micro_cpu.json` 跑通流程。
2. 用几千到几万行三语陪伴对话训练 `tiny_nvidia.json`。
3. 观察聊天质量，补充它说不好的场景。
4. 数据量达到几十 MB 以后再尝试 `small_nvidia.json`。
5. 不追求它知道全世界，只训练它懂你的语气、节奏、边界和陪伴方式。

## 虚拟女友成长循环

人格配置在：

```text
configs/girlfriend_persona.json
```

聊天会自动保存到：

```text
logs/conversations.jsonl
```

把真实对话整理成可审核训练样本：

```powershell
python scripts/build_review_queue.py --append
```

也可以用助手脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/growth_cycle.ps1
```

你把 `data/review_queue.jsonl` 里喜欢的样本改成 `"approved": true` 后：

```powershell
python scripts/promote_review.py
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
python scripts/train.py --config configs/tiny_nvidia.json --init-from runs\tiny-lover\ckpt.pt
```

详细说明见 [docs/GIRLFRIEND_GROWTH.md](docs/GIRLFRIEND_GROWTH.md)。
