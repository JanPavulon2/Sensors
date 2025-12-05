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

        Uses `lsof` (Linux) to find the process. May not work on all systems.

        Args:
            port: Port number to check

        Returns:
            PID if found, None otherwise
        """
        try:
            # lsof -ti :PORT returns PID (t=terse, i=ignore+case-insensitive)
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    return int(result.stdout.strip().split()[0])
                except (ValueError, IndexError):
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    async def force_free_port(self, port: int, host: str = "0.0.0.0") -> bool:
        """
        Force free a port by killing any process using it.

        DANGER: This will kill any process using the port!
        Only use during application startup after confirming port should be free.

        This is especially important for recovery from crashes where the previous
        instance left the port orphaned (uvicorn/Starlette lifespan bug).

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
            log.warn(f"Found process {pid} using port {port}, sending SIGKILL...")
            try:
                # Note: Application runs with sudo, so kill should work
                subprocess.run(["kill", "-9", str(pid)], timeout=2)
                await asyncio.sleep(0.5)  # Wait for OS cleanup
                log.debug(f"Process {pid} killed")
            except subprocess.TimeoutExpired:
                log.error(f"Timeout killing process {pid}")
                return False
            except Exception as e:
                log.error(f"Failed to kill process {pid}: {e}")
                return False
        else:
            log.warn(f"Port {port} in use but process not found, waiting for cleanup...")
            await asyncio.sleep(0.5)

        # Verify port is now free
        await asyncio.sleep(0.2)
        if self.is_port_in_use(port, host):
            log.error(f"Port {port} still in use after cleanup attempt")
            return False

        log.info(f"✓ Port {port} successfully freed")
        return True

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
