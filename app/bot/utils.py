# app/bot/utils.py
from __future__ import annotations
import re
from typing import Optional

def normalize(text: str) -> str:
    return (text or "").strip()

def extract_choice(text: str) -> Optional[str]:
    """
    Aceita: "1", "1)", "opção 1", "opcao 1", "menu 1", etc.
    Retorna "0".."9" se achar.
    """
    t = (text or "").strip().lower()
    if not t:
        return None

    # match número isolado no começo
    m = re.match(r"^\s*([0-9])\s*[\)\-\.]?\s*$", t)
    if m:
        return m.group(1)

    # match "opcao 1" / "opção 1"
    m = re.search(r"(opcao|opção|menu)\s*([0-9])", t)
    if m:
        return m.group(2)

    return None