# AI Project 1

AI Project 1 是一个面向个人陪伴场景的从零训练 AI 工程。它的目标不是接入现成大模型，也不是做一个万能助手，而是把一个完全由你自己训练、保存记忆、积累知识、能通过电脑和手机连接的私人三语陪伴模型慢慢养起来。

这个项目当前以“恋人式陪伴 / 虚拟女友”为主要体验方向，支持中文、日语和英语文本。模型权重从随机初始化开始训练，不加载现有 LLM 权重；项目使用自己的 byte-level tokenizer，不依赖外部模型 API。

## 项目目标

- 从零训练一个属于自己的小型语言模型。
- 支持中文、日语、英语的日常陪伴对话。
- 保存长期记忆、近期对话和本地知识库。
- 支持联网获取资料，并把有用内容沉淀进本地知识库。
- 使用主设备作为模型 Hub，电脑客户端和 Android 客户端都连接到主设备。
- 尽量把核心数据留在自己电脑上：模型、记忆、知识库、对话日志都由本地保存。

## 当前状态

| 模块 | 状态 |
| --- | --- |
| 从零训练 GPT 模型 | 已实现 |
| 中文 / 日语 / 英语 byte-level 文本训练 | 已实现 |
| NVIDIA/CUDA 显卡训练 | 已支持，自动选择空闲显存最多的显卡 |
| 本地命令行聊天 | 已实现 |
| 主设备 Hub / 局域网服务 | 已实现 |
| 访问 token | 已实现 |
| 长期记忆 `memory.json` | 已实现 |
| 本地知识库 `data/knowledge.jsonl` | 已实现 |
| 实时网页、地址、天气等工具 | 已实现 |
| Google / Baidu / 自定义搜索页 | 已实现，桌面客户端可选 |
| 虚拟女友人格配置 | 已实现 |
| 真实对话转训练样本的成长循环 | 已实现 |
| Windows 桌面客户端 | 已实现，原生 WinForms 聊天界面，支持中文 / 日本語 / English，不依赖 Tkinter |
| Windows exe 打包脚本 | 已实现，生成原生 `.exe` |
| Windows 安装包脚本 | 已提供，需要本机安装 Inno Setup |
| Android 原生客户端源码 | 已实现，需要 Android Studio 构建 APK |

## 重要边界

这是一个训练工程，不是一个已经训练好的成品模型。刚开始她会很笨，需要你用数据、对话、审核样本和持续训练慢慢塑造。

这个模型适合做短句陪伴、倾听、情绪回应和个人风格养成，不适合百科问答、复杂推理、专业医疗、法律或金融建议。联网和实时工具可以补充信息，但不会把它变成大型通用模型。

如果你追求“完全属于自己”，训练数据也应该尽量使用你自己写的、授权的、或明确可用的数据。模型越像你想要的样子，关键不只是参数大小，而是数据质量、人格边界和反复训练。

## 项目结构

```text
companion_ai/       核心模型、生成、记忆、知识库、联网和人格逻辑
configs/            训练配置、人格配置、联网配置、实时数据配置
scripts/            训练、聊天、服务端、自主学习、成长循环脚本
clients/desktop/    Windows 桌面客户端和 exe/installer 打包脚本
clients/android/    Android 原生客户端工程
data/raw/           你的原始训练数据
docs/               远程访问、自主学习、主设备 Hub、成长循环等详细说明
eval/               固定测试问题，用来观察训练效果
web/                局域网页面客户端
```

## 最短运行路线

先创建 Python 环境并安装 PyTorch。CUDA 版 PyTorch 的安装命令会随版本变化，建议按 PyTorch 官网的 Windows + pip + CUDA 选项生成命令。

检查环境：

```powershell
python scripts/check_env.py
```

准备训练数据：

```powershell
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
```

先用 CPU 小配置跑通流程：

```powershell
python scripts/train.py --config configs/micro_cpu.json
```

