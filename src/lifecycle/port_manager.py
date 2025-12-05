"""
Port management utilities for ensuring clean port binding.

Provides PortManager singleton for:
1. Port availability checking
2. Finding processes using specific ports
3. Force-freeing orphaned ports (recovery from crashes)
4. Pre-startup port cleanup

Used to prevent "Address already in use" crashes when previous
application instance left port orphaned due to Starlette lifespan bug.

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
    Singleton for managing port availability and cleanup.

    Handles port locking, process detection, and force-freeing of orphaned ports.
    """

    _instance: Optional["PortManager"] = None

    def __init__(self):
        """Initialize port manager."""
        pass

    @classmethod
    def instance(cls) -> "PortManager":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_port_in_use(self, port: int, host: str = "0.0.0.0") -> bool:
        """
        Check if a port is currently in use.

        Args:
            port: Port number to check (0-65535)
            host: Host address (default: 0.0.0.0 for any interface)

        Returns:
            True if port is in use, False if available
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return False  # Successfully bound = port is free
            except OSError:
                return True  # Binding failed = port in use

    def find_process_on_port(self, port: int) -> Optional[int]:
        """
        Find process ID (PID) using a specific port.

        Tries multiple methods:
        1. `lsof` - standard approach
        2. `fuser` - fallback if lsof fails or hangs

        Handles both active and suspended processes (from Ctrl+Z).

        Args:
            port: Port number to check

        Returns:
            PID if found, None otherwise
        """
        # Method 1: Try lsof with short timeout
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

        # Method 2: Fallback to fuser (handles suspended processes better)
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

    def _get_process_state(self, pid: int) -> Optional[str]:
        """
        Get process state (R, S, T, Z, etc.) from /proc/[pid]/stat.

        T = stopped (from SIGSTOP, e.g., Ctrl+Z)
        Z = zombie
        S = interruptible sleep
        R = running

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

    async def force_free_port(self, port: int, host: str = "0.0.0.0") -> bool:
        """
        Force free a port by killing any process using it.

        DANGER: This will kill any process using the port!
        Only use during application startup after confirming port should be free.

        This is especially important for recovery from crashes where the previous
        instance left the port orphaned (uvicorn/Starlette lifespan bug) or was
        suspended with Ctrl+Z.

        Handles:
        - Active processes (sends SIGKILL)
        - Suspended processes (sends SIGCONT then SIGKILL)
        - Zombie processes (parent must reap, but port often gets freed)

        Args:
            port: Port to free (0-65535)
            host: Host address

        Returns:
            True if port was successfully freed, False if still in use
        """
        if not self.is_port_in_use(port, host):
            return True  # Already free

        log.warn(f"Port {port} is in use, attempting to free it...")

        # Try to find and kill the process
        pid = self.find_process_on_port(port)
        if pid:
            # Check if process is suspended (T state = stopped by SIGSTOP, e.g., Ctrl+Z)
            state = self._get_process_state(pid)
            if state == 'T':
                log.warn(f"Process {pid} is suspended (Ctrl+Z detected), resuming with SIGCONT...")
                try:
                    subprocess.run(["kill", "-CONT", str(pid)], timeout=1)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    log.debug(f"Failed to send SIGCONT to {pid}: {e}")

            log.warn(f"Found process {pid} using port {port}, sending SIGKILL...")
            try:
                # Note: Application runs with sudo, so kill should work
                subprocess.run(["kill", "-9", str(pid)], timeout=1)
                await asyncio.sleep(0.5)  # Wait for OS cleanup
                log.debug(f"Process {pid} killed")
            except subprocess.TimeoutExpired:
                log.error(f"Timeout killing process {pid}")
                return False
            except Exception as e:
                log.error(f"Failed to kill process {pid}: {e}")
                return False
        else:
            log.warn(f"Port {port} in use but process not found, using fuser fallback...")
            try:
                # Use fuser -k as ultimate fallback to kill ALL processes using the port
                subprocess.run(["fuser", "-k", f"{port}/tcp"], timeout=1)
                await asyncio.sleep(0.5)
            except Exception as e:
                log.debug(f"fuser fallback failed: {e}")

        # Verify port is now free (with retries for OS cleanup)
        for attempt in range(3):
            await asyncio.sleep(0.2)
            if not self.is_port_in_use(port, host):
                log.info(f"✓ Port {port} successfully freed")
                return True
            if attempt < 2:
                log.debug(f"Port {port} still in use, waiting for OS cleanup... (attempt {attempt + 1}/3)")

        log.error(f"Port {port} still in use after cleanup attempts")
        return False

    async def ensure_available(self, port: int, host: str = "0.0.0.0") -> None:
        """
        Ensure port is available for binding, force-freeing if necessary.

        This should be called before starting API server to guarantee
        that port is free, even if previous application instance left it orphaned.

        Raises RuntimeError if port cannot be freed - application cannot proceed safely.

        Args:
            port: Port to ensure availability (0-65535)
            host: Host address to bind (default: any interface)

        Raises:
            RuntimeError: If port cannot be freed after cleanup attempts
        """
        if self.is_port_in_use(port, host):
            log.warn(f"Port {port} is occupied, attempting cleanup...")
            success = await self.force_free_port(port, host)
            if not success:
                raise RuntimeError(
                    f"Port {port} is in use and could not be freed. "
                    f"Previous application instance may have crashed. "
                    f"Please manually kill any process using this port, or wait a few seconds for OS cleanup."
                )
        else:
            log.debug(f"Port {port} is available")
