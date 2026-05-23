from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompanionMemory:
    user_name: str = ""
    preferred_address: str = "亲爱的"
    facts: list[str] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "CompanionMemory":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            user_name=data.get("user_name", ""),
            preferred_address=data.get("preferred_address", "亲爱的"),
            facts=list(data.get("facts", [])),
            history=list(data.get("history", [])),
        )

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "user_name": self.user_name,
                    "preferred_address": self.preferred_address,
                    "facts": self.facts[-200:],
                    "history": self.history[-80:],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def add_turn(self, user: str, assistant: str):
        self.history.append({"role": "user", "content": user})
        self.history.append({"role": "assistant", "content": assistant})
        self.history = self.history[-80:]

    def maybe_capture_fact(self, text: str):
        markers = ["记住", "remember", "覚えて", "覚えといて"]
        lowered = text.lower()
        candidates: list[str] = []
        if any(marker in lowered for marker in markers):
            candidates.append(text.strip())

        candidates.extend(extract_personal_facts(text))
        for fact in candidates:
            cleaned = normalize_fact(fact)
            if cleaned and cleaned not in self.facts:
                self.facts.append(cleaned)
        self.facts = self.facts[-300:]

        preferred = extract_preferred_address(text)
        if preferred:
            self.preferred_address = preferred

        name = extract_user_name(text)
        if name:
            self.user_name = name

    def render(self, query: str = "", max_facts: int = 12, max_turns: int = 10) -> str:
        lines = []
        if self.user_name:
            lines.append(f"用户名字: {self.user_name}")
        if self.preferred_address:
            lines.append(f"称呼偏好: {self.preferred_address}")
        if self.facts:
            lines.append("记忆:")
            for fact in self.relevant_facts(query, limit=max_facts):
                lines.append(f"- {fact}")
        if self.history:
            lines.append("最近对话:")
            for item in self.history[-max_turns:]:
                label = "我" if item["role"] == "user" else "你"
                lines.append(f"{label}: {item['content']}")
        return "\n".join(lines)

    def relevant_facts(self, query: str, limit: int = 12) -> list[str]:
        if not self.facts:
            return []
        terms = memory_terms(query)
        if not terms:
            return self.facts[-limit:]
        scored: list[tuple[int, int, str]] = []
        for idx, fact in enumerate(self.facts):
            fact_terms = memory_terms(fact)
            score = len(terms & fact_terms)
            if score:
                scored.append((score, idx, fact))
        if not scored:
            return self.facts[-limit:]
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [fact for _, _, fact in scored[:limit]]


def normalize_fact(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:300]


def extract_personal_facts(text: str) -> list[str]:
    patterns = [
        r"(我(?:喜欢|不喜欢|讨厌|害怕|希望|想要|需要|习惯|在意)[^。！？!?]{1,80})",
        r"(我的(?:名字|生日|工作|学校|专业|爱好|雷区|偏好|地址|城市)[^。！？!?]{1,80})",
        r"(I (?:like|love|hate|prefer|need|want|work|live|study)[^.!?]{1,120})",
        r"(my (?:name|birthday|job|school|major|hobby|preference|address|city)[^.!?]{1,120})",
        r"((?:私は|僕は|俺は).{0,8}(?:好き|嫌い|苦手|欲しい|必要|住んで|働いて|勉強して)[^。！？!?]{1,80})",
        r"((?:私の|僕の|俺の)(?:名前|誕生日|仕事|学校|趣味|住所|都市)[^。！？!?]{1,80})",
    ]
    facts: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            facts.append(match.group(1).strip())
    return facts


def extract_preferred_address(text: str) -> str:
    patterns = [
        r"(?:叫我|称呼我|喊我)([^。！？!?，,]{1,24})",
        r"(?:call me|address me as)\s+([^.!?]{1,40})",
        r"(?:私を|僕を|俺を)([^。！？!?]{1,24})(?:と呼んで|って呼んで)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_fact(match.group(1)).strip(" 叫做为是")
    return ""


def extract_user_name(text: str) -> str:
    patterns = [
        r"(?:我叫|我的名字是)([^。！？!?，,]{1,24})",
        r"(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z0-9 _-]{0,39})",
        r"(?:私の名前は|僕の名前は|俺の名前は)([^。！？!?]{1,24})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return normalize_fact(match.group(1)).strip()
    return ""


def memory_terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = {m.group(0) for m in re.finditer(r"[a-zA-Z0-9_]+", lowered) if len(m.group(0)) >= 2}
    cjk = [
        ch
        for ch in lowered
        if "\u4e00" <= ch <= "\u9fff"
        or "\u3040" <= ch <= "\u30ff"
        or "\uac00" <= ch <= "\ud7af"
    ]
    terms.update(cjk)
    for i in range(len(cjk) - 1):
        terms.add("".join(cjk[i : i + 2]))
    return terms
