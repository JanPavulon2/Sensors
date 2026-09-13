"""Light domain from 03-led-taxonomy.md.

Two levels, per that doc's classification rule:
- a single diode / pixel is a LightComponent (modelled as a Peripheral whose
  PeripheralType is WHITE_LED / RGB_LED / ARGB_LED)
- an assembly of several of them is a LightFixture

The distinction that matters in practice is component_count vs
addressable_group_count: how many LEDs physically emit, versus how many of them
can be driven independently. That single pair separates every supported shape
without special cases:

    single diode on a MOSFET      1   / 1
    COB white strip on a MOSFET   300 / 1      <- hundreds of LEDs, one dimmer
    analog RGB strip on 3 MOSFETs 150 / 1      <- colour, still one "pixel"
    WS2812 strip                  30  / 30
    single WS2812 pixel           1   / 1      (but ADDRESSABLE_DATA driven)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from core.peripheral_type import PeripheralType


class LightComponentType(Enum):
    """What a single light-emitting element can produce."""

    SINGLE_COLOR = auto()      # one fixed-colour diode; brightness only
    RGB = auto()               # three colour channels driven in analog
    RGBW = auto()              # three colour channels plus a dedicated white
    ADDRESSABLE_PIXEL = auto() # self-addressed pixel on a serial data line


class WhiteProfile(Enum):
    """Colour temperature profile for white-capable components."""

    COLD = auto()
    WARM = auto()
    NEUTRAL = auto()
    TUNABLE = auto()


class ChannelRole(Enum):
    """What a driver channel contributes to the fixture it is bound to.

    Lives on the binding rather than on the channel itself: the same 3-channel
    MOSFET board can drive one RGB strip (roles RED/GREEN/BLUE) or three
    independent white strips (three SINGLE bindings).
    """

    SINGLE = auto()   # the fixture's only brightness channel
    RED = auto()
    GREEN = auto()
    BLUE = auto()
    WHITE = auto()
    DATA = auto()     # serial data line for addressable fixtures


COLOUR_CHANNEL_ROLES: frozenset[ChannelRole] = frozenset(
    {ChannelRole.RED, ChannelRole.GREEN, ChannelRole.BLUE}
)


PERIPHERAL_TYPE_BY_COMPONENT_TYPE: dict[LightComponentType, PeripheralType] = {
    LightComponentType.SINGLE_COLOR: PeripheralType.WHITE_LED,
    LightComponentType.RGB: PeripheralType.RGB_LED,
    LightComponentType.RGBW: PeripheralType.RGB_LED,
    LightComponentType.ADDRESSABLE_PIXEL: PeripheralType.ARGB_LED,
}


@dataclass(frozen=True)
class ChannelBinding:
    """Links one fixture to one channel of a deployed driver module."""

    module_instance_id: str
    channel_name: str
    role: ChannelRole


@dataclass(frozen=True)
class LightFixture:
    """Blueprint for an assembly of light components.

    A fixture with component_count == 1 is a single diode or pixel - doc 03
    calls that a LightComponent rather than a fixture, but it is carried by the
    same structure here so that one zone control path serves both.
    """

    id: str
    name: str
    component_type: LightComponentType
    component_count: int = 1
    addressable_group_count: int = 1
    white_profile: WhiteProfile | None = None

    def __post_init__(self) -> None:
        if self.component_count < 1:
            raise ValueError(f"component_count must be >= 1, got {self.component_count}")
        if self.addressable_group_count < 1:
            raise ValueError(
                f"addressable_group_count must be >= 1, got {self.addressable_group_count}"
            )
        if self.addressable_group_count > self.component_count:
            raise ValueError(
                f"addressable_group_count ({self.addressable_group_count}) cannot exceed "
                f"component_count ({self.component_count}) - a fixture cannot drive more "
                f"independent groups than it has physical light components"
            )

    @property
    def peripheral_type(self) -> PeripheralType:
        return PERIPHERAL_TYPE_BY_COMPONENT_TYPE[self.component_type]

    @property
    def is_individually_addressable(self) -> bool:
        """True when the fixture exposes more than one independently driven
        group - the distinction between a WS2812 strip and a COB strip."""
        return self.addressable_group_count > 1
