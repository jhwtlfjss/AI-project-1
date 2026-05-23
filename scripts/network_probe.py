from __future__ import annotations

import argparse
import socket


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    print(f"hostname: {socket.gethostname()}")
    print(f"lan_ip_guess: {guess_lan_ip()}")
    print(f"local_service: {probe(args.host, args.port)}")
    print()
    print("For direct outside access without third-party tunnels, you still need:")
    print("1. A real public IPv4/IPv6 address from your ISP, not CGNAT.")
    print("2. Router port forwarding from WAN port to this computer's LAN IP and port.")
    print("3. Windows Firewall allowing inbound TCP on that port.")
    print("4. The client connecting to your public IP/domain and this port.")


def guess_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "unknown"
    finally:
        sock.close()


def probe(host: str, port: int) -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
        return f"reachable at {host}:{port}"
    except OSError as exc:
        return f"not reachable at {host}:{port} ({exc})"
    finally:
        sock.close()


if __name__ == "__main__":
    main()

