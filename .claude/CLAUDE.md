# Diuna Project - AI Assistant Guide

**Last Updated**: 2025-11-19
**Version**: 0.3-dev
**Current Phase**: Phase 6 Complete (Unified Rendering + Type Safety)
**Purpose**: Central guide for AI agents working on this codebase

---

## 🎯 Critical Rules - READ FIRST

1. **READ THIS FILE FIRST** before starting any task
2. **SOURCE CODE = TRUTH** - docs may lag behind, always verify in `src/`
3. **NEVER create MD files in project root** - use `.claude/context/` structure
4. **UPDATE FILE HEADERS** when modifying documentation (date + changes)
5. **ONE FILE PER TOPIC** - no duplicate documentation
6. **FOLLOW CODE STYLE RULES** - see Code Style Requirements section below

---

## 📊 Project Overview

**Diuna** is a Raspberry Pi-based LED control system with sophisticated animation rendering, zone management, and real-time frame processing.

### Quick Stats
- **Platform**: Raspberry Pi 4 (Linux)
- **Language**: Python 3.9+ with asyncio
- **Code Size**: ~9,400 lines across 75 Python files
- **Hardware**:
  - Main Strip: 90 WS2811 pixels (12V) in 6-8 zones
  - Preview Panel: 8 WS2812B pixels (5V)
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

### Essential Reading (START HERE)
1. **[.claude/context/INDEX.md]** - Complete documentation index with navigation
2. **[.claude/context/architecture/rendering-system.md]** - Complete rendering architecture
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

---

## 🔄 Development Workflow

### Starting Work on a Task

1. **Read Documentation**
   - Start with `.claude/context/INDEX.md` for navigation
   - Read relevant architecture/domain docs
   - Check `context/project/todo.md` for current status

2. **Understand the Code**
   - Source code is the source of truth
   - Check recent git commits for context
   - Look at related tests

3. **Make Changes**
   - Follow code style rules above
   - Update type hints
   - Write/update tests
   - Keep changes focused

4. **Update Documentation**
   - Update relevant context files in `.claude/context/`
   - Update file headers with date and changes
   - Update `project/todo.md` if completing tasks

### Git Workflow

**Current Branch**: `claude/claude-md-mi6dznm0vhuwbem8-01BZ7yTjfT9EwCCBztC3cUKK`

#### Committing Changes
```bash
# Check status
git status

# Stage files
git add <files>

# Commit with clear message
git commit -m "Brief description of changes"

# Push to current branch
git push -u origin claude/claude-md-mi6dznm0vhuwbem8-01BZ7yTjfT9EwCCBztC3cUKK
```

#### Commit Message Guidelines
- Use present tense ("Add feature" not "Added feature")
- Be specific about what changed
- Reference issue numbers if applicable
- Examples:
  - ✅ "Fix circular import in Color model using TYPE_CHECKING"
  - ✅ "Refactor FrameManager to use type-specific selection methods"
  - ❌ "Fix bugs"
  - ❌ "Update code"

---

## 🧪 Testing

### Running Tests
```bash
# Run all tests
python -m pytest src/tests/

# Run specific test file
python -m pytest src/tests/test_frame_manager.py

# Run with verbose output
python -m pytest -v src/tests/
```

### Test Organization
- Unit tests in `src/tests/`
- Domain model tests in `src/tests/domain_models/`
- Integration tests alongside unit tests
- Mock hardware dependencies for testing

### Writing Tests
- Test one thing per test function
- Use descriptive test names: `test_frame_manager_selects_highest_priority`
- Mock external dependencies (GPIO, hardware)
- Test edge cases and error conditions

---

## 📝 Documentation Update Protocol

### When to Update Documentation

| You Changed... | Update These Files |
|----------------|-------------------|
| Animation logic | `domain/animations.md` + `project/changelog.md` |
| Zone configuration | `domain/zones.md` |
| Hardware wiring/GPIO | `technical/hardware.md` |
| Architecture/design | `architecture/*.md` |
| Fixed a bug | `project/todo.md` + `project/changelog.md` |
| Added feature | `project/roadmap.md` + relevant domain docs |

### File Header Format

**Always update the header when modifying a context file:**

```markdown
---
Last Updated: 2025-11-19
Updated By: @agent-name or Human
Changes: Brief description of what changed
---
```

---

## 🚨 Common Pitfalls to Avoid

### 1. Creating Files in Wrong Location
❌ **NEVER** create documentation in project root
✅ **ALWAYS** use `.claude/context/` for docs

### 2. Duplicate Documentation
❌ **NEVER** create duplicate docs on same topic
✅ **ALWAYS** check if doc exists first, then update it

### 3. Breaking Imports
❌ **NEVER** move files without checking all imports
✅ **ALWAYS** search for imports before refactoring

### 4. Ignoring Type Errors
❌ **NEVER** use `# type: ignore` without understanding why
✅ **ALWAYS** fix the root cause of type errors

### 5. Blocking Async Code
❌ **NEVER** use blocking I/O in async functions
✅ **ALWAYS** use async alternatives (aiofiles, asyncio.sleep, etc.)

### 6. Forgetting Hardware Constraints
❌ **NEVER** call `show()` multiple times per frame
✅ **ALWAYS** render through FrameManager's unified path

---

## 🎓 Key Architectural Concepts

