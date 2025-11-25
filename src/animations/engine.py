"""
Animation Engine

Manages animation lifecycle, switching between animations, and updating strip.
Uses TransitionService for smooth transitions between animation states.
"""

import asyncio
import time
from typing import Optional, Dict, List, Tuple, Any, Type

from animations.base import BaseAnimation  # ✅ direct import — breaks circular import safely

# Import animation classes here (NOT in __init__ to avoid circular imports)
from animations.breathe import BreatheAnimation
from animations.color_fade import ColorFadeAnimation
from animations.snake import SnakeAnimation
from animations.color_snake import ColorSnakeAnimation
from animations.color_cycle import ColorCycleAnimation

from models.domain.zone import ZoneCombined
from models.color import Color
from services.transition_service import TransitionService
from services import AnimationService
from engine import FrameManager
from models.transition import TransitionConfig, TransitionType
from models.enums import ParamID, LogCategory, ZoneID, AnimationID, FramePriority, FrameSource, ZoneRenderMode
from models.frame import ZoneFrame, PixelFrame
from utils.logger import get_category_logger
from zone_layer.zone_strip import ZoneStrip

log = get_category_logger(LogCategory.ANIMATION)

def _build_animation_registry() -> Dict[AnimationID, Type[BaseAnimation]]:
    """Build animation registry dynamically from AnimationID enum"""
    class_map = {
        AnimationID.COLOR_CYCLE: ColorCycleAnimation,
        AnimationID.BREATHE: BreatheAnimation,
        AnimationID.COLOR_FADE: ColorFadeAnimation,
        AnimationID.SNAKE: SnakeAnimation,
        AnimationID.COLOR_SNAKE: ColorSnakeAnimation,
        # AnimationID.MATRIX: MatrixAnimation,  # TEMPORARY: Disabled
    }

    # Convert enum to string keys using .name
    return {anim_id: anim_class for anim_id, anim_class in class_map.items()}

