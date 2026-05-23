from __future__ import annotations

import argparse
import json
from array import array
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.data import iter_training_texts
from companion_ai.tokenizer import ByteTokenizer


def write_u16(path: Path, ids: list[int]):
    arr = array("H", ids)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        arr.tofile(fh)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--out-dir", type=Path, default=Path("data"))
    parser.add_argument("--val-ratio", type=float, default=0.02)
    parser.add_argument("--min-val-tokens", type=int, default=1024)
    args = parser.parse_args()

    tokenizer = ByteTokenizer()
    ids: list[int] = []
    doc_count = 0
    for text in iter_training_texts(args.raw_dir):
        ids.extend(tokenizer.encode(text + "\n", add_bos=True, add_eos=True))
        doc_count += 1

    if len(ids) < 100:
        raise SystemExit("Not enough training data. Add more .txt or .jsonl files under data/raw.")

    requested_val = max(1, int(len(ids) * args.val_ratio), args.min_val_tokens)
    val_count = min(requested_val, max(1, len(ids) // 3))
    train_ids = ids[:-val_count]
    val_ids = ids[-val_count:]
    write_u16(args.out_dir / "train.bin", train_ids)
    write_u16(args.out_dir / "val.bin", val_ids)
    (args.out_dir / "meta.json").write_text(
        json.dumps(
            {
                "documents": doc_count,
                "train_tokens": len(train_ids),
                "val_tokens": len(val_ids),
                "vocab_size": tokenizer.vocab_size,
                "tokenizer": "private_utf8_byte_tokenizer",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"documents={doc_count} train_tokens={len(train_ids)} val_tokens={len(val_ids)}")


if __name__ == "__main__":
    main()
