"""
Animation system for LED strips

Provides base classes and engine for managing LED animations.
"""

from animations.base import BaseAnimation
from animations.engine import AnimationEngine
from animations.breathe import BreatheAnimation
from animations.color_fade import ColorFadeAnimation
from animations.snake import SnakeAnimation
from animations.color_snake import ColorSnakeAnimation

__all__ = [
    'BaseAnimation',
    'AnimationEngine',
    'BreatheAnimation',
    'ColorFadeAnimation',
    'SnakeAnimation',
    'ColorSnakeAnimation',
]
