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

1. **Architecture Documentation**: Maintaining system overviews, data flow diagrams, and component relationships
2. **API References**: Documenting endpoints, events, and configuration options
3. **Domain Documentation**: Documenting models, enums, classes
4. **User Guides**: Creating setup instructions, usage examples, and troubleshooting guides

## When to Use

Use this skill when:
- Making architectural changes that need documentation
- Creating or updating user-facing documentation
- Ensuring documentation conventions are followed

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