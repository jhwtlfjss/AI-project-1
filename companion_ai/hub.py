from __future__ import annotations

import json
import secrets
import socket
import time
from pathlib import Path


def load_or_create_hub_profile(path: Path) -> dict:
    if path.exists():
        profile = json.loads(path.read_text(encoding="utf-8"))
    else:
        profile = {
            "hub_id": secrets.token_urlsafe(12),
            "hub_name": socket.gethostname(),
            "created_at": time.time(),
        }
        save_hub_profile(path, profile)
    profile["lan_ip"] = guess_lan_ip()
    return profile


def save_hub_profile(path: Path, profile: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")


def guess_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def read_token(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def write_client_profile(
    output: Path,
    server_url: str,
    token: str,
    hub_profile: dict,
    client_name: str = "",
):
    payload = {
        "server": server_url.rstrip("/"),
        "token": token,
        "hub_id": hub_profile.get("hub_id", ""),
        "hub_name": hub_profile.get("hub_name", ""),
        "client_name": client_name,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload

