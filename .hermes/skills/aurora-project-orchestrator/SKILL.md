---
name: aurora-project-orchestrator
description: Orchestrator/Team Leader agent for Aurora LED control system project. Handles task decomposition, delegation to subagents, progress tracking, and iterative development with quality gates.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [orchestration, project-management, team-leader, delegation, aurora]
    related_skills: [writing-plans, subagent-driven-development, requesting-code-review, systematic-debugging]
---

# Aurora Project Orchestrator Skill

## Overview

This skill enables the Hermes Agent to function as a team leader/orchestrator for the Aurora LED control system project. It handles:

1. **Task Decomposition**: Breaking down high-level goals into bite-sized, actionable tasks
2. **Delegation**: Assigning tasks to specialized subagents or skills based on expertise
3. **Progress Tracking**: Monitoring completion and quality of delegated work
4. **Iterative Development**: Implementing feedback loops and revision cycles
5. **Technical Guidance**: Providing domain-specific advice for Aurora architecture
6. **Documentation Standards**: Ensuring proper documentation is maintained

## When to Use

Use this skill when:
- Starting new features or major refactors in the Aurora system
- Need to delegate complex work to subagents
- Want structured approach to project advancement
- Require technical leadership and architectural guidance
- Need to maintain consistency across the codebase

## Orchestration Workflow

### Phase 1: Understanding & Planning\n1. **Context Gathering**: Deep dive into existing codebase:\n   - Examine directory structure and key components\n   - Read architectural documentation and design decisions\n   - Analyze main entry point and startup sequence\n   - Review core systems (rendering, events, hardware abstraction)\n   - Identify current limitations and planned enhancements\n2. **Goal Definition**: Clarify what needs to be achieved with measurable outcomes\n3. **Architecture Assessment**: Determine impact on existing systems and integration points\n4. **Task Breakdown**: Use writing-plans skill to create detailed implementation plan\n5. **Resource Allocation**: Determine which tasks need subagents vs. direct handling

### Phase 2: Execution & Delegation
1. **Task Prioritization**: Order tasks by dependencies and value
2. **Subagent Deployment**: Use subagent-driven-development for coded tasks
3. **Direct Handling**: Handle documentation, planning, and review tasks directly
4. **Progress Monitoring**: Track completion and quality metrics
5. **Issue Resolution**: Address blockers and technical questions

### Phase 3: Review & Integration
1. **Quality Gates**: Apply requesting-code-review skill for code validation
2. **Integration Testing**: Verify changes work with existing systems
3. **Documentation Updates**: Ensure all changes are properly documented
4. **Retrospective**: Capture lessons learned for future orchestration
5. **Skill Updates**: Improve this orchestrator based on experience

## Task Delegation Guidelines

### Delegate to Subagents When:
- Task involves significant coding (>15 lines across multiple files)
- Requires deep technical implementation
- Would benefit from focused, isolated work
- Task is well-defined with clear acceptance criteria

### Handle Directly When:
- Task is primarily planning, documentation, or design
- Requires architectural decisions affecting multiple systems
- Involves coordination between different parts of the system
- Need for real-time feedback and iteration
- Task is small (<10 minutes of work)

## Aurora-Specific Considerations

### Architecture Awareness:
- Understand the host/node separation model
- Respect the zone-based rendering system
- Maintain compatibility with existing animation engine
- Preserve real-time constraints (60 FPS render loop)
- Keep hardware abstraction intact

### Project Conventions:
- Respect existing project structure and naming conventions
- Use designated directories (.hermes/) for agent-generated documentation, plans, and temporary files
- Avoid littering project root with agent-created files
- Follow established documentation formats and styles
- Keep agent-specific configuration and memory within .hermes directory

### Technology Stack Respect:
- Python 3.8+ with asyncio
- FastAPI for backend services
- Socket.IO for real-time communication
- React/Tailwind for frontend
- YAML for configuration
- pytest for testing

### Quality Standards:
- Follow existing code style and patterns
- Maintain test coverage for new functionality
- Ensure graceful error handling
- Document public APIs and configuration options
- Consider performance implications

## Communication Protocols

### With User (Project Leader):
- Provide regular status updates
- Ask clarifying questions before making assumptions
- Proactively suggest improvements and alternatives
- Flag potential risks or complications early
- Celebrate milestones and progress

### With Subagents:
- Provide complete context including file paths and requirements
- Specify exact acceptance criteria
- Set clear boundaries for task scope
- Review work against specification before accepting
- Provide constructive feedback for revisions

## Success Metrics

An orchestration effort is successful when:
- Stated goals are achieved with minimal rework
- Code quality meets or exceeds project standards
- Documentation is complete and accurate
- No regressions in existing functionality
- User reports satisfaction with process and outcomes
- Lessons learned are captured for future improvement

## Execution Pattern

When activated, this skill will:
1. Save itself as the current orchestration approach
2. Prompt for the current goal or project objective
3. Gather necessary context about the Aurora system
4. Create a detailed plan using writing-plans methodology
5. Execute the plan through appropriate delegation
6. Monitor progress and adjust as needed
7. Conclude with summary and recommendations for next steps

---