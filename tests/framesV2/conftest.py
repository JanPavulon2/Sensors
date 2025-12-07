import pytest
from unittest.mock import MagicMock

from models.enums import ZoneID
from models.color import Color
from engine.frame_manager import FrameManager
from services.zone_service import ZoneService
from models.domain.zone import ZoneCombined, ZoneState, ZoneConfig
from engine.animation_engine import AnimationEngine


@pytest.fixture
def mock_zone_mapper():
    """
    Fake mapper: 2 zones, each with 5 LEDs.
    """
    mapper = MagicMock()
    mapper.all_zone_ids.return_value = [ZoneID.BOTTOM, ZoneID.TOP]
    mapper.get_zone_length.return_value = 5
    return mapper


@pytest.fixture
def mock_zone_strip(mock_zone_mapper):
    strip = MagicMock()
    strip.mapper = mock_zone_mapper
    return strip


@pytest.fixture
def zone_service():
    service = MagicMock(spec=ZoneService)

    def make_zone(zid, color=(255, 255, 255)):
        cfg = ZoneConfig(id=zid, display_name=zid.name, start_index=0, end_index=4)
        st = ZoneState(color=Color.from_rgb(*color), brightness=100)
        return ZoneCombined(config=cfg, state=st)

    service.get_zone.side_effect = lambda zid: make_zone(zid)
    service.get_all_zones.return_value = [
        service.get_zone(ZoneID.BOTTOM),
        service.get_zone(ZoneID.TOP),
    ]
    return service


@pytest.fixture
def frame_manager(mock_zone_strip):
    fm = FrameManager(fps=1000)  # high FPS so tests run fast
    fm.add_zone_strip(mock_zone_strip)
    return fm


@pytest.fixture
def engine(frame_manager, zone_service):
    return AnimationEngine(frame_manager, zone_service)
