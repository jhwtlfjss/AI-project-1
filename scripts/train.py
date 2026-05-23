from __future__ import annotations

import argparse
import json
import math
import time
from array import array
from contextlib import nullcontext
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import torch

from companion_ai.model import GPT, GPTConfig
from companion_ai.tokenizer import ByteTokenizer


def load_u16(path: Path) -> torch.Tensor:
    arr = array("H")
    with path.open("rb") as fh:
        arr.fromfile(fh, path.stat().st_size // 2)
    return torch.tensor(arr, dtype=torch.long)


def get_batch(data: torch.Tensor, block_size: int, batch_size: int, device: str):
    if len(data) <= block_size + 1:
        raise ValueError(
            f"dataset has {len(data)} tokens, but block_size={block_size}. "
            "Add more data or use a smaller config."
        )
    ix = torch.randint(len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i : i + block_size] for i in ix])
    y = torch.stack([data[i + 1 : i + 1 + block_size] for i in ix])
    return x.to(device, non_blocking=True), y.to(device, non_blocking=True)


def choose_cuda_device() -> str:
    best_index = 0
    best_free = -1
    for index in range(torch.cuda.device_count()):
        try:
            free, _ = torch.cuda.mem_get_info(index)
        except RuntimeError:
            free = 0
        if free > best_free:
            best_index = index
            best_free = free
    return f"cuda:{best_index}"


def resolve_device(requested: str) -> str:
    requested = requested.strip().lower()
    if requested == "auto":
        return choose_cuda_device() if torch.cuda.is_available() else "cpu"
    if requested.startswith("cuda"):
        if not torch.cuda.is_available():
            raise SystemExit("CUDA is not available. Use --device cpu or install CUDA-enabled PyTorch.")
        if ":" in requested:
            try:
                index = int(requested.split(":", 1)[1])
            except ValueError as exc:
                raise SystemExit(f"Invalid CUDA device: {requested}") from exc
            if index < 0 or index >= torch.cuda.device_count():
                raise SystemExit(
                    f"CUDA device {requested} does not exist. "
                    f"Available device count: {torch.cuda.device_count()}."
                )
        return requested
    if requested == "cpu":
        return "cpu"
    raise SystemExit("Device must be auto, cpu, cuda, or cuda:N.")


def describe_device(device: str) -> str:
    if device.startswith("cuda") and torch.cuda.is_available():
        index = torch.device(device).index
        if index is None:
            index = torch.cuda.current_device()
        name = torch.cuda.get_device_name(index)
        free, total = torch.cuda.mem_get_info(index)
        return f"{device} ({name}, free {free // 1024**2} MiB / total {total // 1024**2} MiB)"
    return device


