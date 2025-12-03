# WebSocket Debugging Guide: Lessons Learned

**Date**: December 3, 2025
**Context**: Fixed critical WebSocket `/ws/logs` endpoint returning HTTP 403 Forbidden
**Root Cause**: Missing type hint on WebSocket parameter in FastAPI handler
**Impact**: This knowledge prevents wasted debugging hours on future WebSocket issues

---

## 🚨 Critical Finding: Type Hints are MANDATORY for FastAPI WebSocket

### The Problem
```python
# ❌ BROKEN - Returns HTTP 403 Forbidden at ASGI level
@app.websocket("/ws/logs")
async def websocket_logs(websocket):  # Missing type hint
    await websocket_logs_endpoint(websocket)
```

### The Solution
```python
# ✅ FIXED - Works correctly
from fastapi import WebSocket

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):  # Type hint added
    await websocket_logs_endpoint(websocket)
```

### Why This Matters
- FastAPI uses **type hints for ASGI parameter injection** and routing
- Without `websocket: WebSocket`, FastAPI cannot identify the parameter as a WebSocket
- The error occurs at the **ASGI protocol level**, BEFORE the handler body executes
- Therefore: No exception logging, no traceback, just HTTP 403
- This is **not a handler logic issue** - it's a routing/middleware issue

**Key Insight**: When debugging WebSocket 403 errors, always check the handler signature FIRST before investigating infrastructure, CORS, exception handlers, or async/await logic.

---

## 🔍 Complete Debugging Checklist

When WebSocket endpoints are returning errors, check these items IN ORDER:

### 1. **Handler Signature (CHECK FIRST)**
- [ ] WebSocket parameter has type hint: `websocket: WebSocket`
- [ ] Import statement exists: `from fastapi import WebSocket`
- [ ] No typos in parameter name or type name
- [ ] Decorator is `@app.websocket()` not `@app.get()` or `@app.post()`

**Test**: Try to connect with:
```bash
python tests/test_websocket_connection.py
```

If still broken, continue to next section.

### 2. **WebSocket Lifecycle**
- [ ] `await websocket.accept()` is called FIRST
- [ ] `websocket.client` is accessed AFTER `accept()`, not before
- [ ] Messages are sent AFTER accept
- [ ] Connection lifecycle respects: accept → send/recv → close/disconnect

**Code Pattern**:
```python
async def websocket_logs_endpoint(websocket: WebSocket):
    broadcaster = None
    client_addr = None
    try:
        # FIRST: Accept the connection
        await websocket.accept()

        # AFTER ACCEPT: Now safe to read client info
        client_addr = websocket.client

        # Initialize broadcaster
        broadcaster = get_broadcaster()

        # Keep connection open
        while True:
            data = await websocket.receive_text()
```

### 3. **CORS Configuration**
- [ ] Do NOT use `allow_origins=["*"]` with `allow_credentials=True`
- [ ] Use explicit origins list for development: `localhost:3000`, `localhost:5173`, `localhost:8000`
- [ ] Include both `http://` and `http://127.0.0.1` variants
- [ ] Add API server itself to CORS origins (for WebSocket connections from API docs)

**Code Pattern**:
```python
if cors_origins is None:
    cors_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost",
        "http://localhost:8000",      # API server itself
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Specific list, not ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 4. **Exception Handling**
- [ ] WebSocket exception handler checks `client_state` correctly
- [ ] Logic: `if websocket.client_state.name == 'CONNECTED':` (not `if not`)
- [ ] Always try to close within try/except to prevent cascading errors
- [ ] Use proper logging for debugging

**Code Pattern**:
```python
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    try:
        await websocket_logs_endpoint(websocket)
    except Exception as e:
        log.error(f"WebSocket handler error: {type(e).__name__}: {e}", exc_info=True)
        try:
            # Check if still connected BEFORE trying to close
            if websocket.client_state.name == 'CONNECTED':
                await websocket.close(code=1011, reason="Internal server error")
        except Exception as close_error:
            log.debug(f"Could not close WebSocket after error: {close_error}")
```

### 5. **Logger-Broadcaster Connection**
- [ ] LogBroadcaster is initialized in `main_asyncio.py`
- [ ] Broadcaster is started: `broadcaster.start()`
- [ ] Logger is connected: `get_logger().set_broadcaster(broadcaster)`
- [ ] Connection happens BEFORE API server starts

**Code Pattern**:
```python
# In main_asyncio.py startup sequence
broadcaster = get_broadcaster()
broadcaster.start()

# This enables log streaming through WebSocket
get_logger().set_broadcaster(broadcaster)

