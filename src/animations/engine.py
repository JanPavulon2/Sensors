"""
Animation Engine

Manages animation lifecycle, switching between animations, and updating strip.
Uses TransitionService for smooth transitions between animation states.
"""

import asyncio
from typing import Dict, Optional, Callable, Type, overload
from animations.base import BaseAnimation
from animations.breathe import BreatheAnimation
from engine.frame_manager import FrameManager
from models.enums import AnimationID, ZoneID, FramePriority, FrameSource
# from animations.registry import ANIMATION_REGISTRY
from models.frame import SingleZoneFrame
from services.zone_service import ZoneService
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.ANIMATION)

def _build_animation_registry() -> Dict[AnimationID, Type[BaseAnimation]]:
    """Build animation registry dynamically from AnimationID enum"""
    class_map = {
        # AnimationID.COLOR_CYCLE: ColorCycleAnimation,
        AnimationID.BREATHE: BreatheAnimation,
        # AnimationID.COLOR_FADE: ColorFadeAnimation,
        # AnimationID.SNAKE: SnakeAnimation,
        # AnimationID.COLOR_SNAKE: ColorSnakeAnimation,
        # AnimationID.MATRIX: MatrixAnimation,  # TEMPORARY: Disabled
    }

    # Convert enum to string keys using .name
    return {anim_id: anim_class for anim_id, anim_class in class_map.items()}

