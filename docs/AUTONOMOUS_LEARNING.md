# Autonomous Learning

这个工程里的 Lv3 自主学习分成两层：先学到本地知识库，再由你决定是否把知识库变成训练资料。

第一层是安全的默认行为：

```text
网络资料
  -> scripts/autolearn.py
  -> data/knowledge.jsonl
  -> 聊天时检索引用
```

第二层会影响模型权重，需要你主动运行：

```text
data/knowledge.jsonl
  -> scripts/knowledge_to_training.py
  -> data/raw/learned_web_corpus.jsonl
  -> scripts/prepare_data.py
  -> scripts/train.py
  -> runs/tiny-lover/ckpt.pt
```

也就是说，它可以自己联网积累知识，但不会偷偷重训模型。真正“变成她的一部分”之前，需要你明确执行训练步骤。

## 手动学习一次

```powershell
python scripts/autolearn.py --force
```

这个命令会按 `configs/learning_sources.json` 读取允许的来源，包括 `url`、`rss`/`atom` 和 `wikipedia`。结果会写进：

```text
data/knowledge.jsonl
```

如果你没有本地知识库也没关系，这个文件会自动创建。

## 从网络知识生成训练资料

当 `data/knowledge.jsonl` 里已经有内容后，运行：

```powershell
python scripts/knowledge_to_training.py --knowledge data/knowledge.jsonl --out data/raw/learned_web_corpus.jsonl
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
```

默认会生成两类训练记录：

- 资料摘要语料，让模型接触标题、主题、来源和摘要。
- 简单问答语料，让模型学习用更像陪伴聊天的方式解释资料。

然后再训练：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json
```

如果是继续训练已有模型：

```powershell
python scripts/train.py --config configs/tiny_nvidia.json --init-from runs\tiny-lover\ckpt.pt
```

## 一键准备网络训练资料

Windows 下可以直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_from_web.ps1
```

它会自动执行：

```text
autolearn
knowledge_to_training
prepare_data
```

如果想准备完数据就立刻训练：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_from_web.ps1 -Train
```

如果 `python` 不在 PATH：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\bootstrap_from_web.ps1 -Python "C:\path\to\python.exe"
```

## 聊天时实时联网

Hub 启动时加 `--live-web`，聊天里出现“查一下、搜索、最新、ニュース、調べて、search、latest”等触发词，或直接发送 URL，就会尝试联网。

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web
```

实时查询结果会写入 `data/knowledge.jsonl`，除非启动时使用：

```powershell
python scripts/serve_lan.py --checkpoint runs/tiny-lover/ckpt.pt --host 0.0.0.0 --port 8765 --live-web --no-knowledge-cache
```

不保存知识缓存时，它可以实时查，但重启后不会保留这些网络资料。

## 实时地址和天气

配置文件：

```text
configs/realtime_data.json
```

当前支持低频个人使用的公开接口：

- OpenStreetMap Nominatim：地点转地址、坐标转地址。
- Open-Meteo：当前天气。

示例：

```text
东京站地址在哪里？
东京站天气怎么样？
35.6811505, 139.7659765 这个位置是哪？
```

查询结果同样会写入 `data/knowledge.jsonl`，除非使用 `--no-knowledge-cache`。

## 长期后台运行

```powershell
python scripts/autolearn.py --daemon --sleep-minutes 30
```

脚本每 30 分钟醒来检查一次；是否真正学习由 `learning_interval_minutes` 控制，默认是 720 分钟。

也可以注册 Windows 计划任务：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_autolearn_task.ps1 -IntervalMinutes 720
```

如果 Python 不在 PATH：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_autolearn_task.ps1 -Python "C:\path\to\python.exe"
```

## 添加学习主题

编辑 `configs/learning_sources.json` 的 `topics`：

```json
{
  "name": "my_interests",
  "enabled": true,
  "keywords": ["关键词", "keyword2", "言葉"],
  "sources": [
    {"type": "rss", "url": "https://example.com/feed.xml"},
    {"type": "url", "url": "https://example.com/article"},
    {"type": "wikipedia", "lang": "ja", "query": "人工知能"}
  ]
}
```

## 安全边界

- 自主学习默认只写入本地知识库，不自动重训模型。
- 只有你运行 `knowledge_to_training.py` 和 `train.py` 后，网络知识才会进入模型权重。
- 可以用 `allowed_domains` 限制只访问指定域名。
- 可以用 `blocked_domains` 禁止访问指定域名。
- 网络内容可能有版权、噪声或错误；严格自有路线应优先使用你自己写的、授权的或明确可用的资料。
- 手机聊天服务仍建议只开放在私有网络、VPN 或你自己配置的 HTTPS 直连里。
