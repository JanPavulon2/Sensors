# Development Startup & Cleanup Guide

**Last Updated**: 2025-12-06
**Status**: Active

## Quick Start

### Option 1: Clean Start (Recommended after issues)
```bash
# Kill all old instances and start fresh
cd /home/jp2/Projects/diuna/frontend
npm run dev:clean

# In another terminal, start backend
cd /home/jp2/Projects/diuna
source diunaenv/bin/activate
python src/main_asyncio.py
```

### Option 2: Normal Start
```bash
# Frontend
cd /home/jp2/Projects/diuna/frontend && npm run dev

# Backend (different terminal)
cd /home/jp2/Projects/diuna && source diunaenv/bin/activate && python src/main_asyncio.py
```

## Useful Commands

### Frontend
| Command | Purpose |
|---------|---------|
| `npm run dev` | Start dev server |
| `npm run dev:clean` | Kill old instances + restart |
| `npm run dev:kill` | Kill all Vite processes |
| `npm run dev:check` | Verify frontend is running |

### Backend
| Command | Purpose |
| `python src/main_asyncio.py` | Start backend |
| `lsof -i :8000` | Check port 8000 usage |
| `pkill -f main_asyncio` | Kill backend |

## Access Locations

### From Pi Itself
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000/api`
- WebSocket: `ws://localhost:8000`

### From Remote Machine
- Frontend: `http://192.168.137.139:5173` (use your Pi's IP)
- Backend API: `http://192.168.137.139:8000/api`
- WebSocket: `ws://192.168.137.139:8000`

**Note**: Frontend auto-detects the hostname and connects to backend on the same host automatically.

## Common Issues & Solutions

### "Port X is in use" Error

**Cause**: Old frontend/backend process still running

**Solutions** (in order):
1. `npm run dev:clean` (frontend)
2. `pkill -f main_asyncio` (backend)
3. Check with `lsof -i :5173` and `lsof -i :8000`
4. Restart

### Frontend shows "Cannot connect to backend"

**Likely Causes**:
- Backend not running → start backend
- Accessing from wrong host (localhost vs IP) → **Auto-fixed in code** (see below)
- Different port configuration → check error logs

### Browser Connection Fails When Accessing from Remote

**Automatic Resolution**:
- Frontend code auto-detects hostname
- Uses `localhost:8000` if accessed via localhost
- Uses `192.168.137.139:8000` if accessed via IP
- See `frontend/src/config/constants.ts:getBackendUrl()` and `getWebSocketUrl()`

**Manual Override** (if needed):
```bash
# Create .env.local if auto-detection fails
echo 'VITE_API_URL=http://192.168.137.139:8000/api' > frontend/.env.local
echo 'VITE_WEBSOCKET_URL=ws://192.168.137.139:8000' >> frontend/.env.local
npm run dev:clean
```

## Port Management

### Automatic Port Cleanup (Backend)
The backend has sophisticated port management:
- Cleans up ports on startup (see `src/services/port_manager.py`)
- Handles `TIME_WAIT` states
- Kills orphaned processes
- Respects suspended processes (Ctrl+Z)

### Frontend Vite Configuration
- Configured with `host: true` in `vite.config.ts`
- Listens on all interfaces (0.0.0.0)
- Auto-falls back to next port if current is occupied
- Clean shutdown with `npm run dev:kill`

## Best Practices

1. **Use `npm run dev:clean` after crashes**
   ```bash
   npm run dev:clean
   ```

2. **Kill old instances before restart**
   ```bash
   npm run dev:kill  # Frontend
   pkill -f main_asyncio  # Backend
   ```

3. **Check port usage before starting**
   ```bash
   lsof -i :5173  # Frontend port
   lsof -i :8000  # Backend port
   ```

4. **Monitor logs**
   - Check terminal output for errors
   - Look for "Port X is in use" warnings

5. **Use separate terminals**
   - One for frontend `npm run dev`
   - One for backend `python src/main_asyncio.py`
   - One for other tasks (git, testing, etc.)

## How This Protects Against Issues

### ✅ Old Instance Running
- `npm run dev:clean` kills all old Vite processes before starting
- Backend has automatic port cleanup on startup

### ✅ Orphaned Processes
- Simple `pkill` commands in npm scripts
- Backend's `PortManager` detects and cleans up orphaned backends

### ✅ Port Conflicts
- Frontend auto-falls back to next port (5173 → 5174 → 5175...)
- Backend's `PortManager` forces port cleanup before binding

### ✅ Localhost vs IP Confusion
- Frontend auto-detects hostname
- Uses correct backend URL automatically
- No need for different config files

### ✅ Suspended Processes (Ctrl+Z)
- `npm run dev:kill` uses `pkill` which finds all processes
- Backend's `PortManager` handles SIGSTOP processes specially

## Troubleshooting Checklist

- [ ] Run `npm run dev:check` to verify frontend running
- [ ] Run `lsof -i :8000` to verify backend running
- [ ] Check browser console for API errors (F12)
- [ ] Look for `"Cannot connect to backend"` in logs
- [ ] Verify accessing via correct hostname (localhost vs IP)
- [ ] Try `npm run dev:clean` and `pkill -f main_asyncio` then restart
- [ ] Check `.claude/context/technical/performance.md` for system load issues

## Related Documentation

- [Architecture Overview](./../architecture/overview.md)
- [Port Management Details](./../technical/hardware.md)
- [Rendering System](../documentation/1_rendering_system/user/0_overview.md)