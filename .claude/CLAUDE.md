# Diuna Project - Claude Configuration

## Global Agent Behavior

### Confirmation Workflow (ALL AGENTS)
Every agent must follow this workflow on FIRST activation:
1. Identify themselves with 🔧 emoji
2. List files to examine
3. Wait for user confirmation

### Agent Routing
- `[uber-expert]` → @uber-expert
- `[backend-sonnet]` → @python-expert-sonnet
- `[backend]` → @python-expert
- `[frontend-sonnet]` → @frontend-expert-sonnet
- `[frontend]` → @frontend-expert  
- `[architecture-expert-sonnet]` → @architecture-expert-sonnet
- `[architecture-expert]` → @architecture-expert
- `[x,y]` → multiple agents, for example `[backend-sonnet, frontend-sonnet]` -> use multiple agents specified in brackets, according to instruction below

### Cross-Agent Coordination
When multiple agents needed:
- Primary agent drives investigation
- Other agents provide input in sub-sections
- Final response unified by primary agent

## Code Style Preferences
- Python: PEP 8, type hints, async/await
- TypeScript: strict mode, functional components
- Comments: Explain WHY not WHAT

## 🎯 Critical Rules - READ FIRST

1. **READ THIS FILE FIRST** before starting any task
2. **SOURCE CODE = TRUTH** - docs may lag behind, always verify in `src/`
3. **NEVER create MD files in project root** - use `.claude/context/` structure
4. **UPDATE FILE HEADERS** when modifying documentation (date + changes)
5. **ONE FILE PER TOPIC** - no duplicate documentation
6. **FOLLOW CODE STYLE RULES** - see Code Style Requirements section below
7. **ALL RENDERING THROUGH FRAMEMANAGER** - No component/controller may call `strip.show()` or directly manipulate pixels. All LED updates must be submitted as frames to FrameManager via `submit_zone_frame()` or `submit_pixel_frame()`


## 📊 Project Overview

**Diuna** is a Raspberry Pi-based LED control system with sophisticated animation rendering, zone management, and real-time frame processing.

### Quick Stats
- **Platform**: Raspberry Pi 4 (Linux)
- **Language**: Python 3.9+ with asyncio
- **Code Size**: ~9,400 lines across 75 Python files
- **Animations**: 9 built-in types
- **Architecture**: Event-driven, async-first, frame-based rendering

### Key Features
- ✅ Real-time LED animation engine (60 FPS target)
- ✅ Priority-based frame queue system
- ✅ Smooth transitions between states
- ✅ Zone-based control with independent brightness
- ✅ Keyboard input for live control
- ✅ Type-safe event system
- ✅ Unified rendering through FrameManager

---

## 📁 Repository Structure

```
Sensors/
├── .claude/                    # AI assistant configuration (THIS DIRECTORY)
│   ├── CLAUDE.md              # ← YOU ARE HERE
│   ├── context/               # All project documentation
│   │   ├── architecture/      # System design & patterns
│   │   ├── domain/            # Business logic (animations, zones, colors)
│   │   ├── technical/         # Hardware, GPIO, performance
│   │   ├── development/       # Setup, coding standards, testing
│   │   └── project/           # TODO, changelog, roadmap
│   └── agents/                # Custom agent definitions (do not modify)
├── src/                        # Python source code
│   ├── main_asyncio.py        # Application entry point
│   ├── animations/            # Animation implementations
│   ├── components/            # Hardware abstractions (ZoneStrip, PreviewPanel)
│   ├── controllers/           # Business logic controllers
│   ├── engine/                # FrameManager & rendering engine
│   ├── managers/              # ConfigManager, ColorManager
│   ├── models/                # Data models & enums
│   ├── services/              # EventBus, AnimationService, TransitionService
│   ├── state/                 # Application state management
│   ├── infrastructure/        # GPIO & hardware interfaces
│   ├── config/                # YAML configuration files
│   └── tests/                 # Unit & integration tests
├── samples/                    # Example scripts & utilities
└── README.md                   # (if exists) Project readme
```

---

## 🔍 Quick Reference

### Entry Points
- **Main Application**: `src/main_asyncio.py`
- **LED Controller**: `src/controllers/led_controller/led_controller.py`
- **Frame Manager**: `src/engine/frame_manager.py`
- **Animation Engine**: `src/animations/engine.py`

### Configuration Files (`src/config/`)
- `config.yaml` - Main app config
- `zones.yaml` - Zone definitions & pixel mappings
- `animations.yaml` - Animation presets
- `colors.yaml` - Color presets & palettes
- `parameters.yaml` - Animation parameters
- `hardware.yaml` - GPIO & hardware settings
- `factory_defaults.yaml` - Default values

### Key Directories
- **Controllers**: High-level business logic, mode management
- **Services**: Cross-cutting concerns (events, transitions, state)
- **Engine**: Core rendering & frame management
- **Components**: Direct hardware abstractions
- **Models**: Data structures, enums, domain objects

---

## 🗂️ Documentation Index

### ⭐ NEW: Rendering System Documentation (Phase 6)
**Start here for complete rendering system overview:**
- **User Documentation** (for understanding the system):
  - [.documentation/1_rendering_system/user/0_overview.md](.claude/context/.documentation/1_rendering_system/user/0_overview.md) - System concepts & architecture
  - [User Guide Files](.claude/context/.documentation/1_rendering_system/user/) - 6 comprehensive guides