@torch.no_grad()
def estimate_loss(model, train_data, val_data, cfg, device, ctx):
    model.eval()
    out = {}
    for split, data in [("train", train_data), ("val", val_data)]:
        losses = torch.zeros(cfg["eval_iters"])
        for k in range(cfg["eval_iters"]):
            x, y = get_batch(data, model.config.block_size, cfg["batch_size"], device)
            with ctx:
                _, loss = model(x, y)
            losses[k] = loss.item()
        out[split] = losses.mean().item()
    model.train()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--init-from", type=Path, help="Continue training from an existing ckpt.pt.")
    parser.add_argument("--out-dir", type=Path, help="Override train.out_dir from config.")
    parser.add_argument("--additional-steps", type=int, help="When continuing, run this many extra optimizer steps.")
    parser.add_argument("--device", help="Override device: auto, cpu, cuda, or cuda:N.")
    parser.add_argument("--dtype", choices=["float32", "float16", "bfloat16"], help="Override training dtype.")
    parser.add_argument("--batch-size", type=int, help="Override batch size for this run.")
    parser.add_argument("--grad-accum-steps", type=int, help="Override gradient accumulation steps.")
    args = parser.parse_args()

    full_cfg = json.loads(args.config.read_text(encoding="utf-8"))
    model_cfg = full_cfg["model"]
    train_cfg = full_cfg["train"]
    if args.device:
        train_cfg["device"] = args.device
    if args.dtype:
        train_cfg["dtype"] = args.dtype
    if args.batch_size:
        train_cfg["batch_size"] = args.batch_size
    if args.grad_accum_steps:
        train_cfg["grad_accum_steps"] = args.grad_accum_steps

    torch.manual_seed(train_cfg.get("seed", 1337))
    device = resolve_device(train_cfg.get("device", "auto"))

    dtype = train_cfg.get("dtype", "float16")
    ptdtype = {"float32": torch.float32, "float16": torch.float16, "bfloat16": torch.bfloat16}[dtype]
    device_type = "cuda" if device.startswith("cuda") else "cpu"
    ctx = (
        nullcontext()
        if device_type == "cpu"
        else torch.amp.autocast(device_type=device_type, dtype=ptdtype)
    )

    train_data = load_u16(args.data_dir / "train.bin")
    val_data = load_u16(args.data_dir / "val.bin")

    config = GPTConfig(vocab_size=ByteTokenizer.vocab_size, **model_cfg)
    if len(train_data) <= config.block_size + 1:
        raise SystemExit(
            f"Training data is too small for block_size={config.block_size}. "
            "Add more data or choose configs/micro_cpu.json."
        )
    if len(val_data) <= config.block_size + 1:
        print("Validation data is too small for this block_size; using train data for validation.")
        val_data = train_data
    model = GPT(config)
    start_step = 0
    best_val_loss = float("inf")
    if args.init_from:
        ckpt = torch.load(args.init_from, map_location="cpu")
        ckpt_args = ckpt["model_args"]
        if ckpt_args != model.config_dict():
            raise SystemExit(
                "Checkpoint model_args do not match this config. "
                "Use the same model size/block_size as the original checkpoint."
            )
        model.load_state_dict(ckpt["model"])
        start_step = int(ckpt.get("step", 0)) + 1
        best_val_loss = float(ckpt.get("best_val_loss", float("inf")))
        print(f"Continuing from {args.init_from} at step {start_step}.")
    model = model.to(device)
    if train_cfg.get("compile", False):
        model = torch.compile(model)

    print(f"parameters={model.parameter_count() / 1e6:.2f}M device={describe_device(device)} dtype={dtype}")
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_cfg["learning_rate"],
        betas=(0.9, 0.95),
        weight_decay=train_cfg["weight_decay"],
    )
    scaler = torch.cuda.amp.GradScaler(enabled=(device_type == "cuda" and dtype == "float16"))

    out_dir = args.out_dir or Path(train_cfg["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    end_step = train_cfg["max_steps"]
    if args.additional_steps is not None:
        end_step = start_step + max(0, args.additional_steps)
    elif args.init_from and end_step <= start_step:
        end_step = start_step + train_cfg["max_steps"]
        print(
            "Configured max_steps is not greater than checkpoint step; "
            f"treating it as additional steps and training until step {end_step}."
        )

    for step in range(start_step, end_step + 1):
        lr = train_cfg["learning_rate"]
        for param_group in optimizer.param_groups:
            param_group["lr"] = lr

        if step % train_cfg["eval_interval"] == 0:
            losses = estimate_loss(model, train_data, val_data, train_cfg, device, ctx)
            print(
                f"step={step} train_loss={losses['train']:.4f} "
                f"val_loss={losses['val']:.4f} ppl={math.exp(min(losses['val'], 20)):.2f}"
            )
            if losses["val"] < best_val_loss:
                best_val_loss = losses["val"]
                raw_model = model._orig_mod if hasattr(model, "_orig_mod") else model
                torch.save(
                    {
                        "model": raw_model.state_dict(),
                        "model_args": raw_model.config_dict(),
                        "train_config": train_cfg,
                        "step": step,
                        "best_val_loss": best_val_loss,
                    },
                    out_dir / "ckpt.pt",
                )

        optimizer.zero_grad(set_to_none=True)
        for _ in range(train_cfg["grad_accum_steps"]):
            x, y = get_batch(train_data, config.block_size, train_cfg["batch_size"], device)
            with ctx:
                _, loss = model(x, y)
                loss = loss / train_cfg["grad_accum_steps"]
            scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        if step % train_cfg["log_interval"] == 0:
            dt = time.time() - t0
            print(f"step={step} loss={loss.item() * train_cfg['grad_accum_steps']:.4f} dt={dt:.1f}s")
            t0 = time.time()


if __name__ == "__main__":
    main()
