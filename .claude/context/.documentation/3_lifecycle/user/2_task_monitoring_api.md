---
Last Updated: 2025-12-02
Updated By: Claude Code
Changes: Task monitoring REST API documentation
---

# Task Monitoring REST API

Real-time visibility into what tasks are running in the Diuna application.

## Quick Reference

```bash
# Task summary (counts and high-level view)
curl http://localhost:8000/api/v1/system/tasks/summary

# All tasks with details
curl http://localhost:8000/api/v1/system/tasks

# Only currently running tasks (for debugging hangs)
curl http://localhost:8000/api/v1/system/tasks/active

# Failed tasks with exception details
curl http://localhost:8000/api/v1/system/tasks/failed

# Application health status
curl http://localhost:8000/api/v1/system/health
```

## Endpoint Details

### 1. GET `/api/v1/system/tasks/summary`

**Purpose**: High-level overview of task counts

**Response**:
```json
{
  "summary": "Total: 8 | Active: 7 | Failed: 0 | Cancelled: 1",
  "total": 8,
  "active": 7,
  "failed": 0,
  "cancelled": 1
}
```

**Fields**:
- `summary` - Human-readable summary string
- `total` - Total tasks ever created (since app start)
- `active` - Currently running tasks
- `failed` - Tasks that ended with exceptions
- `cancelled` - Tasks that were cancelled (normally during shutdown)

**When to use**: Dashboard widgets, quick status checks

---

### 2. GET `/api/v1/system/tasks`

**Purpose**: Detailed information on ALL tasks (past and present)

**Response**:
```json
{
  "count": 8,
  "tasks": [
    {
      "id": 1,
      "category": "RENDER",
      "description": "Frame Manager renders loops",
      "created_at": "2025-12-02T10:30:45.123456+00:00",
      "created_by": "src.engine.frame_manager:290",
      "status": "running",
      "error": null
    },
    {
      "id": 2,
      "category": "API",
      "description": "FastAPI/Uvicorn Server",
      "created_at": "2025-12-02T10:30:45.234567+00:00",
      "created_by": "src.main_asyncio:391",
      "status": "running",
      "error": null
    },
    {
      "id": 5,
      "category": "ANIMATION",
      "description": "AnimationEngine main loop",
      "created_at": "2025-12-02T10:30:46.345678+00:00",
      "created_by": "src.animations.engine:238",
      "status": "failed",
      "error": "AttributeError: 'NoneType' object has no attribute 'get_current_frame'"
    }
  ]
}
```

**Fields per task**:
- `id` - Unique task ID (auto-incremented)
- `category` - Task category (RENDER, API, HARDWARE, ANIMATION, INPUT, SYSTEM, etc.)
- `description` - Human-readable purpose
- `created_at` - When task started (ISO 8601 UTC)
- `created_by` - Where in code it was created (if provided)
- `status` - Current status: `running`, `completed`, `cancelled`, `failed`
- `error` - Exception message if status is `failed`, else `null`

**When to use**: Full audit trail, debugging, long-term monitoring

---

### 3. GET `/api/v1/system/tasks/active`

**Purpose**: See ONLY currently running tasks (best for debugging hangs)

**Response**:
```json
{
  "count": 5,
  "tasks": [
    {
      "id": 1,
      "category": "RENDER",
      "description": "Frame Manager renders loops",
      "created_at": "2025-12-02T10:30:45.123456+00:00",
      "running_for_seconds": 45.2
    },
    {
      "id": 2,
      "category": "API",
      "description": "FastAPI/Uvicorn Server",
      "created_at": "2025-12-02T10:30:45.234567+00:00",
      "running_for_seconds": 45.1
    },
    {
      "id": 4,
      "category": "HARDWARE",
      "description": "ControlPanel Polling Loop",
      "created_at": "2025-12-02T10:30:46.456789+00:00",
      "running_for_seconds": 44.0
    }
  ]
}
```

**Fields per task**:
- `id` - Task ID
- `category` - Task category
- `description` - What it does
- `created_at` - When it started
- `running_for_seconds` - How long it's been running (useful for finding which task is stuck)

