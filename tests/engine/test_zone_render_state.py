"""
Tests for ZoneRenderState (Phase 1+2: Foundation for frame change detection).

Tests that ZoneRenderState properly:
- Stores zone render data
- Computes and caches pixel hashes
- Tracks update source and timestamps
- Marks zones as dirty
"""

import pytest
import time

from models.enums import ZoneID, ZoneRenderMode, FrameSource
from models.color import Color
from engine.zone_render_state import ZoneRenderState


class TestZoneRenderStateBasics:
    """Test ZoneRenderState creation and properties."""

    def test_create_zone_render_state(self):
        """Create ZoneRenderState with initial pixels."""
        pixels = [Color.from_rgb(255, 0, 0), Color.from_rgb(0, 255, 0)]
        zrs = ZoneRenderState(
            zone_id=ZoneID.FLOOR,
            pixels=pixels,
            brightness=100,
            mode=ZoneRenderMode.STATIC,
            source=FrameSource.STATIC,
        )

        assert zrs.zone_id == ZoneID.FLOOR
        assert len(zrs.pixels) == 2
        assert zrs.brightness == 100
        assert zrs.mode == ZoneRenderMode.STATIC
        assert zrs.source == FrameSource.STATIC
        assert zrs.dirty is True

    def test_default_zone_render_state(self):
        """Create ZoneRenderState with defaults."""
        zrs = ZoneRenderState(zone_id=ZoneID.LAMP)

        assert zrs.zone_id == ZoneID.LAMP
        assert zrs.pixels == []
        assert zrs.brightness == 100
        assert zrs.source is None
        assert zrs.dirty is True


class TestZoneRenderStateHashing:
    """Test pixel hash computation and caching."""

    def test_pixel_hash_consistent(self):
        """Same pixels should produce same hash."""
        pixels1 = [Color.from_rgb(255, 0, 0), Color.from_rgb(0, 255, 0)]
        pixels2 = [Color.from_rgb(255, 0, 0), Color.from_rgb(0, 255, 0)]

        zrs1 = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels1)
        zrs2 = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels2)

        assert zrs1.get_pixel_hash() == zrs2.get_pixel_hash()

    def test_pixel_hash_different(self):
        """Different pixels should produce different hashes."""
        pixels1 = [Color.from_rgb(255, 0, 0)]
        pixels2 = [Color.from_rgb(0, 255, 0)]

        zrs1 = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels1)
        zrs2 = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels2)

        assert zrs1.get_pixel_hash() != zrs2.get_pixel_hash()

    def test_pixel_hash_caching(self):
        """Hash should be cached after first computation."""
        pixels = [Color.from_rgb(255, 0, 0)]
        zrs = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels)

        hash1 = zrs.get_pixel_hash()
        hash2 = zrs.get_pixel_hash()

        assert hash1 == hash2
        assert hash1 is not None

    def test_pixel_hash_invalidated_on_update(self):
        """Hash should be invalidated when pixels are updated."""
        pixels1 = [Color.from_rgb(255, 0, 0)]
        pixels2 = [Color.from_rgb(0, 255, 0)]

        zrs = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels1)
        hash1 = zrs.get_pixel_hash()

        # Update pixels
        zrs.update_pixels(pixels2, FrameSource.ANIMATION)
        hash2 = zrs.get_pixel_hash()

        assert hash1 != hash2

    def test_pixel_hash_includes_zone_id(self):
        """Different zones with same pixels should have different hashes."""
        pixels = [Color.from_rgb(255, 0, 0)]

        zrs_floor = ZoneRenderState(zone_id=ZoneID.FLOOR, pixels=pixels)
        zrs_lamp = ZoneRenderState(zone_id=ZoneID.LAMP, pixels=pixels)

        # Hashes differ because zone_id is different
        assert zrs_floor.get_pixel_hash() != zrs_lamp.get_pixel_hash()


class TestZoneRenderStateUpdates:
    """Test updating zone render state."""

    def test_update_pixels_with_source(self):
        """Update pixels and track source."""
        zrs = ZoneRenderState(zone_id=ZoneID.FLOOR)

        pixels = [Color.from_rgb(255, 0, 0)]
        zrs.update_pixels(pixels, FrameSource.ANIMATION)

        assert zrs.pixels == pixels
        assert zrs.source == FrameSource.ANIMATION
        assert zrs.dirty is True

    def test_update_pixels_updates_timestamp(self):
        """Timestamp should update when pixels change."""
        zrs = ZoneRenderState(zone_id=ZoneID.FLOOR)
        old_ts = zrs.last_update_ts

        time.sleep(0.01)  # Small delay
        pixels = [Color.from_rgb(255, 0, 0)]
        zrs.update_pixels(pixels, FrameSource.ANIMATION)

        assert zrs.last_update_ts > old_ts

    def test_update_pixels_invalidates_hash(self):
        """Hash should be invalidated on update."""
        zrs = ZoneRenderState(zone_id=ZoneID.FLOOR)
        zrs.update_pixels([Color.from_rgb(255, 0, 0)], FrameSource.STATIC)
        hash1 = zrs.get_pixel_hash()

        zrs.update_pixels([Color.from_rgb(0, 255, 0)], FrameSource.ANIMATION)
        hash2 = zrs.get_pixel_hash()

        assert hash1 != hash2


class TestZoneRenderStateRepr:
    """Test string representation."""

    def test_repr_shows_zone_id_and_source(self):
        """__repr__ should show useful debug info."""
        zrs = ZoneRenderState(
            zone_id=ZoneID.LAMP,
            pixels=[Color.from_rgb(255, 255, 255)],
            brightness=75,
            source=FrameSource.ANIMATION,
        )

        repr_str = repr(zrs)
        assert "LAMP" in repr_str
        assert "ANIMATION" in repr_str
        assert "75" in repr_str
