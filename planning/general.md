# Current Planning Tasks

This file tracks CURRENT/ACTIVE tasks being worked on right now (max 1-3 task groups).

**Focus Rule**: Keep this file focused on immediate, active work only.

---

## 📋 ACTIVE TASKS

### [2024-12-28] Refactor Tool Decorator to Use Cornice Services

**Status**: IN PROGRESS  
**Assigned**: Assistant  
**Estimated Time**: 3-4 hours  
**Related Issue**: User request - "refactor tool decorator to use cornice services and remove MCP metadata"

#### 🎯 Problem Analysis
Currently the `@tool` decorator has two different discovery paths in introspection:

1. **Cornice service discovery** (the clean path we want to keep) 
2. **MCP metadata discovery** (the `__mcp_tool_*` path we want to remove)

The decorator currently:
- Creates Pyramid views directly with `__mcp_tool_*` metadata attributes
- Uses separate metadata-based discovery path in introspection
- Lives in `core.py` instead of a dedicated file
- Accepts both GET and POST methods

#### 🎯 Goal: Unified Cornice-Only Discovery

Refactor the `@tool` decorator to:

1. **Move to `decorators.py`**: Extract from `core.py` for better organization
2. **Create Cornice services**: Instead of Pyramid views with metadata
3. **Auto-generate schemas**: From function signatures (no user-defined schemas)  
4. **POST-only endpoints**: Restrict to POST for schema validation
5. **Remove metadata discovery**: Eliminate `__mcp_tool_*` attributes completely
6. **Maintain error format**: Keep current `{"error": "...", "tool_name": "..."}` format
7. **Keep naming conventions**: `tool_{tool_name}` and `/mcp/tools/{tool_name}`

#### 📋 Implementation Plan

- [ ] **Task 1**: Create `pyramid_mcp/decorators.py` file
- [ ] **Task 2**: Move `tool` decorator class from `core.py` to `decorators.py`
- [ ] **Task 3**: Refactor decorator to create Cornice services instead of views
- [ ] **Task 4**: Implement auto-schema generation from function signatures
- [ ] **Task 5**: Remove all `__mcp_tool_*` metadata code from decorator
- [ ] **Task 6**: Remove metadata-based discovery path from `introspection.py`
- [ ] **Task 7**: Update imports in `__init__.py` to expose decorator from new location
- [ ] **Task 8**: Run tests and fix any issues with unified discovery

#### 🔧 Technical Design

**New Decorator Behavior:**
```python
# Before (creates view with metadata)
@tool(name="add", description="Add numbers")
def add_numbers(a: int, b: int) -> int:
    return a + b
# Creates: view with __mcp_tool_name__, __mcp_tool_description__, etc.

# After (creates Cornice service)  
@tool(name="add", description="Add numbers")
def add_numbers(a: int, b: int) -> int:
    return a + b
# Creates: Cornice service with auto-generated schema, POST-only
```

**Auto-Schema Generation:**
- Inspect function signature and type hints
- Generate JSON schema for request body validation
- Use `marshmallow_body_validator` pattern
- Support basic types: int, float, str, bool

**Discovery Path:**
- Remove: `if hasattr(view_callable, "__mcp_tool_name__"):` path
- Keep: Existing Cornice service discovery in introspection
- Tool decorators will be discovered as regular Cornice services

#### 🚧 Current Progress
- [ ] Analysis of current decorator implementation
- [ ] Identified removal targets in introspection code
- [ ] Planned new Cornice-based architecture

#### ⚠️ Risks & Considerations
- **Breaking Changes**: Tests expecting `__mcp_tool_*` metadata will break
- **Schema Complexity**: Auto-generation must handle various Python types  
- **Import Dependencies**: Need to ensure `cornice` is available in decorator module
- **Error Handling**: Must maintain current error response format

#### 🎯 Success Criteria
- [ ] **All tests pass**: `make test` returns 0 failures
- [ ] **Code quality**: `make check` passes all linting
- [ ] **Single discovery path**: Only Cornice service discovery remains
- [ ] **Decorator in decorators.py**: Clean file organization  
- [ ] **Auto-generated schemas**: No user-defined schemas required
- [ ] **POST-only tools**: Consistent with schema validation approach

---

### [2024-12-28] Filter Forbidden Tools Configuration

