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


if getattr(sys, "frozen", False):
    ROOT = Path(getattr(sys, "_MEIPASS", Path.cwd())).resolve()
else:
    ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from companion_ai.client_api import CompanionClient


APP_NAME = "AI Project 1"
CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "AI Project 1"
CONFIG_PATH = CONFIG_DIR / "desktop_client_settings.json"

COLORS = {
    "sidebar": "#202225",
    "sidebar_panel": "#2f3136",
    "sidebar_border": "#3f4248",
    "chat_bg": "#eef2f5",
    "header": "#ffffff",
    "muted": "#b9bbbe",
    "muted_dark": "#6b7280",
    "text": "#111827",
    "white": "#ffffff",
    "accent": "#5865f2",
    "accent_hover": "#4752c4",
    "user_bubble": "#95ec69",
    "assistant_bubble": "#ffffff",
    "system_bubble": "#dde3ea",
    "entry_bg": "#40444b",
    "entry_fg": "#f5f6f7",
}


def resource_path(relative: str) -> Path:
    return ROOT / relative


class ChatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1120x760")
        self.minsize(900, 600)
        self.configure(bg=COLORS["chat_bg"])
        self.set_window_icon()

        self.client: CompanionClient | None = None
        self.ui_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.settings = self.load_settings()
        self.message_count = 0

        self.build_styles()
        self.build_ui()
        self.apply_settings()
        self.after(120, self.process_queue)

    def set_window_icon(self):
        icon_png = resource_path("assets/app_icon.png")
        icon_ico = resource_path("assets/app_icon.ico")
        try:
            if icon_png.exists():
                self._app_icon = tk.PhotoImage(file=str(icon_png))
                self.iconphoto(True, self._app_icon)
            elif icon_ico.exists():
                self.iconbitmap(str(icon_ico))
        except tk.TclError:
            pass

    def build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Search.TCombobox", padding=4)

    def build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=COLORS["sidebar"], width=310)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.main = tk.Frame(self, bg=COLORS["chat_bg"])
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        self.build_sidebar()
        self.build_chat_area()

    def build_sidebar(self):
        brand = tk.Frame(self.sidebar, bg=COLORS["sidebar"], padx=18, pady=18)
        brand.pack(fill="x")
        avatar = tk.Canvas(brand, width=42, height=42, bg=COLORS["sidebar"], highlightthickness=0)
        avatar.create_oval(3, 3, 39, 39, fill=COLORS["accent"], outline="")
        avatar.create_text(21, 21, text="AI", fill="white", font=("Segoe UI", 12, "bold"))
        avatar.pack(side="left")
        title_box = tk.Frame(brand, bg=COLORS["sidebar"])
        title_box.pack(side="left", padx=(12, 0))
        tk.Label(
            title_box,
            text=APP_NAME,
            bg=COLORS["sidebar"],
            fg=COLORS["white"],
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="private companion hub",
            bg=COLORS["sidebar"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self.server_var = tk.StringVar(value="http://127.0.0.1:8765")
        self.token_var = tk.StringVar()
        self.client_id_var = tk.StringVar(value=socket.gethostname())
        self.self_signed_var = tk.BooleanVar(value=False)
        self.search_enabled_var = tk.BooleanVar(value=True)
        self.search_auto_var = tk.BooleanVar(value=True)
        self.search_engine_var = tk.StringVar(value="google")
        self.custom_search_url_var = tk.StringVar()

        connection = self.sidebar_card("Connection")
        self.add_entry(connection, "Server", self.server_var)
        self.add_entry(connection, "Token", self.token_var, show="*")
        self.add_entry(connection, "Client", self.client_id_var)
        self.add_check(connection, "Self-signed HTTPS", self.self_signed_var)
        self.add_button(connection, "Connect", self.connect_async, fill=COLORS["accent"])
        self.add_button(connection, "Save Settings", self.save_settings_from_ui)

        search = self.sidebar_card("Search")
        self.add_check(search, "Live web search", self.search_enabled_var)
        self.add_check(search, "Auto lookup triggers", self.search_auto_var)
        tk.Label(
            search,
            text="Engine",
            bg=COLORS["sidebar_panel"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(8, 3))
        self.search_engine_combo = ttk.Combobox(
            search,
            textvariable=self.search_engine_var,
            values=("google", "baidu", "custom"),
            state="readonly",
            style="Search.TCombobox",
        )
        self.search_engine_combo.pack(fill="x")
        self.search_engine_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_custom_search_state())
        self.custom_search_entry = self.add_entry(search, "Custom URL", self.custom_search_url_var)
        self.custom_search_entry.insert(0, self.custom_search_url_var.get())

        actions = self.sidebar_card("Chat")
        self.add_button(actions, "Clear Screen", self.clear_chat)
        self.status_var = tk.StringVar(value="Not connected")
        self.hub_var = tk.StringVar(value="Hub: -")
        self.memory_var = tk.StringVar(value="Memory: -")
        self.knowledge_var = tk.StringVar(value="Knowledge: -")
        self.search_status_var = tk.StringVar(value="Search: -")
        for var in (self.status_var, self.hub_var, self.memory_var, self.knowledge_var, self.search_status_var):
            tk.Label(
                actions,
                textvariable=var,
                bg=COLORS["sidebar_panel"],
                fg=COLORS["muted"],
                justify="left",
                wraplength=245,
                font=("Segoe UI", 9),
            ).pack(anchor="w", pady=(8, 0))

    def build_chat_area(self):
        header = tk.Frame(self.main, bg=COLORS["header"], height=72, highlightbackground="#d9dde4", highlightthickness=1)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(1, weight=1)

        avatar = tk.Canvas(header, width=44, height=44, bg=COLORS["header"], highlightthickness=0)
        avatar.create_oval(4, 4, 40, 40, fill=COLORS["accent"], outline="")
        avatar.create_text(22, 22, text="她", fill="white", font=("Microsoft YaHei UI", 13, "bold"))
        avatar.grid(row=0, column=0, padx=(20, 12), pady=14)
        title = tk.Frame(header, bg=COLORS["header"])
        title.grid(row=0, column=1, sticky="w")
        tk.Label(
            title,
            text="AI Project 1",
            bg=COLORS["header"],
            fg=COLORS["text"],
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title,
            text="三语陪伴模型 · 主设备 Hub",
            bg=COLORS["header"],
            fg=COLORS["muted_dark"],
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        tk.Button(
            header,
            text="Reconnect",
            command=self.connect_async,
            bg=COLORS["white"],
            fg=COLORS["text"],
            activebackground="#f3f4f6",
            activeforeground=COLORS["text"],
            relief="flat",
            padx=14,
            pady=8,
            cursor="hand2",
        ).grid(row=0, column=2, padx=(0, 20))

        self.canvas = tk.Canvas(self.main, bg=COLORS["chat_bg"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main, orient="vertical", command=self.canvas.yview)
        self.messages = tk.Frame(self.canvas, bg=COLORS["chat_bg"])
        self.messages.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.messages, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.scrollbar.grid(row=1, column=1, sticky="ns")
        self.canvas.bind("<Configure>", self.resize_messages)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        composer = tk.Frame(self.main, bg=COLORS["header"], padx=18, pady=14, highlightbackground="#d9dde4", highlightthickness=1)
        composer.grid(row=2, column=0, sticky="ew")
        composer.columnconfigure(0, weight=1)
        input_shell = tk.Frame(composer, bg="#f3f4f6", padx=12, pady=8)
        input_shell.grid(row=0, column=0, sticky="ew")
        input_shell.columnconfigure(0, weight=1)
        self.input_text = tk.Text(
            input_shell,
            height=3,
            wrap="word",
            font=("Microsoft YaHei UI", 11),
            bg="#f3f4f6",
            fg=COLORS["text"],
            relief="flat",
            bd=0,
            padx=2,
            pady=2,
            insertbackground=COLORS["text"],
        )
        self.input_text.grid(row=0, column=0, sticky="ew")
        self.input_text.bind("<Control-Return>", lambda _event: self.send_async())
        self.input_text.bind("<Return>", self.on_enter)
        self.send_button = tk.Button(
            composer,
            text="Send",
            command=self.send_async,
            bg=COLORS["accent"],
            fg="white",
            activebackground=COLORS["accent_hover"],
            activeforeground="white",
            relief="flat",
            padx=22,
            pady=10,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
        )
        self.send_button.grid(row=0, column=1, padx=(12, 0), sticky="ns")

        self.add_message("system", "连接主设备 Hub 后就可以开始聊天。", align="left")

    def sidebar_card(self, title: str) -> tk.Frame:
        card = tk.Frame(self.sidebar, bg=COLORS["sidebar_panel"], padx=14, pady=12)
        card.pack(fill="x", padx=14, pady=(0, 12))
        tk.Label(
            card,
            text=title,
            bg=COLORS["sidebar_panel"],
            fg=COLORS["white"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 8))
        return card

    def add_entry(self, parent: tk.Frame, label: str, variable: tk.StringVar, show: str | None = None) -> tk.Entry:
        tk.Label(parent, text=label, bg=COLORS["sidebar_panel"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(
            anchor="w", pady=(6, 3)
        )
        entry = tk.Entry(
            parent,
            textvariable=variable,
            show=show or "",
            bg=COLORS["entry_bg"],
            fg=COLORS["entry_fg"],
            insertbackground=COLORS["entry_fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["sidebar_border"],
            highlightcolor=COLORS["accent"],
        )
        entry.pack(fill="x", ipady=6)
        return entry

    def add_check(self, parent: tk.Frame, text: str, variable: tk.BooleanVar):
        tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            bg=COLORS["sidebar_panel"],
            fg=COLORS["entry_fg"],
            activebackground=COLORS["sidebar_panel"],
            activeforeground=COLORS["entry_fg"],
            selectcolor=COLORS["entry_bg"],
            relief="flat",
            anchor="w",
            font=("Segoe UI", 9),
        ).pack(fill="x", pady=(4, 0))

    def add_button(self, parent: tk.Frame, text: str, command, fill: str | None = None):
        bg = fill or COLORS["entry_bg"]
        active = COLORS["accent_hover"] if fill else COLORS["sidebar_border"]
        tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg="white",
            activebackground=active,
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
        ).pack(fill="x", pady=(8, 0))

    def apply_settings(self):
        self.server_var.set(self.settings.get("server", "http://127.0.0.1:8765"))
        self.token_var.set(self.settings.get("token", ""))
        self.client_id_var.set(self.settings.get("client_id", socket.gethostname()))
        self.self_signed_var.set(bool(self.settings.get("insecure", False)))
        self.search_enabled_var.set(bool(self.settings.get("search_enabled", True)))
        self.search_auto_var.set(bool(self.settings.get("search_auto_lookup", True)))
        self.search_engine_var.set(self.settings.get("search_engine", "google"))
        self.custom_search_url_var.set(self.settings.get("custom_search_url", ""))
        self.update_custom_search_state()

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
            "server": self.server_var.get().strip(),
            "token": self.token_var.get().strip(),
            "client_id": self.client_id_var.get().strip() or socket.gethostname(),
            "insecure": bool(self.self_signed_var.get()),
            "search_enabled": bool(self.search_enabled_var.get()),
            "search_auto_lookup": bool(self.search_auto_var.get()),
            "search_engine": self.search_engine_var.get().strip() or "google",
            "custom_search_url": self.custom_search_url_var.get().strip(),
        }
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.settings = data
        self.status_var.set("Settings saved")

    def update_custom_search_state(self):
        state = "normal" if self.search_engine_var.get() == "custom" else "disabled"
        self.custom_search_entry.configure(state=state)

    def web_search_options(self) -> dict:
        return {
            "enabled": bool(self.search_enabled_var.get()),
            "auto_lookup": bool(self.search_auto_var.get()),
            "search_engine": self.search_engine_var.get().strip() or "google",
            "custom_search_url": self.custom_search_url_var.get().strip(),
        }

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
        try:
            self.client = self.make_client()
        except Exception as exc:
            self.status_var.set(f"Connection failed: {exc}")
            self.add_message("system", f"连接设置不完整：{exc}", align="left")
            return
        self.status_var.set("Connecting...")
        threading.Thread(target=self.connect_worker, args=(self.client,), daemon=True).start()

    def connect_worker(self, client: CompanionClient):
        try:
            status = client.status()
            self.ui_queue.put(("status", status))
        except Exception as exc:
            self.ui_queue.put(("error", f"Connection failed: {exc}"))

    def send_async(self):
        message = self.input_text.get("1.0", "end").strip()
        if not message:
            return "break"
        if self.client is None:
            try:
                self.client = self.make_client()
            except Exception as exc:
                self.add_message("system", f"连接设置不完整：{exc}", align="left")
                return "break"
        web_search = self.web_search_options()
        self.input_text.delete("1.0", "end")
        self.add_message("me", message, align="right")
        self.send_button.configure(state="disabled", text="...")
        self.status_var.set("Thinking...")
        threading.Thread(target=self.send_worker, args=(message, web_search), daemon=True).start()
        return "break"

    def send_worker(self, message: str, web_search: dict):
        try:
            assert self.client is not None
            reply = self.client.chat(message, web_search=web_search)
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
                    self.add_message("system", "已连接到主设备 Hub。", align="left")
                elif kind == "reply":
                    self.add_message("assistant", str(payload), align="left")
                    self.status_var.set("Connected")
                elif kind == "error":
                    self.status_var.set(str(payload))
                    self.add_message("system", str(payload), align="left")
                elif kind == "send_done":
                    self.send_button.configure(state="normal", text="Send")
        except queue.Empty:
            pass
        self.after(120, self.process_queue)

    def show_status(self, status: dict):
        ready = "ready" if status.get("ready") else "no model"
        self.status_var.set(f"Connected: {ready}, device={status.get('device')}")
        hub = status.get("hub") or {}
        self.hub_var.set(f"Hub: {hub.get('hub_name', '-')}")
        self.memory_var.set(f"Memory: {status.get('memory_facts', 0)} facts, {status.get('memory_turns', 0)} turns")
        self.knowledge_var.set(f"Knowledge: {status.get('knowledge_entries', 0)} notes")
        live_settings = status.get("live_web_settings") or {}
        if status.get("live_web"):
            self.search_status_var.set(f"Search: {live_settings.get('search_engine', 'google')}")
        else:
            self.search_status_var.set("Search: disabled on Hub")

    def add_message(self, speaker: str, text: str, align: str):
        row = tk.Frame(self.messages, bg=COLORS["chat_bg"])
        row.pack(fill="x", pady=7, padx=18)
        wrap = max(360, int(self.canvas.winfo_width() * 0.58))
        is_user = align == "right"
        is_system = speaker == "system"
        bubble_color = COLORS["user_bubble"] if is_user else COLORS["assistant_bubble"]
        avatar_fill = "#43b581"
        title = "我" if is_user else "AI Project 1"
        if is_system:
            bubble_color = COLORS["system_bubble"]
            avatar_fill = COLORS["muted_dark"]
            title = "System"

        avatar = tk.Canvas(row, width=36, height=36, bg=COLORS["chat_bg"], highlightthickness=0)
        avatar.create_oval(3, 3, 33, 33, fill=avatar_fill, outline="")
        avatar.create_text(18, 18, text="我" if is_user else ("i" if is_system else "AI"), fill="white", font=("Segoe UI", 9, "bold"))

        bubble = tk.Frame(row, bg=bubble_color, padx=12, pady=8, highlightbackground="#d1d5db", highlightthickness=1)
        meta = tk.Label(
            bubble,
            text=f"{title} · {datetime.now().strftime('%H:%M')}",
            bg=bubble_color,
            fg=COLORS["muted_dark"],
            font=("Segoe UI", 8),
            anchor="w",
        )
        meta.pack(anchor="w")
        label = tk.Label(
            bubble,
            text=text,
            justify="left",
            anchor="w",
            wraplength=wrap,
            bg=bubble_color,
            fg=COLORS["text"],
            font=("Microsoft YaHei UI", 10),
        )
        label.pack(fill="both")

        if is_user:
            avatar.pack(side="right", padx=(8, 0), anchor="n")
            bubble.pack(side="right", padx=(90, 0), anchor="e")
        else:
            avatar.pack(side="left", padx=(0, 8), anchor="n")
            bubble.pack(side="left", padx=(0, 90), anchor="w")
        self.message_count += 1
        self.after(50, lambda: self.canvas.yview_moveto(1.0))

    def on_enter(self, event):
        if event.state & 0x0001:
            return None
        return self.send_async()

    def resize_messages(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear_chat(self):
        for child in self.messages.winfo_children():
            child.destroy()
        self.add_message("system", "屏幕已清空。", align="left")


def main():
    try:
        app = ChatApp()
        app.mainloop()
    except Exception as exc:
        messagebox.showerror(APP_NAME, str(exc))


if __name__ == "__main__":
    main()
