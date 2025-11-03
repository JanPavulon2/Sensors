"""
Control Panel - Hardware Abstraction Layer (Layer 1)

Physical control panel entity containing 2 encoders, 4 buttons, and preview panel.
This is a fixed hardware module that cannot be extended.

Provides event-driven interface for hardware input polling.
Publishes events to EventBus instead of using callbacks.
"""

import asyncio
from components import RotaryEncoder, Button, PreviewPanel
from managers.hardware_manager import HardwareManager
from managers.GPIOManager import GPIOManager
from services.event_bus import EventBus
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent
from models.enums import EncoderSource, ButtonID


class ControlPanel:
    """
    Hardware control panel for LED station

    Physical components (fixed hardware):
        - Selector (Encoder): Selects items (zones, animations, etc.)
        - Modulator (Encoder): Modulates parameter values
        - 4x Buttons: Mode toggles and special functions
        - Preview Panel (CJMCU-2812-8): 8 RGB LEDs for previews

    Event-driven: Publishes events to EventBus instead of callbacks.
    """

    def __init__(
        self,
        hardware_manager: HardwareManager,
        event_bus: EventBus,
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
        self.event_bus = event_bus
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
        self.buttons = [Button(pin, gpio_manager) for pin in button_pins]

        # Preview Panel (CJMCU-2812-8)
        # preview_cfg = hardware_manager.get_preview_config()
        # self.preview_panel = PreviewPanel(
        #     gpio=preview_cfg["gpio"], # type: ignore
        #     gpio_manager=gpio_manager
        # )

    def poll(self):
        """
        Poll all hardware inputs and publish events to EventBus

        Call this in main loop to process hardware events.
        """
        # Selector rotation
        delta = self.selector.read()
        if delta != 0:
            event = EncoderRotateEvent(EncoderSource.SELECTOR, delta)
            asyncio.create_task(self.event_bus.publish(event))

        # Selector button
        if self.selector.is_pressed():
            event = EncoderClickEvent(EncoderSource.SELECTOR)
            asyncio.create_task(self.event_bus.publish(event))

        # Modulator rotation
        delta = self.modulator.read()
        if delta != 0:
            event = EncoderRotateEvent(EncoderSource.MODULATOR, delta)
            asyncio.create_task(self.event_bus.publish(event))

        # Modulator button
        if self.modulator.is_pressed():
            event = EncoderClickEvent(EncoderSource.MODULATOR)
            asyncio.create_task(self.event_bus.publish(event))

        # Buttons (map index to ButtonID enum)
        button_ids = [ButtonID.BTN1, ButtonID.BTN2, ButtonID.BTN3, ButtonID.BTN4]
        for i, btn in enumerate(self.buttons):
            if btn.is_pressed():
                event = ButtonPressEvent(button_ids[i])
                asyncio.create_task(self.event_bus.publish(event))





