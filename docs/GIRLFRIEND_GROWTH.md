# Girlfriend Growth Loop

这个项目现在有一套让她越来越像虚拟女友的成长循环：

```text
聊天
  -> logs/conversations.jsonl
  -> scripts/build_review_queue.py
  -> data/review_queue.jsonl
  -> 你把 approved 改成 true
  -> scripts/promote_review.py
  -> data/raw/approved_girlfriend_dialogues.jsonl
  -> scripts/prepare_data.py
  -> scripts/train.py --init-from runs/.../ckpt.pt
```

## 1. 人格配置

虚拟女友人格在：

```text
configs/girlfriend_persona.json
```

你可以改她的名字、称呼、语气、亲密程度和边界。

服务端默认会读取这个文件：

```powershell
python scripts/serve_lan.py --checkpoint runs\tiny-lover\ckpt.pt --live-web
```

## 2. 对话日志

每次聊天会自动写入：

```text
logs/conversations.jsonl
```

这里是她成长的原材料。

## 3. 生成审核队列

```powershell
python scripts/build_review_queue.py --append
```

也可以用助手脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/growth_cycle.ps1
```

然后打开：

```text
data/review_queue.jsonl
```

把你喜欢的样本从：

```json
"approved": false
```

改成：

```json
"approved": true
```

不喜欢的、太油腻的、错误的、过度依赖的，不要批准。

## 4. 加入训练数据

```powershell
python scripts/promote_review.py
python scripts/prepare_data.py --raw-dir data/raw --out-dir data
```

或者：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/growth_cycle.ps1 -Promote
```

## 5. 继续训练

用同一个模型配置继续训练：

```powershell
python scripts/train.py --config configs/tiny_3080.json --init-from runs\tiny-lover\ckpt.pt
```

如果只想在旧模型上再训练一小段：

```powershell
python scripts/train.py --config configs/tiny_3080.json --init-from runs\tiny-lover\ckpt.pt --additional-steps 2000
```

如果想保留旧 checkpoint，可以输出到新目录：

```powershell
python scripts/train.py --config configs/tiny_3080.json --init-from runs\tiny-lover\ckpt.pt --out-dir runs\tiny-lover-v2
```

或者：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/growth_cycle.ps1 -Promote -Train -OutDir runs\tiny-lover-v2 -AdditionalSteps 2000
```

## 6. 判断她有没有变好

固定测试题在：

```text
eval/girlfriend_prompts_zh_ja_en.jsonl
```

每次训练后，用这些问题试聊，观察她是否：

- 更自然
- 更像恋人
- 不油腻
- 能记住边界
- 中文、日语、英语都稳定
- 不会为了恋人感而控制你