# Then create and start API server
app = create_app()
```

### 6. **Service Implementation**
- [ ] LogBroadcaster has proper imports (logger, asyncio)
- [ ] ConnectionManager safely manages active connections with locks
- [ ] Broadcast method has timeouts to prevent hung connections
- [ ] Queue is sized appropriately (default: 1000 messages)

---

## 📋 All Issues Found and Fixed

### Issue #1: Missing Type Hint (CRITICAL)
**File**: `src/api/main.py:180`
**Symptom**: HTTP 403 Forbidden from ASGI layer
**Root Cause**: `async def websocket_logs(websocket):` missing type annotation
**Fix**: Add `websocket: WebSocket` parameter type hint
**Learning**: Type hints are not optional in FastAPI - they're part of the ASGI routing mechanism

### Issue #2: Invalid CORS Configuration
**File**: `src/api/main.py:87-110`
**Symptom**: Potential CORS rejection of WebSocket upgrade requests
**Root Cause**: `allow_origins=["*"]` used with `allow_credentials=True` (violates CORS spec)
**Fix**: Use explicit origins list instead of wildcard
**Learning**: CORS spec disallows credentialed requests with wildcard origins

### Issue #3: Accessing websocket.client Before accept()
**File**: `src/api/websocket.py:46`
**Symptom**: Potential connection state errors
**Root Cause**: `websocket.client` accessed before `websocket.accept()` called
**Fix**: Move `client_addr = websocket.client` to after `await websocket.accept()`
**Learning**: WebSocket has strict lifecycle - many properties only valid after accept()

### Issue #4: Exception Handler Logic Backwards
**File**: `src/api/main.py:199`
**Symptom**: Attempt to close non-connected WebSockets
**Root Cause**: Condition was `if not websocket.client_state.name == 'CONNECTED'`
**Fix**: Remove the `not` to check if connected before closing
**Learning**: Logic inversions are easy to miss - use positive assertions (`if is ...`)

### Issue #5: Undefined Logger Reference
**File**: `src/services/log_broadcaster.py:181`
**Symptom**: NameError if broadcast worker encounters exception
**Root Cause**: Logger not imported or initialized
**Fix**: Add `log = get_logger().for_category(LogCategory.RENDER_ENGINE)`
**Learning**: Ensure all dependencies are initialized before use

### Issue #6: Broadcaster Not Connected to Logger
**File**: `src/main_asyncio.py:479`
**Symptom**: Logs generated but not transmitted to WebSocket clients
**Root Cause**: `get_logger().set_broadcaster(broadcaster)` was commented out
**Fix**: Uncomment the line to connect broadcaster to logger
**Learning**: Initialization sequence matters - set broadcaster before creating app

---

## ✅ WebSocket Endpoint Template

Use this template when creating new WebSocket endpoints:

```python
# src/api/main.py
from fastapi import FastAPI, WebSocket

