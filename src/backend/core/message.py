
# =========================================================
# core/message.py
# =========================================================

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any


class MessageType(str, Enum):
    EVENT = "event"
    COMMAND = "command"


@dataclass
class Message:
    type: MessageType
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)

