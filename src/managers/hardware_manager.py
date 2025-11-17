"""
Hardware Manager

Loads hardware configuration and provides access to GPIO pin assignments.
Returns simple dicts compatible with existing component constructors.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, TypedDict


class LEDStripConfig(TypedDict, total=False):
    """Type definition for LED strip configuration"""
    gpio: int
    zones: List[str]
    color_order: str
    count: Optional[int]
    brightness: Optional[int]


class HardwareManager:
    """
    Manages hardware configuration from hardware.yaml

    Provides access to:
    - Encoder GPIO configurations (as dicts)
    - Button GPIO pins
    - LED strip specifications (as dicts)

    Example:
        hw_mgr = HardwareManager()
        hw_mgr.load()

        # Get encoder pins
        zone_enc = hw_mgr.get_encoder("zone_selector")
        # Returns: {"clk": 5, "dt": 6, "sw": 13}
        encoder = RotaryEncoder(**zone_enc)  # Unpack directly

        # Get button pins
        buttons = hw_mgr.button_pins  # [22, 26, 23, 24]

        # Get LED strip config
        strip_cfg = hw_mgr.get_led_strip("strip")
        # Returns: {"gpio": 18, "count": 45, "color_order": "BRG", "brightness": 255}
    """

    def __init__(self, config_path="config/hardware.yaml"):
        """
        Initialize HardwareManager

        Args:
            config_path: Path to hardware.yaml (relative to src/ directory)
        """
        self.config_path = Path(config_path)
        self.data = {}

    def load(self):
        """
        Load hardware configuration from YAML

        Raises:
            FileNotFoundError: If hardware.yaml doesn't exist
            ValueError: If configuration is malformed
        """
        # Resolve path relative to src/ directory
        src_dir = Path(__file__).parent.parent
        full_path = src_dir / self.config_path

        if not full_path.exists():
            raise FileNotFoundError(f"Hardware config not found: {full_path}")

        # Load YAML
        with open(full_path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)

        return self.data

    # ===== Encoder Access =====

    def get_encoder(self, name: str) -> Optional[Dict[str, int]]:
        """
        Get encoder GPIO configuration by name

        Args:
            name: Encoder name (e.g., "zone_selector", "modulator")

        Returns:
            Dict with keys: clk, dt, sw (GPIO pin numbers)
            None if not found

        Example:
            enc = hw_mgr.get_encoder("zone_selector")
            # {"clk": 5, "dt": 6, "sw": 13}
            encoder = RotaryEncoder(**enc)
        """
        encoders = self.data.get('encoders', {})
        return encoders.get(name)

    @property
    def encoders(self) -> Dict[str, Dict[str, int]]:
        """
        Get all encoder configurations

        Returns:
            Dict mapping encoder name to pin config
        """
        return self.data.get('encoders', {})

    # ===== Button Access =====

    @property
    def button_pins(self) -> List[int]:
        """
        Get list of button GPIO pins

        Returns:
            List of GPIO pin numbers (e.g., [22, 26, 23, 24])
        """
        return self.data.get('buttons', [])

    def get_button_pin(self, index: int) -> Optional[int]:
        """
        Get button GPIO pin by index

        Args:
            index: Button index (0-based)

        Returns:
            GPIO pin number or None if index out of range
        """
        pins = self.button_pins
        if 0 <= index < len(pins):
            return pins[index]
        return None

    # ===== LED Strip Access =====

    def get_led_strip(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get LED strip configuration by name

        Args:
            name: Strip name (e.g., "strip", "preview")

        Returns:
            Dict with keys: gpio, count, color_order, brightness
            None if not found

        Example:
            strip_cfg = hw_mgr.get_led_strip("strip")
            # {"gpio": 18, "count": 45, "color_order": "BRG", "brightness": 255}
        """
        led_strips = self.data.get('led_strips', [])
        return led_strips.get(name)

    @property
    def led_strips(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all LED strip configurations (named strips)

        Returns:
            Dict mapping strip name to config dict
        """
        leds = self.data.get('leds', {})
        # Return only non-list items (legacy named strips, not the new led_strips list)
        return {k: v for k, v in leds.items() if not isinstance(v, list) and k != 'led_strips'}

    def get_gpio_to_zones_mapping(self) -> List[LEDStripConfig]:
        """
        Get GPIO-to-zones mapping for multi-GPIO strip support

        Returns:
            List of LEDStripConfig dicts describing which zones are on each GPIO pin
            Each dict contains: gpio (int), zones (List[str]), color_order (str)

        Example:
            mapping = hw_mgr.get_gpio_to_zones_mapping()
            # [
            #   {"gpio": 18, "zones": ["FLOOR", "LEFT", "TOP", ...], "color_order": "BRG"},
            #   {"gpio": 19, "zones": ["PIXEL", "PREVIEW"], "color_order": "GRB"}
            # ]
        """
        leds = self.data.get('leds', {})
        led_strips = leds.get('led_strips', [])
        return led_strips if isinstance(led_strips, list) else []

    # ===== Validation =====

    def validate_gpio_pins(self) -> List[str]:
        """
        Validate GPIO pin assignments and detect conflicts

        Returns:
            List of warning/error messages (empty if no issues)

        Checks:
        - WS281x GPIO compatibility (only 10, 12, 18, 21 supported)
        - Pin conflicts (same GPIO used multiple times)
        """
        warnings = []
        used_pins = {}

        # Check encoder pins
        for enc_name, enc_cfg in self.encoders.items():
            for pin_name in ['clk', 'dt', 'sw']:
                pin = enc_cfg.get(pin_name)
                if pin in used_pins:
                    warnings.append(
                        f"GPIO {pin} conflict: {enc_name}.{pin_name} and {used_pins[pin]}"
                    )
                used_pins[pin] = f"{enc_name}.{pin_name}"

        # Check button pins
        for idx, pin in enumerate(self.button_pins):
            if pin in used_pins:
                warnings.append(
                    f"GPIO {pin} conflict: button[{idx}] and {used_pins[pin]}"
                )
            used_pins[pin] = f"button[{idx}]"

        # Check LED strip pins
        WS281X_SUPPORTED_PINS = [10, 12, 18, 21]
        for strip_name, strip_cfg in self.led_strips.items():
            pin = strip_cfg.get('gpio')

            if pin in used_pins:
                warnings.append(
                    f"GPIO {pin} conflict: LED strip '{strip_name}' and {used_pins[pin]}"
                )
            used_pins[pin] = f"LED strip '{strip_name}'"

            # WS281x library check (warning only, not error)
            if pin not in WS281X_SUPPORTED_PINS:
                warnings.append(
                    f"LED strip '{strip_name}' uses GPIO {pin} which is not officially "
                    f"supported by rpi_ws281x (supported: {WS281X_SUPPORTED_PINS}). "
                    f"May work depending on library version."
                )

        return warnings

    # ===== Debug Output =====

    def print_summary(self):
        """Print hardware configuration summary"""
        print("=" * 70)
        print("HARDWARE CONFIGURATION")
        print("=" * 70)

        print("\nEncoders:")
        for name, cfg in self.encoders.items():
            print(f"  {name:15} CLK={cfg['clk']}, DT={cfg['dt']}, SW={cfg['sw']}")

        print(f"\nButtons: {self.button_pins}")
        for idx, pin in enumerate(self.button_pins):
            print(f"  BTN{idx+1} (index {idx}): GPIO {pin}")

        print("\nLED Strips:")
        for name, cfg in self.led_strips.items():
            count_str = f"{cfg['count']} px" if 'count' in cfg else "auto-calc"
            print(f"  {name:10} GPIO {cfg['gpio']}: {count_str}, {cfg['color_order']}")

        # Validation warnings
        warnings = self.validate_gpio_pins()
        if warnings:
            print("\n�  GPIO WARNINGS:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\n GPIO validation passed (no conflicts)")

        print("=" * 70)
