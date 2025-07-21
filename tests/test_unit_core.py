"""
Unit tests for pyramid_mcp core functionality.

This module tests:
- Package imports and availability
- MCPConfiguration class functionality
- PyramidMCP class creation and basic functionality
- Core module integration

Uses enhanced fixtures from conftest.py for clean, non-duplicated test setup.
"""

from pyramid_mcp import PyramidMCP, __version__, tool
from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.protocol import MCPErrorCode, MCPProtocolHandler, MCPTool
from pyramid_mcp.schemas import MCPErrorSchema
from pyramid_mcp.wsgi import MCPWSGIApp

# =============================================================================
# 🧪 MODULE-LEVEL TOOLS FOR TESTING
# =============================================================================


@tool(name="unit_calculate", description="Unit test calculator")
def unit_calculate(operation: str, a: float, b: float) -> float:
    """Perform basic math operations."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


# =============================================================================
# 📦 PACKAGE IMPORT TESTS
# =============================================================================


def test_main_package_imports():
    """Test main package imports are available."""
    assert PyramidMCP is not None
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_protocol_imports():
    """Test protocol module imports are available."""
    assert MCPProtocolHandler is not None
    assert MCPTool is not None
    assert MCPErrorSchema is not None
    assert MCPErrorCode is not None


def test_core_imports():
    """Test core module imports are available."""
    assert MCPConfiguration is not None


def test_introspection_imports():
    """Test introspection module imports are available."""
    assert PyramidIntrospector is not None


def test_wsgi_imports():
    """Test WSGI module imports are available."""
    assert MCPWSGIApp is not None


# =============================================================================
# ⚙️ MCP CONFIGURATION TESTS
# =============================================================================


def test_default_configuration(minimal_mcp_config):
    """Test MCPConfiguration default values using minimal fixture."""
    config = minimal_mcp_config

    assert config.server_name == "pyramid-mcp"
    assert config.server_version == "1.0.0"
    assert config.mount_path == "/mcp"
    assert config.include_patterns is None
    assert config.exclude_patterns is None
    assert config.enable_sse is True
    assert config.enable_http is True


def test_custom_configuration():
    """Test MCPConfiguration with custom values."""
    config = MCPConfiguration(
        server_name="my-api",
        server_version="2.0.0",
        mount_path="/api/mcp",
        include_patterns=["users/*"],
        exclude_patterns=["admin/*"],
        enable_sse=False,
    )

    assert config.server_name == "my-api"
    assert config.server_version == "2.0.0"
    assert config.mount_path == "/api/mcp"
    assert config.include_patterns == ["users/*"]
    assert config.exclude_patterns == ["admin/*"]
    assert config.enable_sse is False
    assert config.enable_http is True  # Default value


def test_mcp_config_with_patterns_fixture(mcp_config_with_patterns):
    """Test MCP configuration fixture with include/exclude patterns."""
    config = mcp_config_with_patterns

    assert config.server_name == "pattern-test"
    assert config.include_patterns == ["api/*", "users/*"]
    assert config.exclude_patterns == ["admin/*", "internal/*"]


# =============================================================================
# 🏗️ PYRAMID MCP CLASS TESTS
# =============================================================================


def test_pyramid_mcp_creation_basic(pyramid_mcp_basic):
    """Test PyramidMCP creation with basic configuration."""
    pyramid_mcp = pyramid_mcp_basic

    assert pyramid_mcp is not None
    assert pyramid_mcp.protocol_handler is not None
    assert pyramid_mcp.config.server_name == "pyramid-mcp"  # From minimal_mcp_config


def test_pyramid_mcp_creation_configured(pyramid_mcp_configured):
    """Test PyramidMCP creation with full configuration."""
    pyramid_mcp = pyramid_mcp_configured

    assert pyramid_mcp is not None
    assert pyramid_mcp.protocol_handler is not None
    assert pyramid_mcp.config.server_name == "test-server"  # From custom_mcp_config


def test_pyramid_mcp_manual_tool_registration(pyramid_app_with_auth):
    """Test registering tools manually with PyramidMCP."""
    # Use our proven working fixture with route discovery enabled
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "unit-test-server",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
    }

    # Create TestApp using the global fixture (which handles scanning automatically)
    testapp = pyramid_app_with_auth(settings)

    # Get the pyramid_mcp instance from the TestApp's app registry
    pyramid_mcp = testapp.app.registry.pyramid_mcp

    # Check that the module-level tool is registered
    assert "unit_calculate" in pyramid_mcp.protocol_handler.tools
    tool = pyramid_mcp.protocol_handler.tools["unit_calculate"]
    assert tool.name == "unit_calculate"
    assert tool.description == "Unit test calculator"

    # Verify tool has handler
    assert tool.handler is not None

    print("✅ Manual tool registration successful!")
    print(f"✅ Registered tool: {tool.name} - {tool.description}")
    print(f"✅ Total tools registered: {len(pyramid_mcp.protocol_handler.tools)}")


def test_pyramid_mcp_mount_endpoints(minimal_pyramid_config, pyramid_mcp_basic):
    """Test mounting MCP endpoints to Pyramid configuration."""
    pyramid_mcp = pyramid_mcp_basic

    # Mount the MCP endpoints without auto-commit for backward compatibility
    pyramid_mcp.mount(auto_commit=False)

    # Commit the configuration to make routes visible
    pyramid_mcp.configurator.commit()

    # Check that MCP routes are added to pyramid_mcp's configurator
    routes = pyramid_mcp.configurator.get_routes_mapper().get_routes()
    mcp_routes = [
        route for route in routes if route.name and route.name.startswith("mcp_")
    ]

    # Should have at least the HTTP route
    assert len(mcp_routes) >= 1

    # Check for MCP HTTP route
    http_routes = [route for route in mcp_routes if "http" in route.name]
    assert len(http_routes) >= 1


# =============================================================================
# 🔧 PYRAMID INTROSPECTOR TESTS
# =============================================================================


def test_introspector_creation_with_config(pyramid_config_with_routes):
    """Test that PyramidIntrospector can be created with configuration."""
    introspector = PyramidIntrospector(pyramid_config_with_routes)

    assert introspector is not None
    assert introspector.configurator == pyramid_config_with_routes


def test_introspector_creation_minimal(minimal_pyramid_config):
    """Test PyramidIntrospector creation with minimal configuration."""
    introspector = PyramidIntrospector(minimal_pyramid_config)

    assert introspector is not None
    assert introspector.configurator == minimal_pyramid_config


def test_introspector_has_discovery_methods(pyramid_config_committed):
    """Test that PyramidIntrospector has expected methods."""
    introspector = PyramidIntrospector(pyramid_config_committed)

    # Test that key methods exist
    assert hasattr(introspector, "discover_routes")
    assert hasattr(introspector, "discover_tools_from_pyramid")
    assert callable(introspector.discover_routes)
    assert callable(introspector.discover_tools_from_pyramid)
