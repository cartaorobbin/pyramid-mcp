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
# 📦 PACKAGE IMPORTS AND AVAILABILITY TESTS
# =============================================================================


def test_pyramid_mcp_package_import():
    """Test that pyramid_mcp package can be imported."""
    import pyramid_mcp

    assert pyramid_mcp is not None


def test_pyramid_mcp_version():
    """Test that pyramid_mcp has a version."""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_main_classes_available():
    """Test that main classes are available for import."""
    # These imports should work without errors
    assert PyramidMCP is not None
    assert MCPConfiguration is not None
    assert PyramidIntrospector is not None
    assert MCPProtocolHandler is not None
    assert MCPTool is not None
    assert MCPErrorCode is not None
    assert MCPErrorSchema is not None
    assert MCPWSGIApp is not None


# =============================================================================
# 🔧 MCP CONFIGURATION TESTS
# =============================================================================


def test_mcp_configuration_creation():
    """Test MCPConfiguration creation with defaults."""
    config = MCPConfiguration()

    # Check default values
    assert config.server_name == "pyramid-mcp"
    assert (
        config.server_version == "1.0.0"
    )  # Default hardcoded value, not package version
    assert config.route_discovery_enabled is False  # Default is False
    assert config.mount_path == "/mcp"


def test_mcp_configuration_custom_values():
    """Test MCPConfiguration creation with custom values."""
    config = MCPConfiguration(
        server_name="custom-server",
        server_version="2.0.0",
        route_discovery_enabled=False,
        mount_path="/custom-mcp",
    )

    assert config.server_name == "custom-server"
    assert config.server_version == "2.0.0"
    assert config.route_discovery_enabled is False
    assert config.mount_path == "/custom-mcp"


def test_mcp_configuration_with_patterns(mcp_config_with_patterns):
    """Test MCPConfiguration with include/exclude patterns."""
    config = mcp_config_with_patterns

    assert config.server_name == "pattern-test"
    assert config.include_patterns == ["api/*", "users/*"]
    assert config.exclude_patterns == ["admin/*", "internal/*"]


# =============================================================================
# 🏗️ PYRAMID MCP CLASS TESTS
# =============================================================================


def test_pyramid_mcp_creation_basic(minimal_pyramid_config, minimal_mcp_config):
    """Test PyramidMCP creation with basic configuration."""
    pyramid_mcp = PyramidMCP(minimal_pyramid_config, config=minimal_mcp_config)

    assert pyramid_mcp is not None
    assert pyramid_mcp.protocol_handler is not None
    assert pyramid_mcp.config.server_name == "pyramid-mcp"  # From minimal_mcp_config


def test_pyramid_mcp_creation_configured(custom_mcp_config):
    """Test PyramidMCP creation with full configuration."""
    from pyramid.config import Configurator

    config = Configurator()
    pyramid_mcp = PyramidMCP(config, config=custom_mcp_config)

    assert pyramid_mcp is not None
    assert pyramid_mcp.protocol_handler is not None
    assert pyramid_mcp.config.server_name == "test-server"  # From custom_mcp_config


def test_pyramid_mcp_manual_tool_registration(pyramid_app):
    """Test registering tools manually with PyramidMCP."""
    # Use our proven working fixture with route discovery enabled
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "unit-test-server",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
    }

    # Create TestApp using the global fixture (which handles scanning automatically)
    testapp = pyramid_app(settings)

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


def test_pyramid_mcp_mount_endpoints(minimal_pyramid_config, minimal_mcp_config):
    """Test mounting MCP endpoints to Pyramid configuration."""
    pyramid_mcp = PyramidMCP(minimal_pyramid_config, config=minimal_mcp_config)

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


def test_introspector_creation_with_config(pyramid_config):
    """Test that PyramidIntrospector can be created with configuration."""
    # Use pyramid_config fixture directly since we need the configurator
    config = pyramid_config()
    introspector = PyramidIntrospector(config)

    assert introspector is not None
    assert introspector.configurator == config


def test_introspector_creation_minimal(minimal_pyramid_config):
    """Test PyramidIntrospector creation with minimal configuration."""
    introspector = PyramidIntrospector(minimal_pyramid_config)

    assert introspector is not None
    assert introspector.configurator == minimal_pyramid_config


def test_introspector_has_discovery_methods(pyramid_config):
    """Test that PyramidIntrospector has expected methods."""

    # Use pyramid_config fixture with a test view
    def test_view(request):
        return {"message": "test"}

    views = [(test_view, "test_route", {"renderer": "json"})]
    config = pyramid_config(views=views)
    introspector = PyramidIntrospector(config)

    # Test that key methods exist
    assert hasattr(introspector, "discover_routes")
    assert hasattr(introspector, "discover_tools_from_pyramid")
    assert callable(introspector.discover_routes)
    assert callable(introspector.discover_tools_from_pyramid)
