---
Last Updated: 2025-12-02
Updated By: Claude Code
Changes: Created complete lifecycle and shutdown documentation
---

# Application Lifecycle and Shutdown Documentation

Complete guide to Diuna's task management and graceful shutdown system.

## Quick Start

**New to the lifecycle system?** Start here:

1. **[User Overview](./user/0_overview.md)** - 5-minute overview of how it works
2. **[Shutdown Sequence](./user/1_shutdown_sequence.md)** - What happens when you press Ctrl+C
3. **[Task Monitoring API](./user/2_task_monitoring_api.md)** - How to see what tasks are running

**Implementing changes?** Start here:

1. **[Agent Overview](./agent/0_agent_overview.md)** - Architecture and key classes
2. **[Implementation Patterns](./agent/1_implementation_patterns.md)** - Code templates and best practices

## What is This?

Diuna uses a sophisticated system to manage application startup, long-running tasks, and graceful shutdown:

- **TaskRegistry**: Tracks all asyncio tasks with metadata (why they exist, when they started, etc.)
- **ShutdownCoordinator**: Orchestrates safe shutdown of all components in the right order
- **REST API**: Exposes real-time task visibility for monitoring and debugging

## Directory Structure

```
3_lifecycle/
├── README.md                    # ← You are here
│
├── user/                        # For users and system administrators
│   ├── 0_overview.md            # High-level concepts and quick reference
│   ├── 1_shutdown_sequence.md   # Detailed timeline of shutdown
│   └── 2_task_monitoring_api.md # REST API endpoints for task introspection
│
└── agent/                       # For AI agents implementing changes
    ├── 0_agent_overview.md      # Architecture, classes, key concepts
    └── 1_implementation_patterns.md # Code templates and best practices
```

## Key Concepts

### Task Registry
Central database of all asyncio tasks with metadata:
- Unique ID for each task
- Category (API, HARDWARE, ANIMATION, etc.)
- Description of what it does
- When it started, when it finished
- Exception if it crashed

**Use for**: Debugging ("what's running?"), monitoring, REST API introspection

### Shutdown Coordinator
Orchestrates graceful shutdown with priority-based handler execution:
- Handlers run in priority order (highest first)
- Each handler has timeout (5 seconds)
- Total shutdown timeout (15 seconds)
- Handles signal reception (SIGINT, SIGTERM)

**Use for**: Safe shutdown, component cleanup, preventing orphaned resources

### REST API
HTTP endpoints for real-time task monitoring:
- `/api/v1/system/tasks/summary` - Task counts
- `/api/v1/system/tasks` - All tasks with details
- `/api/v1/system/tasks/active` - Currently running tasks
- `/api/v1/system/tasks/failed` - Tasks that crashed
- `/api/v1/system/health` - Overall app health

**Use for**: Dashboards, health checks, debugging

## Typical Flows

### Normal Application Startup

```
main() starts
  ↓
Initialize infrastructure (GPIO, config, services)
  ↓
Create long-running tasks with create_tracked_task()
  ↓
Register shutdown handlers with coordinator
  ↓
Install signal handlers (SIGINT, SIGTERM)
  ↓
Main loop waits for shutdown event
```

### User Presses Ctrl+C

```
OS sends SIGINT
  ↓
Signal handler sets shutdown_event
  ↓
Main loop wakes up
  ↓
Coordinator.shutdown_all() starts
  ↓
Handlers run in priority order:
  1. LEDShutdownHandler - Turn off lights
  2. AnimationShutdownHandler - Stop animations
  3. APIServerShutdownHandler - Stop API
  4. TaskCancellationHandler - Cancel known tasks
  5. AllTasksCancellationHandler - Cancel remaining tasks
  6. GPIOShutdownHandler - Reset GPIO
  ↓
All handlers complete
  ↓
App exits cleanly
```

### Task Lifecycle

```
create_tracked_task(coroutine, category, description)
  ↓
TaskRegistry.register() creates TaskInfo and TaskRecord
  ↓
Done callback attached to task
  ↓
Task runs to completion (or exception or cancellation)
  ↓
Done callback fires, TaskRecord updated
  ↓
Task appears in /system/tasks API endpoint
  ↓
On shutdown, task is cancelled and awaited
```

## Common Questions

### Q: How do I see what my app is doing?

**A**: Use the REST API:
```bash
curl http://localhost:8000/api/v1/system/tasks/active
```

This shows all currently running tasks with timestamps.

### Q: My app doesn't shut down cleanly

**A**: Check active tasks:
```bash
curl http://localhost:8000/api/v1/system/tasks/active
```

Look for a task that's been running for a very long time. That's likely blocking shutdown. Ensure the task properly handles `asyncio.CancelledError` and re-raises it.

### Q: How do I add a new background task?