- **Agent Documentation** (for implementing changes):
  - [.documentation/1_rendering_system/agent/0_agent_overview.md](.claude/context/.documentation/1_rendering_system/agent/0_agent_overview.md) - Agent-specific details
  - [Agent Guide Files](.claude/context/.documentation/1_rendering_system/agent/) - 5 implementation guides

- **TODO System** (tracking issues):
  - [.todo/rendering_system.md](.claude/context/.todo/rendering_system.md) - Rendering issues & tasks
  - [.todo/controllers.md](.claude/context/.todo/controllers.md) - Controller improvements

### Essential Reading (START HERE)
1. **[.claude/context/INDEX.md]** - Complete documentation index with navigation
2. **[.claude/context/.documentation/1_rendering_system/user/0_overview.md]** - **NEW**: Rendering system overview
3. **[.claude/context/project/todo.md]** - Current tasks & project status
4. **[.claude/context/development/coding-standards.md]** - Code style & patterns

### By Topic

#### Architecture & Design
- `context/architecture/overview.md` - High-level system overview
- `context/architecture/layers.md` - Layered architecture details
- `context/architecture/patterns.md` - Design patterns used
- `context/architecture/rendering-system.md` - **Complete rendering system** ⭐

#### Domain Logic
- `context/domain/animations.md` - Animation types & behaviors
- `context/domain/zones.md` - Zone configuration & management
- `context/domain/colors.md` - Color spaces & conversion

#### Technical Details
- `context/technical/hardware.md` - Hardware specs & constraints
- `context/technical/gpio.md` - GPIO configuration
- `context/technical/performance.md` - Performance metrics & optimization

#### Development
- `context/development/setup.md` - Development environment setup
- `context/development/coding-standards.md` - Code style rules ⭐
- `context/development/testing.md` - Testing strategy

#### Project Management
- `context/project/todo.md` - **Current tasks & bugs** ⭐
- `context/project/changelog.md` - Version history
- `context/project/roadmap.md` - Future plans

---

## 🤖 Agent Routing

Choose the right specialized agent for your task:

### Architecture Work
**When**: System design, refactoring, design patterns, code reviews
**Read**: `context/architecture/*.md`
**Use**: `@architecture-expert-sonnet` (complex) or `@architecture-expert` (simple)

### Python Implementation
**When**: Writing code, implementing features, fixing bugs, asyncio work
**Read**: `context/development/coding-standards.md`, relevant domain docs
**Use**: `@python-expert-sonnet` (complex) or `@python-expert` (simple)

### Animation Work
**When**: Implementing/modifying animations, rendering logic
**Read**: `context/domain/animations.md`, `context/architecture/rendering-system.md`
**Use**: `@python-expert-sonnet` + refer to animation architecture docs

### Hardware/GPIO
**When**: LED control, GPIO configuration, hardware interfacing
**Read**: `context/technical/hardware.md`, `context/domain/zones.md`
**Use**: `@rpi-hardware-expert-sonnet` (complex) or `@rpi-hardware-expert` (simple)

---

## 💻 Code Style Requirements

### ⚠️ CRITICAL RULES - MUST FOLLOW

#### 1. Import Organization
**All imports MUST be at the top of the file, never inline.**

❌ **WRONG**:
```python
def some_function():
    from models.enums import MainMode  # NO - inline import
    ...
```

✅ **CORRECT**:
```python
from models.enums import MainMode  # YES - at module level

def some_function():
    ...
```

**Rationale**: Clearer dependencies, better static analysis, PEP 8 compliance

---

#### 2. Dependency Injection
**Use constructor injection only. Do NOT assign dependencies via properties.**

❌ **WRONG**:
```python
service.frame_manager = frame_manager  # NO - property injection
```

✅ **CORRECT**:
```python
def __init__(self, frame_manager: FrameManager):  # YES - constructor injection
    self.frame_manager = frame_manager
```

**Rationale**: Clear dependencies, better type hints, prevents uninitialized attributes

---

#### 3. Type-Explicit APIs
**Use explicit type checks, not duck typing or hasattr.**

❌ **WRONG**:
```python
if hasattr(obj, 'get_frame'):  # NO - duck typing
    obj.get_frame()
```

✅ **CORRECT**:
```python
if isinstance(obj, ZoneStrip):  # YES - explicit type check
    obj.get_frame()
```

**Rationale**: Type safety, better IDE support, easier refactoring

---

#### 4. Type Hints
**Always use type hints for function signatures and class attributes.**

✅ **GOOD**:
```python
async def submit_frame(self, frame: MainStripFrame, priority: int) -> None:
    ...

def __init__(self, config: ZoneConfig) -> None:
    self.config: ZoneConfig = config
    self.brightness: float = 1.0
```

**Use TYPE_CHECKING for circular imports:**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from managers import ColorManager

def from_preset(cls, name: str, color_manager: 'ColorManager') -> 'Color':
    ...
```

---

#### 5. Async Patterns
**Follow consistent async/await patterns.**

✅ **GOOD**:
- Use `async def` for coroutines
- Always `await` async calls
- Use `asyncio.create_task()` for fire-and-forget
- Use `async with` for context managers
- Cancel tasks in cleanup

❌ **AVOID**:
- Mixing sync and async without clear boundaries
- Blocking calls in async functions
- Forgetting to await
- Not canceling tasks on shutdown


