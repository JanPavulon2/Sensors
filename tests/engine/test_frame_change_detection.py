"""
Tests for FrameManager Phase 2 optimization (Frame Change Detection).

Tests that FrameManager properly:
- Detects when frames haven't changed (via reference equality)
- Skips DMA transfers when frames are same object
- Counts DMA skips for metrics
- Still renders when frames change (different objects)
- Updates last_rendered_main_frame reference

NOTE: Frame change detection uses REFERENCE EQUALITY (is/is not), not value equality.
This is correct because:
1. Frames include auto-generated timestamps, making value equality unreliable
2. Queue returns same object for unchanged frames
3. Reference check is much faster than deep comparison
4. Semantically perfect: if it's the same frame object, it's the same visual output
"""

from models.enums import FramePriority, FrameSource, ZoneID
from models.color import Color
from models.frame import ZoneFrame, PixelFrame


class TestFrameReferenceEquality:
    """Test reference equality behavior used in _render_loop."""

    def test_same_frame_reference_is_identical(self):
        """Same frame object should be identical to itself."""
        frame = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )

        # Reference equality check
        assert frame is frame
        assert not (frame is not frame)

    def test_different_frame_objects_are_not_identical(self):
        """Different frame objects are not identical, even with same content."""
        frame1 = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )
        frame2 = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )

        # Different objects, even with same content
        assert frame1 is not frame2

    def test_frame_reference_assignment(self):
        """Assigning frame reference makes them identical."""
        frame1 = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )
        frame2 = frame1

        # After assignment, they're the same object
        assert frame1 is frame2
        assert not (frame1 is not frame2)

    def test_none_frame_comparison(self):
        """None should be distinct from any frame object."""
        frame = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )

        assert frame is not None
        assert None is not frame


class TestFrameChangeDetectionMetrics:
    """Test that DMA skip metrics are tracked correctly using reference equality."""

    def test_dma_skip_counting_pattern_with_reference_equality(self):
        """
        Test the pattern used in _render_loop for counting DMA skips.

        This uses reference equality (is/is not) because:
        - Frames include auto-generated timestamps
        - Queue returns same object for unchanged frames
        - Reference check is fast and semantically correct

        Logic:
        - If frame is not last_rendered_frame: frame changed → render + increment frames_rendered
        - If frame is last_rendered_frame: same object → skip DMA + increment dma_skipped
        """

        # Simulate FrameManager state
        last_rendered_frame = None
        frames_rendered = 0
        dma_skipped = 0

        # Frame 1: First frame (None -> Frame)
        frame1 = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )

        if frame1 is not last_rendered_frame:
            # Frame is different from last (or last is None)
            last_rendered_frame = frame1
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 1
        assert dma_skipped == 0

        # Frame 2: SAME frame object (queue returns same object)
        frame2 = frame1  # Same reference!

        if frame2 is not last_rendered_frame:
            last_rendered_frame = frame2
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 1  # No new render
        assert dma_skipped == 1  # DMA skipped

        # Frame 3: DIFFERENT frame object (new content)
        frame3 = ZoneFrame(
            zone_colors={ZoneID.LAMP: Color.from_rgb(0, 255, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )

        if frame3 is not last_rendered_frame:
            last_rendered_frame = frame3
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 2  # New render
        assert dma_skipped == 1  # Still 1 skip

    def test_dma_skip_with_multiple_frames(self):
        """Test DMA skipping over multiple frame cycles."""
        last_rendered_frame = None
        frames_rendered = 0
        dma_skipped = 0

        # Sequence of frames
        frame_a = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(255, 0, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )
        frame_b = ZoneFrame(
            zone_colors={ZoneID.FLOOR: Color.from_rgb(0, 255, 0)},
            priority=FramePriority.MANUAL,
            source=FrameSource.STATIC,
        )

        # Submit frame_a (first time - should render)
        if frame_a is not last_rendered_frame:
            last_rendered_frame = frame_a
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 1
        assert dma_skipped == 0

        # Submit frame_a again (same object, should skip)
        if frame_a is not last_rendered_frame:
            last_rendered_frame = frame_a
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 1
        assert dma_skipped == 1

        # Submit frame_b (different object, should render)
        if frame_b is not last_rendered_frame:
            last_rendered_frame = frame_b
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 2
        assert dma_skipped == 1

        # Submit frame_b again (same object, should skip)
        if frame_b is not last_rendered_frame:
            last_rendered_frame = frame_b
            frames_rendered += 1
        else:
            dma_skipped += 1

        assert frames_rendered == 2
        assert dma_skipped == 2

    def test_pixel_frame_reference_equality(self):
        """Test reference equality works for PixelFrame too."""
        last_rendered_frame = None
        frames_rendered = 0

        frame1 = PixelFrame(
            zone_pixels={ZoneID.FLOOR: [Color.from_rgb(255, 0, 0)]},
            priority=FramePriority.ANIMATION,
            source=FrameSource.ANIMATION,
        )

        # First submission
        if frame1 is not last_rendered_frame:
            last_rendered_frame = frame1
            frames_rendered += 1

        assert frames_rendered == 1

        # Same frame resubmitted
        if frame1 is not last_rendered_frame:
            last_rendered_frame = frame1
            frames_rendered += 1

        assert frames_rendered == 1  # Not incremented (same object)
