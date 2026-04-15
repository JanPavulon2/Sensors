---
name: documentation-writer
description: Creates and maintains project documentation for the Aurora LED control system. Handles module documentation, architecture overviews, API references, and user guides.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [documentation, technical-writing, aurora]
    related_skills: [writing-plans, requesting-code-review]
---
# Documentation Writer Skill

## Overview

This skill enables the Hermes Agent to act as a documentation specialist for the Aurora project. It handles:

1. **Module Documentation**: Creating and updating hardware module files following the `{Module code} ({english desc}).md` format
2. **Architecture Documentation**: Maintaining system overviews, data flow diagrams, and component relationships
3. **API References**: Documenting endpoints, events, and configuration options
4. **User Guides**: Creating setup instructions, usage examples, and troubleshooting guides
5. **Media Management**: Organizing photos and diagrams in `vault/_media/moduły/{MODULE-CODE}/`

## When to Use

Use this skill when:
- Adding new hardware modules or sensors
- Making architectural changes that need documentation
- Creating or updating user-facing documentation
- Organizing media assets for modules
- Ensuring documentation conventions are followed

## Documentation Conventions

### Module Files
- Location: `vault/_media/moduły/{MODULE-CODE}/`
- Filename: `{Module code} ({english desc}).md`
- Language: English by default, Polish only in parentheses for clarification
- Must include: module purpose, pinout, wiring diagram, usage example, and any quirks

### Media Organization
- Photos: `vault/_media/moduły/{MODULE-CODE}/photo1.jpg`, `photo2.png`, etc.
- Diagrams: SVG or PNG formats preferred
- Always reference media from module documentation using relative paths

### Structure of Module Documentation
```markdown
# {MODULE-CODE} ({English Description})

## Purpose
Brief description of what the module does and its role in the Aurora system.

## Pinout / Connections
- Pin 1: Description
- Pin 2: Description
*(Include wiring diagram if complex)*

## Usage Example
Code snippet showing how to initialize and use the module in Aurora.

## Notes / Quirks
Any special considerations, timing requirements, or known issues.

## Photos
![Module photo](./photo1.jpg)
```

## Execution Pattern

When activated, this skill will:
1. Save itself as the current documentation approach
2. Prompt for what needs documentation (new module, architecture update, etc.)
3. Gather necessary context about the subject
4. Create or update documentation following conventions
5. Organize any associated media
6. Verify completeness and clarity
7. Conclude with summary and next steps

## Success Metrics

Documentation is successful when:
- Follows established naming and formatting conventions
- Contains all necessary information for someone to understand and use the module
- Includes proper media references
- Is clear, concise, and free of errors
- Integrates well with existing documentation