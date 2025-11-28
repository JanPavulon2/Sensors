"""
Shutdown handler protocol for component-based graceful shutdown.

Each component that needs cleanup implements ShutdownHandler to participate
in the graceful shutdown sequence.
"""

from typing import Protocol
from abc import abstractmethod


class ShutdownHandler(Protocol):
    """
    Protocol for components that need graceful shutdown.

    Any application component can implement this protocol to participate
    in the shutdown sequence. The ShutdownCoordinator will call shutdown()
    on each handler in priority order.

    Example:
        class LEDShutdownHandler:
            @property
            def shutdown_priority(self) -> int:
                return 100  # Shutdown first

            async def shutdown(self) -> None:
                # Clear LEDs
                for strip in self.strips:
                    strip.clear()
    """

    @property
    def shutdown_priority(self) -> int:
        """
        Shutdown priority (higher = shutdown first).

        Priority levels:
        - 100: LEDs (clear immediately to prevent leaving them on)
        - 80: Animations (stop animation engine)
        - 60: API Server (stop HTTP/WebSocket server)
        - 40: Controllers (stop background processing)
        - 20: Event systems (stop event bus)
        - 10: GPIO (cleanup hardware last)

        Returns:
            Priority value (0-100+). Higher priority shuts down first.
        """
        ...

    async def shutdown(self) -> None:
        """
        Perform graceful shutdown of this component.

        This method is called during the shutdown sequence. It should:
        1. Stop all activity
        2. Clean up resources
        3. Release ports/handles
        4. Be idempotent (safe to call multiple times)

        Can raise exceptions, which are caught and logged by ShutdownCoordinator.

        Returns:
            None

        Raises:
            asyncio.TimeoutError: If shutdown takes too long
            Exception: Any other exception is logged but doesn't prevent other handlers
        """
        ...
