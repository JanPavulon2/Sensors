"""
Animation system for LED strips

Provides base classes and engine for managing LED animations.

Current implementation:
- engine: Per-zone animation engine (active)
- base: Base animation class
- breathe, color_fade, etc.: Animation implementations
"""

# from .engine import AnimationEngine 
# from .base import BaseFrame, BaseAnimation
# from .breathe import BreatheAnimation

__all__ = [
    "engine",
    "base",
    "breathe"
]