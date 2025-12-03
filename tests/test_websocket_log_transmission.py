#!/usr/bin/env python3
"""
Test WebSocket log transmission pipeline.

This test verifies that logs are actually being transmitted through the WebSocket,
independent of GPIO or hardware. It simulates log messages and checks if they're
received through the WebSocket.

Usage:
    python tests/test_websocket_log_transmission.py
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_log_transmission():
    """Test that logs are transmitted through WebSocket."""

    try:
        import websockets
    except ImportError:
        print("ERROR: websockets library not installed")
        return False

    # Setup logger and broadcaster
    from utils.logger import get_logger, configure_logger
    from services.log_broadcaster import get_broadcaster
    from models.enums import LogLevel, LogCategory

    print("Setting up broadcaster...")
    configure_logger(LogLevel.DEBUG)
    broadcaster = get_broadcaster()
    broadcaster.start()

    logger = get_logger()
    logger.set_broadcaster(broadcaster)

    print("✓ Broadcaster initialized")

    # Start WebSocket connection
    uri = "ws://localhost:8000/ws/logs"
    print(f"\nAttempting to connect to {uri}...")

    try:
        async with websockets.connect(uri, ping_interval=None) as websocket:
            print("✓ WebSocket connected successfully!")
            print("Sending test log message...\n")

            # Send test log
            bound_logger = logger.for_category(LogCategory.SYSTEM)
            bound_logger.info("TEST MESSAGE: WebSocket log transmission working!")

            # Wait for message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2)
                data = message[:200]
                print(f"✓ RECEIVED LOG: {data}")
                print("\n✅ SUCCESS: Log transmission pipeline is working!")
                return True
            except asyncio.TimeoutError:
                print("✗ TIMEOUT: No log message received")
                print("  This means the broadcaster isn't sending logs to WebSocket clients")
                return False

    except ConnectionRefusedError:
        print("ERROR: Connection refused")
        print("  - Is the backend running on localhost:8000?")
        print("  - Run: python -m src.main_asyncio")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_log_transmission())
    sys.exit(0 if success else 1)
