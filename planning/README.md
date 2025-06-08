# Planning Directory

This directory contains all project planning and task tracking files.

## File Organization

### `general.md`
- **Purpose**: **CURRENT/ACTIVE** tasks being worked on right now
- **Use for**: Tasks in active development, immediate work in progress
- **Examples**: Current Docker integration, active bug fixes, ongoing feature implementation
- **Status**: Only contains IN PROGRESS and immediate TODO tasks
- **Goal**: Keep focused and manageable (max 1-3 active task groups)

### `backlog.md`
- **Purpose**: **PLANNED** future tasks (product backlog)
- **Use for**: TODO tasks planned for future development, prioritized feature list
- **Examples**: Route discovery phases, PyPI publishing, planned enhancements
- **Status**: Organized by priority (HIGH/MEDIUM/LOW), ready to move to general.md
- **Goal**: Complete list of planned work with time estimates

### `done.md`
- **Purpose**: **COMPLETED** project tasks archive
- **Use for**: Historical record of finished work, implementation reference, progress tracking
- **Examples**: Completed test infrastructure, finished security features, deployed examples
- **Status**: Only contains DONE tasks from general.md, backlog.md, and feature files

### Feature-Specific Files
- **Pattern**: `[feature-name].md` (e.g., `user-authentication.md`, `api-endpoints.md`)
- **Purpose**: Dedicated planning for specific features or major components
- **Use for**: Feature development, major refactors, new functionality

### `feature-template.md`
- **Purpose**: Template for creating new feature planning files
- **Usage**: Copy this file to start planning a new feature

## When to Create a New Feature File

Create a new feature planning file when:

- ✅ Feature will take more than 1 day of work
- ✅ Feature involves multiple related tasks
- ✅ Feature requires coordination between team members
- ✅ Feature has complex requirements or dependencies
- ✅ Feature needs dedicated testing strategy

Use `general.md` for:

- ✅ Tasks currently being worked on
- ✅ Active development in progress
- ✅ Immediate priority work
- ✅ No more than 1-3 active task groups

Use `backlog.md` for:

- ✅ Planned future features
- ✅ TODO tasks not yet started
- ✅ Prioritized development pipeline
- ✅ Feature requirements and planning

## File Naming Conventions

- Use kebab-case: `user-authentication.md`, `payment-integration.md`
- Be descriptive but concise
- Use nouns for features: `user-management.md` not `manage-users.md`
- Group related features: `api-v1.md`, `api-v2.md`

## Workflow

1. **Planning**: Add new tasks to `backlog.md` with priority
2. **Active Work**: Move tasks from `backlog.md` to `general.md` when starting
3. **Development**: Update progress in `general.md` as you work
4. **Completion**: Move completed tasks from `general.md` to `done.md`
5. **Focus**: Keep `general.md` focused on only current active work

## Cross-References

- Always reference related GitHub issues: `#123`
- Link to related pull requests: `#456`
- Reference other planning files when features depend on each other
- Update `general.md` when completing major features

## Examples

```
planning/
├── README.md                 # This file
├── general.md               # CURRENT/ACTIVE tasks being worked on
├── backlog.md               # PLANNED future tasks (prioritized)
├── done.md                  # COMPLETED tasks archive
├── feature-template.md      # Template for new features
├── user-authentication.md   # User auth feature planning (if needed)
├── api-endpoints.md         # API development planning (if needed)
└── deployment-pipeline.md   # CI/CD planning (if needed)
```

---

**Remember**: Always plan before coding! These files are living documents that should be updated throughout development. 