"""
Animation Engine

Manages animation lifecycle, switching between animations, and updating strip.
Uses TransitionService for smooth transitions between animation states.
"""

import asyncio
from typing import Optional, Dict, List, Any, Type

from animations.base import BaseAnimation  # ✅ direct import — breaks circular import safely

# Import animation classes here (NOT in __init__ to avoid circular imports)
from animations.breathe import BreatheAnimation
from animations.color_fade import ColorFadeAnimation
from animations.snake import SnakeAnimation
from animations.color_snake import ColorSnakeAnimation
from animations.color_cycle import ColorCycleAnimation

from models.domain.zone import ZoneCombined
from services.transition_service import TransitionService
from services import AnimationService
from engine import FrameManager
from models.transition import TransitionConfig, TransitionType
from models.enums import ParamID, LogCategory
from models.frame import Frame, ZoneFrame
from models.enums import ZoneID
from utils.logger import get_category_logger
from models.enums import LogCategory, AnimationID
from components import ZoneStrip

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
        self.transition_service = TransitionService(strip)
        self.frame_manager = frame_manager
        
        self.zone_pixel_buffers: dict[ZoneID, dict[int, tuple[int, int, int]]] = {}
        self.zone_lengths: dict[ZoneID, int] = {
            z.config.id: z.config.pixel_count for z in zones
        }
        
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
            color = self.strip.get_zone_color(zone.config.tag)
            if color:
                self.current_animation.set_zone_color_cache(zone.config.id, *color)

        # Step 5: Render first frame to buffer (WITHOUT starting loop)
        log.debug("AnimEngine: Rendering first frame...")
        first_frame = await self._get_first_frame()

        # Step 6: CROSSFADE from old to new (or fade_in if no old frame)
        if first_frame:
            if old_frame and len(old_frame) == len(first_frame):
                log.debug("AnimEngine: Crossfading from old to new animation...")
                await self.transition_service.crossfade(old_frame, first_frame, transition)
            else:
                # No old frame or size mismatch - just fade in from black
                log.debug("AnimEngine: Fading in from black...")
                await self.transition_service.fade_in(first_frame, transition)

        # Step 7: NOW start animation loop (transition complete - no race condition)
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
        if not skip_fade:
            await self.transition_service.fade_out(transition)

        # Stop animation task
        self.current_animation.stop()

        if self.animation_task:
            self.animation_task.cancel()
            try:
                await self.animation_task
            except asyncio.CancelledError:
                pass
            self.animation_task = None

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


    # ------------------------------------------------------------------
    # INTERNAL LOOP
    # ------------------------------------------------------------------

    async def _get_first_frame(self) -> Optional[List]:
        """
        Render first frame of animation to buffer without starting full loop.

        This allows fade_in to work on a complete first frame before animation starts,
        eliminating race condition between fade and animation loop.

        Returns:
            List of RGB tuples (one per pixel) or empty list if failed
        """
        if not self.current_animation:
            return []

        try:
            # Create async generator
            gen = self.current_animation.run()

            # Collect yields for first frame (animations yield multiple times per frame)
            # For zone-based animations: ~10 yields (one per zone)
            # For pixel-based animations: varies by animation (Snake=5-10, Breathe=10)
            max_yields = 50  # Safety limit
            yields_collected = 0

            async for frame in gen:
                # Apply to buffer (show=False)
                if len(frame) == 5:
                    zone_id, pixel_index, r, g, b = frame
                    self.strip.set_pixel_color(zone_id.name, pixel_index, r, g, b, show=False)
                elif len(frame) == 4:
                    zone_id, r, g, b = frame
                    self.strip.set_zone_color(zone_id.name, r, g, b, show=False)

                yields_collected += 1

                # Small delay to collect batch of yields for first frame
                # (most animations yield all zones/pixels quickly, then sleep)
                await asyncio.sleep(0.01)

                # Break after collecting yields (before animation sleeps for frame delay)
                if yields_collected >= 10:  # Most animations yield ~10 times per frame
                    break

                if yields_collected >= max_yields:
                    log.warn(f"First frame collection exceeded {max_yields} yields")
                    break

            # Stop the generator
            await gen.aclose()

            # Return current buffer state
            frame = self.strip.get_frame() if hasattr(self.strip, 'get_frame') else []
            log.debug(f"First frame rendered: {yields_collected} yields collected")
            return frame

        except Exception as e:
            log.error(f"Failed to get first frame: {e}")
            return []

    async def _run_loop(self):
        """Main loop — consumes frames from the running animation"""
        
        assert self.current_animation is not None
        
        frame_count = 0
        log.info("AnimationEngine: run_loop started", animation=self.current_id)

        try:
            
            async for frame in self.current_animation.run():
                frame_count += 1
                
                if not frame:
                    log.warn(f"[Frame {frame_count}] Empty frame received.")
                    continue
                
                # Batch pixel/zone updates without immediate show()
                if len(frame) == 5:
                    zone_id, pixel_index, r, g, b = frame
                    zone_pixels = self.zone_pixel_buffers.setdefault(zone_id, {})
                    zone_pixels[pixel_index] = (r, g, b)
                    
                    log.debug(
                        f"[Frame {frame_count}] Pixel update: {zone_id.name}[{pixel_index}] = ({r},{g},{b})"
                    )
                    
                    # frame = ZoneFrame(zone_id=zone_id, pixels=[(pixel_index, r, g, b)])
                    # self.strip.set_pixel_color(zone_id.name, pixel_index, r, g, b, show=False)
                elif len(frame) == 4:
                    zone_id, r, g, b = frame
                    zone_length = self.zone_lengths.get(zone_id, 0)
                    pixels = [(r, g, b)] * zone_length
                    
                    self.zone_pixel_buffers[zone_id] = {
                        i: (r, g, b) for i in range(zone_length)
                    }
                    
                    log.debug(
                        f"[Frame {frame_count}] Zone update: {zone_id.name} len={zone_length}, color=({r},{g},{b})"
                    )
                
                else:
                    log.warn(f"[Frame {frame_count}] Unexpected frame format: {frame}")
                    continue
                
                    # frame = ZoneFrame(zone_id=zone_id, zone_color=(r, g, b))
                    # self.strip.set_zone_color(zone_id.name, r, g, b, show=False)

                 # === Push to FrameManager ===
                if not hasattr(self, "frame_manager") or self.frame_manager is None:
                    log.error("[FrameManager] Missing reference — frame ignored!")
                    continue

                # co tick wysyłamy gotową ramkę do FrameManagera
                for zone_id, pix_dict in self.zone_pixel_buffers.items():
                    pixels_list = [pix_dict[i] for i in sorted(pix_dict.keys())]
                    try:
                        self.frame_manager.submit_zone_frame(zone_id, pixels_list)
                        if frame_count % 60 == 0:  # Log every 60 frames (~1 second at 60fps)
                            log.info(
                                f"[FrameManager] ZoneFrame submitted #{frame_count}: {zone_id.name} ({len(pixels_list)} px)"
                            )
                    except Exception as e:
                        log.error(f"[FrameManager] Failed to submit ZoneFrame: {e}")

                # odroczony yield (można dodać delay jeśli trzeba)
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