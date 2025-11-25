"""
HardwareManager v3
==================

!!! THIS VERSION MATCHES ConfigManager ARCHITECTURE EXACTLY !!!

- Does NOT load YAML.
- ConfigManager assigns raw dict via .data
- HardwareManager converts dict → typed HardwareConfig
- Registers GPIO pins through GPIOManager
- No dependency on zones
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List

from models.hardware import (
    HardwareConfig,
    BuzzersConfig,
    BuzzerConfig,
    EncodersConfig,
    EncoderConfig,
    ButtonConfig,
    ButtonsConfig,
    LEDStripsConfig,
    LEDStripConfig,
)
from models.enums import BuzzerID, LEDStripID, LEDStripType, ButtonID, EncoderID

from hardware.gpio.gpio_manager import GPIOManager
from utils.logger import get_logger, LogCategory
from utils.serialization import Serializer

log = get_logger().for_category(LogCategory.HARDWARE)

WS281X_ALLOWED_PINS = [10, 12, 18, 21, 19]  # 19 works on many boards

class HardwareManager:
    """
    HardwareManager v3:

    - Receives raw dict (ConfigManager.data)
    - Parses ONLY hardware-related sections
    - Produces HardwareConfig dataclass
    - Registers all GPIO pins
    """

    def __init__(self, data: Dict[str, Any], gpio_manager: GPIOManager):
        self.data = data
        self.gpio = gpio_manager
        self.config: Optional[HardwareConfig] = None

        self.config = self._process_data()
        
    # ------------------------------------------------------
    # ENTRY POINT
    # ------------------------------------------------------

    def _process_data(self) -> HardwareConfig:
        """
        Called once by ConfigManager._initialize_managers().

        Steps:
        1. parse dict → dataclasses
        2. validate pins
        3. register GPIO pins
        """
        config = self._parse()
        self._validate(config)
        self._register(config)

        self.config = config

        log.info("HardwareManager initialized successfully")
        return config
    
    # ------------------------------------------------------
    # PARSER
    # ------------------------------------------------------

    def _parse(self) -> HardwareConfig:
        raw_buzz_list = self.data.get("buzzers", [])
        raw_enc_list = self.data.get("encoders", [])
        raw_buttons_list = self.data.get("buttons", [])
        raw_strips = self.data.get("led_strips", [])

        # Parse buzzers
        active_buzz = None
        passive_buzz = None
        for buzz_entry in raw_buzz_list:
            buzz_id_str = buzz_entry.get("id").upper()
            buzz_id = Serializer.str_to_enum(buzz_id_str, BuzzerID)
            if buzz_id == BuzzerID.ACTIVE:
                active_buzz = self._parse_buzzer(buzz_entry, buzz_id)
            elif buzz_id == BuzzerID.PASSIVE:
                passive_buzz = self._parse_buzzer(buzz_entry, buzz_id)

        buzz_cfg = BuzzersConfig(
            active=active_buzz,
            passive=passive_buzz
        )
        
        # Parse encoders (new format: list with id field)
        selector_enc = None
        modulator_enc = None
        for enc_entry in raw_enc_list:
            enc_id_str = enc_entry.get("id").upper()
            enc_id = Serializer.str_to_enum(enc_id_str, EncoderID)
            if enc_id == EncoderID.SELECTOR:
                selector_enc = self._parse_encoder(enc_entry, enc_id)
            elif enc_id == EncoderID.MODULATOR:
                modulator_enc = self._parse_encoder(enc_entry, enc_id)

        enc_cfg = EncodersConfig(
            selector=selector_enc,
            modulator=modulator_enc,
        )

        # Parse buttons (new format: list with id and gpio)
        button_list = []
        for btn_entry in raw_buttons_list:
            try:
                btn_id = ButtonID[btn_entry["id"]]
                button_list.append(
                    ButtonConfig(
                        id=btn_id,
                        gpio=btn_entry["gpio"],
                    )
                )
            except KeyError as e:
                log.warn(f"Invalid button entry: {btn_entry}, error: {e}")

        button_cfg = ButtonsConfig(buttons=button_list)

        # Parse LED strips
        strip_list: List[LEDStripConfig] = []
        for entry in raw_strips:
            try:
                strip_list.append(
                    LEDStripConfig(
                        id=LEDStripID[entry["id"]],
                        type=LEDStripType(entry["type"]),
                        gpio=entry["gpio"],
                        color_order=entry["color_order"],
                        count=entry.get("count"),
                        voltage=entry.get("voltage", 5.0),
                    )
                )
            except (KeyError, ValueError) as e:
                log.warn(f"Invalid LED strip entry: {entry}, error: {e}")

        led_cfg = LEDStripsConfig(strips=strip_list)

        return HardwareConfig(
            buzzers=buzz_cfg,
            encoders=enc_cfg,
            buttons=button_cfg,
            led_strips=led_cfg,
        )
        
    def _parse_encoder(self, entry: Optional[Dict[str, Any]], encoder_id: EncoderID) -> Optional[EncoderConfig]:
        if entry is None:
            return None
        try:
            return EncoderConfig(
                id=encoder_id,
                clk=entry["clk"],
                dt=entry["dt"],
                sw=entry.get("sw")
            )
        except KeyError as e:
            log.warn(f"Invalid encoder entry for {encoder_id.name}: missing key {e}")
            return None
        
    def _parse_buzzer(self, entry: Optional[Dict[str, Any]], buzzer_id: BuzzerID) -> Optional[BuzzerConfig]:
        if entry is None:
            return None
        try:
            return BuzzerConfig(
                id=buzzer_id,
                gpio=entry["gpio"]
            )
        except KeyError as e:
            log.warn(f"Invalid buzzer entry for {buzzer_id.name}: missing key {e}")
            return None
        
    # ------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------

    def _validate(self, cfg: HardwareConfig) -> None:
        used = {}

        # encoders
        for name, enc in [
            ("selector", cfg.encoders.selector),
            ("modulator", cfg.encoders.modulator),
        ]:
            if enc:
                for field, pin in [("clk", enc.clk), ("dt", enc.dt), ("sw", enc.sw)]:
                    if pin is None:
                        continue

                    if pin in used:
                        raise ValueError(
                            f"GPIO conflict: encoder {name}.{field} pin {pin} "
                            f"already used by {used[pin]}"
                        )
                    used[pin] = f"encoder.{name}.{field}"

        # buttons
        for i, btn in enumerate(cfg.buttons.buttons):
            if btn.gpio in used:
                raise ValueError(
                    f"GPIO conflict: button[{i}] pin {btn.gpio} already used by {used[btn.gpio]}"
                )
            used[btn.gpio] = f"button[{i}]"

        # LED strips
        for strip in cfg.led_strips.strips:
            pin = strip.gpio
            if pin in used:
                raise ValueError(
                    f"GPIO conflict: LED strip {strip.id.name} pin {pin} "
                    f"already used by {used[pin]}"
                )
            used[pin] = f"led_strip.{strip.id.name}"

            if pin not in WS281X_ALLOWED_PINS:
                log.warn(
                    f"WS281x strip '{strip.id.name}' uses GPIO {pin}, "
                    f"not officially recommended. Allowed: {WS281X_ALLOWED_PINS}"
                )


    
    # ------------------------------------------------------
    # REGISTRATION
    # ------------------------------------------------------

    def _register(self, cfg: HardwareConfig) -> None:

        # encoders
        for name, enc in [
            ("selector", cfg.encoders.selector),
            ("modulator", cfg.encoders.modulator),
        ]:
            if enc:
                self.gpio.register_input(enc.clk, f"Encoder({name}).clk")
                self.gpio.register_input(enc.dt, f"Encoder({name}).dt")
                if enc.sw is not None:
                    self.gpio.register_input(enc.sw, f"Encoder({name}).sw")

        # buttons
        for i, btn in enumerate(cfg.buttons.buttons):
            self.gpio.register_input(btn.gpio, f"Button[{i}]")

        # LED strips (WS281x)
        for strip in cfg.led_strips.strips:
            self.gpio.register_ws281x(strip.gpio, f"WS281xStrip({strip.id.name})")

        # buzzer
        for name, buzz in [
            ("active", cfg.buzzers.active),
            ("passive", cfg.buzzers.passive),
        ]:
            if buzz:
                self.gpio.register_output(buzz.gpio, f"Buzzer({name}).gpio")
                
    # ------------------------------------------------------
    # ACCESSORS
    # ------------------------------------------------------

    def get_encoder(self, encoder_id: str) -> Optional[Dict[str, Any]]:
        """
        Get encoder config by name (selector or modulator)

        Args:
            encoder_id: "selector" or "modulator"

        Returns:
            Dict with clk, dt, sw keys or None if not found
        """
        if not self.config:
            raise RuntimeError("HardwareManager not initialized")

        encoder = None
        if encoder_id == "selector":
            encoder = self.config.encoders.selector
        elif encoder_id == "modulator":
            encoder = self.config.encoders.modulator

        if encoder is None:
            return None

        return {
            "clk": encoder.clk,
            "dt": encoder.dt,
            "sw": encoder.sw,
        }

    @property
    def button_pins(self) -> List[int]:
        """
        Get list of GPIO pins for all buttons

        Returns:
            List of GPIO pin numbers
        """
        if not self.config:
            raise RuntimeError("HardwareManager not initialized")

        return [btn.gpio for btn in self.config.buttons.buttons]

    def get_strip(self, strip_id: LEDStripID) -> LEDStripConfig:
        if not self.config:
            raise RuntimeError("HardwareManager not initialized")

        for strip in self.config.led_strips.strips:
            if strip.id == strip_id:
                return strip

        raise KeyError(f"LED strip not found: {strip_id.name}")

    def get_gpio_to_zones_mapping(self) -> List[Dict[str, Any]]:
        """
        Get GPIO-to-zones mapping for multi-GPIO strip support

        Returns:
            List of dicts describing each LED strip: gpio, type, color_order, count, voltage, id

        Example:
            mapping = hw_mgr.get_gpio_to_zones_mapping()
            # [
            #   {"gpio": 18, "type": "WS2811_12V", "color_order": "BRG", "count": 100, "voltage": 12, "id": "MAIN_12V"},
            #   {"gpio": 19, "type": "WS2812_5V", "color_order": "GRB", "count": 38, "voltage": 5, "id": "AUX_5V"}
            # ]
        """
        if not self.config:
            raise RuntimeError("HardwareManager not initialized")

        return [
            {
                "gpio": strip.gpio,
                "type": strip.type.value,
                "color_order": strip.color_order,
                "count": strip.count,
                "voltage": strip.voltage,
                "id": strip.id.name,
            }
            for strip in self.config.led_strips.strips
        ]

    def cleanup(self):
        self.gpio.cleanup()
