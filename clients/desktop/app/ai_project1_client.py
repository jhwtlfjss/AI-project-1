from __future__ import annotations

import json
import os
import queue
import socket
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from companion_ai.client_api import CompanionClient


APP_NAME = "AI Project 1"
CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "AI Project 1"
CONFIG_PATH = CONFIG_DIR / "desktop_client_settings.json"


class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1060x740")
        self.minsize(860, 560)
        self.configure(bg="#f7f3ed")
        self.client: CompanionClient | None = None
        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.settings = self.load_settings()
        self.build_styles()
        self.build_ui()
        self.apply_settings()
        self.after(120, self.process_queue)

    def build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Panel.TFrame", background="#fffaf4")
        style.configure("Main.TFrame", background="#fffdf9")
        style.configure("Muted.TLabel", background="#fffaf4", foreground="#6f6a63")
        style.configure("Title.TLabel", background="#fffaf4", foreground="#202123", font=("Segoe UI", 18, "bold"))
        style.configure("Header.TLabel", background="#fffdf9", foreground="#202123", font=("Segoe UI", 16, "bold"))
        style.configure("Accent.TButton", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.configure("Ghost.TButton", padding=(10, 7))

    def build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = ttk.Frame(self, style="Panel.TFrame", padding=16)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.configure(width=300)
        self.sidebar.grid_propagate(False)

        ttk.Label(self.sidebar, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.sidebar, text="Private desktop client", style="Muted.TLabel").pack(anchor="w", pady=(2, 18))

        self.server_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.client_id_var = tk.StringVar(value=socket.gethostname())
        self.self_signed_var = tk.BooleanVar(value=False)

        self.add_sidebar_field("Server", self.server_var, "http://主设备IP:8765")
        self.add_sidebar_field("Token", self.token_var, "data/server_token.txt", show="*")
        self.add_sidebar_field("Client", self.client_id_var, "desktop-pc")

        ttk.Checkbutton(
            self.sidebar,
            text="Trust self-signed HTTPS",
            variable=self.self_signed_var,
        ).pack(anchor="w", pady=(4, 12))

        ttk.Button(self.sidebar, text="Connect", style="Accent.TButton", command=self.connect_async).pack(fill="x")
        ttk.Button(self.sidebar, text="Save Settings", style="Ghost.TButton", command=self.save_settings_from_ui).pack(
            fill="x", pady=(8, 0)
        )
        ttk.Button(self.sidebar, text="Clear Screen", style="Ghost.TButton", command=self.clear_chat).pack(
            fill="x", pady=(8, 0)
        )

        ttk.Separator(self.sidebar).pack(fill="x", pady=18)

        self.status_var = tk.StringVar(value="Not connected")
        self.knowledge_var = tk.StringVar(value="Knowledge: -")
        self.memory_var = tk.StringVar(value="Memory: -")
        self.hub_var = tk.StringVar(value="Hub: -")
        ttk.Label(self.sidebar, textvariable=self.status_var, style="Muted.TLabel", wraplength=255).pack(anchor="w")
        ttk.Label(self.sidebar, textvariable=self.hub_var, style="Muted.TLabel", wraplength=255).pack(anchor="w", pady=(8, 0))
        ttk.Label(self.sidebar, textvariable=self.memory_var, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Label(self.sidebar, textvariable=self.knowledge_var, style="Muted.TLabel").pack(anchor="w", pady=(8, 0))

        self.main = ttk.Frame(self, style="Main.TFrame", padding=18)
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.rowconfigure(1, weight=1)
        self.main.columnconfigure(0, weight=1)

        header = ttk.Frame(self.main, style="Main.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Chat", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Reconnect", command=self.connect_async).grid(row=0, column=1, sticky="e")

        self.canvas = tk.Canvas(self.main, bg="#fffdf9", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main, orient="vertical", command=self.canvas.yview)
        self.messages = tk.Frame(self.canvas, bg="#fffdf9")
        self.messages.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.messages, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.canvas.bind("<Configure>", self.resize_messages)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        composer = ttk.Frame(self.main, style="Main.TFrame")
        composer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        composer.columnconfigure(0, weight=1)
        self.input_text = tk.Text(
            composer,
            height=4,
            wrap="word",
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#202123",
            relief="solid",
            bd=1,
            padx=10,
            pady=8,
        )
        self.input_text.grid(row=0, column=0, sticky="ew")
        self.input_text.bind("<Control-Return>", lambda _event: self.send_async())
        self.send_button = ttk.Button(composer, text="Send", style="Accent.TButton", command=self.send_async)
        self.send_button.grid(row=0, column=1, sticky="ns", padx=(10, 0))

        self.add_message("system", "Welcome. Connect to your main device Hub, then start chatting.", align="left")

    def add_sidebar_field(self, label: str, variable: tk.StringVar, placeholder: str, show: str | None = None):
        ttk.Label(self.sidebar, text=label, style="Muted.TLabel").pack(anchor="w")
        entry = ttk.Entry(self.sidebar, textvariable=variable, show=show or "")
        entry.pack(fill="x", pady=(2, 10))
        entry.insert(0, variable.get() or "")
        if not variable.get():
            entry.configure(foreground="#6f6a63")
            variable.set("")
            entry.insert(0, placeholder)

            def clear_placeholder(_event, e=entry, v=variable, p=placeholder):
                if e.get() == p:
                    e.delete(0, "end")
                    e.configure(foreground="#202123")
                    v.set("")

            def restore_placeholder(_event, e=entry, v=variable, p=placeholder):
                if not e.get().strip():
                    e.configure(foreground="#6f6a63")
                    e.insert(0, p)

            entry.bind("<FocusIn>", clear_placeholder)
            entry.bind("<FocusOut>", restore_placeholder)

    def apply_settings(self):
        self.server_var.set(self.settings.get("server", ""))
        self.token_var.set(self.settings.get("token", ""))
        self.client_id_var.set(self.settings.get("client_id", socket.gethostname()))
        self.self_signed_var.set(bool(self.settings.get("insecure", False)))

    def load_settings(self) -> dict:
        if CONFIG_PATH.exists():
            try:
                return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def save_settings_from_ui(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "server": self.clean_entry(self.server_var.get()),
            "token": self.clean_entry(self.token_var.get()),
            "client_id": self.clean_entry(self.client_id_var.get()) or socket.gethostname(),
            "insecure": bool(self.self_signed_var.get()),
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.settings = data
        self.status_var.set("Settings saved")

    def make_client(self) -> CompanionClient:
        self.save_settings_from_ui()
        server = self.settings.get("server", "")
        token = self.settings.get("token", "")
        client_id = self.settings.get("client_id", socket.gethostname())
        if not server.startswith(("http://", "https://")):
            raise ValueError("Server must start with http:// or https://")
        if not token:
            raise ValueError("Token is required")
        return CompanionClient(server, token, verify_tls=not self.settings.get("insecure", False), client_id=client_id)

    def connect_async(self):
        self.status_var.set("Connecting...")
        threading.Thread(target=self.connect_worker, daemon=True).start()

    def connect_worker(self):
        try:
            self.client = self.make_client()
            status = self.client.status()
            self.ui_queue.put(("status", status))
        except Exception as exc:
            self.ui_queue.put(("error", f"Connection failed: {exc}"))

    def send_async(self):
        message = self.input_text.get("1.0", "end").strip()
        if not message:
            return
        if self.client is None:
            try:
                self.client = self.make_client()
            except Exception as exc:
                self.add_message("system", f"Connection settings are incomplete: {exc}", align="left")
                return
        self.input_text.delete("1.0", "end")
        self.add_message("我", message, align="right")
        self.send_button.configure(state="disabled")
        self.status_var.set("Thinking...")
        threading.Thread(target=self.send_worker, args=(message,), daemon=True).start()

    def send_worker(self, message: str):
        try:
            assert self.client is not None
            reply = self.client.chat(message)
            self.ui_queue.put(("reply", reply))
        except Exception as exc:
            self.ui_queue.put(("error", f"Send failed: {exc}"))
        finally:
            self.ui_queue.put(("send_done", None))

    def process_queue(self):
        try:
            while True:
                kind, payload = self.ui_queue.get_nowait()
                if kind == "status":
                    self.show_status(payload)
                    self.add_message("system", "Connected to Hub.", align="left")
                elif kind == "reply":
                    self.add_message("你", str(payload), align="left")
                    self.status_var.set("Connected")
                elif kind == "error":
                    self.status_var.set(str(payload))
                    self.add_message("system", str(payload), align="left")
                elif kind == "send_done":
                    self.send_button.configure(state="normal")
        except queue.Empty:
            pass
        self.after(120, self.process_queue)

    def show_status(self, status: dict):
        self.status_var.set(f"Connected: ready={status.get('ready')}, device={status.get('device')}")
        hub = status.get("hub") or {}
        self.hub_var.set(f"Hub: {hub.get('hub_name', '-')}")
        self.memory_var.set(f"Memory: {status.get('memory_facts', 0)} facts, {status.get('memory_turns', 0)} turns")
        self.knowledge_var.set(f"Knowledge: {status.get('knowledge_entries', 0)} notes")

    def add_message(self, speaker: str, text: str, align: str):
        row = tk.Frame(self.messages, bg="#fffdf9")
        row.pack(fill="x", pady=6)
        bubble_color = "#e9f1ff" if align == "right" else "#fff7f2"
        if speaker == "system":
            bubble_color = "#f4efe7"
        wrap = max(320, int(self.canvas.winfo_width() * 0.62))
        bubble = tk.Frame(row, bg=bubble_color, padx=12, pady=9, highlightbackground="#ddd4c8", highlightthickness=1)
        label = tk.Label(
            bubble,
            text=f"{speaker} · {datetime.now().strftime('%H:%M')}\n{text}",
            justify="left",
            anchor="w",
            wraplength=wrap,
            bg=bubble_color,
            fg="#202123",
            font=("Segoe UI", 10),
        )
        label.pack(fill="both")
        bubble.pack(anchor="e" if align == "right" else "w", padx=(80, 6) if align == "right" else (6, 80))
        self.after(50, lambda: self.canvas.yview_moveto(1.0))

    def resize_messages(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear_chat(self):
        for child in self.messages.winfo_children():
            child.destroy()
        self.add_message("system", "Screen cleared.", align="left")

    @staticmethod
    def clean_entry(value: str) -> str:
        placeholders = {"http://主设备IP:8765", "data/server_token.txt", "desktop-pc"}
        value = value.strip()
        return "" if value in placeholders else value


def main():
    try:
        app = ChatApp()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror(APP_NAME, str(exc))


if __name__ == "__main__":
    main()

