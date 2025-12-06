#!/usr/bin/env python3
"""
Comprehensive WebSocket diagnostic tool.
Tests all aspects of WebSocket connection and log transmission.
"""

import asyncio
import sys
import subprocess
import json
from pathlib import Path

# Set UTF-8 encoding for output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_websocket_connection():
    """Test basic WebSocket connection"""
    try:
        import websockets
    except ImportError:
        print("❌ websockets library not installed")
        return False

    uri = "ws://localhost:8000/ws/logs"
    print(f"\n1. Testing WebSocket connection to {uri}...")

    try:
        async with websockets.connect(uri, ping_interval=None, open_timeout=3) as ws:
            print("✅ WebSocket connection successful")

            # Test message reception
            print("\n2. Testing message reception...")
            try:
                # Trigger a log message
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    print("   Triggering HTTP request to generate logs...")
                    await session.get('http://localhost:8000/api/health')

                # Wait for log message
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(msg)
                print(f"✅ Received log message:")
                print(f"   Timestamp: {data.get('timestamp')}")
                print(f"   Level: {data.get('level')}")
                print(f"   Category: {data.get('category')}")
                print(f"   Message: {data.get('message')[:50]}...")
                return True
            except asyncio.TimeoutError:
                print("⚠️  No message received (timeout)")
                print("   This could mean:")
                print("   - LogBroadcaster not initialized")
                print("   - Logger not connected to broadcaster")
                print("   - No logs being generated")
                return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cors_headers():
    """Test CORS headers for WebSocket upgrade"""
    print("\n3. Testing CORS headers...")

    # Skip curl test (it hangs on WebSocket), just test with websockets library
    try:
        import websockets
        async with websockets.connect(
            'ws://localhost:8000/ws/logs',
            extra_headers={'Origin': 'http://localhost:5173'},
            open_timeout=3
        ) as ws:
            print("✅ CORS headers allow WebSocket upgrade from frontend origin")
            return True
    except Exception as e:
        print(f"❌ WebSocket upgrade failed: {e}")
        return False


def test_port_availability():
    """Test if port 8000 is available"""
    print("\n4. Testing port availability...")

    result = subprocess.run(
        ['netstat', '-tulpn'],
        capture_output=True,
        text=True
    )

    if '8000' in result.stdout:
        print("✅ Port 8000 is in use (backend running)")
        # Check for TIME_WAIT
        if 'TIME_WAIT' in result.stdout and '8000' in result.stdout:
            print("⚠️  Port 8000 has TIME_WAIT connections")
            print("   This could cause issues on restart")
        return True
    else:
        print("❌ Port 8000 is not in use")
        print("   Backend may not be running")
        return False


def test_backend_health():
    """Test backend health endpoint"""
    print("\n5. Testing backend health...")

    result = subprocess.run(
        ['curl', '-s', 'http://localhost:8000/api/health'],
        capture_output=True,
        text=True,
        timeout=3
    )

    try:
        data = json.loads(result.stdout)
        if data.get('status') == 'healthy':
            print(f"✅ Backend is healthy")
            print(f"   Service: {data.get('service')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print(f"⚠️  Backend health check returned unexpected status: {data}")
            return False
    except:
        print(f"❌ Backend health check failed")
        print(f"   Response: {result.stdout[:100]}")
        return False


async def main():
    """Run all diagnostics"""
    print("=" * 60)
    print("WebSocket Diagnostic Tool for Diuna")
    print("=" * 60)

    results = {
        'backend_health': test_backend_health(),
        'port_availability': test_port_availability(),
        'cors_headers': await test_cors_headers(),
        'websocket_connection': await test_websocket_connection(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")

    print("\n" + "=" * 60)

    if all(results.values()):
        print("✅ All tests passed!")
        print("\nThe WebSocket endpoint is working correctly.")
        print("If the frontend still can't connect, check:")
        print("1. Browser console for JavaScript errors")
        print("2. Browser DevTools Network tab for WebSocket requests")
        print("3. Frontend is using the correct URL: ws://localhost:8000/ws/logs")
        print("4. useLoggerWebSocket hook is being called correctly")
    else:
        print("❌ Some tests failed")
        print("\nTroubleshooting steps:")
        if not results['backend_health']:
            print("- Start the backend: sudo python -m src.main_asyncio")
        if not results['websocket_connection']:
            print("- Check LogBroadcaster initialization in main_asyncio.py")
            print("- Check if logger is connected to broadcaster")

    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted")
    except Exception as e:
        print(f"\n\nDiagnostic failed: {e}")
        import traceback
        traceback.print_exc()
