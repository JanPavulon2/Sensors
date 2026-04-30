
# =========================================================
# core/message.py
# =========================================================

from dataclasses import dataclass, field
from enum import auto

from core.primitives import AutoSnakeStrEnum, JsonObject


class MessageType(AutoSnakeStrEnum):
    EVENT = auto()
    COMMAND = auto()


@dataclass
class Message:
    type: MessageType
    name: str
    payload: JsonObject = field(default_factory=dict)

