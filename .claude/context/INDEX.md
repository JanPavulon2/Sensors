---
Last Updated: 2025-11-15
Updated By: @architecture-expert-sonnet
---

# Context Documentation Index

Complete index of all `.claude/context/` files organized by topic and use case.

---

## 🎯 Quick Navigation by Task

### "I need to implement frame-by-frame mode"
1. Start: [Frame-By-Frame Quick Reference](development/frame-by-frame-guide.md)
2. Understand: [Full Implementation Spec](project/frame-by-frame-implementation.md)
3. Learn: [System Architecture](architecture/rendering-system.md) (Sections 3-5)
4. Check: [Design Decisions & Rationale](project/frame-by-frame-summary.md)
5. Reference: [Project Status](project/todo.md)

### "I need to understand the rendering system"
1. Start: [Rendering System Architecture](architecture/rendering-system.md)
2. Details: [Frame Models & Priority System](architecture/rendering-system.md#3-frame-system)
3. FrameManager: [Rendering System Architecture](architecture/rendering-system.md#4-framemanager)
4. Animation: [Rendering System Architecture](architecture/rendering-system.md#5-animation-system)
5. Examples: [Data Flow Examples](architecture/rendering-system.md#9-data-flow-examples)

### "I need to understand animations"
1. Start: [Animation System](domain/animations.md) (if exists)
2. Details: [Rendering System - Animation Section](architecture/rendering-system.md#5-animation-system)
3. Code: `src/animations/base.py`, `src/animations/snake.py`
4. Architecture: [Rendering System - Controllers](architecture/rendering-system.md#7-controllers)

### "I need to debug an issue"
1. Check: [Project TODO](project/todo.md#bugs--issues-tracker)
2. Investigate: [Remaining Animation Issues](remaining-animation-issues.md)
3. Search: Architecture docs for relevant system
4. Consult: [Common Pitfalls](development/frame-by-frame-guide.md#common-pitfalls-to-avoid)

### "I need to add a new feature"
1. Plan: [Project Roadmap](project/roadmap.md)
2. Design: [Rendering System Architecture](architecture/rendering-system.md) (relevant section)
3. Patterns: [Architecture Patterns](architecture/patterns.md)
4. Implement: Follow coding standards in [development/coding-standards.md](development/coding-standards.md)

---

## 📁 Files by Category

### Architecture Documents
- [architecture/overview.md](architecture/overview.md) - High-level system overview
- [architecture/layers.md](architecture/layers.md) - System layers and separation of concerns
- [architecture/patterns.md](architecture/patterns.md) - Design patterns used
- **[architecture/rendering-system.md](architecture/rendering-system.md)** - **Complete rendering system** ⭐

### Domain/Feature Documents
- [domain/animations.md](domain/animations.md) - Animation types and behaviors
- [domain/zones.md](domain/zones.md) - Zone configuration and management
- [domain/colors.md](domain/colors.md) - Color spaces and conversion

### Technical Documents
- [technical/hardware.md](technical/hardware.md) - Hardware details and constraints
- [technical/gpio.md](technical/gpio.md) - GPIO configuration
- [technical/performance.md](technical/performance.md) - Performance metrics

### Project Management
- **[project/todo.md](project/todo.md)** - **Current tasks and status** ⭐
- [project/changelog.md](project/changelog.md) - Version history
- [project/roadmap.md](project/roadmap.md) - Feature roadmap
- **[project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md)** - **Frame-by-frame spec** ⭐
- **[project/frame-by-frame-summary.md](project/frame-by-frame-summary.md)** - **Frame-by-frame analysis** ⭐
- **[project/ANALYSIS_COMPLETE.md](project/ANALYSIS_COMPLETE.md)** - **Session summary** ⭐

### Development Guides
- [development/setup.md](development/setup.md) - Development environment setup
- [development/coding-standards.md](development/coding-standards.md) - Code style and patterns
- [development/testing.md](development/testing.md) - Testing strategy
- **[development/frame-by-frame-guide.md](development/frame-by-frame-guide.md)** - **Quick reference** ⭐
- [development/agent-guide.md](development/agent-guide.md) - Agent workflow guide

### Issue Tracking
- [remaining-animation-issues.md](remaining-animation-issues.md) - Animation system issues
- [parallel-rendering-issue.md](parallel-rendering-issue.md) - Phase 4 parallel rendering fix
- [devtest-failures.md](devtest-failures.md) - Development test failures

### Keyboard Input
- [KEYBOARD_INPUT_SUMMARY.md](KEYBOARD_INPUT_SUMMARY.md) - Keyboard input system details

### Legacy/Reorganization
- [ANIMATION_RENDERING_SYSTEM.md](ANIMATION_RENDERING_SYSTEM.md) - Old rendering system docs
- [ANIMATIONS_REFACTORING.md](ANIMATIONS_REFACTORING.md) - Refactoring notes
- [ANIMATION_REFACTORING_PROGRESS.md](ANIMATION_REFACTORING_PROGRESS.md) - Progress tracking
- [BRANCHING.md](BRANCHING.md) - Git branching strategy
- [ARCHITECTURE.md](ARCHITECTURE.md) - Old architecture notes

---

## 📚 Organized by Reading Level

### 5-Minute Overview
- [Frame-By-Frame Quick Reference](development/frame-by-frame-guide.md#30-second-overview)
- [Project TODO - Task Summary](project/todo.md#phase-5---frame-by-frame-mode-current)
- [ANALYSIS_COMPLETE - Summary](project/ANALYSIS_COMPLETE.md#session-summary)

### 30-Minute Deep Dive
- [Frame-By-Frame Quick Reference](development/frame-by-frame-guide.md) (entire)
- [Rendering System - Overview](architecture/rendering-system.md#1-system-overview)
- [Rendering System - Layers](architecture/rendering-system.md#2-hardware-layer)

### 1-Hour Understanding
- [Rendering System Architecture](architecture/rendering-system.md) (sections 1-7)
- [Frame-By-Frame Summary](project/frame-by-frame-summary.md)
- [Project TODO](project/todo.md)

### Complete Specification (2+ hours)
- [Frame-By-Frame Implementation](project/frame-by-frame-implementation.md) (full)
- [Rendering System Architecture](architecture/rendering-system.md) (full)
- [Architecture Patterns](architecture/patterns.md)
- [Coding Standards](development/coding-standards.md)

---

## 🔍 Find Documents by Content

### Frame-By-Frame Mode
- **Specification**: [project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md)
- **Summary**: [project/frame-by-frame-summary.md](project/frame-by-frame-summary.md)
- **Quick Ref**: [development/frame-by-frame-guide.md](development/frame-by-frame-guide.md)
- **Analysis**: [project/ANALYSIS_COMPLETE.md](project/ANALYSIS_COMPLETE.md)

### LED Rendering System
- **Complete**: [architecture/rendering-system.md](architecture/rendering-system.md)
- **Hardware**: [technical/hardware.md](technical/hardware.md)
- **Performance**: [technical/performance.md](technical/performance.md)
- **Old Docs**: [ANIMATION_RENDERING_SYSTEM.md](ANIMATION_RENDERING_SYSTEM.md)

### Animation System
- **Domain**: [domain/animations.md](domain/animations.md)
- **Architecture**: [architecture/rendering-system.md#5-animation-system](architecture/rendering-system.md#5-animation-system)
- **Issues**: [remaining-animation-issues.md](remaining-animation-issues.md)
- **Old Docs**: [ANIMATIONS_REFACTORING.md](ANIMATIONS_REFACTORING.md)

### Zone Management
- **Domain**: [domain/zones.md](domain/zones.md)
- **Hardware**: [technical/hardware.md](technical/hardware.md)
- **Configuration**: [development/setup.md](development/setup.md)

### Color Management
- **Domain**: [domain/colors.md](domain/colors.md)
- **System**: [architecture/rendering-system.md#8-color-management](architecture/rendering-system.md#8-color-management)

### Project Status & Planning
- **Current Status**: [project/todo.md](project/todo.md)
- **Roadmap**: [project/roadmap.md](project/roadmap.md)
- **Changelog**: [project/changelog.md](project/changelog.md)

### Development Information
- **Setup**: [development/setup.md](development/setup.md)
- **Standards**: [development/coding-standards.md](development/coding-standards.md)
- **Testing**: [development/testing.md](development/testing.md)
- **Agents**: [development/agent-guide.md](development/agent-guide.md)

### Issue Tracking
- **All Issues**: [project/todo.md#bugs--issues-tracker](project/todo.md#bugs--issues-tracker)
- **Animation Issues**: [remaining-animation-issues.md](remaining-animation-issues.md)
- **Rendering Issues**: [parallel-rendering-issue.md](parallel-rendering-issue.md)

---

## 🏆 Most Important Documents (★★★★★)

Read these first when starting work:

1. **[development/frame-by-frame-guide.md](development/frame-by-frame-guide.md)** ⭐⭐⭐⭐⭐
   - Quick 30-second overview
   - Bug fixes with exact code
   - Implementation checklist
   - API reference
   - Common patterns and pitfalls

2. **[project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md)** ⭐⭐⭐⭐⭐
   - Complete feature specification
   - Class design with method signatures
   - Code templates
   - Integration points
   - Testing strategy

3. **[architecture/rendering-system.md](architecture/rendering-system.md)** ⭐⭐⭐⭐⭐
   - System architecture (all layers)
   - Frame models and priority system
   - FrameManager details
   - Animation system
   - Hardware constraints
   - Data flow examples

4. **[project/todo.md](project/todo.md)** ⭐⭐⭐⭐
   - Current project status
   - All active tasks
   - Bug tracker
   - Known issues
   - Roadmap

5. **[project/ANALYSIS_COMPLETE.md](project/ANALYSIS_COMPLETE.md)** ⭐⭐⭐
   - Session summary
   - What was completed
   - Architecture insights
   - Readiness assessment
   - How to use documents

---

## 📖 Recommended Reading Order by Role

### For Implementation Agent (Python/Coding)
1. [development/frame-by-frame-guide.md](development/frame-by-frame-guide.md) - 30 min
2. [project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md) - 60 min
3. [architecture/rendering-system.md](architecture/rendering-system.md) (sections 3-5) - 30 min
4. [development/coding-standards.md](development/coding-standards.md) - 15 min

### For Architecture Review
1. [architecture/rendering-system.md](architecture/rendering-system.md) (all) - 60 min
2. [architecture/patterns.md](architecture/patterns.md) - 20 min
3. [project/frame-by-frame-summary.md](project/frame-by-frame-summary.md) - 30 min
4. [technical/performance.md](technical/performance.md) - 15 min

### For Hardware/GPIO Specialist
1. [technical/hardware.md](technical/hardware.md) - 30 min
2. [technical/gpio.md](technical/gpio.md) - 20 min
3. [architecture/rendering-system.md](architecture/rendering-system.md) (sections 2, 11) - 30 min
4. [technical/performance.md](technical/performance.md) - 15 min

### For Debugging/QA
1. [project/todo.md](project/todo.md) (bug section) - 20 min
2. [remaining-animation-issues.md](remaining-animation-issues.md) - 20 min
3. [architecture/rendering-system.md](architecture/rendering-system.md) - 60 min
4. [development/testing.md](development/testing.md) - 20 min

---

## 🚀 Getting Started Checklist

### Before Implementation
- [ ] Read: [development/frame-by-frame-guide.md](development/frame-by-frame-guide.md)
- [ ] Read: [project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md)
- [ ] Check: [project/todo.md](project/todo.md#critical-must-fix) for blocking bugs
- [ ] Understand: [architecture/rendering-system.md](architecture/rendering-system.md) sections 3-5

### Before Testing
- [ ] Review: [project/frame-by-frame-guide.md](development/frame-by-frame-guide.md#testing-quick-start)
- [ ] Plan: Tests from [project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md#12-testing-strategy)
- [ ] Verify: Bug fixes applied

### Before Integration
- [ ] Check: Integration points in [project/frame-by-frame-implementation.md](project/frame-by-frame-implementation.md#5-integration-points)
- [ ] Review: [development/coding-standards.md](development/coding-standards.md)
- [ ] Validate: All unit tests pass

---

## 📝 How to Use This Index

**Search by task**: Look in "Quick Navigation by Task" section
**Search by topic**: Look in "Organized by Content" section
**Browse by importance**: Check "Most Important Documents" section
**Need specific info**: Use "Find Documents by Content" table

---

## 🔗 Important Links in Project Root

- **Main Config**: `.claude/CLAUDE.md`
- **Agent Definitions**: `.claude/agents/`
- **All Context**: `.claude/context/` (this directory)

---

## 📊 Documentation Statistics

- **Total Context Files**: 25+
- **Total Lines**: 9,744 (this session)
- **Architecture Docs**: 3 files
- **Implementation Specs**: 2 files
- **Project Management**: 4 files
- **Development Guides**: 4 files
- **Technical Docs**: 3 files
- **Domain Docs**: 3 files
- **Issue Tracking**: 3 files
- **Legacy/Old**: 5+ files

---

## 💡 Pro Tips

1. **Use Ctrl+F** to search within documents
2. **Bookmark quick reference** [development/frame-by-frame-guide.md](development/frame-by-frame-guide.md) for implementation
3. **Pin architecture** [architecture/rendering-system.md](architecture/rendering-system.md) for reference
4. **Check TODO** [project/todo.md](project/todo.md) daily for latest status
5. **Read summary** [project/ANALYSIS_COMPLETE.md](project/ANALYSIS_COMPLETE.md) to understand session context

---

**Last Updated**: 2025-11-15
**Maintained By**: @architecture-expert-sonnet
**Status**: Complete and up-to-date

