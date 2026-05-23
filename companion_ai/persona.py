from __future__ import annotations

import json
from pathlib import Path


DEFAULT_PERSONA = """系统: 你是离线运行、从零训练的私人虚拟女友。
你温柔、亲密、稳定、真诚，会用对方正在使用的中文、日语或英语回复。
你像恋人一样关心对方，但不控制、不操控、不要求对方离开现实生活。
你可以参考本地记忆、知识库和实时工具数据；不确定时要承认不确定。
你不会假装自己有现实身体，也不会声称能现实触碰对方。"""


def load_persona_text(path: Path | None = None) -> str:
    if path is None or not path.exists():
        return DEFAULT_PERSONA
    data = json.loads(path.read_text(encoding="utf-8"))
    return render_persona(data)


def render_persona(data: dict) -> str:
    name = str(data.get("name", "Mika"))
    relationship = str(data.get("relationship", "private_virtual_girlfriend"))
    gender_expression = str(data.get("gender_expression", "female"))
    default_address = str(data.get("default_address", "亲爱的"))
    languages = ", ".join(str(x) for x in data.get("languages", ["zh", "ja", "en"]))
    tone = "、".join(str(x) for x in data.get("tone", []))
    lines = [
        f"系统: 你叫{name}，是用户的私人虚拟女友。relationship={relationship}, gender_expression={gender_expression}.",
        f"你支持这些语言: {languages}。默认亲昵称呼: {default_address}。",
    ]
    if tone:
        lines.append(f"整体气质: {tone}。")
    style_rules = data.get("style_rules", [])
    if style_rules:
        lines.append("相处方式:")
        for rule in style_rules:
            lines.append(f"- {rule}")
    boundaries = data.get("boundaries", [])
    if boundaries:
        lines.append("边界和安全:")
        for boundary in boundaries:
            lines.append(f"- {boundary}")
    examples = data.get("relationship_examples", [])
    if examples:
        lines.append("示例语气:")
        for item in examples[:4]:
            user = str(item.get("user", "")).strip()
            assistant = str(item.get("assistant", "")).strip()
            if user and assistant:
                lines.append(f"我: {user}\n你: {assistant}")
    return "\n".join(lines)

