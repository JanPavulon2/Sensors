"""
PreviewPanel (v2) - logical preview generator

PreviewPanel w opcji A:
- NIE jest driverem PixelStrip.
- Jest *logiczznym* generatorem PreviewFrame'ów (uogólniony, hardware-agnostyczny).
- Pobiera aktualny bufor/kolory aktywnej strefy (lub listę pikseli),
  kompresuje/skaluję je do rozmiaru preview (np. 8) i zwraca PreviewFrame,
  lub samo wyśle go do FrameManagera (submit_preview_frame).

Umieszczenie: src/hardware/preview_panel.py
Zależności:
- models.color.Color
- models.domain.zone.ZoneCombined (opcjonalnie)
- models.frame.PreviewFrame / FramePriority
- engine.frame_manager.FrameManager (interfejs submit_preview_frame)
- utils.logger
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Sequence

from utils.logger import get_logger
from models.color import Color
from models.enums import ZoneID, FramePriority
from models.frame import PreviewFrame  # zakładamy że PreviewFrame istnieje
from models.domain.zone import ZoneCombined
from engine.frame_manager import FrameManager

log = get_logger().for_category("PREVIEW")  # lub LogCategory.PREVIEW jeśli masz enum


@dataclass
class PreviewPanel:
    """
    Logical preview generator.

    Args:
        frame_manager: FrameManager - do którego submitujemy PreviewFrame'y
        preview_zone_id: ZoneID - identyfikator zone używanego jako PREVIEW (np. ZoneID.PREVIEW)
        preview_size: int - liczba pixeli w preview (np. 8 dla CJMCU-2812-8)
        sample_mode: str - "average" | "median" | "nearest" (jak kompresujemy)
    """
    frame_manager: FrameManager
    preview_zone_id: ZoneID
    preview_size: int = 8
    sample_mode: str = "average"  # prosty start

    # opcjonalne: można przechować ostatni wygenerowany frame
    last_frame: Optional[PreviewFrame] = None

    # ---------------------------
    # Public API
    # ---------------------------
    async def render_zone_preview(self, source_pixels: Sequence[Color], priority: FramePriority = FramePriority.PULSE, ttl_ms: int = 500) -> PreviewFrame:
        """
        Generate a PreviewFrame from a sequence of Color objects (logical zone pixels)
        and submit it to FrameManager with given priority.

        Args:
            source_pixels: list/sequence of Color (or RGB tuples) representing the active zone logical pixels
            priority: FramePriority for preview rendering
            ttl_ms: time-to-live (ms) for the PreviewFrame (how long it is valid)

        Returns:
            PreviewFrame object that was submitted
        """
        # Convert source pixels to RGB tuples
        rgb_list = [self._color_to_rgb_tuple(c) for c in source_pixels]

        # Compress to preview size
        preview_pixels = self._compress_to_preview(rgb_list, self.preview_size, mode=self.sample_mode)

        # Build PreviewFrame (model) — minimal fields: pixels, priority, created_at, ttl_ms
        frame = PreviewFrame(
            pixels=preview_pixels,
            priority=priority,
            ttl_ms=ttl_ms
        )

        # cache
        self.last_frame = frame

        # Submit to frame manager
        try:
            await self.frame_manager.submit_preview_frame(frame)
        except Exception as ex:
            log.error("Failed to submit preview frame", error=str(ex))

        return frame

    async def render_preview_for_zonecombined(self, zone: ZoneCombined, priority: FramePriority = FramePriority.PULSE, ttl_ms: int = 500) -> PreviewFrame:
        """
        Convenience: take ZoneCombined (domain object), read its color representation
        and generate a preview that approximates the zone's current visual.

        Strategy:
        - If animation provides per-pixel data we should use it (future).
        - For now: sample the zone length and produce a gradient/replicated color list
        """
        # Try to get per-pixel frame from zone state (if exists). For now, use zone.state.color repeated.
        zone_len = zone.config.pixel_count
        try:
            # If zone has an animation that exposes per-pixel frame, prefer that. (Hook point)
            # For now: generate array filled with zone.state.color
            base_color: Color = zone.state.color
            pixels = [self._color_to_rgb_tuple(base_color) for _ in range(zone_len)]
        except Exception:
            # Fallback: black
            pixels = [(0, 0, 0)] * max(1, zone_len)

        return await self.render_zone_preview(pixels, priority=priority, ttl_ms=ttl_ms)

    # ---------------------------
    # Helpers
    # ---------------------------

    def _color_to_rgb_tuple(self, c: Color | Tuple[int, int, int] | Sequence[int]) -> Tuple[int, int, int]:
        """
        Normalize a Color object or tuple/list to an (r,g,b) tuple of ints 0-255.
        """
        if isinstance(c, Color):
            return c.to_rgb()
        if isinstance(c, (tuple, list)) and len(c) >= 3:
            return (int(c[0]), int(c[1]), int(c[2]))
        # Unknown input -> black
        return (0, 0, 0)

    def _compress_to_preview(self, pixels: List[Tuple[int, int, int]], target_len: int, mode: str = "average") -> List[Tuple[int, int, int]]:
        """
        Compress/scale `pixels` list to `target_len` items.

        Simple approach:
        - Partition pixels into `target_len` buckets (floor/ceil), average each bucket.
        - If length < target_len, repeat/upsample by nearest neighbor.

        Modes:
            - "average": average R/G/B in bucket
            - "nearest": pick representative (first) in bucket
            - "median": median per channel (robust to spikes)
        """
        if not pixels:
            return [(0, 0, 0)] * target_len

        n = len(pixels)
        if n == target_len:
            return pixels[:]

        if n < target_len:
            # upsample: repeat and then cut
            out = []
            for i in range(target_len):
                src_idx = int(i * n / target_len)
                out.append(pixels[min(src_idx, n - 1)])
            return out

        # n > target_len -> bucket
        out: List[Tuple[int, int, int]] = []
        # compute bucket boundaries
        for i in range(target_len):
            start = int(i * n / target_len)
            end = int((i + 1) * n / target_len)  # exclusive
            if end <= start:
                end = start + 1
            bucket = pixels[start:end]
            if not bucket:
                out.append((0, 0, 0))
                continue

            if mode == "average":
                r = sum(p[0] for p in bucket) // len(bucket)
                g = sum(p[1] for p in bucket) // len(bucket)
                b = sum(p[2] for p in bucket) // len(bucket)
                out.append((int(r), int(g), int(b)))
            elif mode == "median":
                import statistics
                r = int(statistics.median([p[0] for p in bucket]))
                g = int(statistics.median([p[1] for p in bucket]))
                b = int(statistics.median([p[2] for p in bucket]))
                out.append((r, g, b))
            else:  # nearest
                out.append(bucket[0])

        return out
