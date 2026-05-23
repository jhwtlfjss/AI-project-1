from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import secrets
import ssl
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.knowledge import KnowledgeBase
from companion_ai.live_web import LiveWebClient
from companion_ai.memory import CompanionMemory
from companion_ai.conversation_log import append_turn
from companion_ai.hub import load_or_create_hub_profile
from companion_ai.persona import load_persona_text
from companion_ai.realtime_data import RealtimeDataClient


class ChatState:
    def __init__(
        self,
        checkpoint: Path | None,
        memory_path: Path,
        knowledge_path: Path,
        network_config: Path,
        realtime_config: Path,
        hub_profile_path: Path,
        persona_path: Path,
        conversation_log_path: Path,
        device: str,
        use_knowledge_cache: bool,
        use_live_web: bool,
        use_realtime_data: bool,
    ):
        self.memory_path = memory_path
        self.knowledge_path = knowledge_path
        self.conversation_log_path = conversation_log_path
        self.memory = CompanionMemory.load(memory_path)
        self.use_knowledge_cache = use_knowledge_cache
        self.use_live_web = use_live_web
        self.use_realtime_data = use_realtime_data
        self.hub_profile = load_or_create_hub_profile(hub_profile_path)
        self.persona_path = persona_path
        self.persona_text = load_persona_text(persona_path)
        self.last_client_id = ""
        self.knowledge = KnowledgeBase.load(knowledge_path) if use_knowledge_cache else KnowledgeBase()
        self.memory.save(memory_path)
        if use_knowledge_cache:
            self.knowledge.save(knowledge_path)
        self.knowledge_mtime = knowledge_path.stat().st_mtime if knowledge_path.exists() else 0.0
        self.live_web = LiveWebClient.load(network_config) if use_live_web else None
        self.realtime_data = RealtimeDataClient.load(realtime_config) if use_realtime_data else None
        self.model = None
        self.generate_reply = None
        self.device = device
        if checkpoint is not None and checkpoint.exists():
            from companion_ai.generate import generate_reply, load_model

            self.model, self.device = load_model(checkpoint, device)
            self.generate_reply = generate_reply

    def refresh_knowledge(self):
        if not self.use_knowledge_cache:
            return
        if not self.knowledge_path.exists():
            self.knowledge = KnowledgeBase()
            self.knowledge_mtime = 0.0
            return
        mtime = self.knowledge_path.stat().st_mtime
        if mtime != self.knowledge_mtime:
            self.knowledge = KnowledgeBase.load(self.knowledge_path)
            self.knowledge_mtime = mtime

    def reply(self, text: str, live_web_options: dict | None = None) -> str:
        if self.model is None:
            return "模型还没有加载。请先训练并用 --checkpoint 指向 runs/.../ckpt.pt。"
        self.refresh_knowledge()
        live_context = ""
        live_results = []
        if self.live_web:
            live_web = self.live_web.with_overrides(live_web_options)
            live_context, live_results = live_web.lookup_context(text)
            if self.use_knowledge_cache and live_results:
                live_web.cache_results(self.knowledge, live_results)
                self.knowledge.save(self.knowledge_path)
                self.knowledge_mtime = self.knowledge_path.stat().st_mtime
        realtime_context = ""
        realtime_results = []
        if self.realtime_data:
            realtime_context, realtime_results = self.realtime_data.context_for_prompt(text)
            if self.use_knowledge_cache and realtime_results:
                self.realtime_data.cache_results(self.knowledge, realtime_results)
                self.knowledge.save(self.knowledge_path)
                self.knowledge_mtime = self.knowledge_path.stat().st_mtime
        answer = self.generate_reply(
            self.model,
            self.device,
            self.memory,
            text,
            knowledge=self.knowledge if self.use_knowledge_cache else None,
            live_context=live_context,
            realtime_context=realtime_context,
            persona_text=self.persona_text,
        )
        self.memory.maybe_capture_fact(text)
        self.memory.add_turn(text, answer)
        self.memory.save(self.memory_path)
        append_turn(
            self.conversation_log_path,
            text,
            answer,
            {
                "client_id": self.last_client_id,
                "persona": str(self.persona_path),
                "live_web": bool(live_context),
                "realtime_data": bool(realtime_context),
            },
        )
        return answer

    def note_client(self, client_id: str):
        if client_id:
            self.last_client_id = client_id[:80]


