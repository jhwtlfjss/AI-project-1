from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class ConversationTurn:
    timestamp: float
    user: str
    assistant: str
    metadata: dict = field(default_factory=dict)


def append_turn(path: Path, user: str, assistant: str, metadata: dict | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    turn = ConversationTurn(
        timestamp=time.time(),
        user=user.strip(),
        assistant=assistant.strip(),
        metadata=metadata or {},
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(turn), ensure_ascii=False) + "\n")


def iter_turns(path: Path):
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

