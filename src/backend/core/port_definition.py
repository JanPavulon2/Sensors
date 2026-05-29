from dataclasses import dataclass
from enum import Enum, auto


class PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class SignalType(Enum):
    BOOL = auto()
    INT = auto()
    FLOAT = auto()
    RGB = auto()
    FRAME = auto()
    DELTA_INT = auto()


@dataclass(frozen=True)
class PortDefinition:
    """Static port contract declared on a DeviceDefinition."""

    name: str
    direction: PortDirection
    signal_type: SignalType
