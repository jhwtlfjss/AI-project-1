from __future__ import annotations

import sys


def main():
    print(f"Python: {sys.version.split()[0]}")
    try:
        import torch
    except ImportError:
        print("PyTorch: not installed")
        print("Install PyTorch first, then rerun this script.")
        return 1

    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA runtime: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        for index in range(torch.cuda.device_count()):
            free, total = torch.cuda.mem_get_info(index)
            print(
                f"GPU {index}: {torch.cuda.get_device_name(index)} "
                f"free/total={free // 1024**2} MiB / {total // 1024**2} MiB"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
