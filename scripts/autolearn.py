from __future__ import annotations

import argparse
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.autonomous_learning import run_learning_cycle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/learning_sources.json"))
    parser.add_argument("--knowledge", type=Path, default=Path("data/knowledge.jsonl"))
    parser.add_argument("--state", type=Path, default=Path("data/learning_state.json"))
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--sleep-minutes", type=int, default=30)
    args = parser.parse_args()

    while True:
        result = run_learning_cycle(args.config, args.knowledge, args.state, force=args.force)
        print(result)
        if not args.daemon:
            break
        args.force = False
        time.sleep(max(1, args.sleep_minutes) * 60)


if __name__ == "__main__":
    main()