class AnimationEngine:
    """
    Animation engine that manages running animations

    Handles:
    - Starting/stopping animations
    - Switching between animations
    - Updating LED strip with animation frames
    - Parameter updates

    Example:
        engine = AnimationEngine(strip, zones)
        await engine.start('BREATHE', speed=50, color=(255, 0, 0))
        await asyncio.sleep(5)
        await engine.stop()
    """

    # Registry of available animations - built dynamically from enum
    ANIMATIONS: Dict[AnimationID, Type[BaseAnimation]] = _build_animation_registry()

    def __init__(self, strip, zones: List[ZoneCombined], frame_manager: FrameManager):
        """
        Initialize animation engine

        Args:
            strip: ZoneStrip instance
            zones: List of Zone objects
        """
        self.strip: ZoneStrip = strip
        self.zones = zones
        self.current_animation: Optional[BaseAnimation] = None
        self.animation_task: Optional[asyncio.Task] = None
        self.current_id: Optional[AnimationID] = None

        # Transition service for smooth animation switches
        self.frame_manager = frame_manager
        self.transition_service = TransitionService(strip, frame_manager)

        # Pixel buffer: zone_id -> pixel_index -> (r, g, b) for pixel-level animations
        self.zone_pixel_buffers: dict[ZoneID, dict[int, tuple[int, int, int]]] = {}
        # Zone color buffer: zone_id -> (r, g, b) for zone-level animations
        self.zone_color_buffers: dict[ZoneID, tuple[int, int, int]] = {}
        self.zone_lengths: dict[ZoneID, int] = {
            z.config.id: z.config.pixel_count for z in zones
        }

        # Frame-by-frame debugging: when frozen, animation continues running but doesn't submit frames
        self._frozen: bool = False

        log.info("AnimationEngine initialized", animations=list(self.ANIMATIONS.keys()))

    
    # ============================================================
    # Core control methods
    # ============================================================

    async def start(
        self,
        animation_id: AnimationID,
        excluded_zones: Optional[List] = None,
        transition: Optional[TransitionConfig] = None,
        from_frame: Optional[List] = None,
        **params
    ):
        """
        Start an animation by animation ID with optional transition

        Args:
            animation_id: Animation ID (AnimationID.BREATHE, AnimationID.SNAKE, etc.)
            excluded_zones: List of zone names to exclude from animation (e.g., ["lamp"])
            transition: Transition configuration for switching (defaults to ANIMATION_SWITCH)
            from_frame: Optional starting frame for crossfade (if None, captures current strip state)
            **params: Animation-specific parameters (speed, color, etc.)

        Raises:
            ValueError: If animation name is not recognized

        Example:
            # Start with default fade transition
            await engine.start(AnimationID.BREATHE, speed=50)

            # Start with crossfade from specific frame
            await engine.start(AnimationID.SNAKE, from_frame=old_frame)
        """
        # DEBUG: Skip animations if testing static mode only
        try:
            from main_asyncio import DEBUG_NOPULSE
            if DEBUG_NOPULSE:
                log.info("DEBUG_STATIC_ONLY: Skipping animation start")
                return
        except ImportError:
            pass
        transition = transition or self.transition_service.ANIMATION_SWITCH
        log.info(f"AnimEngine.start(): {animation_id}")

        # Step 1: Wait for any active transitions to complete
        await self.transition_service.wait_for_idle()

        # Step 2: Determine old frame for crossfade
        old_frame = from_frame if from_frame is not None else []

        # Step 3: Stop old animation if running (capture frame if not provided)
        if self.is_running():
            if not old_frame and hasattr(self.strip, "get_frame"):
                old_frame = self.strip.get_frame() or []

            # Stop old animation WITHOUT fade (we'll crossfade instead)
            if self.current_animation:
                self.current_animation.stop()

            if self.animation_task:
                self.animation_task.cancel()
                try:
                    await self.animation_task
                except asyncio.CancelledError:
                    pass
                self.animation_task = None

            # Clear buffers from old animation before starting new one
            self.zone_pixel_buffers.clear()
            self.zone_color_buffers.clear()

            self.current_animation = None
            self.current_id = None
            log.debug("AnimEngine: Stopped old animation (no fade, preparing for crossfade)")

        # Step 3: Create animation instance
        if animation_id not in self.ANIMATIONS:
            raise ValueError(f"Unknown animation: {animation_id}")

        animation_class = self.ANIMATIONS[animation_id]
        self.current_animation = animation_class(self.zones, excluded_zones=excluded_zones or [], **params)
        self.current_id = animation_id

        log.info(f"AnimEngine: Created instance: {animation_id}")

        # Step 4: Cache current zone colors
        for zone in self.zones:
            color = self.strip.get_zone_color(zone.config.id)
            if color:
                self.current_animation.set_zone_color_cache(zone.config.id, color)

        # Step 5: Keep old frame visible while building first frame
        # Submit old frame with low priority to prevent black flash during _get_first_frame()
        if old_frame:
            zone_pixels_dict_old = self.transition_service._get_zone_pixels_dict(old_frame)
            pixel_frame_old = PixelFrame(
                zone_pixels=zone_pixels_dict_old,
                priority=FramePriority.MANUAL,
                source=FrameSource.ANIMATION,
                ttl=5.0  # High TTL to persist while first frame builds (~250ms)
            )
            await self.frame_manager.submit_pixel_frame(pixel_frame_old)

        # Step 6: Build first frame in memory (WITHOUT touching strip buffer)
        log.debug("AnimEngine: Building first frame...")
        zone_pixels_dict = await self._get_first_frame()

        # Step 7: Convert zone_pixels dict to absolute frame for transitions
        # (strip knows how to map zone pixels to physical indices)
        # Build as Color objects (transitions expect List[Color])
        first_frame = []
        if zone_pixels_dict:
            # Build full frame from zone pixels using Color objects
            first_frame = [Color.black()] * self.strip.pixel_count
            for zone_id, pixels in zone_pixels_dict.items():
                indices = self.strip.mapper.get_indices(zone_id)
                for logical_idx, (r, g, b) in enumerate(pixels):
                    if logical_idx < len(indices):
                        phys_idx = indices[logical_idx]
                        if 0 <= phys_idx < self.strip.pixel_count:
                            first_frame[phys_idx] = Color.from_rgb(r, g, b)

        # Step 8: CROSSFADE from old to new (or fade_in if no old frame)
        if first_frame:
            if old_frame and len(old_frame) == len(first_frame):
                log.debug("AnimEngine: Crossfading from old to new animation...")
                await self.transition_service.crossfade(old_frame, first_frame, transition)
            else:
                # No old frame or size mismatch - just fade in from black
                log.debug("AnimEngine: Fading in from black...")
                await self.transition_service.fade_in(first_frame, transition)

        # Step 9: Clear all buffers before starting loop (prevents stale frame glitch)
        self.zone_pixel_buffers.clear()
        self.zone_color_buffers.clear()

        # Step 10: NOW start animation loop (transition complete - no race condition)
        log.info(f"AnimEngine: Starting loop for {animation_id}")
        self.animation_task = asyncio.create_task(self._run_loop())
        log.info(f"AnimEngine: Started {animation_id} | params:{params}")

        
    async def stop(self, transition: Optional[TransitionConfig] = None, skip_fade: bool = False):
        """
        Stop animation with optional fade out.

        Args:
            transition: Transition config for fade out
            skip_fade: If True, skip fade out (used when caller already faded out)
        """
        if not self.is_running() or not self.current_animation:
            return

        transition = transition or self.transition_service.ANIMATION_SWITCH
        log.info(f"AnimEngine: Stopping animation {self.current_id} (skip_fade={skip_fade})")

        # Fade out (fade_out handles its own locking)
        # if not skip_fade:
        #    await self.transition_service.fade_out(transition)

        # Stop animation task
        self.current_animation.stop()

        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
            self.animation_task = None

        # Clear buffers after stopping animation (prevents stale pixels)
        self.zone_pixel_buffers.clear()
        self.zone_color_buffers.clear()

        log.debug(f"AnimEngine: stopped {self.current_id.name if self.current_id else '?'}")
        self.current_animation = None
        self.current_id = None
        
    
    # ------------------------------------------------------------------
    # RUNTIME HELPERS
    # ------------------------------------------------------------------

    def update_param(self, param: str, value):
        """
        Update parameter of running animation

        Args:
            param: Parameter name ('speed', 'color', etc.)
            value: New value
        """
        if self.current_animation:
            self.current_animation.update_param(param, value)

    def is_running(self) -> bool:
        """Check if animation is currently running"""
        return self.animation_task is not None and not self.animation_task.done()

    def get_current_animation_id(self) -> Optional[AnimationID]:
        """Get name of currently running animation"""
        return self.current_id if self.is_running() else None

    def get_current_animation(self) -> Optional['BaseAnimation']:
        """Get name of currently running animation"""
        return self.current_animation if self.is_running() else None

    def freeze(self) -> None:
        """
        Freeze animation frame submission for frame-by-frame debugging.

        Animation loop continues running internally, but frames are not
        submitted to FrameManager. This allows manual frame stepping without
        animation flicker.

        Used by FramePlaybackController when entering frame-by-frame mode.
        """
        self._frozen = True
        log.info(f"AnimationEngine: Froze animation {self.current_id.name if self.current_id else '?'}")

    def unfreeze(self) -> None:
        """
        Unfreeze animation frame submission after frame-by-frame debugging.

        Resumes normal frame submission to FrameManager.
        """
        self._frozen = False
        log.info(f"AnimationEngine: Unfroze animation {self.current_id.name if self.current_id else '?'}")

    # ------------------------------------------------------------------
    # INTERNAL LOOP
    # ------------------------------------------------------------------

    async def _get_first_frame(self) -> Optional[Dict]:
        """
        Build first frame of animation in memory without touching strip buffer.

        This allows fade_in to work on a complete first frame before animation starts,
        eliminating race condition between fade and animation loop.

        Returns:
            Dict mapping ZoneID to list of (r, g, b) tuples (zone_pixels format)
            or empty dict if failed
        """
        if not self.current_animation:
            return {}

        try:
            # Create async generator
            gen = self.current_animation.run()

            # Collect yields for first frame (animations yield multiple times per frame)
            # For zone-based animations: ~10 yields (one per zone)
            # For pixel-based animations: varies by animation (Snake=5-10, Breathe=10)
            zone_pixels_buffer: Dict[ZoneID, Dict[int, Tuple[int, int, int]]] = {}
            zone_colors_buffer: Dict[ZoneID, Tuple[int, int, int]] = {}

            yields_collected = 0
            max_yields = 100
            start_time = time.perf_counter()

            async for frame in gen:
                if len(frame) == 5:
                    # Pixel-level: (zone_id, pixel_index, r, g, b)
                    zone_id, pixel_index, r, g, b = frame
                    zone_pixels_buffer.setdefault(zone_id, {})[pixel_index] = (r, g, b)
                elif len(frame) == 4:
                    # Zone-level: (zone_id, r, g, b)
                    zone_id, r, g, b = frame
                    zone_colors_buffer[zone_id] = (r, g, b)

                yields_collected += 1

                # Small delay to collect batch of yields for first frame
                await asyncio.sleep(0.005)

                # Break after collecting adequate yields
                if yields_collected >= 15:
                    break

                if yields_collected >= max_yields:
                    log.warn(f"First frame collection exceeded {max_yields} yields")
                    break

            # Stop the generator
            await gen.aclose()

            # Convert to PixelFrame format
            zone_pixels_dict: Dict[ZoneID, List[Tuple[int, int, int]]] = {}

            # Process zone-level updates
            for zone_id, color in zone_colors_buffer.items():
                zone_length = self.zone_lengths.get(zone_id, 0)
                zone_pixels_dict[zone_id] = [color] * zone_length

            # Process pixel-level updates (overwrites zone colors if present)
            for zone_id, pixels_dict in zone_pixels_buffer.items():
                zone_length = self.zone_lengths.get(zone_id, 0)
                # Start with zone color if present, else black
                if zone_id in zone_pixels_dict:
                    pixels_list = zone_pixels_dict[zone_id].copy()
                else:
                    pixels_list = [(0, 0, 0)] * zone_length

                # Overlay pixel updates
                for pixel_idx, color in pixels_dict.items():
                    if 0 <= pixel_idx < zone_length:
                        pixels_list[pixel_idx] = color

                zone_pixels_dict[zone_id] = pixels_list

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            log.debug(f"First frame built: {yields_collected} yields in {elapsed_ms:.1f}ms")
            return zone_pixels_dict

        except Exception as e:
            log.error(f"Failed to build first frame: {e}")
            return {}

    async def _run_loop(self):
        """Main loop — consumes frames from the running animation"""

        assert self.current_animation is not None

        frame_count = 0
        log.info("AnimationEngine: run_loop started", animation=self.current_id)

        try:

            async for frame in self.current_animation.run(): # type: ignore
                frame_count += 1

                if not frame:
                    log.warn(f"[Frame {frame_count}] Empty frame received.")
                    continue

                # Collect pixel/zone updates for this frame
                if len(frame) == 5:
                    # Pixel-level update: (zone_id, pixel_index, r, g, b)
                    zone_id, pixel_index, r, g, b = frame
                    zone_pixels = self.zone_pixel_buffers.setdefault(zone_id, {})
                    zone_pixels[pixel_index] = (r, g, b)

                    log.debug(
                        f"[Frame {frame_count}] Pixel update: {zone_id.name}[{pixel_index}] = ({r},{g},{b})"
                    )

                elif len(frame) == 4:
                    # Zone-level update: (zone_id, r, g, b) - entire zone gets one color
                    zone_id, r, g, b = frame
                    # Store in zone color buffer (for zone-level animations like Breathe)
                    self.zone_color_buffers[zone_id] = (r, g, b)

                    log.debug(
                        f"[Frame {frame_count}] Zone update: {zone_id.name} color=({r},{g},{b})"
                    )

                else:
                    log.warn(f"[Frame {frame_count}] Unexpected frame format: {frame}")
                    continue

                # === Push collected frame to FrameManager ===
                if not hasattr(self, "frame_manager") or self.frame_manager is None:
                    log.error("[FrameManager] Missing reference — frame ignored!")
                    continue

                # Build frame from both buffers
                zone_pixels_dict = {}

                # Process zone-level updates (like Breathe animation)
                for zone_id, color in self.zone_color_buffers.items():
                    zone_length = self.zone_lengths.get(zone_id, 0)
                    # Create pixel list with all pixels set to the zone color
                    pixels_list = [color] * zone_length
                    zone_pixels_dict[zone_id] = pixels_list

                # Process pixel-level updates (like Snake animation) - overwrites zone colors if present
                for zone_id, pix_dict in self.zone_pixel_buffers.items():
                    if pix_dict:  # Only include zones with pixels
                        # Build complete pixel list for this zone (all pixels, default to black for unset)
                        zone_length = self.zone_lengths.get(zone_id, 0)
                        # If this zone was in zone_color_buffers, start with those colors
                        if zone_id in zone_pixels_dict:
                            pixels_list = zone_pixels_dict[zone_id].copy()
                        else:
                            # Otherwise start with black
                            pixels_list = [(0, 0, 0)] * zone_length

                        # Overlay pixel updates
                        for i in range(zone_length):
                            if i in pix_dict:
                                pixels_list[i] = pix_dict[i]
                        zone_pixels_dict[zone_id] = pixels_list

                # === Merge static zones into frame ===
                # Before submitting, add all STATIC zones to the frame
                for zone in self.zones:
                    zone_id = zone.config.id
                    # Skip if this zone is already in the animated frame or is OFF
                    if zone_id in zone_pixels_dict or zone.state.mode == ZoneRenderMode.OFF:
                        continue

                    # If zone is STATIC, add its current color
                    if zone.state.mode == ZoneRenderMode.STATIC:
                        rgb = zone.get_rgb()
                        zone_length = self.zone_lengths.get(zone_id, 0)
                        # Fill entire zone with static color
                        zone_pixels_dict[zone_id] = [rgb] * zone_length
                        log.debug(
                            f"[Frame {frame_count}] Merged static zone: {zone_id.name} color={rgb}"
                        )

                if zone_pixels_dict:
                    # Skip frame submission if frozen (frame-by-frame debugging)
                    if not self._frozen:
                        try:
                            frame = PixelFrame(
                                priority=FramePriority.ANIMATION,
                                source=FrameSource.ANIMATION,
                                zone_pixels=zone_pixels_dict
                            )
                            await self.frame_manager.submit_pixel_frame(frame)
                            if frame_count % 60 == 0:  # Log every 60 frames (~1 second at 60fps)
                                log.debug(
                                    f"[FrameManager] PixelFrame submitted #{frame_count}"
                                )
                        except Exception as e:
                            log.error(f"[FrameManager] Failed to submit PixelFrame: {e}")

                # Yield to event loop
                await asyncio.sleep(0)
                
                # log.debug(f"Yielded frame from {self.current_id.name} for {frame.zone_id}: {frame_data}")
        except asyncio.CancelledError:
            log.debug("Animation loop cancelled gracefully")
        except Exception as e:
            log.error(f"Animation error: {e}", animation=self.current_id)
            raise
        finally:
            log.info(
                f"AnimationEngine: run_loop stopped after {frame_count} frames ({self.current_id})"
            )

    def create_animation_instance(self, animation_id: AnimationID, **params):
        """
        Create (but do not start) an animation instance.
        Used for offline preview or frame-by-frame playback.
        """
        if animation_id not in self.ANIMATIONS:
            raise ValueError(f"Unknown animation ID: {animation_id}")

        anim_class = self.ANIMATIONS[animation_id]

        # Convert enum keys to str if needed
        safe_params = self.convert_params(params)

        anim = anim_class(
            zones=self.zones,
            excluded_zones=[],
            **safe_params
        )
        return anim
        
    def convert_params(self, params: dict) -> dict:
        """
        Convert parameter dictionary keys (possibly enums) to string names.

        Ensures **kwargs passed into animation constructors use string keys,
        since Python requires keyword argument names to be str.

        Example:
            {ParamID.ANIM_SPEED: 50, ParamID.ANIM_INTENSITY: 80}
            → {"ANIM_SPEED": 50, "ANIM_INTENSITY": 80}
        """
        if not params:
            return {}

        safe_params = {}
        for k, v in params.items():
            if hasattr(k, "name"):
                safe_params[k.name] = v
            elif isinstance(k, str):
                safe_params[k] = v
            else:
                safe_params[str(k)] = v
        return safe_params