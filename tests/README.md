# Tests Documentation

This document describes the test organization and structure for the pyramid-mcp project.

## Test File Organization

The test suite uses **pytest** with a clear file organization pattern:

### Current Test Structure (94 tests, 76% coverage)

```
tests/
├── conftest.py                     # Comprehensive fixtures (16+ fixtures)
├── test_unit_core.py               # Core functionality unit tests (15 tests)
├── test_unit_protocol.py           # MCP protocol unit tests (16 tests)
├── test_unit_introspection.py      # Route discovery unit tests (21 tests)
├── test_integration_webtest.py     # HTTP integration tests (20 tests)
├── test_integration_plugin.py      # Plugin integration tests (15 tests)
├── test_integration_end_to_end.py  # End-to-end tests (7 tests)
└── __init__.py                     # Empty init file
```

### File Purposes

- **`test_unit_core.py`**: Package imports, MCP configuration, PyramidMCP class functionality
- **`test_unit_protocol.py`**: MCP protocol handlers, tool registration, JSON-RPC handling
- **`test_unit_introspection.py`**: Route discovery, tool generation, pattern matching, schema generation
- **`test_integration_webtest.py`**: HTTP MCP endpoints, Pyramid+MCP integration via WebTest
- **`test_integration_plugin.py`**: Plugin functionality, includeme, settings parsing, tool decorators
- **`test_integration_end_to_end.py`**: Complex scenarios, real route calling, multi-step workflows

## Fixture System

Comprehensive fixture system in `conftest.py` organized by category:

### Core Pyramid Fixtures
- `minimal_pyramid_config` - Basic Configurator setup
- `pyramid_config_with_routes` - Config with test routes
- `pyramid_config_committed` - Pre-committed config for introspection
- `pyramid_app_factory` - Factory for WSGI apps

### MCP Configuration Fixtures  
- `minimal_mcp_config` - Basic MCPConfiguration
- `custom_mcp_config` - Parameterized MCP settings
- `mcp_config_with_patterns` - Config with include/exclude patterns
- `mcp_settings_factory` - Settings dictionary factory

### Integration Fixtures
- `pyramid_mcp_basic` - PyramidMCP with minimal config
- `pyramid_mcp_configured` - PyramidMCP with custom config
- `protocol_handler` - Standalone MCP protocol handler

### WebTest Fixtures
- `testapp_basic` - TestApp without MCP
- `testapp_with_mcp` - TestApp with MCP mounted
- `testapp_custom_mount` - TestApp with custom mount path
- `testapp_factory` - Factory for TestApp instances

### Test Data Fixtures
- `sample_tools` - Collection of test MCP tools
- `test_route_scenarios` - Various route configurations

## Running Tests

```bash
# Run all tests
make test

# Run specific categories
pytest tests/test_unit_*.py           # Unit tests
pytest tests/test_integration_*.py    # Integration tests

# Run with coverage
pytest --cov

# Run across environments
tox
```

## Benefits of New Structure

- **Clear Organization**: Each file has specific purpose
- **No Duplication**: All setup via reusable fixtures  
- **Better Maintainability**: Easy to add tests without copying code
- **Preserved Functionality**: All existing tests maintained
- **Improved Developer Experience**: Easy to understand structure

## Migration from Old Structure

The test suite was migrated from 7 old test files to 6 new organized files:

### Old → New File Mapping

| **Old File** | **Tests** | **New File(s)** |
|-------------|-----------|------------------|
| `test_basic.py` | 14 tests | `test_unit_core.py` + `test_unit_protocol.py` |
| `test_integration.py` | 15 tests | `test_unit_core.py` + `test_integration_end_to_end.py` |
| `test_route_discovery.py` | 13 tests | `test_unit_introspection.py` |
| `test_route_discovery_webtest.py` | 2 tests | `test_integration_webtest.py` |
| `test_webtest_mcp.py` | 18 tests | `test_integration_webtest.py` |
| `test_plugin.py` | 9 tests | `test_integration_plugin.py` |
| `test_real_route_calling.py` | 2 tests | `test_integration_end_to_end.py` |

### Benefits of New Structure

- **✅ Clear Organization**: Each file has a specific, non-overlapping purpose
- **✅ No Duplication**: All setup handled by reusable fixtures
- **✅ Better Maintainability**: Easy to add tests without copying code
- **✅ Preserved Functionality**: All existing tests maintained and passing
- **✅ Improved Developer Experience**: New developers can easily understand structure
- **✅ Efficient Testing**: Faster test development with comprehensive fixtures

## Contributing

When adding new tests:

1. **Choose the Right File**: Use the file that matches your test's domain and scope
2. **Use Existing Fixtures**: Leverage the comprehensive fixture system in `conftest.py`
3. **Follow Naming Conventions**: Use descriptive test names starting with `test_`
4. **Add Documentation**: Include docstrings explaining what your test validates
5. **Run Tests Locally**: Ensure all tests pass before submitting

### Test File Selection Guide

- **Unit tests for core functionality** → `test_unit_core.py`
- **Unit tests for MCP protocol** → `test_unit_protocol.py`  
- **Unit tests for route discovery** → `test_unit_introspection.py`
- **HTTP integration tests** → `test_integration_webtest.py`
- **Plugin system tests** → `test_integration_plugin.py`
- **Complex end-to-end scenarios** → `test_integration_end_to_end.py`

### Adding New Fixtures

If you need new fixtures:

1. Add them to `conftest.py`
2. Follow the existing categorization (🏗️ Pyramid, ⚙️ MCP Config, etc.)
3. Include comprehensive docstrings
4. Consider parameterization for flexible testing
5. Document usage patterns in this README

---

This test infrastructure provides a solid foundation for maintaining and extending the pyramid-mcp project with confidence and clarity. 