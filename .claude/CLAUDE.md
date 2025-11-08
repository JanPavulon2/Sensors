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

**CRITICAL**: All imports MUST be at the top of the file, not inline within functions.

❌ WRONG:
```python
def some_function():
    from models.enums import MainMode  # NO - inline import
    ...
```

✅ CORRECT:
```python
from models.enums import MainMode  # YES - at module level

def some_function():
    ...
```

**Rationale**:
- Clearer code readability - imports visible at a glance
- Easier to identify dependencies
- Better static analysis and IDE support
- Consistent with PEP 8 style guide

### Dependency Injection

**CRITICAL**: Use constructor injection only. Do NOT assign dependencies via property assignment.

❌ WRONG:
```python
service.frame_manager = frame_manager  # NO - property injection
```

✅ CORRECT:
```python
def __init__(self, frame_manager):  # YES - constructor injection
    self.frame_manager = frame_manager
```

**Rationale**:
- Clear and explicit dependencies
- Easier to understand object initialization
- Type hints work better with constructor params
- Prevents issues with uninitialized attributes

### Type-Explicit APIs

**CRITICAL**: Use explicit type checks and objects, not string-based type detection.

❌ WRONG:
```python
if hasattr(obj, 'get_frame'):  # NO - checking for method existence
    obj.get_frame()
```

✅ CORRECT:
```python
if isinstance(obj, ZoneStrip):  # YES - explicit type check
    ...
```

**Rationale**:
- Type safety and clarity
- Prevents accidental duck-typing bugs
- IDE can provide better autocomplete
- Easier to refactor