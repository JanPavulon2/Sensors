# Diuna Project - Agent Navigation Hub

**Last Updated**: 2025-11-15  
**Version**: 0.2-dev  
**Purpose**: Central router for AI agents - READ THIS FIRST

---

## 🎯 Critical Rules

1. **READ THIS FILE FIRST** before any task
2. **NEVER create MD files in project root** - use `.claude/context/` structure
3. **UPDATE FILE HEADERS** when modifying (date + changes)
4. **SOURCE CODE = TRUTH** - docs may be outdated, trust `src/`
5. **ONE FILE PER TOPIC** - no duplicate docs

---

## 📁 File Organization
```
.claude/
├── claude.md           # ← YOU ARE HERE
├── context/            # ALL documentation goes here
│   ├── architecture/   # System design
│   ├── domain/         # Business logic (animations, zones, colors)
│   ├── technical/      # Hardware, GPIO, performance
│   ├── development/    # Setup, coding standards, testing
│   └── project/        # TODO, changelog, roadmap
└── agents/             # Agent configs (Sonnet + Haiku variants)
```

---

## 🗂️ Current Files (to be reorganized)

**In `.claude/context/`** (flat structure - will be moved to subfolders):
- `ARCHITECTURE.md` → `architecture/layers.md`
- `ANIMATIONS_REFACTORING.md` → `project/roadmap.md` (section)
- `ANIMATION_RENDERING_SYSTEM.md` → `domain/animations.md`
- `TODO.md` → `project/todo.md`
- `BRANCHING.md` → `development/git-workflow.md`

---

## 🤖 Agent Routing

### Architecture Work
**Read**: `context/architecture/layers.md`, `context/architecture/patterns.md`  
**Agents**: `@architecture-expert-sonnet`, `@architecture-expert-haiku`

### Animation Work
**Read**: `context/domain/animations.md`, actual code in `src/animations/`  
**Agents**: `@python-expert-sonnet`, `@python-expert-haiku`

### Hardware/GPIO
**Read**: `context/technical/hardware.md`, `context/domain/zones.md`  
**Agents**: `@rpi-hardware-expert-sonnet`, `@rpi-hardware-expert-haiku`

### Python/Asyncio
**Read**: `context/technical/async-patterns.md`, `context/development/coding-standards.md`  
**Agents**: `@python-expert-sonnet`, `@python-expert-haiku`

---

## 📝 Update Protocol

### Header Format
```markdown
---
Last Updated: 2025-11-15
Updated By: @agent-name or Human
Changes: What changed
---
```

### When to Update

| Changed What | Update Where |
|--------------|--------------|
| Animation logic | `domain/animations.md` + changelog |
| Zone config | `domain/zones.md` |
| Hardware wiring | `technical/hardware.md` |
| Architecture | `architecture/*.md` |
| Fixed bug | `project/todo.md` + `project/changelog.md` |

---

## 🔍 Quick Find

- **Entry point**: `src/main_asyncio.py`
- **Main controller**: `src/controllers/led_controller/led_controller.py`
- **Animations**: `src/animations/`
- **Services**: `src/services/`
- **Config**: `src/config/*.yaml`

---

## 📊 Project Stats

- **Lines of Code**: ~8,000
- **Python Files**: 50+
- **LED Zones**: 8 (90 pixels total)
- **Animations**: 6 built-in
- **Hardware**: Raspberry Pi 4 + WS2811 LEDs

---

**Next Steps for Agents**:
1. Read relevant `context/` file based on task
2. Check actual source code (`src/`)
3. Update docs if you change code
4. Never create files in project root



# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Important
- ALL instructions within this document MUST BE FOLLOWED, these are not optional unless explicitly stated.
- ASK FOR CLARIFICATION If you are uncertain of any of thing within the document.
- DO NOT edit more code than you have to.
- DO NOT WASTE TOKENS, be succinct and concise.


## File Organization Rules

### Project Documentation Location
ALL project documentation, configuration files, and context files MUST be stored in the `.claude/` directory structure:

- **`.claude/CLAUDE.md`** - Main project configuration and agent orchestration
- **`.claude/context/`** - Context files, notes, decisions, architecture docs
- **`.claude/agents/`** - Custom agent definitions (do not modify during normal work)

### File Creation Rules

When creating documentation or configuration files:

1. **Markdown documentation** → `.claude/context/`
   - Architecture decisions: `.claude/context/architecture/`
   - Feature specs: `.claude/context/features/`
   - Meeting notes: `.claude/context/notes/`
   - Research: `.claude/context/research/`

2. **Configuration files** → `.claude/` (root of .claude folder)
   - Project settings
   - Tool configurations

3. **Code files** → Appropriate `src/` directories
   - NOT in `.claude/` folder

### Examples

✅ CORRECT:
```
.claude/context/architecture/led-system-design.md
.claude/context/features/rainbow-effect-spec.md
.claude/context/notes/2024-01-meeting.md
```

❌ WRONG:
```
./architecture-notes.md
./docs/system-design.md
~/Desktop/project-notes.md
```

### Critical Rules

- **NEVER** create documentation files in project root
- **ALWAYS** use `.claude/context/` for new markdown files
- **ALWAYS** check if file should be in `.claude/` before creating
- When asked to "create a document", default to `.claude/context/`

---

## Code Style Requirements

### Import Organization

**CRITICAL**: All imports MUST be at the top of the file (unless impossible due to circular deps).

❌ WRONG:
```python
def some_function():
    from models.enums import MainMode  # NO - inline import
```

✅ CORRECT:
```python
from models.enums import MainMode  # YES - at module level

def some_function():
    ...
```

### Naming Conventions

**NO abbreviations** - use full names always.

❌ WRONG: `hw`, `cfg`, `mgr`, `svc`, `ctrl`
✅ CORRECT: `hardware`, `config`, `manager`, `service`, `controller`

### Enums Over Strings

**ALWAYS use enums**, never magic strings.

❌ WRONG: `"zone_name"`, `"BRG"` (strings in code)
✅ CORRECT: `ZoneID.FLOOR`, `ColorOrder.BRG` (enums)

### Dependency Injection

**Constructor injection only** - no property assignment.

❌ WRONG:
```python
service.frame_manager = frame_manager
```

✅ CORRECT:
```python
def __init__(self, frame_manager):
    self.frame_manager = frame_manager
```

### Type-Explicit APIs

**Explicit type checks**, no duck-typing.

❌ WRONG:
```python
if hasattr(obj, 'get_frame'):
    obj.get_frame()
```

✅ CORRECT:
```python
if isinstance(obj, ZoneStrip):
    ...
```

### Main Function Structure

**Flat, readable, no embedded logic loops**.

✅ CORRECT:
```python
log.info("Loading configuration...")
config_manager = ConfigManager(gpio_manager)
config_manager.load()

log.info("Initializing services...")
animation_service = AnimationService(assembler)
```

❌ WRONG: Don't embed `for` loops or complex logic in main() - extract to helper functions.