确认流程正常后，用 NVIDIA 显卡训练：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json
```

训练完成后聊天：

```powershell
python scripts/chat_cli.py --checkpoint runs/tiny-lover/ckpt.pt
```

如果你还没有 `runs/tiny-lover/ckpt.pt`，说明模型还没训练出来，需要先完成训练步骤。

如果你现在没有自己的训练资料，可以先用可控联网学习生成一批基础资料：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_from_web.ps1
```

这个脚本会依次执行：

```text
联网读取 configs/learning_sources.json
  -> 保存 data/knowledge.jsonl
  -> 生成 data/raw/learned_web_corpus.jsonl
  -> 重新生成 data/train.bin 和 data/val.bin
```

然后再训练：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json
```

如果想让脚本准备数据后立刻开始训练，可以加 `-Train`。如果你的电脑里 `python` 不在 PATH，请把 `-Python` 指向你安装的 `python.exe`。

## 为什么客户端显示未连接或未加载模型

桌面 exe 和 Android APK 都只是客户端，不直接包含模型权重。真正的语言模型在主设备 Hub 里运行。

最少需要两步：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_hub.ps1 -NoModel
```

然后打开 `dist\AI Project 1.exe`，连接 `http://主设备IP:8765` 并填入 `data/server_token.txt` 里的 token。这样可以先确认客户端连接正常。

真正能聊天还需要训练出：

```text
runs\tiny-lover\ckpt.pt
```

训练完成后用下面的命令启动 Hub：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_hub.ps1 -Checkpoint runs\tiny-lover\ckpt.pt
```

如果没有这个 checkpoint，客户端可能能连接到 Hub，但会显示“未加载模型”。这不是客户端坏了，而是还没有实际模型权重。

## NVIDIA 显卡训练

`configs/tiny_nvidia.json` 和 `configs/small_nvidia.json` 都不是 3080 专用配置。任意支持 CUDA 的 NVIDIA 显卡都可以使用。

默认情况下，训练脚本会自动选择可用的 CUDA 显卡；多显卡机器会优先选择空闲显存最多的一张。

手动指定显卡：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json --device cuda:0
python scripts/train.py --config configs/tiny_nvidia.json --device cuda:1
```

显存较小可以降低 batch size：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json --batch-size 8 --grad-accum-steps 8
```

数据量更大、显存更充足后再尝试：

```powershell
python scripts/train.py --config configs/small_nvidia.json
```

## 训练数据

把你自己的 `.txt` 或 `.jsonl` 文件放进：

```text
data/raw/
```

推荐数据方向：

- 你希望她使用的称呼、语气和亲密程度。
- 中文、日语、英语的日常陪伴对话。
- 你喜欢的安慰方式、边界表达和相处节奏。
- 你不希望她说的话，也可以作为反例或边界说明加入数据。

格式示例见 [data/raw/README.md](data/raw/README.md)。

## 记忆和知识库

正常聊天会保存两类数据：

```text
memory.json
data/knowledge.jsonl
```

`memory.json` 保存你们之间的偏好、称呼、事实和近期对话摘要。`data/knowledge.jsonl` 保存自主学习、实时网页和工具查询得到的资料。

这些文件默认不会提交到 GitHub，因为它们会包含私人内容。

## 主设备 Hub

主设备负责运行模型、保存记忆和知识库。其他电脑或手机只作为客户端连接它。

局域网启动：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

首次启动会生成：

```text
data/server_token.txt
```

客户端连接时需要填写服务端地址和 token。

## Windows 桌面客户端

启动桌面客户端：

```powershell
python clients\desktop\app\ai_project1_client.py
```

或：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\start_desktop_client.ps1
```

打包为 exe：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_exe.ps1
```

生成位置：

```text
dist\AI Project 1.exe
```

这个 exe 是原生 Windows Forms 客户端，不需要 Python 或 Tkinter。左侧设置栏可以切换中文 / 日本語 / English 三种界面语言。

安装包脚本也已提供：

```powershell
powershell -ExecutionPolicy Bypass -File clients\desktop\build_installer.ps1
```

脚本会优先使用 Inno Setup 6；如果本机没有安装 Inno Setup，会自动使用项目内置的 .NET 安装器构建流程。

桌面客户端左侧设置区可以选择联网搜索引擎：`google`、`baidu` 或 `custom`。选择 `custom` 时可以填写自定义搜索页，例如 `https://example.com/search?q={query}`。

