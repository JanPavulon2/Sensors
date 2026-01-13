---
Title: API Quick Start Guide
Last Updated: 2025-11-26
Purpose: Get the API running and test endpoints
---

# Diuna API - Quick Start Guide

## 🚀 Installation

### 1. Install Dependencies

```bash
cd /home/jp2/Projects/diuna

# Create virtual environment (if not already done)
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install required packages
pip install fastapi==0.104.1
pip install pydantic==2.5.0
pip install uvicorn[standard]==0.24.0
pip install python-multipart==0.0.6
```

### 2. Verify Installation

```bash
python -c "import fastapi; print(f'FastAPI {fastapi.__version__} installed')"
python -c "import pydantic; print(f'Pydantic {pydantic.__version__} installed')"
```

---

## 📝 Quick Test: Run API Standalone

### Option 1: Run API Only (Development Mode)

```bash
cd /home/jp2/Projects/diuna/src

# Start API server
python -m api.main

# Output should show:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### Option 2: Access API Documentation

Open in browser:
- **Swagger UI (Interactive docs):** http://localhost:8000/docs
- **ReDoc (Pretty docs):** http://localhost:8000/redoc
- **OpenAPI Schema (JSON):** http://localhost:8000/openapi.json

---

## 🧪 Testing Endpoints with curl

### 1. Health Check

```bash
curl http://localhost:8000/health

# Response:
# {"status":"healthy","service":"diuna-led-api","version":"1.0.0"}
```

### 2. Get All Zones (GET /zones)

```bash
# Without auth (will fail)
curl http://localhost:8000/api/v1/zones

# With test bearer token
curl -H "Authorization: Bearer test-user-abc123" \
  http://localhost:8000/api/v1/zones

# Response: 200 OK with zone list
# {
#   "zones": [...],
#   "count": 6
# }
```

### 3. Get Single Zone

```bash
curl -H "Authorization: Bearer test-user-abc123" \
  http://localhost:8000/api/v1/zones/FLOOR

# Response:
# {
#   "id": "FLOOR",
#   "name": "Floor Strip",
#   ...
# }
```

### 4. Update Zone Color

```bash
# Change FLOOR to blue (HUE mode)
curl -X PUT \
  -H "Authorization: Bearer test-user-abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "color": {
      "mode": "HUE",
      "hue": 240
    }
  }' \
  http://localhost:8000/api/v1/zones/FLOOR/color

# Response: Updated zone
```

### 5. Update Zone Brightness

```bash
curl -X PUT \
  -H "Authorization: Bearer test-user-abc123" \
  -H "Content-Type: application/json" \
  -d '{"brightness": 150}' \
  http://localhost:8000/api/v1/zones/FLOOR/brightness

# Response: Updated zone
```

### 6. Reset Zone

```bash
curl -X POST \
  -H "Authorization: Bearer test-user-abc123" \
  http://localhost:8000/api/v1/zones/FLOOR/reset

# Response: Reset zone
```

---

## 🔍 Testing with Python (requests library)

```bash
# Install requests
pip install requests
```

```python
import requests

BASE_URL = "http://localhost:8000"
HEADERS = {"Authorization": "Bearer test-user-abc123"}

# Get all zones
response = requests.get(
    f"{BASE_URL}/api/v1/zones",
    headers=HEADERS
)
print(response.json())

# Update zone color
response = requests.put(
    f"{BASE_URL}/api/v1/zones/FLOOR/color",
    headers=HEADERS,
    json={
        "color": {
            "mode": "HUE",
            "hue": 120  # Green
        }
    }
)
print(response.json())

# Check status
if response.status_code == 200:
    print("✅ Color updated successfully")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())
