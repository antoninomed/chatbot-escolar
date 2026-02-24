from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, List

@dataclass
class Msg:
    role: str   # "user" or "assistant"
    content: str

_store: Dict[str, Deque[Msg]] = defaultdict(lambda: deque(maxlen=12))

def remember(user_id: str, role: str, content: str) -> None:
    _store[user_id].append(Msg(role=role, content=content))

def recent_history(user_id: str) -> List[Msg]:
    return list(_store[user_id])