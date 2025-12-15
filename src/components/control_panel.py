"""
Control Panel - Hardware Abstraction Layer (Layer 1)

Physical control panel entity containing 2 encoders, 4 buttons, and preview panel.
This is a fixed hardware module that cannot be extended.

Provides event-driven interface for hardware input polling.
Publishes events to EventBus instead of using callbacks.
"""

import asyncio
from components import RotaryEncoder, PreviewPanel
#from hardware.input.button import Button
from hardware import Button
from managers.hardware_manager import HardwareManager
from hardware.gpio.gpio_manager import GPIOManager
from services.event_bus import EventBus
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent
from models.enums import EncoderSource, ButtonID, LEDStripID


class ControlPanel:
    """
    Hardware control panel for LED station

    Physical components (fixed hardware):
        - Selector (Encoder): Selects items (zones, animations, etc.)
        - Modulator (Encoder): Modulates parameter values
        - 4x Buttons: Mode toggles and special functions
        - Preview Panel (CJMCU-2812-8): 8 RGB LEDs for previews
    """

    def __init__(
        self,
        hardware_manager: HardwareManager,
        gpio_manager: GPIOManager
    ):
        """
        Initialize ControlPanel

        Args:
            hardware_manager: Hardware configuration provider
            event_bus: EventBus for publishing hardware events
            gpio_manager: GPIOManager for GPIO pin registration
        """
        self.hardware_manager = hardware_manager
        self.gpio_manager = gpio_manager

        # Selector (Encoder) - multi-purpose selector
        selector_cfg = hardware_manager.get_encoder("selector")
        self.selector = RotaryEncoder(
            clk=selector_cfg["clk"], # type: ignore
            dt=selector_cfg["dt"], # type: ignore
            sw=selector_cfg["sw"], # type: ignore
            gpio_manager=gpio_manager
        )

        # Modulator (Encoder) - parameter value modulation
        modulator_cfg = hardware_manager.get_encoder("modulator")
        self.modulator = RotaryEncoder(
            clk=modulator_cfg["clk"], # type: ignore
            dt=modulator_cfg["dt"], # type: ignore
            sw=modulator_cfg["sw"], # type: ignore
            gpio_manager=gpio_manager
        )

        # Buttons
        button_pins = hardware_manager.button_pins
        self.buttons = [Button(pin) for pin in button_pins]

        # Preview Panel - initialized later in main_asyncio.py after zone_strips are created
        # PreviewPanel is a logical view of PREVIEW zone within ZoneStrip(GPIO 19)
        # It will be passed the zone_strip instance that contains both PIXEL and PREVIEW zones
        self.preview_panel = None