@app.websocket("/ws/your-endpoint")
async def websocket_handler(websocket: WebSocket):  # ← TYPE HINT IS MANDATORY
    """
    WebSocket endpoint for [purpose].

    Args:
        websocket: The WebSocket connection (type hint required for FastAPI routing)
    """
    try:
        # 1. Accept connection first
        await websocket.accept()

        # 2. Now access client info and initialize dependencies
        client_addr = websocket.client
        logger.info(f"WebSocket connection from {client_addr}")

        # 3. Delegate to handler or implement logic
        await websocket_handler_impl(websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {type(e).__name__}: {e}", exc_info=True)
        try:
            if websocket.client_state.name == 'CONNECTED':
                await websocket.close(code=1011, reason="Internal error")
        except Exception:
            pass
```

---

## 🧪 Testing Strategy

### Unit Test - Handler Exists
```python
def test_websocket_handler_exists():
    """Verify handler is registered with correct type hints"""
    from src.api.main import create_app
    app = create_app()

    # Find websocket route
    websocket_routes = [r for r in app.routes if r.path == "/ws/logs"]
    assert len(websocket_routes) == 1
    # Type hint check would go here
```

### Integration Test - Connection
```python
async def test_websocket_connection():
    """Test actual WebSocket connection"""
    async with websockets.connect("ws://localhost:8000/ws/logs") as ws:
        # Connection should succeed
        assert ws is not None
        # Try to receive (may timeout if no logs, that's OK)
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            assert msg is not None
        except asyncio.TimeoutError:
            pass  # Expected if no logs
```

Run with:
```bash
python tests/test_websocket_connection.py
```

---

## 🛡️ Prevention Mechanisms

### 1. Startup Validation (IMPLEMENTED)
The app now validates all WebSocket handlers at startup time. Located in:
- **Validator**: `src/api/middleware/websocket_validation.py`
- **Integration**: Called automatically in `src/api/main.py` during `create_app()`

This validation:
- Runs when the API server starts (BEFORE uvicorn binding)
- Fails fast with clear error messages
- Prevents HTTP 403 errors at runtime
- No terminal spam - clean error output only when there's a problem

If you see this error on startup:
```
❌ WebSocket Handler Validation Failed:
  1. WebSocket handler 'websocket_logs' is missing type hint on 'websocket' parameter...
```

The fix is simple: Add the type hint to the handler signature.

### 2. Command-Line Validator Tool
Located in `tools/websocket_validator.py`

Usage:
```bash
# Scan src/api for WebSocket issues
python tools/websocket_validator.py -v

# Or check a specific directory
python tools/websocket_validator.py --path src/api -v
```

Add to CI/CD pipeline to catch issues in pull requests.

### 3. Type Checking (MyPy)
Add to your CI/CD or pre-commit hooks:
```bash
mypy src/api/main.py --strict
```

This will catch missing type hints before deployment.

### 4. Pre-commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Prevent commits with missing WebSocket type hints
python tools/websocket_validator.py
if [ $? -ne 0 ]; then
    echo "ERROR: WebSocket validation failed"
    exit 1
fi
```

### 5. Logging Strategy
**Important**: Uvicorn debug logs are NOT enabled by default to avoid terminal spam.
To manually enable debug logging for development:

Edit `src/main_asyncio.py`, function `run_api_server()`:
```python
config = uvicorn.Config(
    app=app,
    log_level="debug",  # Enable to see routing details (development only)
    # ... rest of config
)
```

This reveals ASGI-level issues but generates verbose output. Only use for debugging.

### 6. Documentation Standard
Require this in all WebSocket endpoints:
- [ ] Type hint on handler parameter: `websocket: WebSocket`
- [ ] WebSocket import: `from fastapi import WebSocket`
- [ ] Docstring explaining the connection purpose
- [ ] Try/except with proper error handling
- [ ] `accept()` called FIRST before any other operation
- [ ] Graceful disconnect handling (WebSocketDisconnect exception)

---

## 🎯 Quick Reference for Future Debugging

**Q: WebSocket returns HTTP 403?**
A: Check handler signature has `websocket: WebSocket` type hint first

**Q: WebSocket accepts but no messages received?**
A: Check broadcaster is started and logger is connected via `set_broadcaster()`

**Q: WebSocket connection hangs?**
A: Check for blocking operations or missing `receive_text()` loop

**Q: WebSocket messages not sent?**
A: Check `websocket.accept()` called before any send operations

**Q: Exception when accessing websocket.client?**
A: Ensure accessed AFTER `websocket.accept()`

---

## 📚 Additional Resources

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [Starlette WebSocket Implementation](https://github.com/encode/starlette/blob/master/starlette/websockets.py)
- [ASGI WebSocket Spec](https://asgi.readthedocs.io/en/latest/specs/www.html#websocket)

---

---

## 🔍 Why No Error Messages Were Logged

This is one of the most important lessons: When the WebSocket handler was missing a type hint, **NO error was logged anywhere** - neither in the application logs nor in uvicorn's output. This is why the debugging took so long.

### The Root Cause (Architectural Understanding)

```
Client Request → Uvicorn (ASGI) → FastAPI Routing → Handler Execution
                      ↑ ERROR HAPPENS HERE
                      │
                      └─ Missing type hint causes HTTP 403
                         BEFORE handler body executes
                         NO application-level logging
```

**Why no error logging:**
1. **ASGI-level rejection**: The error happens at the ASGI protocol layer, BEFORE FastAPI routing
2. **No handler execution**: The handler body never runs, so no try/except in the handler catches anything
3. **No exception propagation**: ASGI layer silently returns HTTP 403 without raising exceptions
4. **No debug output**: Uvicorn only logs routing details at DEBUG level (we were using INFO)
5. **Silent failure**: Client gets HTTP 403, but server has no error message to explain why

### The Solution (Early Validation)

To prevent this in the future, we implemented **startup validation** that runs BEFORE uvicorn binds to the port. This:

- ✅ Catches missing type hints immediately at app startup
- ✅ Provides clear, actionable error messages
- ✅ Fails fast before accepting any client connections
- ✅ Doesn't spam logs (only errors are shown)
- ✅ Works in production (no debug mode needed)

### For Future Issues: Key Debugging Tactics

When something returns HTTP 403 or HTTP 500 with no error message:

1. **Check Application Logs First**: Look for error stack traces in your logger output
2. **Check Uvicorn Logs**: Run with `log_level="debug"` to see ASGI-level issues (development only)
3. **Check Handler Signatures**: Before debugging handler logic, verify:
   - Type hints are present on all parameters
   - Parameter names match what FastAPI expects
   - Imports are correct
4. **Use Validation Tools**: Run the WebSocket validator to check endpoint signatures
5. **Test Directly**: Use the test script to verify connectivity before investigating

### The Broader Lesson

**Type annotations in FastAPI are not optional conveniences - they are part of the framework's contract with the ASGI server.** When type hints are missing:
- The framework cannot inject the parameter
- The ASGI server returns an error at the protocol level
- No application-level code executes to log the problem
- The error appears to be "infrastructure" but is actually "code"

This applies beyond WebSocket - any FastAPI parameter without a proper type hint can cause silent failures.

---

## Summary

The key learning from this debugging session: **Type hints in FastAPI are not optional documentation - they are part of the framework's routing mechanism.** Missing type hints on WebSocket parameters causes ASGI-level rejection (HTTP 403) that occurs before the handler body even executes.

**Critical insight**: Because this error happens at the ASGI layer before handler execution, there are NO error messages, NO exceptions, NO stack traces. This is why it's so hard to debug.

**Solution**: We implemented startup validation that catches missing type hints immediately when the app starts, with clear error messages.

**Always check handler signatures first** when debugging WebSocket issues, before investigating infrastructure, middleware, or application logic.
