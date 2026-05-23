from __future__ import annotations

import json
import re
from pathlib import Path

from companion_ai.conversation_log import iter_turns


BAD_PATTERNS = [
    "网络查询失败",
    "实时数据查询失败",
    "模型还没有加载",
    "Traceback",
    "error",
]


def build_review_items(log_path: Path, min_assistant_chars: int = 12) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for turn in iter_turns(log_path) or []:
        user = str(turn.get("user", "")).strip()
        assistant = str(turn.get("assistant", "")).strip()
        if not is_good_candidate(user, assistant, min_assistant_chars):
            continue
        key = f"{user}\n{assistant}"
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "approved": False,
                "reason": score_reason(user, assistant),
                "messages": [
                    {"role": "user", "content": user},
                    {"role": "assistant", "content": assistant},
                ],
                "source": {
                    "timestamp": turn.get("timestamp"),
                    "metadata": turn.get("metadata", {}),
                },
            }
        )
    return items


def write_review_queue(items: list[dict], out_path: Path, append: bool = False):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing_keys = set()
    if append and out_path.exists():
        for item in read_jsonl(out_path):
            existing_keys.add(item_key(item))
    mode = "a" if append else "w"
    with out_path.open(mode, encoding="utf-8") as fh:
        for item in items:
            if append and item_key(item) in existing_keys:
                continue
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")


def promote_approved(review_path: Path, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with out_path.open("a", encoding="utf-8") as out:
        for item in read_jsonl(review_path):
            if not item.get("approved", False):
                continue
            messages = item.get("messages", [])
            if len(messages) < 2:
                continue
            out.write(json.dumps({"messages": messages}, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc


def is_good_candidate(user: str, assistant: str, min_assistant_chars: int) -> bool:
    if len(user) < 2 or len(assistant) < min_assistant_chars:
        return False
    if len(user) > 900 or len(assistant) > 1200:
        return False
    haystack = f"{user}\n{assistant}"
    if any(pattern.lower() in haystack.lower() for pattern in BAD_PATTERNS):
        return False
    if looks_like_code_or_log(haystack):
        return False
    return True


def looks_like_code_or_log(text: str) -> bool:
    code_markers = ["```", "def ", "class ", "import ", "Traceback", "Exception:", "{", "}"]
    hits = sum(1 for marker in code_markers if marker in text)
    return hits >= 3


def score_reason(user: str, assistant: str) -> str:
    combined = f"{user}\n{assistant}"
    if any(word in combined for word in ["喜欢", "想你", "寂しい", "miss", "love", "抱抱", "亲爱的", "宝贝"]):
        return "relationship_tone"
    if any(word in combined for word in ["记住", "remember", "覚えて", "喜欢", "不喜欢"]):
        return "memory_preference"
    if re.search(r"[ぁ-んァ-ン]", combined):
        return "japanese_style"
    if re.search(r"[A-Za-z]", combined):
        return "english_style"
    return "general_companion"


def item_key(item: dict) -> str:
    messages = item.get("messages", [])
    return json.dumps(messages, ensure_ascii=False, sort_keys=True)

