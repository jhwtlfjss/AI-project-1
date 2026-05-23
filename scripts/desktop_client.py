from __future__ import annotations

import json
import socket
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.client_api import CompanionClient


CONFIG_PATH = ROOT / "data" / "client_config.json"


class DesktopClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("My Companion AI Client")
        self.geometry("760x640")
        self.minsize(520, 420)
        self.client: CompanionClient | None = None
        self.config_data = load_config()
        self.build_ui()

    def build_ui(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        connection = ttk.Frame(outer)
        connection.pack(fill=tk.X)
        ttk.Label(connection, text="Server").grid(row=0, column=0, sticky="w")
        self.server_var = tk.StringVar(value=self.config_data.get("server", "http://127.0.0.1:8765"))
        ttk.Entry(connection, textvariable=self.server_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Label(connection, text="Token").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.token_var = tk.StringVar(value=self.config_data.get("token", ""))
        ttk.Entry(connection, textvariable=self.token_var, show="*").grid(row=1, column=1, sticky="ew", padx=8, pady=(6, 0))
        ttk.Label(connection, text="Client").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.client_id_var = tk.StringVar(value=self.config_data.get("client_id", socket.gethostname()))
        ttk.Entry(connection, textvariable=self.client_id_var).grid(row=2, column=1, sticky="ew", padx=8, pady=(6, 0))
        self.insecure_var = tk.BooleanVar(value=bool(self.config_data.get("insecure", False)))
        ttk.Checkbutton(connection, text="Self-signed HTTPS", variable=self.insecure_var).grid(
            row=3, column=1, sticky="w", padx=8, pady=(6, 0)
        )
        ttk.Button(connection, text="Connect", command=self.connect).grid(row=0, column=2, rowspan=4, sticky="nsew")
        connection.columnconfigure(1, weight=1)

        self.status_var = tk.StringVar(value="Not connected")
        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w", pady=(8, 8))

        self.chat = tk.Text(outer, wrap="word", state="disabled")
        self.chat.pack(fill=tk.BOTH, expand=True)

        composer = ttk.Frame(outer)
        composer.pack(fill=tk.X, pady=(10, 0))
        self.input = tk.Text(composer, height=3, wrap="word")
        self.input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(composer, text="Send", command=self.send_message).pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        self.input.bind("<Control-Return>", lambda _event: self.send_message())

    def connect(self):
        server = self.server_var.get().strip()
        token = self.token_var.get().strip()
        insecure = self.insecure_var.get()
        client_id = self.client_id_var.get().strip()
        self.client = CompanionClient(server, token, verify_tls=not insecure, client_id=client_id)
        save_config({"server": server, "token": token, "client_id": client_id, "insecure": insecure})
        self.status_var.set("Connecting...")
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self):
        try:
            status = self.client.status() if self.client else {}
            text = (
                f"Connected: ready={status.get('ready')} "
                f"memory={status.get('memory_facts', 0)} facts "
                f"knowledge={status.get('knowledge_entries', 0)} notes"
            )
            self.after(0, lambda: self.status_var.set(text))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Connection failed", str(exc)))
            self.after(0, lambda: self.status_var.set("Connection failed"))

    def send_message(self):
        if self.client is None:
            self.connect()
            return
        text = self.input.get("1.0", tk.END).strip()
        if not text:
            return
        self.input.delete("1.0", tk.END)
        self.add_message("我", text)
        self.status_var.set("Thinking...")
        threading.Thread(target=self._send_worker, args=(text,), daemon=True).start()

    def _send_worker(self, text: str):
        try:
            reply = self.client.chat(text) if self.client else ""
            self.after(0, lambda: self.add_message("你", reply))
            self.after(0, lambda: self.status_var.set("Connected"))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Send failed", str(exc)))
            self.after(0, lambda: self.status_var.set("Send failed"))

    def add_message(self, speaker: str, text: str):
        self.chat.configure(state="normal")
        self.chat.insert(tk.END, f"{speaker}> {text}\n\n")
        self.chat.configure(state="disabled")
        self.chat.see(tk.END)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(data: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    DesktopClient().mainloop()