```

---

## 🧬 Testing with Swagger UI (Interactive)

1. Open http://localhost:8000/docs
2. You'll see all endpoints listed
3. Click "Authorize" button (top right)
4. Enter: `Bearer test-user-abc123`
5. Click "Try it out" on any endpoint
6. Fill in parameters and click "Execute"
7. See response in real-time

---

## ⚠️ Important: Current Limitations

### Not Yet Implemented

These endpoints will return "NotImplementedError" or need integration:

```
❌ PUT /api/v1/zones/{zone_id}/enabled - Coming in Phase 8.2
❌ PUT /api/v1/zones/{zone_id}/render-mode - Coming in Phase 8.3
❌ All animation endpoints - Coming in Phase 8.3
❌ All color endpoints - Coming in Phase 8.3
❌ WebSocket endpoints - Coming in Phase 8.2
```

### Dependency Injection Not Wired

Currently, the API will fail because `get_zone_service()` returns `None`.

**Fix needed in `api/routes/zones.py`:**
```python
# Replace this:
def get_zone_service() -> ZoneAPIService:
    """Dependency to get zone service instance"""
    # Placeholder - will be set up in main.py
    pass

# With actual setup in main_asyncio.py:
from services.zone_service import ZoneService
from managers.color_manager import ColorManager
from api.services.zone_service import ZoneAPIService

zone_service_domain = ZoneService(assembler, app_state_service)
color_manager = ColorManager(...)

def get_zone_service() -> ZoneAPIService:
    return ZoneAPIService(zone_service_domain, color_manager)

# Then wire into FastAPI app
app.dependency_overrides[get_zone_service] = get_zone_service
```

---

## 🐛 Debugging

### Enable Debug Logging

```python
# In main.py
configure_logger(LogLevel.DEBUG)

# Or run with:
PYTHONPATH=src python -m api.main --log-level debug
```

### Check Server Logs

Watch for:
- `[INFO] FastAPI app starting up`
- `[DEBUG] Routes registered`
- `[INFO] Uvicorn running on...`

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: api` | PYTHONPATH not set | Run from `src/` directory |
| `ConnectionRefusedError` | API not running | Start with `python -m api.main` |
| `401 Unauthorized` | No/invalid token | Add `Authorization: Bearer <token>` header |
| `404 Not Found` | Zone doesn't exist | Check zone IDs in /docs |
| `422 Unprocessable Entity` | Invalid JSON | Check request body against schema |

---

## 📊 Example: Complete Test Flow

```bash
# 1. Start API
python -m api.main &

# 2. Test health
curl http://localhost:8000/health

# 3. Create test token
TOKEN="Bearer test-user-abc123"

# 4. Get zones
curl -H "Authorization: $TOKEN" http://localhost:8000/api/v1/zones

# 5. Update color
curl -X PUT \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"color":{"mode":"HUE","hue":240}}' \
  http://localhost:8000/api/v1/zones/FLOOR/color

# 6. Check updated zone
curl -H "Authorization: $TOKEN" http://localhost:8000/api/v1/zones/FLOOR

# 7. Verify color changed
# Should see: "hue": 240, "rgb": [0, 0, 255]
```

---

## 🔗 Next Integration Step

Once API is working standalone, integrate with `main_asyncio.py`:

```python
# main_asyncio.py
from api.main import create_app
from api.services.zone_service import ZoneAPIService
import uvicorn

async def main():
    # Existing Phase 6 setup
    zone_service_domain = ZoneService(assembler, app_state_service)
    color_manager = ColorManager(...)

    # Create API
    app = create_app()

    # Wire dependencies
    def get_zone_api_service():
        return ZoneAPIService(zone_service_domain, color_manager)

    app.dependency_overrides[ZoneAPIService] = get_zone_api_service

    # Run together
    await asyncio.gather(
        led_controller.start(),
        animation_engine.start(),
        # ... other Phase 6 components
        run_uvicorn_app(app)
    )
```

---

## 📚 Resources

- **FastAPI Tutorial:** https://fastapi.tiangolo.com/tutorial/
- **Pydantic Validation:** https://docs.pydantic.dev/latest/concepts/validators/
- **HTTP Status Codes:** https://httpwg.org/specs/rfc7231.html#status.codes
- **REST API Best Practices:** https://restfulapi.net/

---

**Status:** Phase 8.1 API ready for standalone testing and integration with Phase 6
