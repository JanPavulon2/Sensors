"""
Demo/test for logger system - shows example output
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger, configure_logger, LogLevel, LogCategory


def demo_logger():
    """Demonstrate logger output with various scenarios"""
    logger = get_logger()

    print("\n" + "=" * 70)
    print("LED Control Station - Logger Demo")
    print("=" * 70 + "\n")

    # System events
    logger.system("Application started", version="2.0", mode="STATIC")

    # Hardware events
    logger.encoder_event("zone_selector", "rotate", delta=1)
    logger.button_event(1, "pressed")

    # State changes
    logger.mode_change("STATIC", "ANIMATION")
    logger.state("Edit mode toggled", edit_mode="ON")

    # Zone changes
    logger.zone_change("lamp", "top")

    # Color adjustments
    logger.color_adjust(
        zone="lamp",
        color_from="120°",
        color_to="150°",
        mode="HUE"
    )

    logger.color_adjust(
        zone="top",
        color_from="red",
        color_to="orange",
        mode="PRESET"
    )

    # Brightness
    logger.brightness_adjust(zone="lamp", brightness_from=80, brightness_to=100)

    # Animation events
    logger.animation_start("color_snake", zones=["lamp", "top", "right", "bottom", "left"])
    logger.animation_param_change("speed", "50%", "75%")
    logger.animation_param_change("length", "5px", "8px")
    logger.animation_stop("color_snake")

    # Custom detailed logs
    logger.log(
        LogCategory.COLOR,
        "Preset mode → HUE mode conversion",
        zone="strip",
        preset="warm_white",
        hue="30°",
        rgb="(255, 200, 150)"
    )

    # Warnings
    logger.hardware("GPIO channel already in use", level=LogLevel.WARN, channel=18)

    # Errors
    logger.error(
        LogCategory.SYSTEM,
        "Failed to load animation",
        exception=FileNotFoundError("animation_config.yaml not found")
    )

    # Debug messages (won't show by default)
    logger.log(
        LogCategory.HARDWARE,
        "Encoder pulse received",
        level=LogLevel.DEBUG,
        pin=5,
        value=1
    )

    print("\n" + "=" * 70)
    print("End of demo")
    print("=" * 70 + "\n")


def demo_no_colors():
    """Demonstrate logger without colors (for file logging)"""
    configure_logger(use_colors=False)
    logger = get_logger()

    print("\n" + "=" * 70)
    print("Logger Demo - No Colors (file logging mode)")
    print("=" * 70 + "\n")

    logger.system("Application started", version="2.0")
    logger.zone_change("lamp", "top")
    logger.color_adjust("top", "120°", "150°", "HUE")
    logger.animation_start("breathe", zones=["lamp"])

    print("\n" + "=" * 70 + "\n")


def demo_debug_level():
    """Demonstrate logger with DEBUG level"""
    configure_logger(min_level=LogLevel.DEBUG)
    logger = get_logger()

    print("\n" + "=" * 70)
    print("Logger Demo - DEBUG Level")
    print("=" * 70 + "\n")

    logger.hardware("Encoder initialized", level=LogLevel.DEBUG, gpio_clk=5, gpio_dt=6)
    logger.hardware("Button initialized", level=LogLevel.DEBUG, gpio=22)
    logger.hardware("LED strip ready", level=LogLevel.INFO, pixels=45)

    print("\n" + "=" * 70 + "\n")


if __name__ == '__main__':
    # Reset to default colors before demos
    configure_logger(min_level=LogLevel.INFO, use_colors=True)

    # Run demos
    demo_logger()
    demo_no_colors()
    demo_debug_level()