**A**: Use `create_tracked_task()`:
```python
from lifecycle.task_registry import create_tracked_task, TaskCategory

create_tracked_task(
    my_coroutine(),
    category=TaskCategory.SYSTEM,
    description="What this task does"
)
```

**Important**: Your coroutine must handle `asyncio.CancelledError` and re-raise it.

### Q: How do I ensure my component shuts down gracefully?

**A**: Create a `IShutdownHandler`:
```python
class MyShutdownHandler(IShutdownHandler):
    @property
    def shutdown_priority(self) -> int:
        return 50  # When to run

    async def shutdown(self) -> None:
        # Clean up your component
        await self.component.stop()
```

Then register it in `main()`:
```python
coordinator.register(MyShutdownHandler(component))
```

### Q: What's the difference between TaskRegistry and ShutdownCoordinator?

**A**:
- **TaskRegistry**: Tracking database. "What tasks are running?"
- **ShutdownCoordinator**: Shutdown orchestrator. "How do we shut down safely?"

They work together but have different jobs.

## File Organization

### Core Implementation
- `src/lifecycle/task_registry.py` - Task tracking singleton
- `src/lifecycle/shutdown_coordinator.py` - Shutdown orchestration
- `src/lifecycle/shutdown_protocol.py` - IShutdownHandler interface
- `src/lifecycle/handlers/` - Individual shutdown handlers
- `src/api/routes/system.py` - REST API endpoints

### Entry Point
- `src/main_asyncio.py` - Application initialization and main loop

## Guides by Role

### For System Administrators
1. Read [User Overview](./user/0_overview.md)
2. Use [Task Monitoring API](./user/2_task_monitoring_api.md) to monitor app
3. Check [Shutdown Sequence](./user/1_shutdown_sequence.md) if shutdown issues

### For Backend Developers
1. Read [Agent Overview](./agent/0_agent_overview.md)
2. Review [Implementation Patterns](./agent/1_implementation_patterns.md)
3. Check source code for specific components

### For Frontend Developers
1. Read [Task Monitoring API](./user/2_task_monitoring_api.md) to understand endpoints
2. Use API to build monitoring dashboards
3. Check [Agent Overview](./agent/0_agent_overview.md) for architecture context

### For AI Agents
1. Start with [Agent Overview](./agent/0_agent_overview.md)
2. Review [Implementation Patterns](./agent/1_implementation_patterns.md)
3. Check [Shutdown Sequence](./user/1_shutdown_sequence.md) for context
4. Look at actual source code in `src/lifecycle/`

## Recent Changes

### Phase 6 - Task Management Integration (Current)

**What Changed**:
- TaskRegistry integrated with ShutdownCoordinator
- AllTasksCancellationHandler uncommented and configured
- 5+ critical infrastructure tasks now tracked:
  - API server (FastAPI)
  - Animation engine
  - Hardware polling loop
  - Keyboard input adapter
  - Log broadcaster
- REST API endpoints for task introspection
- Comprehensive documentation

**Why**: Provides real-time visibility into running tasks for debugging and monitoring.

## Technical Details

### Timeout Management
- Per handler: 5 seconds (configurable)
- Total shutdown: 15 seconds (configurable)
- On timeout: Warning logged, next handler runs

### Task Overhead
- Each task: ~300 bytes metadata
- 100 tasks: ~30 KB
- Minimal CPU impact (only on queries)

### Shutdown Priority Levels
```
100 - LED/Hardware shutdown
90  - Animation shutdown
80  - API server shutdown
50  - Component-specific shutdown
40  - Task cancellation
20  - GPIO cleanup
```

## Troubleshooting

### Symptom: App hangs on Ctrl+C
**Cause**: Task not responding to cancellation
**Fix**: Check task's CancelledError handling

### Symptom: LEDs stay on after exit
**Cause**: LED shutdown handler didn't run
**Fix**: Check shutdown handler priorities and exceptions

### Symptom: Tasks still running after shutdown
**Cause**: Untracked tasks (created with `asyncio.create_task()`)
**Fix**: Use `create_tracked_task()` instead

### Symptom: Cannot connect to REST API
**Cause**: API server not started or different port
**Fix**: Check `src/config/config.yaml` for port setting

## See Also

- **Main Application**: `src/main_asyncio.py`
- **Rendering System**: See `.documentation/1_rendering_system/`
- **Multi-GPIO Architecture**: See `.documentation/2_multi_zone_rendering/`
- **Project TODO**: See `.claude/context/project/todo.md`

## Contact & Support

- Source code: `src/lifecycle/`, `src/api/routes/system.py`
- Issues/questions: Check `src/` source code first, then review these docs
- Implementing changes: Follow patterns in [Implementation Patterns](./agent/1_implementation_patterns.md)

---

**Last Updated**: 2025-12-02
**Status**: Complete and current
**Maintained by**: AI agents and human contributors

