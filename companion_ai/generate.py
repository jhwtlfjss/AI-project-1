from __future__ import annotations

from pathlib import Path

import torch

from companion_ai.knowledge import KnowledgeBase, render_knowledge_context
from companion_ai.memory import CompanionMemory
from companion_ai.model import GPT, GPTConfig
from companion_ai.persona import DEFAULT_PERSONA
from companion_ai.safety import crisis_reply
from companion_ai.tokenizer import ByteTokenizer


def load_model(checkpoint: Path, device: str = "auto"):
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    ckpt = torch.load(checkpoint, map_location=device)
    model_args = ckpt["model_args"]
    config = GPTConfig(**model_args)
    model = GPT(config)
    model.load_state_dict(ckpt["model"])
    model.to(device)
    model.eval()
    return model, device


def build_prompt(
    memory: CompanionMemory,
    user_text: str,
    knowledge: KnowledgeBase | None = None,
    live_context: str = "",
    realtime_context: str = "",
    persona_text: str = DEFAULT_PERSONA,
    max_knowledge_chars: int = 520,
) -> str:
    memory_text = memory.render(query=user_text, max_facts=6, max_turns=6)
    parts = [persona_text]
    if memory_text:
        parts.append(memory_text)
    if knowledge is not None:
        knowledge_text = render_knowledge_context(knowledge.search(user_text), max_chars=max_knowledge_chars)
        if knowledge_text:
            parts.append("可参考知识:\n" + knowledge_text)
    if live_context:
        parts.append("实时网络参考:\n" + live_context)
    if realtime_context:
        parts.append("实时工具数据:\n" + realtime_context)
    parts.append(f"我: {user_text}\n你:")
    return "\n\n".join(parts)


@torch.no_grad()
def generate_reply(
    model: GPT,
    device: str,
    memory: CompanionMemory,
    user_text: str,
    knowledge: KnowledgeBase | None = None,
    live_context: str = "",
    realtime_context: str = "",
    persona_text: str = DEFAULT_PERSONA,
    max_new_tokens: int = 220,
    temperature: float = 0.85,
    top_k: int = 80,
) -> str:
    crisis = crisis_reply(user_text)
    if crisis:
        return crisis

    tokenizer = ByteTokenizer()
    prompt = build_prompt(
        memory,
        user_text,
        knowledge=knowledge,
        live_context=live_context,
        realtime_context=realtime_context,
        persona_text=persona_text,
    )
    ids = tokenizer.encode(prompt, add_bos=True, add_eos=False)
    if len(ids) > model.config.block_size:
        ids = ids[-model.config.block_size :]
    x = torch.tensor([ids], dtype=torch.long, device=device)
    y = model.generate(
        x,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        top_k=top_k,
        eos_id=ByteTokenizer.EOS,
    )
    text = tokenizer.decode(y[0].tolist())
    reply = text[len(tokenizer.decode(ids)) :]
    for stop in ["\n我:", "\n用户:", "\nUser:", "\nHuman:", "\n系统:"]:
        if stop in reply:
            reply = reply.split(stop, 1)[0]
    reply = reply.replace("<|end|>", "").strip()
    return reply or "我在这里。你可以再靠近一点，把刚才那句话慢慢说给我听。"
