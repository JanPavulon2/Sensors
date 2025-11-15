---
Last Updated: 2025-11-15
Created By: New documentation
Purpose: Agent types, usage, and file routing
---

# Agent Guide

## Agent Types

### Custom Agents vs Sub-Agents

**Custom Agents** (in `.claude/agents/`):
- **Purpose**: Specialized expertise for this project
- **When**: Task requires domain knowledge (architecture, animations, hardware)
- **How**: Explicitly select from agent menu

**Sub-Agents** (Claude's built-in):
- **Purpose**: General capabilities (code writing, debugging, search)
- **When**: Task is generic programming or research
- **How**: Automatically activated by Claude

## Available Custom Agents

### @architecture-expert (Sonnet + Haiku)
**Expertise**: System design, patterns, class relationships, refactoring
**Read Before Work**:
1. `context/architecture/overview.md`
2. `context/architecture/layers.md`
3. `context/architecture/patterns.md`
4. Relevant source code in `src/`

**Use For**:
- Designing new features
- Refactoring existing code
- Architectural decisions
- Pattern selection

**Model Choice**:
- **Sonnet**: Complex architectural decisions, major refactors
- **Haiku**: Quick architecture reviews, minor refactors

---

### @python-expert (Sonnet + Haiku)
**Expertise**: Python implementation, asyncio, code quality
**Read Before Work**:
1. `context/development/coding-standards.md`
2. `context/technical/async-patterns.md`
3. Relevant domain docs (`context/domain/*.md`)
4. Existing code to modify

**Use For**:
- Implementing features
- Bug fixes
- Code optimization
- Asyncio debugging

**Model Choice**:
- **Sonnet**: Complex async patterns, new features, performance optimization
- **Haiku**: Bug fixes, simple features, code cleanup

---

### @rpi-hardware-expert (Sonnet + Haiku)
**Expertise**: Raspberry Pi, GPIO, hardware interfaces, timing
**Read Before Work**:
1. `context/technical/hardware.md`
2. `context/domain/zones.md`
3. `context/technical/async-patterns.md` (GPIO polling patterns)

**Use For**:
- GPIO configuration
- Hardware troubleshooting
- Timing optimization
- LED strip issues

**Model Choice**:
- **Sonnet**: Complex timing issues, DMA debugging, new hardware integration
- **Haiku**: GPIO mapping, simple hardware queries

---

### @ux-hardware-expert (Sonnet + Haiku)
**Expertise**: Hardware UX (encoders, buttons), input handling
**Read Before Work**:
1. `context/technical/hardware.md` (GPIO mappings)
2. `src/components/control_panel.py`
3. `src/services/event_bus.py`

**Use For**:
- Adding new input hardware
- Improving encoder responsiveness
- Button debouncing
- Preview panel UX

**Model Choice**:
- **Sonnet**: New input types, complex UX patterns
- **Haiku**: Button mapping, simple UX tweaks

---

## Agent Workflow

### Before Starting Work

1. **Read `claude.md`** - Understand file structure
2. **Read relevant context files** - Based on agent type above
3. **Check actual source code** - Documentation may be outdated
4. **Ask for clarification** - If instructions unclear

### During Work

1. **Follow coding standards** - See `coding-standards.md`
2. **Update documentation** - If you change code
3. **Add file headers** - Date + changes made
4. **Stay in scope** - Don't edit unrelated code

### After Work

1. **Update changelog** - `context/project/changelog.md`
2. **Update TODO** - Mark completed, add new issues
3. **Test changes** - Unit tests or hardware validation
4. **Report results** - What worked, what didn't

## File Routing by Task Type

| Task Type | Agent | Files to Read |
|-----------|-------|---------------|
| Architecture design | @architecture-expert-sonnet | `architecture/*.md` |
| Architecture review | @architecture-expert-haiku | `architecture/overview.md` |
| Implement feature | @python-expert-haiku | `coding-standards.md` + domain docs |
| Fix bug | @python-expert-haiku | `coding-standards.md` + relevant code |
| GPIO issue | @rpi-hardware-expert-sonnet | `technical/hardware.md` |
| Hardware mapping | @rpi-hardware-expert-haiku | `technical/hardware.md` |
| Add input | @ux-hardware-expert-sonnet | `technical/hardware.md` + EventBus code |
| Button tweak | @ux-hardware-expert-haiku | `technical/hardware.md` |

## When to Use Which Model

**Sonnet** (Smarter, Slower, More Expensive):
- Complex problems requiring deep reasoning
- Architectural decisions
- New feature design
- Performance optimization
- Debugging subtle issues

**Haiku** (Faster, Cheaper, Good Enough):
- Simple implementations
- Code reviews
- Documentation updates
- Quick fixes
- Routine tasks

## Best Practices

✅ **DO**:
- Read context files before coding
- Trust source code over docs
- Ask for clarification
- Update docs when changing code
- Use appropriate model (Haiku for simple tasks)

❌ **DON'T**:
- Skip reading context files
- Trust outdated documentation
- Make assumptions without asking
- Modify code without updating docs
- Use Sonnet for trivial tasks (wastes tokens)