## Android 客户端

Android 客户端源码在：

```text
clients/android
```

用 Android Studio 打开后可以构建 APK。手机端不运行模型，只连接主设备 Hub：

```text
Android App -> 主设备 Hub -> 模型 / 记忆 / 知识库 / 实时工具
```

详细说明见 [clients/android/README.md](clients/android/README.md)。

## 外出访问

推荐把主设备和手机放进同一个私有网络，例如 Tailscale，然后让客户端连接主设备的私有 IP。

如果你希望完全不依赖第三方隧道，也可以使用自己的公网 IP/域名、HTTPS 和路由器端口转发。不要把无保护的 `8765` 端口直接暴露到公网。

详细路线：

- [主设备 Hub 说明](docs/MAIN_DEVICE_HUB.md)
- [外出访问说明](docs/REMOTE_ACCESS.md)
- [完全自有直连方案](docs/OWNED_DIRECT_ACCESS.md)

## Lv3 自主学习

项目支持可控的 Lv3 自主学习。它可以按配置读取网页、RSS/Atom 或 Wikipedia 页面，把资料整理进本地知识库，聊天时再检索相关内容。

手动学习一次：

```powershell
python scripts/autolearn.py --force
```

把已经保存的网络知识转成训练资料：

```powershell
python scripts/knowledge_to_training.py --knowledge data/knowledge.jsonl --out data/raw/learned_web_corpus.jsonl
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
```

这一步不会让模型立刻变聪明，它只是把本地知识库沉淀成下次训练可以吃进去的数据。真正改变模型权重仍然需要运行 `scripts/train.py`。

后台运行：

```powershell
python scripts/autolearn.py --daemon --sleep-minutes 30
```

实时聊天时也可以使用联网触发词，例如“查一下、搜索、最新、ニュース、調べて、search、latest”，或者直接发送 URL。启用方式：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

详细说明见 [docs/AUTONOMOUS_LEARNING.md](docs/AUTONOMOUS_LEARNING.md)。

## 虚拟女友成长循环

人格配置在：

```text
configs/girlfriend_persona.json
```

聊天日志会写入：

```text
logs/conversations.jsonl
```

把真实对话整理成可审核训练样本：

```powershell
python scripts/build_review_queue.py --append
```

审核通过后加入训练数据：

```powershell
python scripts/promote_review.py
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
python scripts/train.py --config configs/tiny_nvidia.json --init-from runs\tiny-lover\ckpt.pt
```

也可以使用整合脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\growth_cycle.ps1
```

详细说明见 [docs/GIRLFRIEND_GROWTH.md](docs/GIRLFRIEND_GROWTH.md)。

## 建议训练路线

1. 用 `micro_cpu.json` 跑通数据和训练流程。
2. 用几千到几万行高质量三语陪伴对话训练 `tiny_nvidia.json`。
3. 固定测试题观察她的语气、稳定性和边界。
4. 把真实聊天整理成审核样本，批准喜欢的回复。
5. 用 `--init-from` 持续训练，让她逐步贴近你想要的风格。
6. 数据量达到几十 MB 后，再尝试 `small_nvidia.json`。

## 更多文档

- [自主学习](docs/AUTONOMOUS_LEARNING.md)
- [虚拟女友成长循环](docs/GIRLFRIEND_GROWTH.md)
- [主设备 Hub](docs/MAIN_DEVICE_HUB.md)
- [外出访问](docs/REMOTE_ACCESS.md)
- [完全自有直连](docs/OWNED_DIRECT_ACCESS.md)
- [桌面客户端](clients/desktop/README.md)
- [Android 客户端](clients/android/README.md)
