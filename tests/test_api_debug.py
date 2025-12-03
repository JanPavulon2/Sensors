#!/usr/bin/env python3
"""
Debug script to test API authentication and endpoints
Run the API server first:
  python3 -m api.main &

Then run this script in another terminal.
"""

import httpx
import asyncio
from api.middleware.auth import create_test_token

async def test_api():
    """Test all API endpoints"""

    # Generate token
    token = create_test_token('testuser')
    print(f"✓ Token generated: {token}")
    print()

    # Create async client
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:

        # Test 1: Health check (no auth)
        print("=" * 60)
        print("TEST 1: Health check (no auth required)")
        print("=" * 60)
        response = await client.get("/health")
        print(f"Status: {response.status_code}")
        try:
            print(f"Body: {response.json()}")
        except:
            print(f"Body: {response.text[:300]}")
        print()

        # Test 2: List zones WITHOUT auth
        print("=" * 60)
        print("TEST 2: List zones WITHOUT auth (should be 401)")
        print("=" * 60)
        response = await client.get("/api/v1/zones")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text[:300]}")
        print()

        # Test 3: List zones WITH auth
        print("=" * 60)
        print("TEST 3: List zones WITH auth")
        print("=" * 60)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/zones", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Headers sent: {headers}")

        if response.status_code == 200:
            try:
                print(f"Body: {response.json()}")
            except:
                print(f"Body (raw): {response.text[:300]}")
        elif response.status_code == 500:
            print("❌ 500 ERROR - Server error!")
            print(f"Body: {response.text}")
        elif response.status_code == 401:
            print("❌ 401 ERROR - Auth failed!")
            print(f"Body: {response.text}")
        else:
            print(f"❌ Status {response.status_code}")
            print(f"Body: {response.text[:500]}")
        print()

        # Test 4: Get single zone
        print("=" * 60)
        print("TEST 4: Get single zone")
        print("=" * 60)
        response = await client.get("/api/v1/zones/FLOOR", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code != 200:
            print(f"Body: {response.text[:300]}")
        print()

if __name__ == "__main__":
    asyncio.run(test_api())
