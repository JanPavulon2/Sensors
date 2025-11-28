"""
Lifecycle management for Diuna application.

Handles startup, running, and graceful shutdown with component-based architecture.
"""

from .shutdown_protocol import ShutdownHandler
from .shutdown_coordinator import ShutdownCoordinator
from .handlers import (
    LEDShutdownHandler,
    AnimationShutdownHandler,
    APIServerShutdownHandler,
    GPIOShutdownHandler,
    TaskCancellationHandler,
)

__all__ = [
    "ShutdownHandler",
    "ShutdownCoordinator",
    "LEDShutdownHandler",
    "AnimationShutdownHandler",
    "APIServerShutdownHandler",
    "GPIOShutdownHandler",
    "TaskCancellationHandler",
]
