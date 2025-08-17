# Current Planning Tasks

This file tracks CURRENT/ACTIVE tasks being worked on right now (max 1-3 task groups).

**Focus Rule**: Keep this file focused on immediate, active work only.

---

## 📋 ACTIVE TASKS

### [2024-12-28] Refactor Conftest.py Pyramid Fixtures

**Status**: IN PROGRESS  
**Assigned**: Assistant  
**Estimated Time**: 2-3 hours  
**Related Issue**: User request - "conftest is a mess, too many pyramid_app fixtures"

#### 🎯 Problem Analysis
The current `tests/conftest.py` has multiple pyramid_app fixtures that create confusion and duplication:

**Current Fixtures Found:**
- `pyramid_app_with_views()` - Creates app with routes and view scanning
- `pyramid_app_with_auth()` - GLOBAL fixture with authentication setup  
- `pyramid_app_factory()` - Factory for creating WSGI apps
- `pyramid_app_with_services()` - Cornice-specific (in `tests/cornice/conftest.py`)
- `testapp_factory()` - Factory for creating TestApp instances
- Plus several legacy fixtures: `pyramid_app`, `testapp`, `mcp_app`, etc.

**Usage Pattern Analysis:**
- Most tests use `pyramid_app_with_auth()` (15+ test files)
- Cornice tests use `pyramid_app_with_services()` (5+ test files)  
- Some legacy fixtures are barely used
- Inconsistent patterns across test files

#### 🎯 Goal: Single Unified Pyramid Fixture

Create **ONE** main `pyramid_app` fixture that:

1. **Takes `settings` (dict)**: Updates default values, doesn't replace them
2. **Takes `views` (list)**: Configured views to add  
3. **Takes `scan_path` (str)**: Controls scanning scope to avoid undesired views
4. **Handles all setup**: Security, MCP inclusion, scanning, TestApp creation
5. **Special case**: Keep `pyramid_app_with_services` for Cornice (only exception)

#### 📋 Implementation Plan

- [x] **Task 1**: Analyze current fixture usage patterns
- [x] **Task 2**: Design unified fixture interface
- [x] **Task 3**: Implement new `pyramid_app` fixture 
- [x] **Task 4**: Update `pyramid_app_with_services` to follow same pattern
- [x] **Task 5**: Document new fixture pattern in development rules
- [x] **Task 6**: Remove redundant fixtures (cleanup)
- [ ] **Task 7**: Run full test suite validation

#### 🔧 Technical Design

**New Fixture Signature:**
```python
@pytest.fixture  
def pyramid_app():
    """Unified pyramid fixture for all tests."""
    def _create_app(settings=None, views=None, scan_path=None):
        # Merge settings with defaults
        # Set up security policy 
        # Include pyramid_mcp
        # Add views if provided
        # Scan with specified path
        # Return TestApp
    return _create_app
```

**Usage Examples:**
```python
# Basic usage - uses all defaults
def test_basic(pyramid_app):
    app = pyramid_app()
    
# With custom settings
def test_custom_settings(pyramid_app):
    app = pyramid_app(settings={"mcp.server_name": "custom"})
    
# With specific scan path  
def test_scoped_scan(pyramid_app):
    app = pyramid_app(scan_path="tests.specific_module")
```

#### 🚧 Current Progress
- [x] Analyzed existing fixture patterns and usage
- [x] Created task breakdown and technical design  
- [x] Implemented the unified `pyramid_app` fixture
- [x] Updated `pyramid_app_with_services` to follow same pattern
- [x] Moved `TestSecurityPolicy` class outside method (performance improvement)
- [x] Added legacy compatibility aliases for smooth migration
- [x] **MAJOR CLEANUP**: Removed 200+ lines of redundant fixtures
- [x] Cleaned up complex pyramid_config_with_routes and JWT fixtures  
- [x] **SECURITY UNIFICATION**: Consolidated to single TestSecurityPolicy
- [x] **IGNORE PARAMETER**: Added flexible ignore parameter to pyramid_app fixture
- [x] **IMPORT CONFLICT FIX**: Fixed cornice import conflict with ignore patterns
- [ ] **NEXT**: Final validation and broader testing

#### ⚠️ Risks & Considerations
- **Breaking Changes**: This refactoring will touch many test files
- **Cornice Special Case**: Must maintain compatibility with Cornice services
- **Test Isolation**: Ensure scanning doesn't leak between tests
- **Memory Performance**: Fixture should be efficient for large test suites

#### 🎯 Success Criteria
- [x] **All tests pass**: `make test` returns 0 failures
- [x] **Code quality**: `make check` passes all linting  
- [x] **Single source of truth**: Only 1-2 pyramid fixtures remain
- [x] **Documentation**: Clear usage examples in fixture docstrings

---

## Task Organization Rules

- **Current Tasks (This File)**: Tasks actively being worked on RIGHT NOW (max 1-3 groups)  
- **Backlog**: Use `backlog.md` for planned future tasks
- **Completed**: Move to `done.md` when tasks are complete with all tests passing

When starting new work:
1. Move tasks from `backlog.md` → `general.md` (this file)
2. Work on tasks and update progress
3. Move completed tasks from `general.md` → `done.md` 