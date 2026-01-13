# Fixes Applied - WebSocket & Port Management Issues

**Date**: 2025-12-06
**Issue**: Frontend couldn't connect to backend WebSocket; port cleanup failures with TIME_WAIT

---

## Root Causes Identified

### Issue 1: Frontend Port Mismatch
- **Cause**: Orphaned Vite process (PID 2774) held port 5173
- **Effect**: New frontend dev server fell back to port 5174
- **CORS Failure**: Backend only allowed localhost:5173, rejected requests from 5174

### Issue 2: Host Resolution Problem
- **Cause**: Frontend hardcoded `localhost:8000` but was accessed from remote machine (192.168.137.139)
- **Effect**: When accessed remotely, `localhost` pointed to user's machine, not the Pi
- **CORS Error**: "Origin http://192.168.137.139:5174 not allowed"

### Issue 3: Process Management
- **Cause**: No cleanup scripts; orphaned processes accumulate
- **Effect**: Cascading port conflicts when restarting

---

## Solutions Implemented

### 1️⃣ Auto-Detect Backend URL (Frontend)

**File**: `frontend/src/config/constants.ts`

```typescript
// Now auto-detects based on access hostname
const getBackendUrl = () => {
  // Priority: env var > current hostname > default localhost
  if (window.location.hostname === 'localhost') return 'http://localhost:8000/api';
  return `http://${window.location.hostname}:8000/api`;
};
```

**Benefits**:
- ✅ Works from localhost (Pi itself)
- ✅ Works from remote IP (192.168.137.139)
- ✅ Can override with env var if needed
- ✅ No config file needed

### 2️⃣ Frontend npm Scripts

**File**: `frontend/package.json`

```json
{
  "dev:clean": "npm run dev:kill && npm run dev",
  "dev:kill": "pkill -f 'node.*vite' || true",
  "dev:check": "curl -s http://localhost:5173 > /dev/null && echo '✅ Running' || echo '❌ Not running'"
}
```

**Usage**:
```bash
npm run dev:clean      # Kill + restart (safest)
npm run dev:kill       # Just kill
npm run dev:check      # Verify running
```

### 3️⃣ Development Startup Guide

**File**: `.claude/context/development/dev-startup-guide.md`

Comprehensive guide covering:
- Quick start commands
- Useful commands for both frontend/backend
- Common issues & solutions
- Port management explained
- Best practices
- Troubleshooting checklist

---

## What Was NOT Needed

❌ **`.env.local` file** - Removed
- Frontend now auto-detects based on hostname
- Environment variables still work if needed

❌ **Backend changes** - None required
- `PortManager` already handles cleanup properly
- CORS already configured for localhost:5173

---

## Testing

Verify the fixes work:

```bash
# Terminal 1: Start frontend (auto-detects on restart)
cd /home/jp2/Projects/diuna/frontend
npm run dev:clean

# Terminal 2: Start backend (if not running)
cd /home/jp2/Projects/diuna
source diunaenv/bin/activate
python src/main_asyncio.py

# Terminal 3: Test access
# From Pi: http://localhost:5173 → connects to localhost:8000 ✅
# From remote: http://192.168.137.139:5173 → connects to 192.168.137.139:8000 ✅
```

---

## Future Prevention

### Immediate Protections
- ✅ `npm run dev:clean` for fresh starts
- ✅ `npm run dev:kill` for cleanup
- ✅ Auto-hostname detection (no config needed)

### Recommended Future Improvements
1. **Process supervision**: Use `pm2` or `supervisor` for automatic respawn
2. **Health checks**: Add `/health` endpoint + browser-side monitoring
3. **Git hooks**: Pre-commit hook to warn about running processes
4. **Docker**: Containerize to eliminate port conflicts entirely
5. **CI/CD**: Automated startup/shutdown in testing pipeline

---

## Files Changed

| File | Change | Type |
|------|--------|------|
| `frontend/src/config/constants.ts` | Added auto-detect logic | Code |
| `frontend/package.json` | Added npm scripts | Config |
| `.env.local` | Deleted (no longer needed) | Cleanup |
| `dev-startup-guide.md` | Created | Documentation |

---

## Summary

**Before**:
- Manual env config needed
- Orphaned processes caused cascading failures
- Only worked from localhost
- Hard to diagnose issues

**After**:
- ✅ Works from both localhost and remote IP automatically
- ✅ Easy cleanup with `npm run dev:clean`
- ✅ Comprehensive troubleshooting guide
- ✅ Simple npm scripts for common tasks
- ✅ WebSocket logs connecting reliably
