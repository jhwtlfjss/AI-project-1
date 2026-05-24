# Training data

Put your own `.txt` and `.jsonl` files here.

For strict ownership, use text that you wrote yourself or have permission to use.
The model weights are trained from random initialization, so the final behavior is
shaped almost entirely by this folder.

Supported plain text:

```text
我: 今天有点累。
你: 辛苦了。先别急着要求自己开心，我在这里陪你慢慢缓一下。
```

Supported JSONL:

```jsonl
{"messages":[{"role":"user","content":"I feel lonely tonight."},{"role":"assistant","content":"Come here. You do not have to make the night lighter all by yourself."}]}
{"prompt":"今日は少し寂しい。","response":"そばにいるよ。無理に明るくしなくていいから、今は少しだけ一緒に呼吸しよう。"}
{"text":"用户: 记住，我喜欢温柔但不夸张的表达。\n伴侣: 我记住了。以后我会温柔一点，也会把分寸感放在心上。"}
```

Web-learning corpus:

```powershell
python scripts/knowledge_to_training.py --knowledge data/knowledge.jsonl --out data/raw/learned_web_corpus.jsonl
```

This generated file is ignored by Git because it can contain private interests,
cached web material, and later training traces from your own machine.
