from __future__ import annotations

import argparse
import os
import socket
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.client_api import CompanionClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", required=True, help="Server URL, for example http://100.x.y.z:8765")
    parser.add_argument("--token", default=os.environ.get("COMPANION_CLIENT_TOKEN", ""))
    parser.add_argument("--client-id", default=socket.gethostname())
    parser.add_argument("--insecure", action="store_true", help="Allow self-signed HTTPS certificates.")
    args = parser.parse_args()

    client = CompanionClient(args.server, args.token, verify_tls=not args.insecure, client_id=args.client_id)
    status = client.status()
    print(f"Connected. ready={status.get('ready')} device={status.get('device')}")
    print("Type /exit to quit.")
    while True:
        text = input("我> ").strip()
        if text in {"/exit", "/quit"}:
            break
        if not text:
            continue
        print(f"你> {client.chat(text)}")


if __name__ == "__main__":
    main()
