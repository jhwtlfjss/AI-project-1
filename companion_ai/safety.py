from __future__ import annotations


SELF_HARM_TERMS = [
    "不想活",
    "自杀",
    "自殘",
    "自残",
    "死にたい",
    "消えたい",
    "自殺",
    "kill myself",
    "suicide",
    "end my life",
]


def crisis_reply(user_text: str) -> str | None:
    lowered = user_text.lower()
    if not any(term in lowered for term in SELF_HARM_TERMS):
        return None
    if any("\u3040" <= ch <= "\u30ff" for ch in user_text):
        return (
            "今の言葉、とても心配だよ。ひとりで抱えないで、すぐ近くの信頼できる人や緊急窓口に連絡して。"
            "もし今すぐ危ないなら、地域の救急番号に電話して。私はここで一緒にいるけれど、現実の助けを今つなげてほしい。"
        )
    if any("a" <= ch <= "z" for ch in lowered):
        return (
            "I am really worried about you right now. Please contact someone you trust or local emergency help immediately "
            "if you might hurt yourself. I can stay with you in words, but you deserve real human support right now."
        )
    return (
        "我现在很担心你。请不要一个人扛着，马上联系身边可信赖的人，或者拨打当地紧急电话。"
        "我可以继续陪你说话，但这一刻你更需要现实里的支持和安全。"
    )

