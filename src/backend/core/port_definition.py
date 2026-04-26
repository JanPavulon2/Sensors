from dataclasses import dataclass
from enum import Enum


class PortDirection(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class SignalType(str, Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    RGB = "rgb"
    FRAME = "frame"
    DELTA_INT = "delta_int"


@dataclass(frozen=True)
class PortDefinition:
    """Static port contract declared on a DeviceDefinition."""

    name: str
    direction: PortDirection
    signal_type: SignalType
