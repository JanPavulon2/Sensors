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