class AnimationEngine:
    """
    NEW AnimationEngine V3 (per-zone)
    
    • Each zone gets its own animation task
    • Tasks yield SingleZoneFrame(partial=True)
    • Engine forwards frames to FrameManager
    """

    # Registry of available animations - built dynamically from enum
    ANIMATIONS: Dict[AnimationID, Type[BaseAnimation]] = _build_animation_registry()

    def __init__(self, frame_manager: FrameManager, zone_service: ZoneService):
        """
        Initialize animation engine
        """
        self.frame_manager = frame_manager
        self.zone_service = zone_service
        
        # active tasks: zone_id → asyncio.Task
        self.tasks: Dict[ZoneID, asyncio.Task] = {}
        
        # remembering what runs where
        self.active_anim_ids: Dict[ZoneID, AnimationID] = {}
        self.active_params: Dict[ZoneID, dict] = {}
        
        self._lock = asyncio.Lock()
    
    # ============================================================
    # Core control methods
    # ============================================================

    async def start_for_zone(
        self,
        zone_id: ZoneID,
        anim_id: AnimationID,
        params: dict
    ):
        """
        Start an animation by animation ID with optional transition
        """
        
        async with self._lock:
            # Stop previous if exists
            if zone_id in self.tasks:
                log.warn(f"Zone {zone_id.name} already has animation, stopping old one")
                await self.stop_for_zone(zone_id)

            # Resolve zone model
            zone = self.zone_service.get_zone(zone_id)
            if not zone:
                log.error(f"No such zone: {zone_id}")
                return


            # Build animation instance
            AnimClass = self.ANIMATIONS.get(anim_id)
            if AnimClass is None:
                log.error(f"Animation {anim_id} not registered")
                return

            safe_params = params.copy()

            speed = safe_params.pop("speed", 50)

            anim = AnimClass(
                zone=zone,
                speed=speed,
                **safe_params
            )

            # Store meta
            self.active_anim_ids[zone_id] = anim_id
            self.active_params[zone_id] = params

            # Spawn task
            task = asyncio.create_task(self._run_loop(zone_id, anim))
            self.tasks[zone_id] = task

            log.info(f"Started animation {anim_id.name} on zone {zone_id.name}. Active zones: {list(self.tasks.keys())}")
            
    async def stop_for_zone(self, zone_id: ZoneID):
        """Stop animation for a single zone."""
        async with self._lock:
            task = self.tasks.pop(zone_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self.active_anim_ids.pop(zone_id, None)
            self.active_params.pop(zone_id, None)

            log.info(f"Stopped animation on zone {zone_id.name}")
            

    async def stop_all(self):
        """Stop all animations safely."""
        zones = list(self.tasks.keys())
        for zid in zones:
            await self.stop_for_zone(zid)
        
    # ------------------------------------------------------------
    # Parameter update (live)
    # ------------------------------------------------------------

    def update_param(self, zone_id: ZoneID, param_name: str, value):
        """Update a running animation's parameter live."""
        if zone_id not in self.tasks:
            return

        params = self.active_params.get(zone_id)
        if not params:
            return

        params[param_name] = value

        # Animation instance is stored inside coroutine:
        # the coroutine will check params each frame
        log.info(
            f"Live param update on {zone_id.name}: {param_name} → {value}"
        )


    # ------------------------------------------------------------
    # Internal animation loop
    # ------------------------------------------------------------

    async def _run_loop(self, zone_id: ZoneID, animation: BaseAnimation):
        """Run an animation until stopped."""
        log.info(f"_run_loop started for {zone_id.name}")
        try:
            frame_count = 0
            while True:
                try:
                    frame = await animation.step()
                    frame_count += 1
                    # if frame_count % 60 == 0:
                    #     log.debug(f"[{zone_id.name}] Animation frame #{frame_count}")

                except Exception as e:
                    log.error(f"Animation step error on {zone_id.name}: {e}", exc_info=True)
                    await asyncio.sleep(0.05)
                    continue

                try:
                    await self.frame_manager.push_frame(frame)
                except Exception as e:
                    log.error(f"Failed to push frame for {zone_id.name}: {e}", exc_info=True)

                # yield to event loop (FrameManager drives actual refresh rate)
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            log.debug(f"Animation task for {zone_id.name} canceled")
        except Exception as e:
            log.error(f"Animation error on {zone_id.name}: {e}", exc_info=True)
        finally:
            # remove itself if crashed
            self.tasks.pop(zone_id, None)
            log.info(f"Animation task for {zone_id.name} finished after {frame_count} frames")
            
    # ------------------------------------------------------------------
    # RUNTIME HELPERS
    # ------------------------------------------------------------------

    def get_current_animation_id(self, zone_id: ZoneID) -> Optional[AnimationID]:
        """Get name of currently running animation"""
        return self.active_anim_ids.get(zone_id)

    # def update_param(self, param: str, value):
    #     """
    #     Update parameter of running animation

    #     Args:
    #         param: Parameter name ('speed', 'color', etc.)
    #         value: New value
    #     """
    #     if self.current_animation:
    #         self.current_animation.update_param(param, value)

    def is_running(self, zone_id: Optional[ZoneID] = None) -> bool:
        """
        Check if animations are running.

        If zone_id is None → check if ANY zone has running animation.
        If zone_id provided → check that one zone.
        """
        if zone_id is not None:
            task = self.tasks.get(zone_id)
            return task is not None and not task.done()

        return any(not t.done() for t in self.tasks.values())

    def create_animation_instance(self, anim_id: AnimationID, zone_id: Optional[ZoneID] = None, **params):
        """
        Create an animation instance for offline use (frame-by-frame debugging).

        Does not start the animation - just creates the instance.
        Used by FramePlaybackController for preloading animation frames.

        Args:
            anim_id: Animation ID to instantiate
            zone_id: Zone to attach animation to (uses first available if not provided)
            **params: Animation parameters (speed, etc.)

        Returns:
            Animation instance or None if animation type not found
        """
        AnimClass = self.ANIMATIONS.get(anim_id)
        if AnimClass is None:
            log.error(f"Animation {anim_id} not registered")
            return None

        # Get zone (use first available if not specified)
        if zone_id is None:
            all_zones = self.zone_service.get_all()
            if not all_zones:
                log.error("No zones available for animation instance")
                return None
            zone = all_zones[0]
        else:
            zone = self.zone_service.get_zone(zone_id)
            if not zone:
                log.error(f"Zone {zone_id} not found")
                return None

        # Extract speed and other params
        safe_params = params.copy()
        speed = safe_params.pop("speed", 50)

        # Create instance
        try:
            anim = AnimClass(zone=zone, speed=speed, **safe_params)
            return anim
        except Exception as e:
            log.error(f"Failed to create animation instance: {e}")
            return None
    
    # def is_running(self, zone_id: Optional[ZoneID] = None) -> bool:
    #     """
    #     Check if animation is currently running.

    #     When called without arguments, checks if any animation is running for any zone.
    #     When called with zone_id, checks if that specific zone has a running animation.

    #     Args:
    #         zone_id: Optional zone ID to check. If None, checks all zones.

    #     Returns:
    #         True if at least one animation is running, False otherwise
    #     """
    #     if zone_id is not None:
    #         task = self.tasks.get(zone_id)
    #         return task is not None and not task.done()

    #     # Check if any animation is running for any zone
    #     for task in self.tasks.values():
    #         if not task.done():
    #             return True
    #     return False


    # def get_current_animation(self) -> Optional['BaseAnimation']:
    #     """Get name of currently running animation"""
    #     return self.current_animation if self.is_running() else None

    # def freeze(self) -> None:
    #     """
    #     Freeze animation frame submission for frame-by-frame debugging.

    #     Animation loop continues running internally, but frames are not
    #     submitted to FrameManager. This allows manual frame stepping without
    #     animation flicker.

    #     Used by FramePlaybackController when entering frame-by-frame mode.
    #     """
    #     self._frozen = True
    #     log.info(f"AnimationEngine: Froze animation {self.current_id.name if self.current_id else '?'}")

    # def unfreeze(self) -> None:
    #     """
    #     Unfreeze animation frame submission after frame-by-frame debugging.

    #     Resumes normal frame submission to FrameManager.
    #     """
    #     self._frozen = False
    #     log.info(f"AnimationEngine: Unfroze animation {self.current_id.name if self.current_id else '?'}")

    # # ------------------------------------------------------------------
    # # INTERNAL LOOP
    # # ------------------------------------------------------------------

    # async def _get_first_frame(self) -> Optional[Dict]:
    #     """
    #     Build first frame of animation in memory without touching strip buffer.

    #     This allows fade_in to work on a complete first frame before animation starts,
    #     eliminating race condition between fade and animation loop.

    #     Returns:
    #         Dict mapping ZoneID to list of (r, g, b) tuples (zone_pixels format)
    #         or empty dict if failed
    #     """
    #     if not self.current_animation:
    #         return {}

    #     try:
    #         # Create async generator
    #         gen = self.current_animation.run()

    #         # Collect yields for first frame (animations yield multiple times per frame)
    #         # For zone-based animations: ~10 yields (one per zone)
    #         # For pixel-based animations: varies by animation (Snake=5-10, Breathe=10)
    #         zone_pixels_buffer: Dict[ZoneID, Dict[int, Color]] = {}
    #         zone_colors_buffer: Dict[ZoneID, Color] = {}

    #         yields_collected = 0
    #         max_yields = 100
    #         start_time = time.perf_counter()

    #         async for frame in gen:
    #             if len(frame) == 5:
    #                 # Pixel-level: (zone_id, pixel_index, r, g, b)
    #                 zone_id, pixel_index, r, g, b = frame
    #                 zone_pixels_buffer.setdefault(zone_id, {})[pixel_index] = Color.from_rgb(r, g, b)
    #             elif len(frame) == 4:
    #                 # Zone-level: (zone_id, r, g, b)
    #                 zone_id, r, g, b = frame
    #                 zone_colors_buffer[zone_id] = Color.from_rgb(r, g, b)

    #             yields_collected += 1

    #             # Small delay to collect batch of yields for first frame
    #             await asyncio.sleep(0.005)

    #             # Break after collecting adequate yields
    #             if yields_collected >= 15:
    #                 break

    #             if yields_collected >= max_yields:
    #                 log.warn(f"First frame collection exceeded {max_yields} yields")
    #                 break

    #         # Stop the generator
    #         await gen.aclose()

    #         # Convert to PixelFrame format
    #         zone_pixels_dict: Dict[ZoneID, List[Color]] = {}

    #         # Process zone-level updates
    #         for zone_id, color in zone_colors_buffer.items():
    #             zone_length = self.zone_lengths.get(zone_id, 0)
    #             zone_pixels_dict[zone_id] = [color] * zone_length

    #         # Process pixel-level updates (overwrites zone colors if present)
    #         for zone_id, pixels_dict in zone_pixels_buffer.items():
    #             zone_length = self.zone_lengths.get(zone_id, 0)
    #             # Start with zone color if present, else black
    #             if zone_id in zone_pixels_dict:
    #                 pixels_list = zone_pixels_dict[zone_id].copy()
    #             # else:
    #                 # pixels_list = Color.black().to_rgb() * zone_length

    #             # Overlay pixel updates
    #             for pixel_idx, color in pixels_dict.items():
    #                 if 0 <= pixel_idx < zone_length:
    #                     pixels_list[pixel_idx] = color

    #             zone_pixels_dict[zone_id] = pixels_list

    #         elapsed_ms = (time.perf_counter() - start_time) * 1000
    #         log.debug(f"First frame built: {yields_collected} yields in {elapsed_ms:.1f}ms")
    #         return zone_pixels_dict

    #     except Exception as e:
    #         log.error(f"Failed to build first frame: {e}")
    #         return {}

    # async def _run_loop(self):
    #     """Main loop — consumes frames from the running animation"""

    #     assert self.current_animation is not None

    #     frame_count = 0
    #     log.info("AnimationEngine: run_loop started", animation=self.current_id)

    #     try:

    #         async for frame in self.current_animation.run(): # type: ignore
    #             frame_count += 1

    #             if not frame:
    #                 log.warn(f"[Frame {frame_count}] Empty frame received.")
    #                 continue

    #             # Collect pixel/zone updates for this frame
    #             if len(frame) == 5:
    #                 # Pixel-level update: (zone_id, pixel_index, r, g, b)
    #                 zone_id, pixel_index, r, g, b = frame
    #                 zone_pixels = self.zone_pixel_buffers.setdefault(zone_id, {})
    #                 zone_pixels[pixel_index] = Color.from_rgb(r, g, b)

    #                 log.debug(
    #                     f"[Frame {frame_count}] Pixel update: {zone_id.name}[{pixel_index}] = ({r},{g},{b})"
    #                 )

    #             elif len(frame) == 4:
    #                 # Zone-level update: (zone_id, r, g, b) - entire zone gets one color
    #                 zone_id, r, g, b = frame
    #                 # Store in zone color buffer (for zone-level animations like Breathe)
    #                 self.zone_color_buffers[zone_id] = Color.from_rgb(r, g, b)

    #                 log.debug(
    #                     f"[Frame {frame_count}] Zone update: {zone_id.name} color=({r},{g},{b})"
    #                 )
                    
    #             elif len(frame) == 2:
    #                 # Zone-level update: (zone_id, Color) - entire zone gets one color
    #                 zone_id, color = frame
    #                 # Store in zone color buffer (for zone-level animations like Breathe)
    #                 self.zone_color_buffers[zone_id] = color

    #                 log.debug(
    #                     f"[Frame {frame_count}] Zone update: {zone_id.name} color=({color})"
    #                 )

    #             else:
    #                 log.warn(f"[Frame {frame_count}] Unexpected frame format: {frame}")
    #                 continue

    #             # === Push collected frame to FrameManager ===
    #             if not hasattr(self, "frame_manager") or self.frame_manager is None:
    #                 log.error("[FrameManager] Missing reference — frame ignored!")
    #                 continue

    #             # Build frame from both buffers
    #             zone_pixels_dict = {}

    #             # Process zone-level updates (like Breathe animation)
    #             for zone_id, color in self.zone_color_buffers.items():
    #                 zone_length = self.zone_lengths.get(zone_id, 0)
    #                 # Create pixel list with all pixels set to the zone color (convert RGB tuple to Color)
    #                 color_obj = color
    #                 pixels_list = [color_obj] * zone_length
    #                 zone_pixels_dict[zone_id] = pixels_list

    #             # Process pixel-level updates (like Snake animation) - overwrites zone colors if present
    #             for zone_id, pix_dict in self.zone_pixel_buffers.items():
    #                 if pix_dict:  # Only include zones with pixels
    #                     # Build complete pixel list for this zone (all pixels, default to black for unset)
    #                     zone_length = self.zone_lengths.get(zone_id, 0)
    #                     # If this zone was in zone_color_buffers, start with those colors
    #                     if zone_id in zone_pixels_dict:
    #                         pixels_list = zone_pixels_dict[zone_id].copy()
    #                     else:
    #                         # Otherwise start with black (as Color objects)
    #                         pixels_list = [Color.black()] * zone_length

    #                     # Overlay pixel updates (convert RGB tuples to Color objects)
    #                     for i in range(zone_length):
    #                         if i in pix_dict:
    #                             pixels_list[i] = pix_dict[i]
    #                     zone_pixels_dict[zone_id] = pixels_list

    #             if zone_pixels_dict:
    #                 # Skip frame submission if frozen (frame-by-frame debugging)
    #                 if not self._frozen:
    #                     try:
    #                         frame = PixelFrame(
    #                             priority=FramePriority.ANIMATION,
    #                             source=FrameSource.ANIMATION,
    #                             zone_pixels=zone_pixels_dict,
    #                             partial=True
    #                         )
    #                         await self.frame_manager.submit_pixel_frame(frame)
    #                         if frame_count % 60 == 0:  # Log every 60 frames (~1 second at 60fps)
    #                             log.debug(
    #                                 f"[FrameManager] PixelFrame submitted #{frame_count}"
    #                             )
    #                     except Exception as e:
    #                         log.error(f"[FrameManager] Failed to submit PixelFrame: {e}")

    #             # Yield to event loop
    #             await asyncio.sleep(0)
                
    #             # log.debug(f"Yielded frame from {self.current_id.name} for {frame.zone_id}: {frame_data}")
    #     except asyncio.CancelledError:
    #         log.debug("Animation loop cancelled gracefully")
    #     except Exception as e:
    #         log.error(f"Animation error: {e}", animation=self.current_id)
    #         raise
    #     finally:
    #         log.info(
    #             f"AnimationEngine: run_loop stopped after {frame_count} frames ({self.current_id})"
    #         )

    # def create_animation_instance(self, animation_id: AnimationID, **params):
    #     """
    #     Create (but do not start) an animation instance.
    #     Used for offline preview or frame-by-frame playback.
    #     """
    #     if animation_id not in self.ANIMATIONS:
    #         raise ValueError(f"Unknown animation ID: {animation_id}")

    #     anim_class = self.ANIMATIONS[animation_id]

    #     # Convert enum keys to str if needed
    #     safe_params = self.convert_params(params)

    #     anim = anim_class(
    #         zones=self.zones,
    #         excluded_zones=[],
    #         **safe_params
    #     )
    #     return anim
        
    # def convert_params(self, params: dict) -> dict:
    #     """
    #     Convert parameter dictionary keys (possibly enums) to string names.

    #     Ensures **kwargs passed into animation constructors use string keys,
    #     since Python requires keyword argument names to be str.

    #     Example:
    #         {ParamID.ANIM_SPEED: 50, ParamID.ANIM_INTENSITY: 80}
    #         → {"ANIM_SPEED": 50, "ANIM_INTENSITY": 80}
    #     """
    #     if not params:
    #         return {}

    #     safe_params = {}
    #     for k, v in params.items():
    #         if hasattr(k, "name"):
    #             safe_params[k.name] = v
    #         elif isinstance(k, str):
    #             safe_params[k] = v
    #         else:
    #             safe_params[str(k)] = v
    #     return safe_params