**Status**: IN PROGRESS  
**Assigned**: Assistant  
**Estimated Time**: 2-3 hours  
**Related Issue**: User request - "add configuration called filter_forbidden_tools"

#### 🎯 Problem Statement
Currently, the MCP `tools/list` method returns all discovered tools regardless of whether the current user has permission to access them. This can expose tools that users cannot actually use, leading to confusion and potential security concerns.

#### 🎯 Goal: Security-Aware Tool Filtering

Add a new configuration `mcp.filter_forbidden_tools` that:

1. **Enabled by default**: `True` - users only see accessible tools by default
2. **Permission-based filtering**: Check view permissions using Pyramid's security system
3. **Subrequest-based checks**: Create subrequests for accurate permission evaluation
4. **Configurable**: Can be disabled if needed to show all tools

#### 📋 Implementation Plan

- [x] **Task 1**: Document the plan in planning files (CURRENT)
- [ ] **Task 2**: Add `mcp.filter_forbidden_tools` configuration setting with default `True`
- [ ] **Task 3**: Implement permission checking logic using subrequests for each tool
- [ ] **Task 4**: Modify the tools/list handler to filter tools based on permissions
- [ ] **Task 5**: Add comprehensive tests for the new functionality
- [ ] **Task 6**: Update documentation to explain the new configuration

#### 🔧 Technical Design

**Configuration:**
- Setting: `mcp.filter_forbidden_tools = True` (default)
- Location: Pyramid settings, parsed in MCP configuration

**Permission Check Logic:**
```python
# For each tool in tools/list
for tool in discovered_tools:
    # Create subrequest to the tool's route
    subrequest = request.copy()
    subrequest.path = tool.route_path
    subrequest.method = 'POST'  # or tool's method
    
    # Get security policy and check permission
    policy = request.registry.queryUtility(ISecurityPolicy)
    if policy and policy.permits(subrequest, context, permission):
        # Include tool in list
        accessible_tools.append(tool)
```

**Filtering Implementation:**
- Modify `tools/list` method in protocol.py
- When `filter_forbidden_tools` is `True`, filter out inaccessible tools
- When `False`, return all tools (current behavior)

#### 🚧 Current Progress
- [x] **Planning**: Documented comprehensive plan in planning files
- [x] **Analysis**: Review current tools/list implementation
- [x] **Configuration**: Add new setting and parsing
- [x] **Permission Logic**: Implement subrequest-based permission checking
- [x] **Integration**: Modify tools/list to use filtering
- [x] **Variable Naming**: Renamed confusing request variables (mcp_request vs request)
- [ ] **Testing**: Add unit and integration tests

#### 📝 Technical Questions Resolved
1. ✅ **Configuration name**: `filter_forbidden_tools` (typo corrected)
2. ✅ **Applies to**: MCP `tools/list` method
3. ✅ **Permission source**: Pyramid view permissions (not @tool decorator)
4. ✅ **Context strategy**: Create subrequests for each tool
5. ✅ **Default behavior**: Enabled by default (`True`)
6. ✅ **Configuration type**: Pyramid setting `mcp.filter_forbidden_tools`

#### ⚠️ Implementation Considerations
- **Performance**: Subrequest creation for each tool - may need optimization for large tool sets
- **Fallback**: Handle cases where no security policy is configured
- **Error Handling**: Graceful handling of permission check failures
- **Backward Compatibility**: Default enabled may change behavior for existing users

#### 🎯 Success Criteria
- [ ] **Configuration works**: Setting properly parsed and controls filtering
- [ ] **Permission checks work**: Tools correctly filtered based on actual permissions
- [ ] **Default behavior**: Filtering enabled by default
- [ ] **All tests pass**: `make test` returns 0 failures  
- [ ] **Code quality**: `make check` passes all linting
- [ ] **Documentation updated**: New configuration explained in docs

---

## Task Organization Rules

- **Current Tasks (This File)**: Tasks actively being worked on RIGHT NOW (max 1-3 groups)  
- **Backlog**: Use `backlog.md` for planned future tasks
- **Completed**: Move to `done.md` when tasks are complete with all tests passing

When starting new work:
1. Move tasks from `backlog.md` → `general.md` (this file)
2. Work on tasks and update progress
3. Move completed tasks from `general.md` → `done.md` 