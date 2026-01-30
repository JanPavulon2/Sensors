
from __future__ import annotations
from typing import Dict, List, Optional

from models.domain.zone import ZoneCombined, ZoneConfig
from managers.hardware_manager import HardwareManager
from hardware.led.led_channel import LedChannel
from hardware.led import VirtualStrip
from hardware.led import IPhysicalStrip
from hardware.led.ws281x_strip import WS281xStrip
from runtime.runtime_info import RuntimeInfo
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.HARDWARE)

class LedChannelFactory:
    """
    Factory responsible for building LedChannel instances.

    Responsibilities:
    - group zones by GPIO pin
    - resolve hardware parameters (GPIO, DMA, channel, color order)
    - decide between WS281xStrip and VirtualStrip
    - create LedChannel (zone-aware logical renderer)

    This is the ONLY place that:
    - touches RuntimeInfo
    - knows about GPIO ↔ channel ↔ DMA mapping
    """
    
    
    @classmethod
    def create(
        cls,
        all_zones: List[ZoneCombined], 
        hardware_manager: HardwareManager
    ) -> Dict[int, LedChannel]:
        """
        Build LedChannel instances grouped by GPIO pin.

        Returns:
            dict[gpio_pin, LedChannel]
        """

        # ------------------------------
        # 1) Group zones by GPIO
        # ------------------------------
        zones_by_gpio: Dict[int, List[ZoneConfig]] = {}
        
        for zone in all_zones:
            gpio = zone.config.gpio
            zones_by_gpio.setdefault(gpio, []).append(zone.config)

        if not zones_by_gpio:
            log.warn("LedChannelFactory: no zones configured")
            return {}
        
        
        # ------------------------------
        # 2) Load hardware mapping (yaml)
        # ------------------------------
        
        gpio_mappings = hardware_manager.get_gpio_to_zones_mapping()
        
        channels: Dict[int, LedChannel] = {}


        # ------------------------------
        # 3) Build LedChannel per GPIO
        # ------------------------------
        
        for gpio_pin, zones_configs in zones_by_gpio.items():
            mapping = cls._find_gpio_mapping(gpio_pin, gpio_mappings)
            
            if not mapping:
                log.warn(f"LedChannelFactory: No LED mapping found for GPIO {gpio_pin}")
                continue

            # Total pixel count on this GPIO
            pixel_count = sum(z.pixel_count for z in zones_configs)

            hardware_led_strip = cls._create_physical_strip(
                gpio_pin=gpio_pin,
                pixel_count=pixel_count,
                mapping=mapping
            )
            
            channel = LedChannel(
                pixel_count=pixel_count, 
                zones=zones_configs,
                hardware=hardware_led_strip
            )
            
            channels[gpio_pin] = channel
            
            log.info(
                "LedChannel created",
                gpio=gpio_pin,
                pixels=pixel_count,
                zones=[z.id.name for z in zones_configs],
                hardware=type(hardware_led_strip).__name__
            )
            
        return channels
    
    # def create_strip(
    #     *,
    #     pixel_count: int,
    #     gpio_pin: Optional[int],
    #     color_order: str = "BGR",
    # ) -> IPhysicalStrip:
    #     """
    #     Factory that NEVER crashes the app on PC / WSL.
    #     """

    #     if RuntimeInfo.is_raspberry_pi() and RuntimeInfo.has_ws281x():
    #         try:
    #             from hardware.led.ws281x_strip import WS281xStrip
    #             assert gpio_pin is not None
                
    #             return WS281xStrip(
    #                 pixel_count=pixel_count,
    #                 gpio_pin=gpio_pin,
    #                 color_order=color_order
    #             )
    #         except Exception:
    #             pass
            
    #     return VirtualStrip(pixel_count)

    # ==================================================
    # INTERNAL HELPERS
    # ==================================================

    @staticmethod
    def _find_gpio_mapping(gpio_pin: int, mappings: List[dict]) -> dict | None:
        for m in mappings:
            if m.get("gpio") == gpio_pin:
                return m
        return None

    @classmethod
    def _create_physical_strip(
        cls,
        gpio_pin: int,
        pixel_count: int,
        mapping: dict,
    ) -> IPhysicalStrip:
        """
        Create WS281xStrip or VirtualStrip depending on runtime.
        """

        color_order = mapping.get("color_order", "GRB")
        dma_channel = mapping.get("dma", 10)
        pwm_channel = cls._resolve_pwm_channel(gpio_pin)

        # --------------------------------------------------
        # Real hardware path
        # --------------------------------------------------
        if RuntimeInfo.has_ws281x():
            log.info(
                "Creating WS281xStrip",
                gpio=gpio_pin,
                pixels=pixel_count,
                order=color_order,
                dma=dma_channel,
                pwm=pwm_channel,
            )

            return WS281xStrip(
                gpio_pin=gpio_pin,
                pixel_count=pixel_count,
                color_order=color_order,
                dma_channel=dma_channel,
                channel=pwm_channel,
            )

        # --------------------------------------------------
        # Virtual / dev fallback
        # --------------------------------------------------
        log.warn(
            "WS281x not available – using VirtualStrip",
            gpio=gpio_pin,
            pixels=pixel_count,
        )

        return VirtualStrip(pixel_count=pixel_count)

    @staticmethod
    def _resolve_pwm_channel(gpio_pin: int) -> int:
        """
        Map GPIO pin → PWM channel for rpi_ws281x.

        GPIO 18 → channel 0
        GPIO 19 → channel 1
        default → channel 0
        """
        if gpio_pin == 18:
            return 0
        if gpio_pin == 19:
            return 1
        return 0
    
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
    
    # @staticmethod
    # def create(all_zones: List[ZoneCombined], hardware_manager: HardwareManager) -> Dict[int, LedChannel]:
    #     """
    #     Build LedChannel instances grouped by GPIO pin.

    #     Args:
    #         all_zones: full list of ZoneCombined
    #         hardware_manager: provides hardware mapping config

    #     Returns:
    #         dict[gpio_pin, LedChannel]
    #     """

    #     # ------------------------------
    #     # 1) Group zones by GPIO pin
    #     # ------------------------------
    #     zones_by_gpio = {}
    #     for zone in all_zones:
    #         gpio = zone.config.gpio
    #         zones_by_gpio.setdefault(gpio, []).append(zone.config)

    #     # ------------------------------
    #     # 2) Load hardware mapping (yaml)
    #     # ------------------------------
    #     gpio_mappings = hardware_manager.get_gpio_to_zones_mapping()

    #     # ------------------------------
    #     # 3) Build LedChannel per GPIO
    #     # ------------------------------
    #     led_channels = {}

    #     for gpio_pin, zone_configs in zones_by_gpio.items():
    #         mapping = next((m for m in gpio_mappings if m["gpio"] == gpio_pin), None)

    #         if not mapping:
    #             log.warn(f"LedChannelFactory: No LED mapping found for GPIO {gpio_pin}")
    #             continue

    #         # Total pixel count on this GPIO
    #         pixel_count = sum(z.pixel_count for z in zone_configs)

    #         from hardware.led.ws281x_strip import WS281xStrip, WS281xConfig
            
    #         # ------------------------------
    #         # Construct WS281x hardware driver
    #         # ------------------------------
    #         ws_config = WS281xConfig(
    #             gpio_pin=gpio_pin,
    #             pixel_count=pixel_count,
    #             color_order=mapping["color_order"],
    #             frequency_hz=800_000,
    #             dma_channel=10,
    #             brightness=255,
    #             invert=False,
    #             channel=LedChannelFactory._resolve_channel(gpio_pin),
    #         )

    #         hardware_driver = WS281xStrip(
    #             gpio_pin=gpio_pin, 
    #             pixel_count=pixel_count, 
    #             color_order=mapping["color_order"], 
    #             channel=LedChannelFactory._resolve_channel(gpio_pin)
    #         )

    #         # ------------------------------
    #         # Construct the LedChannel
    #         # ------------------------------
    #         strip = LedChannel(
    #             pixel_count=pixel_count,
    #             zones=zone_configs,
    #             hardware=hardware_driver
    #         )

    #         led_channels[gpio_pin] = strip

    #         log.info(
    #             f"LedChannel created on GPIO {gpio_pin}: "
    #             f"{pixel_count}px, {len(zone_configs)} zones"
    #         )

    #     return led_channels

    