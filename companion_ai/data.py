from __future__ import annotations

import json
from pathlib import Path


def iter_training_texts(raw_dir: Path):
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".txt":
            text = path.read_text(encoding="utf-8").strip()
            if text:
                yield text
        elif suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{path}:{line_no}: invalid JSONL") from exc
                    text = jsonl_record_to_text(obj)
                    if text.strip():
                        yield text.strip()


def jsonl_record_to_text(obj: dict) -> str:
    if "text" in obj:
        return str(obj["text"])

    if "messages" in obj:
        lines = []
        for message in obj["messages"]:
            role = str(message.get("role", "")).lower()
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            label = "我" if role in {"user", "human"} else "你"
            lines.append(f"{label}: {content}")
        return "\n".join(lines)

    if "prompt" in obj and "response" in obj:
        return f"我: {obj['prompt']}\n你: {obj['response']}"

    return ""
