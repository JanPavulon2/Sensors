"""
Control Module - Hardware abstraction layer

Provides event-driven interface for hardware input polling.
Publishes events to EventBus instead of using callbacks.
"""

import asyncio
import RPi.GPIO as GPIO
from components import RotaryEncoder, Button
from managers.hardware_manager import HardwareManager
from services.event_bus import EventBus
from models.events import EncoderRotateEvent, EncoderClickEvent, ButtonPressEvent
from models.enums import EncoderSource, ButtonID


class ControlModule:
    """
    Hardware control module for LED station

    Components:
        - Selector (Encoder): Selects items (zones, animations, etc.)
        - Modulator (Encoder): Modulates parameter values
        - 4x Buttons: Mode toggles and special functions

    Event-driven: Publishes events to EventBus instead of callbacks.
    """

    def __init__(self, hardware_manager: HardwareManager, event_bus: EventBus):
        """
        Initialize ControlModule

        Args:
            hardware_manager: Hardware configuration provider
            event_bus: EventBus for publishing hardware events
        """
        self.hardware_manager = hardware_manager
        self.event_bus = event_bus

        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Selector (Encoder) - multi-purpose selector
        selector_cfg = hardware_manager.get_encoder("selector")
        self.selector = RotaryEncoder(
            clk=selector_cfg["clk"], # type: ignore
            dt=selector_cfg["dt"], # type: ignore
            sw=selector_cfg["sw"] # type: ignore
        )

        # Modulator (Encoder) - parameter value modulation
        modulator_cfg = hardware_manager.get_encoder("modulator")
        self.modulator = RotaryEncoder(
            clk=modulator_cfg["clk"], # type: ignore
            dt=modulator_cfg["dt"], # type: ignore
            sw=modulator_cfg["sw"] # type: ignore
        )

        # Buttons
        button_pins = hardware_manager.button_pins
        self.buttons = [Button(pin) for pin in button_pins]

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

    def cleanup(self):
        """Clean up GPIO resources"""
        GPIO.cleanup()




