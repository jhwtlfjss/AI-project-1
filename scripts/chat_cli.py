from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion_ai.generate import generate_reply, load_model
from companion_ai.knowledge import KnowledgeBase
from companion_ai.live_web import LiveWebClient
from companion_ai.memory import CompanionMemory
from companion_ai.conversation_log import append_turn
from companion_ai.persona import load_persona_text
from companion_ai.realtime_data import RealtimeDataClient


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--memory", type=Path, default=Path("memory.json"))
    parser.add_argument("--knowledge", type=Path, default=Path("data/knowledge.jsonl"))
    parser.add_argument("--network-config", type=Path, default=Path("configs/network_access.json"))
    parser.add_argument("--realtime-config", type=Path, default=Path("configs/realtime_data.json"))
    parser.add_argument("--persona", type=Path, default=Path("configs/girlfriend_persona.json"))
    parser.add_argument("--conversation-log", type=Path, default=Path("logs/conversations.jsonl"))
    parser.add_argument("--live-web", action="store_true")
    parser.add_argument("--no-realtime-data", action="store_true")
    parser.add_argument("--no-knowledge-cache", action="store_true")
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    model, device = load_model(args.checkpoint, args.device)
    memory = CompanionMemory.load(args.memory)
    knowledge = None if args.no_knowledge_cache else KnowledgeBase.load(args.knowledge)
    memory.save(args.memory)
    if knowledge is not None:
        knowledge.save(args.knowledge)
    live_web = LiveWebClient.load(args.network_config) if args.live_web else None
    realtime_data = None if args.no_realtime_data else RealtimeDataClient.load(args.realtime_config)
    persona_text = load_persona_text(args.persona)
    print("Companion is ready. Type /exit to quit.")
    while True:
        user_text = input("我> ").strip()
        if user_text in {"/exit", "/quit"}:
            break
        if not user_text:
            continue
        if not args.no_knowledge_cache:
            knowledge = KnowledgeBase.load(args.knowledge)
        live_context = ""
        live_results = []
        if live_web:
            live_context, live_results = live_web.lookup_context(user_text)
            if knowledge is not None and live_results:
                live_web.cache_results(knowledge, live_results)
                knowledge.save(args.knowledge)
        realtime_context = ""
        realtime_results = []
        if realtime_data:
            realtime_context, realtime_results = realtime_data.context_for_prompt(user_text)
            if knowledge is not None and realtime_results:
                realtime_data.cache_results(knowledge, realtime_results)
                knowledge.save(args.knowledge)
        reply = generate_reply(
            model,
            device,
            memory,
            user_text,
            knowledge=knowledge,
            live_context=live_context,
            realtime_context=realtime_context,
            persona_text=persona_text,
        )
        print(f"你> {reply}")
        memory.maybe_capture_fact(user_text)
        memory.add_turn(user_text, reply)
        memory.save(args.memory)
        append_turn(
            args.conversation_log,
            user_text,
            reply,
            {
                "client": "cli",
                "persona": str(args.persona),
                "live_web": bool(live_context),
                "realtime_data": bool(realtime_context),
            },
        )


if __name__ == "__main__":
    main()
