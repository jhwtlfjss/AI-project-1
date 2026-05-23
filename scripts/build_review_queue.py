from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.growth import build_review_items, write_review_queue


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, default=Path("logs/conversations.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("data/review_queue.jsonl"))
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--min-assistant-chars", type=int, default=12)
    args = parser.parse_args()

    items = build_review_items(args.log, min_assistant_chars=args.min_assistant_chars)
    write_review_queue(items, args.out, append=args.append)
    print(f"review_items={len(items)} out={args.out}")
    print("Edit approved=false to approved=true for examples you want her to learn.")


if __name__ == "__main__":
    main()

