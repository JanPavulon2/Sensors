import pytest
import asyncio
from models.enums import ZoneID, AnimationID
from models.color import Color
from animations.engine import AnimationEngine
from engine.frame_manager import FrameManager
from services.zone_service import ZoneService

#
# Dummy classes
#

class DummyZone:
    def __init__(self, zone_id):
        self.config = type("Cfg", (), {"id": zone_id})
        self.state = type(
            "State", (), {
                "color": Color.white()
            })
        self.brightness = 100

class DummyZoneService:
    def __init__(self):
        self.zones = {
            ZoneID.TOP: DummyZone(ZoneID.TOP),
            ZoneID.BOTTOM: DummyZone(ZoneID.BOTTOM)
        }
    def get_zone(self, zid):
        return self.zones[zid]

class DummyMapper:
    def all_zone_ids(self):
        return [ZoneID.TOP, ZoneID.BOTTOM]

    def get_zone_length(self, zid):
        return 5
    
class DummyStrip:
    def __init__(self):
        self.mapper = DummyMapper()
        self.frames = []

    def show_full_pixel_frame(self, frame):
        print("STRIP FRAME:", frame)
        self.frames.append(frame)
        
#
# TEST
#

@pytest.mark.asyncio
async def test_animation_engine_verbose_two_zones_breathe():
    print("\n--- TEST: verbose engine+two zones breathe ---\n")

    fm = FrameManager(fps=240)
    strip = DummyStrip()
    fm.add_zone_strip(strip)

    zone_service = DummyZoneService()
    engine = AnimationEngine(fm, zone_service)

    # uruchamiamy dwie strefy
    await engine.start_for_zone(
        ZoneID.TOP,
        AnimationID.BREATHE,
        {"speed": 50, "intensity": 40}
    )
    await engine.start_for_zone(
        ZoneID.BOTTOM,
        AnimationID.BREATHE,
        {"speed": 30, "intensity": 80}
    )

    # pozwalamy im popracować
    await fm.start()
    await asyncio.sleep(0.1)  # ~24 frames @240FPS
    await fm.stop()

    # sprawdzamy czy były jakiekolwiek ramki wypchane
    assert len(strip.frames) > 0

    # Dodatkowe printy
    print("\nCaptured frames:", len(strip.frames))
    for i, fr in enumerate(strip.frames[:3]):
        print(f"[frame {i}] {fr}")

    # Sprawdzamy czy TOP i BOTTOM mają różne jasności — bo różne intensities
    z0 = strip.frames[-1][ZoneID.TOP]
    z1 = strip.frames[-1][ZoneID.BOTTOM]
    top_color = z0[0]
    bottom_color = z1[0]

    print("\nLast TOP color:", top_color)
    print("Last BOTTOM color:", bottom_color)

    assert top_color != bottom_color
