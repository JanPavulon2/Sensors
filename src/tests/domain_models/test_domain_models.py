"""Test script to verify domain models and services"""

import sys
import os
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from managers import ConfigManager
from services import DataAssembler, AnimationService, ZoneService
from models.enums import AnimationID, ZoneID, ParamID

def main():
    print("=== Testing Domain Models ===\n")

    print("1. Loading configuration...")
    config_manager = ConfigManager()
    config_manager.load()
    print("   ✓ ConfigManager loaded\n")

    print("2. Initializing DataAssembler...")
    state_path = Path("src/state/state.json")
    assembler = DataAssembler(config_manager, state_path)
    print("   ✓ DataAssembler initialized\n")

    print("3. Building animations...")
    animation_service = AnimationService(assembler)
    animations = animation_service.get_all()
    print(f"   ✓ Built {len(animations)} animations:")
    for anim in animations:
        status = "CURRENT" if anim.state.enabled else "available"
        print(f"      - {anim.config.display_name} ({status})")
        for param_id, param in anim.parameters.items():
            print(f"         {param_id.name} = {param.state.value}{param.config.unit or ''}")
    print()

    print("4. Building zones...")
    zone_service = ZoneService(assembler)
    zones = zone_service.get_all()
    print(f"   ✓ Built {len(zones)} zones:")
    for zone in zones:
        rgb = zone.get_rgb()
        print(f"      - {zone.config.display_name} @ [{zone.config.start_index:2}-{zone.config.end_index:2}]")
        print(f"         Color: {zone.state.color.mode.name}, Brightness: {zone.state.brightness}%, RGB: {rgb}")
    print()

    print("5. Testing service operations...")

    current = animation_service.get_current()
    if current and ParamID.ANIM_SPEED in current.parameters:
        old_speed = current.get_param_value(ParamID.ANIM_SPEED)
        print(f"   Current animation speed: {old_speed}")
        animation_service.adjust_parameter(current.config.id, ParamID.ANIM_SPEED, delta=1)
        new_speed = current.get_param_value(ParamID.ANIM_SPEED)
        print(f"   After adjust +1: {new_speed}")
        animation_service.adjust_parameter(current.config.id, ParamID.ANIM_SPEED, delta=-1)
        restored_speed = current.get_param_value(ParamID.ANIM_SPEED)
        print(f"   After adjust -1: {restored_speed}")

    lamp = zone_service.get_zone(ZoneID.LAMP)
    old_brightness = lamp.state.brightness
    print(f"   Lamp brightness: {old_brightness}%")
    zone_service.set_brightness(ZoneID.LAMP, 50)
    print(f"   After set to 50%: {lamp.state.brightness}%")
    zone_service.set_brightness(ZoneID.LAMP, old_brightness)
    print(f"   Restored: {lamp.state.brightness}%")
    print()

    print("=== All Tests Passed! ===")

if __name__ == "__main__":
    main()
