"""
Animation system for LED strips

Provides base classes and engine for managing LED animations.

Current implementation:
- engine: Per-zone animation engine (active)
- base: Base animation class
- breathe, color_fade, etc.: Animation implementations
"""

__all__ = [
    "engine",
    "base",
    "breathe",
    "color_fade",
    "color_cycle",
    "color_snake",
    "snake",
    "matrix",
]