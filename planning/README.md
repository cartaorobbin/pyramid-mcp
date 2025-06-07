# Planning Directory

This directory contains all project planning and task tracking files.

## File Organization

### `general.md`
- **Purpose**: Overall project tasks, infrastructure work, and cross-cutting concerns
- **Use for**: Project setup, CI/CD, general improvements, documentation updates
- **Examples**: Setting up development rules, dependency management, build system changes

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

- ✅ Quick fixes and small improvements
- ✅ Infrastructure and tooling updates
- ✅ Documentation-only changes
- ✅ Project-wide refactors

## File Naming Conventions

- Use kebab-case: `user-authentication.md`, `payment-integration.md`
- Be descriptive but concise
- Use nouns for features: `user-management.md` not `manage-users.md`
- Group related features: `api-v1.md`, `api-v2.md`

## Workflow

1. **Planning**: Create or update the appropriate planning file
2. **Development**: Update progress as you work
3. **Completion**: Mark tasks as DONE and update related files
4. **Archive**: Move completed tasks to Archive section to keep files clean

## Cross-References

- Always reference related GitHub issues: `#123`
- Link to related pull requests: `#456`
- Reference other planning files when features depend on each other
- Update `general.md` when completing major features

## Examples

```
planning/
├── README.md                 # This file
├── general.md               # General project tasks
├── feature-template.md      # Template for new features
├── user-authentication.md   # User auth feature planning
├── api-endpoints.md         # API development planning
├── database-migration.md    # Database changes planning
└── deployment-pipeline.md   # CI/CD planning
```

---

**Remember**: Always plan before coding! These files are living documents that should be updated throughout development. 