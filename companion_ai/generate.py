from __future__ import annotations

from pathlib import Path
import re

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
    max_new_tokens: int = 110,
    temperature: float = 0.55,
    top_k: int = 32,
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
    for stop in ["\n我:", "\n用户:", "\nUser:", "\nHuman:", "\n系统:", "\nSystem:"]:
        if stop in reply:
            reply = reply.split(stop, 1)[0]
    reply = reply.replace("<|end|>", "").strip()
    reply = trim_reply(reply)
    if looks_unstable(reply):
        return fallback_reply(user_text)
    return reply or fallback_reply(user_text)


def trim_reply(text: str, max_chars: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    for mark in ["。", "！", "？", ".", "!", "?"]:
        cut = text.rfind(mark, 0, max_chars)
        if cut >= 24:
            return text[: cut + 1].strip()
    return text[:max_chars].rstrip() + "..."


def looks_unstable(text: str) -> bool:
    if len(text.strip()) < 2:
        return True
    if "�" in text or "\x00" in text:
        return True
    if re.search(r"(.)\1{5,}", text):
        return True
    if len(re.findall(r"[{}\[\]<>|_^~`]", text)) >= 5:
        return True
    chunks = [text[i : i + 3] for i in range(max(0, len(text) - 2))]
    if chunks:
        most_common = max(chunks.count(chunk) for chunk in set(chunks))
        if most_common >= 5:
            return True
    return False


def fallback_reply(user_text: str) -> str:
    if any("\u3040" <= ch <= "\u30ff" for ch in user_text):
        return "ごめん、今の私はまだ少し不安定だから、無理に作って話さないね。そばにいるから、もう少し短く聞かせて。"
    if all(ord(ch) < 128 for ch in user_text) and any(ch.isalpha() for ch in user_text):
        return "I am still a very early local model, so I will not pretend I understood perfectly. I am here with you. Say it a little more simply, and I will stay steady."
    return "我现在还是很早期的本地模型，刚才可能会乱说。先让我稳一点：我在这里，你可以短一点慢慢告诉我。"
