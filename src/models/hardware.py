"""
Hardware Configuration Models

These are PURE DATA MODELS that exactly mirror hardware.yaml.
They contain:
- no logic
- no validation
- no external dependencies

They serve as typed containers for HardwareManager to populate.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Literal, Optional
from models.enums import EncoderID, LEDStripID, LEDStripType, ButtonID, ColorMode

# ============================================================
#  Encoders
# ============================================================

@dataclass(frozen=True)
class EncoderConfig:
    """Single rotary encoder with clk/dt and optional push switch."""
    id: EncoderID
    clk: int
    dt: int
    sw: Optional[int] = None   # Some encoders may not use a switch

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
@dataclass(frozen=True)
class EncodersConfig:
    """All encoders defined in hardware.yaml"""
    selector: Optional[EncoderConfig] = None
    modulator: Optional[EncoderConfig] = None


# ============================================================
#  Buttons
# ============================================================

@dataclass(frozen=True)
class ButtonConfig:
    id: ButtonID
    gpio: int

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class ButtonsConfig:
    buttons: List[ButtonConfig]


# ============================================================
#  LED Strips
# ============================================================

ColorOrder = Literal["RGB", "GRB", "BRG"]

@dataclass(frozen=True)
class LEDStripConfig:
    """
    Physical LED strip connected to a GPIO pin.
    In YAML, 'id' is a free-form string like 'PIXEL', 'PREVIEW'.
    """
    id: LEDStripID
    gpio: int
    type: LEDStripType
    color_order: ColorOrder
    count: Optional[int] = None
    voltage: float = 5.0
    frequency_hz: int = 800_000
    enabled: bool = True
    
    def __post_init__(self):
        if self.count is not None and self.count < 0:
            raise ValueError("LEDStripConfig.count must be >= 0")
        if not (0.0 < self.voltage <= 24.0):
            raise ValueError("LEDStripConfig.voltage seems invalid (expected 0-24V)")
        
    @property
    def led_count(self) -> int:
        """Bezpieczna liczba LEDów: jeśli count nie ustawiony -> 0 (consumers may treat 0 as 'auto')."""
        return self.count or 0

    @property
    def display_name(self) -> str:
        return self.id.name.replace("_", " ").title()

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["type"] = self.type.value if isinstance(self.type, LEDStripType) else d.get("type")
        d["color_order"] = self.color_order if isinstance(self.color_order, ColorOrder) else d.get("color_order")
        return d
    
@dataclass(frozen=True)
class LEDStripsConfig:
    """Container for multiple strips (list, not dict)."""
    strips: List[LEDStripConfig]

# ============================================================
#  Root Hardware Model
# ============================================================

@dataclass(frozen=True)
class HardwareConfig:
    """
    The root model representing the entire hardware.yaml.
    Mirrors YAML exactly and contains no behavior.
    """

    encoders: EncodersConfig
    buttons: ButtonsConfig
    led_strips: LEDStripsConfig