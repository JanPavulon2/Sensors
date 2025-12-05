"""
Port management service for ensuring clean port binding.

Provides PortManager singleton for:
1. Port availability checking
2. Finding processes using specific ports
3. Force-freeing orphaned ports (recovery from crashes)
4. Pre-startup port cleanup with automatic retry logic

Used to prevent "Address already in use" crashes when previous
application instance left port orphaned due to Starlette lifespan bug
or was suspended with Ctrl+Z.

Note: This application runs with sudo privileges due to ws281x library
requirements. Port cleanup commands also run with sudo context.

Usage:
    port_mgr = PortManager.instance()
    await port_mgr.ensure_available(port=8000)
"""

import socket
import subprocess
import asyncio
from typing import Optional
from utils.logger import get_logger, LogCategory

log = get_logger().for_category(LogCategory.SHUTDOWN)


class PortManager:
    """
    Singleton service for managing port availability and cleanup.

    Handles:
    - Port availability checking with timeout protection
    - Process detection (handles suspended processes)
    - Force-freeing orphaned ports with retry logic
    - Automatic recovery from crashes/orphaned sockets
    """

    _instance: Optional["PortManager"] = None

    def __init__(self):
        """Initialize port manager singleton."""
        pass

    @classmethod
    def instance(cls) -> "PortManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    async def is_port_in_use(self, port: int, host: str = "0.0.0.0") -> bool:
        """
        Check if a port is currently in use.

        Uses an async executor with timeout to prevent hanging on suspended
        processes (e.g., from Ctrl+Z).

        Args:
            port: Port number to check (0-65535)
            host: Host address (default: 0.0.0.0 for any interface)

        Returns:
            True if port is in use, False if available
        """
        def _check_port():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)  # Quick timeout
                    s.bind((host, port))
                    return False  # Successfully bound = port is free
            except socket.timeout:
                return True  # Timeout = port in use (likely suspended)
            except OSError:
                return True  # OSError = port in use

        try:
            # Run socket check in executor with overall timeout
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, _check_port),
                timeout=2.0  # 2-second overall timeout
            )
            return result
        except asyncio.TimeoutError:
            log.warn(f"Port {port} check timed out - assuming in use")
            return True
        except Exception as e:
            log.error(f"Error checking port {port}: {e}")
            return True

    def find_process_on_port(self, port: int) -> Optional[int]:
        """
        Find process ID (PID) using a specific port.

        Tries multiple detection methods:
        1. `lsof` - standard approach
        2. `fuser` - fallback if lsof fails or hangs

        Handles both active and suspended processes (from Ctrl+Z).

        Args:
            port: Port number to check

        Returns:
            PID if found, None otherwise
        """
        # Try method 1: lsof
        pid = self._try_lsof_detection(port)
        if pid is not None:
            return pid

        # Fallback: Try method 2: fuser
        pid = self._try_fuser_detection(port)
        if pid is not None:
            return pid

        return None

    async def ensure_available(self, port: int, host: str = "0.0.0.0") -> None:
        """
        Ensure port is available for binding, force-freeing if necessary.

        Multi-stage cleanup process:
        1. Force-free any process holding the port
        2. Wait for OS cleanup (if port in TIME_WAIT state)
        3. Retry with delays
        4. Final fallback: fuser -k

        Handles:
        - Active processes (SIGKILL)
        - Suspended processes (SIGCONT then SIGKILL)
        - Ports in TIME_WAIT state (graceful waiting)
        - Uvicorn/Starlette lifespan task leaks (forced cleanup)

        Args:
            port: Port to ensure availability (0-65535)
            host: Host address to bind (default: any interface)

        Raises:
            RuntimeError: If port cannot be freed after all cleanup attempts
        """
        if not await self.is_port_in_use(port, host):
            log.debug(f"Port {port} is available")
            return

        log.warn(f"Port {port} is occupied, attempting cleanup...")

        # Stage 1: Try to force-free any active process
        if await self._attempt_force_free_port(port, host):
            return

        # Stage 2: Wait for OS cleanup (TIME_WAIT state)
        if await self._attempt_wait_for_cleanup(port, host):
            return

        # Stage 3: Final fallback with fuser
        if await self._attempt_fuser_final(port, host):
            return

        # Failed - port still in use
        raise RuntimeError(
            f"Port {port} is in use and could not be freed after all cleanup attempts. "
            f"A previous application instance may still be running or in an orphaned state. "
            f"Try: sudo fuser -k {port}/tcp  or  lsof -i :{port}"
        )

    # ==========================================================================
    # PRIVATE HELPERS - Process Detection
    # ==========================================================================

    def _try_lsof_detection(self, port: int) -> Optional[int]:
        """
        Try to find process PID using lsof command.

        Args:
            port: Port number to check

        Returns:
            PID if found, None otherwise
        """
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=1  # Shorter timeout to avoid hanging on suspended process
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return int(result.stdout.strip().split()[0])
                except (ValueError, IndexError):
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def _try_fuser_detection(self, port: int) -> Optional[int]:
        """
        Try to find process PID using fuser command (fallback).

        Args:
            port: Port number to check

        Returns:
            PID if found, None otherwise
        """
        try:
            result = subprocess.run(
                ["fuser", f"{port}/tcp"],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return int(result.stdout.strip().split()[0])
                except (ValueError, IndexError):
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    # ==========================================================================
    # PRIVATE HELPERS - Process State Management
    # ==========================================================================

    def _get_process_state(self, pid: int) -> Optional[str]:
        """
        Get process state (R, S, T, Z, etc.) from /proc/[pid]/stat.

        Process states:
        - T = stopped (from SIGSTOP, e.g., Ctrl+Z)
        - Z = zombie
        - S = interruptible sleep
        - R = running

        Args:
            pid: Process ID

        Returns:
            Process state character, or None if process not found
        """
        try:
            with open(f"/proc/{pid}/stat", "r") as f:
                # Format: pid (comm) state ...
                parts = f.read().split()
                if len(parts) > 2:
                    return parts[2]  # 3rd field is state
        except (FileNotFoundError, OSError):
            pass
        return None

    async def _send_signal_to_process(self, pid: int, signal: str) -> bool:
        """
        Send a signal to a process.

        Args:
            pid: Process ID
            signal: Signal name (e.g., "-CONT", "-9")

        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(["kill", signal, str(pid)], timeout=1)
            await asyncio.sleep(0.1)
            return True
        except Exception as e:
            log.debug(f"Failed to send signal {signal} to {pid}: {e}")
            return False

    # ==========================================================================
    # PRIVATE HELPERS - Port Cleanup Stages
    # ==========================================================================

    async def _attempt_force_free_port(self, port: int, host: str) -> bool:
        """
        Stage 1: Try to force-free any active process holding the port.

        Handles:
        - Active processes (SIGKILL)
        - Suspended processes (SIGCONT then SIGKILL)

        Args:
            port: Port to free
            host: Host address

        Returns:
            True if port was successfully freed, False if still in use
        """
        if not await self.is_port_in_use(port, host):
            return True

        log.warn(f"Port {port} is in use, attempting to force-free...")

        # Try to find and kill the process
        pid = self.find_process_on_port(port)
        if pid:
            await self._kill_process(pid, port)
            # Verify port is free (with quick retries)
            return await self._verify_port_free(port, host, attempts=3)

        # Process not found - maybe already exited but port not released yet
        log.warn(f"Port {port} in use but process not found, trying direct fuser...")
        try:
            subprocess.run(["fuser", "-k", f"{port}/tcp"], timeout=1)
            await asyncio.sleep(0.5)
            return not await self.is_port_in_use(port, host)
        except Exception as e:
            log.debug(f"fuser attempt failed: {e}")
            return False

    async def _attempt_wait_for_cleanup(self, port: int, host: str) -> bool:
        """
        Stage 2: Wait for OS cleanup (if port in TIME_WAIT state).

        This handles the case where the process has exited but the OS
        hasn't released the port from TIME_WAIT state yet.

        Args:
            port: Port to check
            host: Host address

        Returns:
            True if port became available, False if still in use
        """
        log.warn(f"Port {port} still in use (possibly TIME_WAIT), waiting for OS cleanup...")

        for attempt in range(3):
            await asyncio.sleep(1.0)  # Wait 1 second between retries
            if not await self.is_port_in_use(port, host):
                log.info(f"✓ Port {port} is now available")
                return True
            log.debug(f"Port {port} still in use, retrying... (attempt {attempt + 1}/3)")

        return False

    async def _attempt_fuser_final(self, port: int, host: str) -> bool:
        """
        Stage 3: Final fallback with fuser -k as absolute last resort.

        Args:
            port: Port to free
            host: Host address

        Returns:
            True if port became available, False if still in use
        """
        log.error(f"Port {port} still in use, using fuser -k as final attempt...")

        try:
            subprocess.run(["fuser", "-k", f"{port}/tcp"], timeout=2)
            await asyncio.sleep(1.0)
            if not await self.is_port_in_use(port, host):
                log.info(f"✓ Port {port} finally freed")
                return True
        except Exception as e:
            log.debug(f"Final fuser attempt failed: {e}")

        return False

    # ==========================================================================
    # PRIVATE HELPERS - Process Killing
    # ==========================================================================

    async def _kill_process(self, pid: int, port: int) -> None:
        """
        Kill a process holding a port.

        Handles:
        - Regular processes (SIGKILL)
        - Suspended processes (SIGCONT first, then SIGKILL)

        Args:
            pid: Process ID to kill
            port: Port number (for logging)
        """
        # Check if process is suspended
        state = self._get_process_state(pid)
        if state == 'T':
            log.warn(f"Process {pid} is suspended (Ctrl+Z detected), resuming with SIGCONT...")
            await self._send_signal_to_process(pid, "-CONT")

        # Send SIGKILL
        log.warn(f"Found process {pid} using port {port}, sending SIGKILL...")
        try:
            subprocess.run(["kill", "-9", str(pid)], timeout=1)
            await asyncio.sleep(0.5)  # Wait for OS cleanup
            log.debug(f"Process {pid} killed")
        except Exception as e:
            log.error(f"Failed to kill process {pid}: {e}")

    async def _verify_port_free(
        self, port: int, host: str, attempts: int = 3
    ) -> bool:
        """
        Verify that a port is free (with retries).

        Args:
            port: Port to verify
            host: Host address
            attempts: Number of retry attempts

        Returns:
            True if port is free, False if still in use
        """
        for attempt in range(attempts):
            await asyncio.sleep(0.2)
            if not await self.is_port_in_use(port, host):
                log.info(f"✓ Port {port} successfully freed")
                return True
            if attempt < attempts - 1:
                log.debug(f"Port {port} still in use, verifying... (attempt {attempt + 1}/{attempts})")

        log.error(f"Port {port} still in use after cleanup attempts")
        return False