**Tasks are sorted by creation time (oldest first)**

**When to use**:
- Debugging: "Why isn't my app responding?" → Check if any tasks are hung
- Monitoring: Daily health checks
- Shutdown: Press Ctrl+C, then call this endpoint before it exits to see what's still running

**Example Debug Session**:
```bash
# Terminal 1: Start app
python src/main_asyncio.py

# Terminal 2: Let it run, then check active tasks
sleep 5
curl http://localhost:8000/api/v1/system/tasks/active | jq '.tasks[] | "\(.id): \(.description) (\(.running_for_seconds)s)"'

# Output:
# 1: Frame Manager renders loops (5.1s)
# 2: FastAPI/Uvicorn Server (5.0s)
# 3: KeyboardInputAdapter (4.9s)
# 4: ControlPanel Polling Loop (4.8s)
# 5: AnimationEngine main loop (4.7s)
# ... more tasks

# All running ~5 seconds = working normally
```

---

### 4. GET `/api/v1/system/tasks/failed`

**Purpose**: See which tasks crashed with exceptions

**Response**:
```json
{
  "count": 1,
  "tasks": [
    {
      "id": 7,
      "category": "ANIMATION",
      "description": "StaticMode pulse animation",
      "created_at": "2025-12-02T10:31:15.567890+00:00",
      "error": "TypeError: unsupported operand type(s) for *: 'NoneType' and 'float'",
      "error_type": "TypeError"
    }
  ]
}
```

**Fields per task**:
- `id` - Task ID
- `category` - What kind of task it was
- `description` - What it was supposed to do
- `created_at` - When it crashed
- `error` - Full error message
- `error_type` - Exception class name (TypeError, ValueError, RuntimeError, etc.)

**When to use**:
- Debugging: "Why did animation stop?" → Check failed tasks
- Monitoring: Alert on failed tasks
- Post-mortem: Historical record of what crashed

