"""Global application clock for animation synchronization."""

import time
from typing import Optional


class AppClock:
    """
    Global application clock for animation synchronization.

    Provides a single source of truth for animation time across the system.
    Supports pause/resume while maintaining accurate elapsed time.
    """

    def __init__(self):
        """Initialize clock at time zero."""
        self._start = time.perf_counter()
        self._paused_at: Optional[float] = None
        self._total_paused_time = 0.0

    def now(self) -> float:
        """
        Get current animation time in seconds.

        Returns time elapsed since clock start, excluding paused periods.
        """
        if self._paused_at is not None:
            # Clock is paused - return time at pause point
            return self._paused_at - self._start - self._total_paused_time

        # Clock is running - return current elapsed time
        return time.perf_counter() - self._start - self._total_paused_time

    def pause(self) -> None:
        """Pause the clock."""
        if self._paused_at is None:
            self._paused_at = time.perf_counter()

    def resume(self) -> None:
        """Resume the clock."""
        if self._paused_at is not None:
            self._total_paused_time += time.perf_counter() - self._paused_at
            self._paused_at = None

    def is_paused(self) -> bool:
        """Check if clock is currently paused."""
        return self._paused_at is not None

    def reset(self) -> None:
        """Reset clock to time zero."""
        self._start = time.perf_counter()
        self._paused_at = None
        self._total_paused_time = 0.0
