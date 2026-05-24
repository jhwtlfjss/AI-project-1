from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.knowledge import KnowledgeBase, KnowledgeEntry


SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    return SPACE_RE.sub(" ", text).strip()


def clip_text(text: str, max_chars: int) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def prompt_for(entry: KnowledgeEntry) -> str:
    title = clean_text(entry.title) or "this topic"
    language = entry.language.lower()
    if language == "ja":
        return f"恋人のような自然な距離感で、簡単に説明して：{title}"
    if language == "en":
        return f"Explain this in a warm companion style: {title}"
    return f"用适合私人陪伴聊天的语气，简单说说：{title}"


def corpus_text(entry: KnowledgeEntry, summary: str, include_source: bool) -> str:
    lines = [
        f"主题: {entry.topic or 'general'}",
        f"标题: {clean_text(entry.title) or 'untitled'}",
        f"语言: {entry.language or 'unknown'}",
    ]
    if include_source and entry.source_url:
        lines.append(f"来源: {entry.source_url}")
    lines.extend(["资料摘要:", summary])
    return "\n".join(lines)


def read_existing_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            knowledge_id = record.get("knowledge_id")
            if knowledge_id:
                ids.add(str(knowledge_id))
    return ids


def make_records(entry: KnowledgeEntry, summary: str, mode: str, include_source: bool) -> list[dict]:
    base = {
        "knowledge_id": entry.id,
        "source_url": entry.source_url,
        "source_type": entry.source_type,
        "topic": entry.topic,
        "language": entry.language,
    }
    records: list[dict] = []
    if mode in {"corpus", "both"}:
        records.append({**base, "text": corpus_text(entry, summary, include_source)})
    if mode in {"qa", "both"}:
        records.append({**base, "prompt": prompt_for(entry), "response": summary})
    return records


def main():
    parser = argparse.ArgumentParser(
        description="Convert local web-learning knowledge into reviewable training JSONL."
    )
    parser.add_argument("--knowledge", type=Path, default=Path("data/knowledge.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("data/raw/learned_web_corpus.jsonl"))
    parser.add_argument("--topic", action="append", help="Only export this topic. Can be used more than once.")
    parser.add_argument("--mode", choices=["corpus", "qa", "both"], default="both")
    parser.add_argument("--min-chars", type=int, default=80)
    parser.add_argument("--max-summary-chars", type=int, default=1200)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--no-source", action="store_true")
    parser.add_argument("--dump-meta", type=Path, help="Optional JSON report path.")
    args = parser.parse_args()

    if not args.knowledge.exists():
        print(f"knowledge_file_missing={args.knowledge}")
        print("Run scripts/autolearn.py --force first, or chat with live web enabled.")
        return

    knowledge = KnowledgeBase.load(args.knowledge)
    topics = set(args.topic or [])
    existing_ids = read_existing_ids(args.out) if args.append else set()
    write_mode = "a" if args.append else "w"
    args.out.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    exported_ids: set[str] = set()
    with args.out.open(write_mode, encoding="utf-8") as fh:
        for entry in knowledge.entries:
            if topics and entry.topic not in topics:
                skipped += 1
                continue
            if entry.id in existing_ids or entry.id in exported_ids:
                skipped += 1
                continue
            summary = clip_text(entry.summary, args.max_summary_chars)
            if len(summary) < args.min_chars:
                skipped += 1
                continue
            for record in make_records(entry, summary, args.mode, include_source=not args.no_source):
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                written += 1
            exported_ids.add(entry.id)

    report = {
        "knowledge": str(args.knowledge),
        "out": str(args.out),
        "mode": args.mode,
        "knowledge_entries": len(knowledge.entries),
        "unique_entries_exported": len(exported_ids),
        "records_written": written,
        "skipped": skipped,
    }
    if args.dump_meta:
        args.dump_meta.parent.mkdir(parents=True, exist_ok=True)
        args.dump_meta.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(" ".join(f"{key}={value}" for key, value in report.items()))


if __name__ == "__main__":
    main()
