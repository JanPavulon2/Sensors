"""
Transition Models

Defines transition types and configurations for LED state changes.
Used across animations, mode switches, and startup/shutdown sequences.
"""

from enum import Enum, auto
from typing import Optional, Callable


class TransitionType(Enum):
    """
    Types of LED state transitions

    Used for any LED state change in the system:
    - App startup/shutdown
    - Mode switches (STATIC ↔ ANIMATION)
    - Animation changes
    - Zone changes
    - Power toggles
    """
    NONE = auto()          # Instant switch (no transition)
    FADE = auto()          # Smooth fade between states
    CUT = auto()           # Hard cut with brief black frame
    CROSSFADE = auto()     # Blend between states (future feature)


class TransitionConfig:
    """
    Configuration for LED state transition

    Reusable configuration object for defining how to transition between
    any LED states in the system. Supports customizable timing, steps,
    and easing functions.

    Attributes:
        type: Type of transition (NONE, FADE, CUT, CROSSFADE)
        duration_ms: Total transition duration in milliseconds
        steps: Number of intermediate frames for smooth transitions
        ease_function: Optional easing function (t: 0.0-1.0) → (factor: 0.0-1.0)

    Examples:
        # Slow fade-in for app startup
        startup = TransitionConfig(
            type=TransitionType.FADE,
            duration_ms=1000,
            steps=20
        )
        
        # Quick cut for animation switch
        anim_switch = TransitionConfig(
            type=TransitionType.CUT,
            duration_ms=100
        )
        
        # Instant (no transition)
        instant = TransitionConfig(type=TransitionType.NONE)
    """

    def __init__(
        self,
        type: TransitionType = TransitionType.FADE,
        duration_ms: int = 300,
        steps: int = 10,
        ease_function: Optional[Callable[[float], float]] = None
    ):
        """
        Initialize transition configuration

        Args:
            type: Transition type (NONE, FADE, CUT, CROSSFADE)
            duration_ms: Total duration in milliseconds
            steps: Number of intermediate frames (for FADE)
            ease_function: Optional easing function for brightness curve
        """
        self.type = type
        self.duration_ms = duration_ms
        self.steps = max(1, steps)  # At least 1 step
        self.ease_function = ease_function or ease_linear

    def __repr__(self):
        return f"TransitionConfig({self.type.name}, {self.duration_ms}ms, {self.steps} steps)"


# === Easing Functions ===
# Common easing functions for smooth transitions

def ease_linear(t: float) -> float:
    """
    Linear easing (constant speed)

    Args:
        t: Progress (0.0 = start, 1.0 = end)

    Returns:
        Factor (0.0 to 1.0) for brightness
    """
    return t


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in (slow start → fast end)"""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out (fast start → slow end)"""
    return 1 - (1 - t) * (1 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out (slow start → fast middle → slow end)"""
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def ease_in_cubic(t: float) -> float:
    """Cubic ease-in (very slow start)"""
    return t * t * t


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out (very slow end)"""
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out (very smooth acceleration/deceleration)"""
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
