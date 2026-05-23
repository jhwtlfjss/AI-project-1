from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass
class KnowledgeEntry:
    id: str
    topic: str
    title: str
    summary: str
    source_url: str
    source_type: str
    language: str = "unknown"
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_seen_at: float = field(default_factory=time.time)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeEntry":
        return cls(
            id=str(data["id"]),
            topic=str(data.get("topic", "")),
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            source_url=str(data.get("source_url", "")),
            source_type=str(data.get("source_type", "")),
            language=str(data.get("language", "unknown")),
            tags=list(data.get("tags", [])),
            created_at=float(data.get("created_at", time.time())),
            last_seen_at=float(data.get("last_seen_at", time.time())),
        )


class KnowledgeBase:
    def __init__(self, entries: list[KnowledgeEntry] | None = None):
        self.entries = entries or []

    @classmethod
    def load(cls, path: Path) -> "KnowledgeBase":
        if not path.exists():
            return cls()
        entries: list[KnowledgeEntry] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(KnowledgeEntry.from_dict(json.loads(line)))
        return cls(entries)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for entry in self.entries:
                fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")

    def add_or_update(
        self,
        topic: str,
        title: str,
        summary: str,
        source_url: str,
        source_type: str,
        language: str = "unknown",
        tags: list[str] | None = None,
    ) -> KnowledgeEntry:
        entry_id = stable_id(source_url, title)
        now = time.time()
        for entry in self.entries:
            if entry.id == entry_id or (source_url and entry.source_url == source_url):
                entry.topic = topic
                entry.title = title
                entry.summary = summary
                entry.source_type = source_type
                entry.language = language
                entry.tags = tags or []
                entry.last_seen_at = now
                return entry
        entry = KnowledgeEntry(
            id=entry_id,
            topic=topic,
            title=title,
            summary=summary,
            source_url=source_url,
            source_type=source_type,
            language=language,
            tags=tags or [],
            created_at=now,
            last_seen_at=now,
        )
        self.entries.append(entry)
        return entry

    def search(self, query: str, limit: int = 4) -> list[KnowledgeEntry]:
        query_terms = extract_terms(query)
        if not query_terms:
            return []
        scored: list[tuple[float, KnowledgeEntry]] = []
        for entry in self.entries:
            haystack = " ".join([entry.topic, entry.title, entry.summary, " ".join(entry.tags)])
            hay_terms = extract_terms(haystack)
            overlap = query_terms & hay_terms
            if not overlap:
                continue
            title_bonus = 2.0 * len(overlap & extract_terms(entry.title))
            tag_bonus = 1.5 * len(overlap & extract_terms(" ".join(entry.tags)))
            freshness = 1.0 / (1.0 + max(0.0, time.time() - entry.last_seen_at) / 2_592_000.0)
            score = len(overlap) + title_bonus + tag_bonus + freshness
            scored.append((score, entry))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in scored[:limit]]

    def clean_noise(self):
        noisy_prefixes = (
            "Jump to content",
            "跳转到内容",
            "コンテンツにスキップ",
            "メインメニュー",
        )
        cleaned: list[KnowledgeEntry] = []
        for entry in self.entries:
            is_noisy_wiki_html = (
                entry.source_type == "url"
                and "wikipedia.org/wiki" in entry.source_url
                and entry.summary.startswith(noisy_prefixes)
            )
            if not is_noisy_wiki_html:
                cleaned.append(entry)
        self.entries = cleaned


def stable_id(source_url: str, title: str) -> str:
    raw = f"{source_url}\n{title}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:24]


def extract_terms(text: str) -> set[str]:
    lowered = text.lower()
    terms = {m.group(0) for m in WORD_RE.finditer(lowered) if len(m.group(0)) >= 2}
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


def render_knowledge_context(entries: list[KnowledgeEntry], max_chars: int = 520) -> str:
    if not entries:
        return ""
    lines: list[str] = []
    used = 0
    for entry in entries:
        line = f"- {entry.title}: {entry.summary}"
        if entry.source_url:
            line += f" 来源: {entry.source_url}"
        if used + len(line) > max_chars:
            remaining = max_chars - used
            if remaining <= 40:
                break
            line = line[:remaining].rstrip() + "..."
        lines.append(line)
        used += len(line)
        if used >= max_chars:
            break
    return "\n".join(lines)
