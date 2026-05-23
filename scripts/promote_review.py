from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.growth import promote_approved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, default=Path("data/review_queue.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("data/raw/approved_girlfriend_dialogues.jsonl"))
    args = parser.parse_args()

    count = promote_approved(args.review, args.out)
    print(f"promoted={count} out={args.out}")
    if count:
        print("Run prepare_data.py again before training.")


if __name__ == "__main__":
    main()

