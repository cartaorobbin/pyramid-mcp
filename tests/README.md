# Tests Documentation

This document describes the test organization and structure for the pyramid-mcp project.

## Test File Organization

The test suite uses **pytest** with a clear, organized file structure that separates concerns by test type and domain.

### Organized Test Structure (258 tests, consolidated organization)

```
tests/
├── conftest.py                     # Comprehensive fixtures (16+ fixtures)
├── README.md                       # This documentation
│
├── unit/                           # Unit tests (isolated component testing)
│   ├── test_core.py               # Core functionality + configuration features (31 tests)
│   ├── test_protocol.py           # MCP protocol + tool name validation (35 tests) 
│   ├── test_introspection.py      # Route discovery + MCP description feature (28 tests)
│   └── test_security.py          # Consolidated security unit tests (49 tests)
│
├── integration/                    # Integration tests (component interaction)
│   ├── test_webtest.py           # HTTP/WebTest integration (20 tests)
│   ├── test_plugin.py            # Plugin integration (15 tests)
│   ├── test_auth.py              # Authentication integration (7 tests)
│   ├── test_end_to_end.py        # Complex end-to-end scenarios (7 tests)
│   └── test_transport.py         # stdio/Docker transport + pyramid_tm (9 tests)
│
├── client/                        # Client simulation tests
│   └── test_mcp_client.py        # MCP client simulation (20 tests)
│
└── cornice/                       # Cornice-specific tests (specialized fixtures)
    ├── conftest.py               # Cornice-specific fixtures & security policy
    ├── test_integration.py       # Consolidated Cornice tests (25 tests)
    └── test_security.py          # Cornice security tests (6 tests)
```

### Benefits of New Organization

✅ **Clear Separation of Concerns**: Unit tests focus on individual components, integration tests on interactions
✅ **Domain Grouping**: Related functionality is co-located (all security tests together)
✅ **Reduced Duplication**: Consolidated from 22 files to 11 files while maintaining all tests
✅ **Better Discoverability**: Developers know exactly where to find and add tests
✅ **Consistent Naming**: Clear, predictable naming convention
✅ **Specialized Support**: Cornice tests kept separate with their own fixtures

## Test Categories

### 🧪 Unit Tests (`unit/`)
Test individual components in isolation:

- **`test_core.py`**: Package imports, MCPConfiguration, PyramidMCP class, security parameter configuration
- **`test_protocol.py`**: MCPProtocolHandler, JSON-RPC message handling, tool registration, tool name validation
- **`test_introspection.py`**: Route discovery, tool generation, pattern matching, MCP description feature
- **`test_security.py`**: Authentication schemas, credential handling, security utilities, unified security architecture

### 🔗 Integration Tests (`integration/`)
Test component interactions and workflows:

- **`test_webtest.py`**: HTTP MCP endpoints, Pyramid+MCP integration via WebTest
- **`test_plugin.py`**: Plugin functionality, includeme, settings parsing, tool decorators
- **`test_auth.py`**: JWT authentication between MCP server and Pyramid security
- **`test_end_to_end.py`**: Complex scenarios, real route calling, multi-step workflows
- **`test_transport.py`**: stdio transport with Docker, pyramid_tm integration, transaction sharing

### 👥 Client Tests (`client/`)
Test external MCP client simulation:

- **`test_mcp_client.py`**: Complete MCP client workflows, protocol compliance, tool calling

### 🌐 Cornice Tests (`cornice/`)
Test Cornice-specific functionality (separate due to specialized requirements):

- **`conftest.py`**: Specialized fixtures including SimpleSecurityPolicy and pyramid_app_with_services
- **`test_integration.py`**: Cornice service discovery, Marshmallow schema integration, tool generation
- **`test_security.py`**: Cornice-specific authentication, Bearer token integration, secure services

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

### Global Pyramid Fixture (CRITICAL)
- `pyramid_app_with_auth` - **Main pyramid setup used by all test files**
  - Takes settings as parameter
  - Creates Pyramid Configurator with provided settings
  - Sets up security policy and authentication
  - Includes pyramid_mcp
  - Runs config.scan() to register @tool decorated functions
  - Returns configured TestApp