### Frame-Based Rendering
- All visual output goes through **FrameManager**
- Frames have **priority levels** (0-100, higher = more important)
- Frame sources submit frames to priority queues
- FrameManager selects highest priority frame per render cycle
- Target: 60 FPS (16.67ms per frame)

### Priority Levels
```
100: Critical system states
50:  Animations (normal operation)
30:  Transitions (fade in/out)
10:  Manual/static colors
0:   Background/default
```

### Event-Driven Architecture
- **EventBus** for pub/sub communication
- Events are typed dataclasses
- Components subscribe to specific event types
- Async event handlers

### Zone Management
- Physical LED strip divided into logical zones
- Each zone: independent color, brightness, enabled state
- Zone configuration in `src/config/zones.yaml`
- ZoneStrip handles zone-to-pixel mapping

### Animation System
- Animations are async generators yielding frames
- AnimationEngine manages animation lifecycle
- Animations can run per-zone or full-strip
- Support for speed, brightness, color parameters

---

## 🔧 Development Environment

### Prerequisites
- Python 3.9+
- Raspberry Pi OS (for hardware)
- GPIO access (for LED control)

### Key Dependencies
- `asyncio` - Async runtime
- `rpi_ws281x` - LED control library (hardware only)
- `pyyaml` - Configuration files
- `pytest` - Testing framework

### Environment Setup
See `context/development/setup.md` for detailed instructions.

---

## 📚 Learning Path for New AI Agents

### Quick Start (30 min)
1. Read this file (CLAUDE.md)
2. Skim `context/INDEX.md`
3. Read `context/project/todo.md` for current status
4. Look at `src/main_asyncio.py` to see system initialization

### Deep Dive (2-3 hours)
1. Read `context/architecture/rendering-system.md` - complete rendering architecture
2. Read `context/architecture/patterns.md` - design patterns
3. Read `context/development/coding-standards.md` - code style
4. Explore `src/` directory structure
5. Read example animation: `src/animations/snake.py`

### Mastery (Full Day)
1. Read all architecture docs in `context/architecture/`
2. Read all domain docs in `context/domain/`
3. Study FrameManager implementation: `src/engine/frame_manager.py`
4. Study LEDController: `src/controllers/led_controller/led_controller.py`
5. Understand event flow in `src/services/event_bus.py`
6. Review all configuration files in `src/config/`

---

## 🎯 Phase 6 Status (Current)

### Recently Completed ✅

1. **Circular Import Resolution**
   - Fixed Color model circular dependency using TYPE_CHECKING
   - Maintains full type safety with string literal type hints

2. **Unified Rendering Architecture**
   - All zone rendering goes through FrameManager
   - Eliminated dual rendering paths
   - Single source of truth for LED output

3. **Type Safety Improvements**
   - Separated generic frame selection into type-specific methods
   - EventBus with proper TypeVar handling
   - Zero type errors in core rendering path

4. **FramePlaybackController**
   - Completed implementation for frame-by-frame playback mode
   - Integration with FrameManager priority system

See `context/project/todo.md` for detailed phase information.

---

## 📞 Getting Help

### For AI Agents
1. **Search documentation**: Start with `.claude/context/INDEX.md`
2. **Check TODO**: Look at `context/project/todo.md` for known issues
3. **Read source code**: Source is always the truth
4. **Check git history**: `git log` for recent changes

### For Humans
- Documentation is in `.claude/context/`
- Configuration is in `src/config/`
- Tests are in `src/tests/`
- Examples are in `samples/`

---

## 🏁 Checklist for AI Agents

Before starting any task:
- [ ] Read this CLAUDE.md file
- [ ] Check `.claude/context/INDEX.md` for relevant docs
- [ ] Read relevant architecture/domain documentation
- [ ] Check `context/project/todo.md` for current status
- [ ] Understand the code style requirements
- [ ] Know which specialized agent to use (if applicable)

Before committing changes:
- [ ] Code follows style requirements (imports, DI, type hints)
- [ ] Type hints are complete and correct
- [ ] No circular imports
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if needed)
- [ ] Commit message is clear and specific

Before pushing:
- [ ] On correct branch: `claude/claude-md-mi6dznm0vhuwbem8-01BZ7yTjfT9EwCCBztC3cUKK`
- [ ] All changes committed
- [ ] No unintended files in commit

---

## 📌 Quick Reference Card

```
Entry Point:        src/main_asyncio.py
Main Controller:    src/controllers/led_controller/led_controller.py
Frame Manager:      src/engine/frame_manager.py
Animation Engine:   src/animations/engine.py
Event Bus:          src/services/event_bus.py

Documentation:      .claude/context/INDEX.md
Current Tasks:      .claude/context/project/todo.md
Architecture:       .claude/context/architecture/rendering-system.md
Code Style:         .claude/context/development/coding-standards.md

Config Files:       src/config/*.yaml
Tests:              src/tests/

Current Branch:     claude/claude-md-mi6dznm0vhuwbem8-01BZ7yTjfT9EwCCBztC3cUKK
Current Phase:      Phase 6 Complete (Unified Rendering + Type Safety)
```

---

**Last Updated**: 2025-11-19
**Maintained By**: AI Agents + Human Contributors
**Status**: Current and accurate as of Phase 6 completion

**Remember**: When in doubt, read the source code. Documentation helps understand intent, but code is the truth.
