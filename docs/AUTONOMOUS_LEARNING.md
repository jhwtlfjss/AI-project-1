# Autonomous Learning

这个工程的 Lv3 自主学习由三个部分组成：

1. `configs/learning_sources.json`
   - 你允许它学习的主题、关键词和来源。
   - 支持 `url`、`rss`/`atom`、`wikipedia`。

2. `scripts/autolearn.py`
   - 按配置联网读取资料。
   - 抽取和主题相关的句子。
   - 写入 `data/knowledge.jsonl`。
   - 不修改模型权重。

3. 聊天端
   - `chat_cli.py` 和 `serve_lan.py` 会自动读取 `data/knowledge.jsonl`。
   - 每次你说话时，会检索相关笔记，作为本地知识上下文。

## 手动跑一次

```powershell
python scripts/autolearn.py --force
```

## 没有本地知识库时

你不需要提前准备任何本地知识库。`data/knowledge.jsonl` 会由自主学习、实时网络查询、地址和天气工具自动生成。

正常推荐命令：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

如果你完全不想使用这个缓存，可以只开实时网络模式：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web --no-knowledge-cache
```

或者 CLI：

```powershell
python scripts/chat_cli.py --checkpoint runs/tiny-lover/ckpt.pt --live-web --no-knowledge-cache
```

这种模式下，它只依赖：

- `memory.json` 里的本地对话记忆
- 当次联网查询结果

注意：如果完全不保存知识缓存，它可以“实时查”，但不能在重启后保留自己学到的网络资料。真正的长期 Lv3 学习至少需要 `memory.json` 或 `data/knowledge.jsonl` 这样的本地保存位置。

## 实时地址和天气

配置文件：

```text
configs/realtime_data.json
```

支持低频个人使用的公开接口：

- OpenStreetMap Nominatim: 地点转地址/坐标、坐标反查地址
- Open-Meteo: 当前天气

示例：

```text
东京站地址在哪里？
东京站天气怎么样？
35.6811505, 139.7659765 这个位置是哪？
```

查询结果会写入 `data/knowledge.jsonl`，除非你启动时使用 `--no-knowledge-cache`。

## 长期后台运行

```powershell
python scripts/autolearn.py --daemon --sleep-minutes 30
```

脚本每 30 分钟醒来检查一次；是否真正学习由
`learning_interval_minutes` 控制，默认是 720 分钟。

## 注册 Windows 计划任务

在 PowerShell 里运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_autolearn_task.ps1 -IntervalMinutes 720
```

如果你的 Python 不在 PATH，可以指定：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_autolearn_task.ps1 -Python "C:\path\to\python.exe"
```

## 添加你关心的主题

在 `configs/learning_sources.json` 的 `topics` 里添加：

```json
{
  "name": "my_interests",
  "enabled": true,
  "keywords": ["关键词1", "keyword2", "言葉"],
  "sources": [
    {"type": "rss", "url": "https://example.com/feed.xml"},
    {"type": "url", "url": "https://example.com/article"},
    {"type": "wikipedia", "lang": "ja", "query": "人工知能"}
  ]
}
```

## 安全边界

- 它会自动学习资料，但只写入本地知识库。
- 它不会自动重训模型权重。
- 可以用 `allowed_domains` 限制只访问指定域名。
- 可以用 `blocked_domains` 禁止访问指定域名。
- 手机聊天服务仍建议只开放在家庭局域网。