**Important**: A task appearing here means:
- It ran, then crashed with an exception
- It's no longer running
- The rest of the app continued (exceptions don't crash app)
- Check logs for full stack trace

---

### 5. GET `/api/v1/system/health`

**Purpose**: Overall application health status

**Response** (Healthy):
```json
{
  "status": "healthy",
  "reason": null,
  "tasks": {
    "total": 8,
    "active": 7,
    "failed": 0,
    "cancelled": 1
  },
  "timestamp": "2025-12-02T10:32:45.789012+00:00"
}
```

**Response** (Degraded):
```json
{
  "status": "degraded",
  "reason": "2 background task(s) have failed",
  "tasks": {
    "total": 8,
    "active": 5,
    "failed": 2,
    "cancelled": 1
  },
  "timestamp": "2025-12-02T10:33:00.123456+00:00"
}
```

**Fields**:
- `status` - "healthy" or "degraded"
- `reason` - Why degraded (null if healthy)
- `tasks` - Summary of task counts
- `timestamp` - When this check was made

**Status Rules**:
- `healthy` - No failed tasks
- `degraded` - One or more tasks have failed

**When to use**:
- Monitoring: Health check endpoint for dashboards
- Alerting: Trigger alerts on "degraded" status
- Kubernetes liveness probes: Return 200 if healthy, 500 if degraded

---

## Practical Examples

### Example 1: Monitor tasks in real-time

```bash
# Watch tasks every second
watch -n 1 'curl -s http://localhost:8000/api/v1/system/tasks/active | jq ".count"'

# Output updates as tasks start/stop
```

### Example 2: Debug a hung app

```bash
# App seems stuck, check what's running
curl -s http://localhost:8000/api/v1/system/tasks/active | jq '.tasks[] | {id, description, running_for_seconds}'

# Look for:
# - Any task with running_for_seconds > 60 (likely stuck)
# - Task that just started (might be slow startup)

# Example output:
# {
#   "id": 4,
#   "description": "ControlPanel Polling Loop",
#   "running_for_seconds": 120.5  # ← This has been running 2 minutes!
# }
#
# Likely culprit: polling loop is blocked, probably on GPIO read
```

### Example 3: Find failed animations

```bash
# After user reports animation crashed
curl -s http://localhost:8000/api/v1/system/tasks/failed | jq '.tasks[] | select(.category == "ANIMATION")'

# Shows which animation tasks failed and why
```

### Example 4: Health check before shutdown

```bash
#!/bin/bash

# Check if safe to shutdown
health=$(curl -s http://localhost:8000/api/v1/system/health | jq -r '.status')

if [ "$health" = "degraded" ]; then
  echo "WARNING: App is degraded, some tasks failed"
  echo "Failed tasks:"
  curl -s http://localhost:8000/api/v1/system/tasks/failed | jq '.tasks[] | {description, error}'
fi

# Safe to shutdown
pkill -TERM diuna
```

### Example 5: Frontend dashboard integration

```javascript
// React component to show task status
function TaskMonitor() {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    // Poll every 2 seconds
    const interval = setInterval(async () => {
      const response = await fetch('/api/v1/system/tasks/active');
      const data = await response.json();
      setTasks(data.tasks);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <h2>Active Tasks ({tasks.length})</h2>
      {tasks.map(task => (
        <div key={task.id}>
          <span>{task.description}</span>
          <span className="muted">{task.running_for_seconds.toFixed(1)}s</span>
        </div>
      ))}
    </div>
  );
}
```

---

## Category Breakdown

### Task Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| `API` | FastAPI/Uvicorn server | HTTP request handler |
| `HARDWARE` | Hardware polling/GPIO | Control panel polling, GPIO reads |
| `RENDER` | Rendering/frame output | FrameManager render loop |
| `ANIMATION` | Animation execution | AnimationEngine, animation coroutines |
| `INPUT` | User input | Keyboard adapter, event listeners |
| `SYSTEM` | Infrastructure | LogBroadcaster, state persistence |
| `TRANSITION` | Fade/transition effects | Transition service tasks |
| `EVENTBUS` | Event handling | Event bus workers |
| `BACKGROUND` | Generic background work | Debounced tasks |
| `GENERAL` | Uncategorized | Legacy tasks without category |

---

## Response Codes

All endpoints return:

- **200 OK** - Request successful, JSON response
- **404 Not Found** - Endpoint doesn't exist
- **500 Internal Server Error** - Server error (rare)

No authentication required (API runs locally).

---

## Performance Notes

### Request Latency
- Typical response time: 1-5ms
- No database queries needed
- Just iterates in-memory task registry
- Safe to call frequently (1Hz+)

### Memory Overhead
- Each task adds ~300 bytes of metadata
- 50 tasks = ~15 KB
- 1000 tasks = ~300 KB

Even with 1000 tasks, memory impact is negligible.

---

## Integration Examples

### Prometheus Metrics

```python
# Expose task counts as Prometheus metrics
from prometheus_client import Counter, Gauge

task_total = Gauge('diuna_tasks_total', 'Total tasks ever created')
task_active = Gauge('diuna_tasks_active', 'Currently running tasks')
task_failed = Counter('diuna_tasks_failed', 'Failed task count')

# Update these from /tasks/summary endpoint
```

### Grafana Dashboard

Create a Grafana dashboard showing:
- Active tasks over time
- Failed tasks counter
- Task category breakdown (pie chart)
- Health status indicator

---

## Troubleshooting

### Endpoint returns 404

Ensure:
1. API server is running (check main startup logs)
2. API port is 8000 (default, check config)
3. Endpoint path is exact: `/api/v1/system/tasks/...`

### Response is empty or count is 0

This is normal when:
- App just started (tasks haven't been created yet)
- All tasks have completed
- You called `/active` and nothing is running

### Can't connect to http://localhost:8000

1. Is the app running? Check for startup logs
2. Is it running on a different port? Check `src/config/config.yaml`
3. On Raspberry Pi? Try the actual IP: `http://192.168.1.100:8000`

---

## See Also

- [Overview](./0_overview.md) - Task lifecycle and concepts
- [Shutdown Sequence](./1_shutdown_sequence.md) - What happens on exit
- Source: `src/api/routes/system.py` - API implementation
- Source: `src/lifecycle/task_registry.py` - Task tracking