## Running Tests

```bash
# Run all tests
make test

# Run specific categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/client/            # Client simulation tests
pytest tests/cornice/           # Cornice-specific tests

# Run specific domains
pytest tests/unit/test_security.py          # All security unit tests
pytest tests/integration/test_auth.py       # Authentication integration
pytest tests/cornice/test_security.py       # Cornice security tests

# Run with coverage
pytest --cov

# Run across environments
tox
```

## Contributing

When adding new tests:

1. **Choose the Right Directory**: Use the directory that matches your test's scope and domain
2. **Use Existing Fixtures**: Leverage the comprehensive fixture system in `conftest.py`
3. **Follow Naming Conventions**: Use descriptive test names starting with `test_`
4. **Add Documentation**: Include docstrings explaining what your test validates
5. **Run Tests Locally**: Ensure all tests pass before submitting

### Test File Selection Guide

- **Unit tests for individual components** → `unit/test_*.py`
- **Integration tests for component interactions** → `integration/test_*.py`
- **Client simulation and workflow tests** → `client/test_*.py`
- **Cornice-specific functionality** → `cornice/test_*.py`

### Adding New Fixtures

If you need new fixtures:

1. Add them to the appropriate `conftest.py` (main or cornice)
2. Follow the existing categorization (🏗️ Pyramid, ⚙️ MCP Config, etc.)
3. Include comprehensive docstrings
4. Consider parameterization for flexible testing
5. Document usage patterns in this README

## Clean Test Pattern for Pyramid-MCP

### Single Fixture Pattern (CRITICAL)

**Always use the global `pyramid_app_with_auth` fixture** for creating TestApps:

```python
def test_my_functionality(pyramid_app_with_auth):
    """Test using the global pyramid fixture."""
    settings = {
        "mcp.server_name": "my-test-server",
        "mcp.route_discovery.enabled": True,
    }
    
    app = pyramid_app_with_auth(settings)
    # Test your functionality
```

### Module-Level Tools Pattern

**Define @tool functions at module level** so they can be discovered by config.scan():

```python
from pyramid_mcp import tool

@tool(name="my_test_tool", description="Tool for testing")
def my_test_tool(param: str) -> str:
    return f"Result: {param}"

def test_my_tool(pyramid_app_with_auth):
    """Test will automatically discover my_test_tool."""
    app = pyramid_app_with_auth({"mcp.route_discovery.enabled": True})
    # Tool is automatically available
```

## Migration from Old Structure

The test suite was reorganized from 22 files to 11 files:

### Consolidation Mapping

| **New File** | **Consolidated From** | **Tests** | **Benefit** |
|-------------|---------------------|-----------|-------------|
| `unit/test_core.py` | `test_unit_core.py` + `test_configurable_security_parameter.py` | 31 tests | All core functionality together |
| `unit/test_protocol.py` | `test_unit_protocol.py` + `test_tool_name_validation.py` | 35 tests | All protocol functionality together |
| `unit/test_introspection.py` | `test_unit_introspection.py` + `test_mcp_description_feature.py` | 28 tests | All introspection features together |
| `unit/test_security.py` | 5 security files | 49 tests | Single security test location |
| `integration/test_transport.py` | `test_stdio_transport.py` + `test_pyramid_tm_integration.py` | 9 tests | All transport mechanisms together |
| `cornice/test_integration.py` | `test_unit_cornice_integration.py` + simple cornice tests | 25 tests | All Cornice functionality together |

### Benefits of New Structure

- **✅ 50% Reduction in Files**: From 22 files to 11 files
- **✅ Clear Organization**: Each file has a specific, non-overlapping purpose
- **✅ No Duplication**: All setup handled by reusable fixtures
- **✅ Better Maintainability**: Easy to add tests without copying code
- **✅ Preserved Functionality**: All existing tests maintained and passing
- **✅ Improved Developer Experience**: New developers can easily understand structure
- **✅ Efficient Testing**: Faster test development with comprehensive fixtures
- **✅ Specialized Support**: Cornice tests kept separate with specialized fixtures

---

This test infrastructure provides a solid foundation for maintaining and extending the pyramid-mcp project with confidence and clarity. 