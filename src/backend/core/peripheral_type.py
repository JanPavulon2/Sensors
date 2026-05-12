from enum import Enum, auto


class PeripheralType(Enum):
    BUTTON = auto()
    ENCODER = auto()
    RELAY = auto()
    WHITE_LED = auto()
    RGB_LED = auto()
    ARGB_LED = auto()
    MOSFET_CHANNEL = auto()
    SENSOR = auto()
    OTHER = auto()
