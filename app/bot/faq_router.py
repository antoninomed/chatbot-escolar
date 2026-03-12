# app/bot/faq_router.py
from __future__ import annotations
from app.bot.faq_data import FAQ

def resolve_faq(text: str) -> str | None:
    t = (text or "").lower()
    for key, answer in FAQ.items():
        if key in t:
            return answer
    return None