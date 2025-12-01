"""
Shutdown handler protocol for component-based graceful shutdown.

Each component that needs cleanup implements ShutdownHandler to participate
in the graceful shutdown sequence.
"""

from typing import Protocol

from abc import abstractmethod

class IShutdownHandler(Protocol):
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
        Higher priority shuts down earlier.
        """
        ...

    async def shutdown(self) -> None:
        """
        Called during coordinated shutdown.
        """
        ...
