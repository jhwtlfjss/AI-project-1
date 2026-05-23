from __future__ import annotations

import argparse
import json
import socket
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.hub import load_or_create_hub_profile, read_token, write_client_profile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme", choices=["http", "https"], default="http")
    parser.add_argument("--host", default="", help="Hub address clients should use. Defaults to this device LAN IP.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token-file", type=Path, default=Path("data/server_token.txt"))
    parser.add_argument("--hub-profile", type=Path, default=Path("data/hub_profile.json"))
    parser.add_argument("--out", type=Path, default=Path("data/client_profile.json"))
    parser.add_argument("--client-name", default=socket.gethostname())
    args = parser.parse_args()

    hub = load_or_create_hub_profile(args.hub_profile)
    token = read_token(args.token_file)
    if not token:
        raise SystemExit("Token file does not exist yet. Start the hub once to generate data/server_token.txt.")
    host = args.host or hub.get("lan_ip", "127.0.0.1")
    server_url = f"{args.scheme}://{host}:{args.port}"
    profile = write_client_profile(args.out, server_url, token, hub, args.client_name)
    print(json.dumps(profile, ensure_ascii=False, indent=2))
    print()
    print(f"Client profile written to {args.out}")
    print("Use this on another client device, or enter Server/Token manually in the desktop client.")


if __name__ == "__main__":
    main()

