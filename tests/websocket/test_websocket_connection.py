#!/usr/bin/env python3
"""
Simple WebSocket connection tester.

Run this while the backend is running to diagnose WebSocket issues:
    python tests/test_websocket_connection.py
"""

import sys

if hasattr(sys.stdout, 'reconfigure') and sys.stdout.encoding != 'UTF-8':
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
if hasattr(sys.stderr, 'reconfigure') and sys.stderr.encoding != 'UTF-8':
    sys.stderr.reconfigure(encoding='utf-8')  # type: ignore

import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def test_websocket():
    """Test WebSocket connection to /ws/logs endpoint."""

    try:
        import websockets
    except ImportError:
        print("ERROR: websockets library not installed")
        print("Install with: pip install websockets")
        return False

    uri = "ws://localhost:8000/ws/logs"
    print(f"Attempting to connect to {uri}...")

    try:
        async with websockets.connect(uri, ping_interval=None) as websocket:
            print("✓ WebSocket connected successfully!")
            print("Listening for logs (press Ctrl+C to exit)...\n")

            try:
                # Wait for messages indefinitely
                # The test will stay connected until you interrupt it (Ctrl+C)
                # This allows you to perform actions (e.g., rotate knob) and see logs in real-time
                while True:
                    message = await websocket.recv()
                    # Print first 100 chars of each message
                    data = message[:100]
                    print(f"  LOG: {data}")
            except KeyboardInterrupt:
                print("\n✓ Test interrupted - WebSocket was working!")
                return True
            except asyncio.TimeoutError:
                print("(No logs received in 3 seconds - this is OK)")
                print("✓ WebSocket connection is working!")
                return True

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
    success = asyncio.run(test_websocket())
    sys.exit(0 if success else 1)