def make_handler(state: ChatState, web_root: Path):
    class Handler(SimpleHTTPRequestHandler):
        auth_token = ""

        def translate_path(self, path):
            path = path.split("?", 1)[0].split("#", 1)[0]
            if path == "/":
                path = "/index.html"
            return str(web_root / path.lstrip("/"))

        def do_GET(self):
            if self.path.startswith("/api/") and not self.authorized():
                self.send_json({"error": "unauthorized"}, status=401)
                return
            state.note_client(self.headers.get("X-Companion-Client", ""))
            parsed_path = urllib.parse.urlparse(self.path).path
            if parsed_path == "/api/status":
                state.refresh_knowledge()
                self.send_json(
                    {
                        "ready": state.model is not None,
                        "device": state.device,
                        "knowledge_entries": len(state.knowledge.entries) if state.use_knowledge_cache else 0,
                        "knowledge_cache": state.use_knowledge_cache,
                        "live_web": state.use_live_web,
                        "live_web_settings": state.live_web.public_settings() if state.live_web else {},
                        "realtime_data": state.use_realtime_data,
                        "memory_facts": len(state.memory.facts),
                        "memory_turns": len(state.memory.history) // 2,
                        "hub": state.hub_profile,
                        "last_client_id": state.last_client_id,
                    }
                )
                return
            return super().do_GET()

        def do_POST(self):
            if not self.authorized():
                self.send_json({"error": "unauthorized"}, status=401)
                return
            state.note_client(self.headers.get("X-Companion-Client", ""))
            parsed_path = urllib.parse.urlparse(self.path).path
            if parsed_path != "/api/chat":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            message = str(payload.get("message", "")).strip()
            live_web_options = payload.get("web_search")
            if not isinstance(live_web_options, dict):
                live_web_options = None
            if not message:
                self.send_json({"reply": "我在这里。你可以慢慢说。"})
                return
            self.send_json({"reply": state.reply(message, live_web_options=live_web_options)})

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_common_headers()
            self.end_headers()

        def authorized(self) -> bool:
            if not self.auth_token:
                return True
            supplied = self.headers.get("X-Companion-Token", "")
            auth = self.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                supplied = auth[7:].strip()
            if not supplied:
                parsed = urllib.parse.urlparse(self.path)
                supplied = urllib.parse.parse_qs(parsed.query).get("token", [""])[0]
            return hmac.compare_digest(supplied, self.auth_token)

        def send_json(self, payload: dict, status: int = 200):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_common_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_common_headers(self):
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Companion-Token, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

        def guess_type(self, path):
            guessed = mimetypes.guess_type(path)[0]
            if guessed:
                return guessed
            return "application/octet-stream"

    return Handler


def resolve_auth_token(args) -> str:
    if args.no_auth:
        return ""
    if args.auth_token:
        return args.auth_token.strip()
    env_token = os.environ.get("COMPANION_SERVER_TOKEN", "").strip()
    if env_token:
        return env_token
    token_path = args.auth_token_file
    if token_path.exists():
        return token_path.read_text(encoding="utf-8").strip()
    token = secrets.token_urlsafe(32)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(token, encoding="utf-8")
    return token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--memory", type=Path, default=Path("memory.json"))
    parser.add_argument("--knowledge", type=Path, default=Path("data/knowledge.jsonl"))
    parser.add_argument("--network-config", type=Path, default=Path("configs/network_access.json"))
    parser.add_argument("--realtime-config", type=Path, default=Path("configs/realtime_data.json"))
    parser.add_argument("--hub-profile", type=Path, default=Path("data/hub_profile.json"))
    parser.add_argument("--persona", type=Path, default=Path("configs/girlfriend_persona.json"))
    parser.add_argument("--conversation-log", type=Path, default=Path("logs/conversations.jsonl"))
    parser.add_argument("--live-web", action="store_true")
    parser.add_argument("--no-realtime-data", action="store_true")
    parser.add_argument("--no-knowledge-cache", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--auth-token", default="")
    parser.add_argument("--auth-token-file", type=Path, default=Path("data/server_token.txt"))
    parser.add_argument("--no-auth", action="store_true")
    parser.add_argument("--ssl-cert", type=Path)
    parser.add_argument("--ssl-key", type=Path)
    args = parser.parse_args()

    state = ChatState(
        args.checkpoint,
        args.memory,
        args.knowledge,
        args.network_config,
        args.realtime_config,
        args.hub_profile,
        args.persona,
        args.conversation_log,
        args.device,
        use_knowledge_cache=not args.no_knowledge_cache,
        use_live_web=args.live_web,
        use_realtime_data=not args.no_realtime_data,
    )
    handler = make_handler(state, ROOT / "web")
    auth_token = resolve_auth_token(args)
    handler.auth_token = auth_token
    server = ThreadingHTTPServer((args.host, args.port), handler)
    scheme = "http"
    if args.ssl_cert or args.ssl_key:
        if not args.ssl_cert or not args.ssl_key:
            raise SystemExit("--ssl-cert and --ssl-key must be provided together.")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=args.ssl_cert, keyfile=args.ssl_key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    print(f"Serving on {scheme}://{args.host}:{args.port}")
    if auth_token:
        print(f"Auth token file: {args.auth_token_file}")
        print("Remote clients must send this token with X-Companion-Token.")
    else:
        print("WARNING: auth is disabled. Only use this for trusted local testing.")
    server.serve_forever()


if __name__ == "__main__":
    main()
