
from __future__ import annotations
from typing import Dict, List

from models.domain.zone import ZoneCombined
from managers.hardware_manager import HardwareManager
from zone_layer.zone_strip import ZoneStrip
from hardware.led.ws281x_strip import WS281xStrip, WS281xConfig
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.HARDWARE)

class ZoneStripFactory:
    """
    Factory responsible for building ZoneStrip instances bound to WS281x hardware.
    Does NOT speak domain logic. Pure hardware factory.
    """

    @staticmethod
    def create(all_zones: List[ZoneCombined], hardware_manager: HardwareManager) -> Dict[int, ZoneStrip]:
        """
        Build ZoneStrip instances grouped by GPIO pin.

        Args:
            all_zones: full list of ZoneCombined
            hardware_manager: provides hardware mapping config

        Returns:
            dict[gpio_pin, ZoneStrip]
        """

        # ------------------------------
        # 1) Group zones by GPIO pin
        # ------------------------------
        zones_by_gpio = {}
        for zone in all_zones:
            gpio = zone.config.gpio
            zones_by_gpio.setdefault(gpio, []).append(zone.config)

        # ------------------------------
        # 2) Load hardware mapping (yaml)
        # ------------------------------
        gpio_mappings = hardware_manager.get_gpio_to_zones_mapping()

        # ------------------------------
        # 3) Build ZoneStrip per GPIO
        # ------------------------------
        zone_strips = {}

        for gpio_pin, zone_configs in zones_by_gpio.items():
            mapping = next((m for m in gpio_mappings if m["gpio"] == gpio_pin), None)

            if not mapping:
                log.warn(f"ZoneStripFactory: No LED mapping found for GPIO {gpio_pin}")
                continue

            # Total pixel count on this GPIO
            pixel_count = sum(z.pixel_count for z in zone_configs)

            # ------------------------------
            # Construct WS281x hardware driver
            # ------------------------------
            ws_config = WS281xConfig(
                gpio_pin=gpio_pin,
                led_count=pixel_count,
                color_order=mapping["color_order"],
                frequency_hz=800_000,
                dma_channel=10,
                brightness=255,
                invert=False,
                channel=ZoneStripFactory._resolve_channel(gpio_pin),
            )

            hardware_driver = WS281xStrip(ws_config)

            # ------------------------------
            # Construct the ZoneStrip
            # ------------------------------
            strip = ZoneStrip(
                pixel_count=pixel_count,
                zones=zone_configs,
                hardware=hardware_driver
            )

            zone_strips[gpio_pin] = strip

            log.info(
                f"ZoneStrip created on GPIO {gpio_pin}: "
                f"{pixel_count}px, {len(zone_configs)} zones"
            )

        return zone_strips

    @staticmethod
    def _resolve_channel(gpio_pin: int) -> int:
        """
        WS281x library requires channel number. This logic was previously in main_asyncio,
        now isolated here. Modify when expanding hardware config.

        GPIO 18 → channel 0  
        GPIO 19 → channel 1  
        Else → fallback channel 0
        """
        if gpio_pin == 18:
            return 0
        if gpio_pin == 19:
            return 1
        return 0