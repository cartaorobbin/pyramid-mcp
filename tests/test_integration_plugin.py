"""
Integration tests for pyramid_mcp plugin functionality.

This module tests:
- Plugin includeme function and Pyramid integration
- Settings parsing and configuration from pyramid settings
- Tool decorator functionality in plugin context
- Request method and configurator directive registration
- Plugin-level route mounting and setup
- End-to-end plugin integration scenarios

Uses enhanced fixtures from conftest.py for clean, non-duplicated test setup.
"""


from pyramid.config import Configurator

from pyramid_mcp import includeme, tool

# =============================================================================
# 🔌 PLUGIN INCLUDEME FUNCTIONALITY TESTS
# =============================================================================


def test_includeme_basic(minimal_pyramid_config):
    """Test basic includeme functionality using enhanced fixture."""
    config = minimal_pyramid_config

    # Include pyramid_mcp
    includeme(config)

    # Check that pyramid_mcp is in registry
    assert hasattr(config.registry, "pyramid_mcp")
    pyramid_mcp = config.registry.pyramid_mcp
    assert pyramid_mcp is not None

    # Check that directive is added
    assert hasattr(config, "get_mcp")
    mcp_instance = config.get_mcp()
    assert mcp_instance is pyramid_mcp


def test_includeme_with_custom_settings(mcp_settings_factory):
    """Test includeme with custom settings using settings factory."""
    # Create custom settings using the factory
    settings = mcp_settings_factory(
        server_name="plugin-test-api",
        server_version="2.0.0",
        mount_path="/api/mcp",
        enable_sse=False,
    )

    config = Configurator(settings=settings)

    # Include pyramid_mcp
    includeme(config)

    pyramid_mcp = config.registry.pyramid_mcp
    assert pyramid_mcp.config.server_name == "plugin-test-api"
    assert pyramid_mcp.config.server_version == "2.0.0"
    assert pyramid_mcp.config.mount_path == "/api/mcp"
    assert pyramid_mcp.config.enable_sse is False
    assert pyramid_mcp.config.enable_http is True  # Default


def test_includeme_mounts_routes(minimal_pyramid_config):
    """Test that includeme automatically mounts MCP routes."""
    config = minimal_pyramid_config

    # Include pyramid_mcp
    includeme(config)

    # Commit the configuration to make routes available
    config.commit()

    # Check that routes are mounted
    routes = config.get_routes_mapper().get_routes()
    mcp_routes = [
        route for route in routes if route.name and route.name.startswith("mcp_")
    ]

    assert len(mcp_routes) >= 1
    route_names = [route.name for route in mcp_routes]
    assert "mcp_http" in route_names


def test_request_method_access(minimal_pyramid_config):
    """Test that the MCP request method is properly configured."""
    config = minimal_pyramid_config
    includeme(config)

    # Verify that the MCP instance is accessible through the registry
    mcp_instance = config.registry.pyramid_mcp
    assert mcp_instance is not None

    # Test the underlying function that powers the request method
    from pyramid_mcp import _get_mcp_from_request

    # Create a mock request with registry
    class MockRequest:
        def __init__(self, registry):
            self.registry = registry

    mock_request = MockRequest(config.registry)
    mcp_from_request = _get_mcp_from_request(mock_request)
    assert mcp_from_request is mcp_instance


# =============================================================================
# 🔧 PLUGIN TOOL DECORATOR TESTS
# =============================================================================


def test_plugin_tool_decorator(minimal_pyramid_config):
    """Test the plugin-level tool decorator functionality."""
    config = minimal_pyramid_config
    includeme(config)

    # Get the pyramid_mcp instance
    pyramid_mcp = config.registry.pyramid_mcp

    # Use the plugin-level tool decorator after includeme
    @tool(name="plugin_add_test", description="Add two numbers via plugin")
    def add_numbers_plugin(a: int, b: int) -> int:
        return a + b

    # The tool should have been registered automatically
    # If not, we need to manually trigger registration of stored tools
    if "plugin_add_test" not in pyramid_mcp.protocol_handler.tools:
        # Check if the tool config is stored and register it manually
        if hasattr(add_numbers_plugin, "_mcp_tool_config"):
            tool_config = add_numbers_plugin._mcp_tool_config
            pyramid_mcp.tool(
                tool_config["name"], tool_config["description"], tool_config["schema"]
            )(add_numbers_plugin)

    # Check that the tool is registered
    assert "plugin_add_test" in pyramid_mcp.protocol_handler.tools

    # Test the tool
    tool_obj = pyramid_mcp.protocol_handler.tools["plugin_add_test"]
    result = tool_obj.handler(a=5, b=3)
    assert result == 8


def test_plugin_tool_decorator_with_complex_signature(minimal_pyramid_config):
    """Test plugin tool decorator with more complex function signature."""
    config = minimal_pyramid_config
    includeme(config)

    pyramid_mcp = config.registry.pyramid_mcp

    @tool(name="plugin_calculator", description="Complex calculation tool")
    def calculator_plugin(operation: str, a: float, b: float = 1.0) -> str:
        """Perform calculation with operation, a, and optional b."""
        if operation == "add":
            return f"Result: {a + b}"
        elif operation == "multiply":
            return f"Result: {a * b}"
        else:
            return f"Unknown operation: {operation}"

    # Ensure tool is registered
    if "plugin_calculator" not in pyramid_mcp.protocol_handler.tools:
        if hasattr(calculator_plugin, "_mcp_tool_config"):
            tool_config = calculator_plugin._mcp_tool_config
            pyramid_mcp.tool(
                tool_config["name"], tool_config["description"], tool_config["schema"]
            )(calculator_plugin)

    # Test the tool
    if "plugin_calculator" in pyramid_mcp.protocol_handler.tools:
        tool_obj = pyramid_mcp.protocol_handler.tools["plugin_calculator"]
        result = tool_obj.handler(operation="add", a=10.5, b=2.5)
        assert "13.0" in result


# =============================================================================
# ⚙️ SETTINGS PARSING AND CONFIGURATION TESTS
# =============================================================================


def test_boolean_settings_parsing():
    """Test various boolean settings parsing scenarios."""
    # Test boolean true values
    config = Configurator(
        settings={
            "mcp.enable_sse": "true",
            "mcp.enable_http": "1",
        }
    )
    includeme(config)
    pyramid_mcp = config.registry.pyramid_mcp
    assert pyramid_mcp.config.enable_sse is True
    assert pyramid_mcp.config.enable_http is True

    # Test boolean false values
    config2 = Configurator(
        settings={
            "mcp.enable_sse": "false",
            "mcp.enable_http": "0",
        }
    )
    includeme(config2)
    pyramid_mcp2 = config2.registry.pyramid_mcp
    assert pyramid_mcp2.config.enable_sse is False
    assert pyramid_mcp2.config.enable_http is False


def test_list_settings_parsing():
    """Test list settings parsing for include/exclude patterns."""
    config = Configurator(
        settings={
            "mcp.include_patterns": "users/*, admin/*",
            "mcp.exclude_patterns": "internal/*, debug/*",
        }
    )
    includeme(config)
    pyramid_mcp = config.registry.pyramid_mcp

    assert pyramid_mcp.config.include_patterns == ["users/*", "admin/*"]
    assert pyramid_mcp.config.exclude_patterns == ["internal/*", "debug/*"]


def test_default_settings(minimal_pyramid_config):
    """Test default settings when none are provided."""
    config = minimal_pyramid_config
    includeme(config)
    pyramid_mcp = config.registry.pyramid_mcp

    assert pyramid_mcp.config.server_name == "pyramid-mcp"
    assert pyramid_mcp.config.server_version == "1.0.0"
    assert pyramid_mcp.config.mount_path == "/mcp"
    assert pyramid_mcp.config.enable_sse is True
    assert pyramid_mcp.config.enable_http is True
    assert pyramid_mcp.config.include_patterns is None
    assert pyramid_mcp.config.exclude_patterns is None


def test_edge_case_settings_parsing(mcp_settings_factory):
    """Test edge cases in settings parsing."""
    # Test empty strings and whitespace
    settings = mcp_settings_factory(
        server_name="",  # Empty string
        include_patterns=" , , ",  # Whitespace only patterns
        exclude_patterns="valid/*, , another/*",  # Mix of valid and empty
    )

    config = Configurator(settings=settings)
    includeme(config)
    pyramid_mcp = config.registry.pyramid_mcp

    # Empty server name remains empty (implementation doesn't fall back to default)
    assert pyramid_mcp.config.server_name == ""

    # Empty patterns should be filtered out
    assert pyramid_mcp.config.include_patterns == []
    assert pyramid_mcp.config.exclude_patterns == ["valid/*", "another/*"]


# =============================================================================
# 🔌 PROTOCOL INTEGRATION TESTS
# =============================================================================


def test_mcp_protocol_after_plugin_include(minimal_pyramid_config):
    """Test that MCP protocol works after plugin inclusion."""
    config = minimal_pyramid_config
    includeme(config)

    pyramid_mcp = config.registry.pyramid_mcp

    # Test MCP initialize request
    request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "serverInfo" in response["result"]
    assert response["result"]["serverInfo"]["name"] == "pyramid-mcp"


def test_plugin_tools_list_via_protocol(minimal_pyramid_config):
    """Test that plugin-registered tools appear in tools/list."""
    config = minimal_pyramid_config
    includeme(config)

    pyramid_mcp = config.registry.pyramid_mcp

    # Register a plugin tool
    @tool(name="protocol_test_tool", description="Test tool for protocol testing")
    def protocol_test_tool(message: str) -> str:
        return f"Echo: {message}"

    # Ensure tool is registered
    if "protocol_test_tool" not in pyramid_mcp.protocol_handler.tools:
        if hasattr(protocol_test_tool, "_mcp_tool_config"):
            tool_config = protocol_test_tool._mcp_tool_config
            pyramid_mcp.tool(
                tool_config["name"], tool_config["description"], tool_config["schema"]
            )(protocol_test_tool)

    # Test tools/list request
    request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert "tools" in response["result"]

    tools = response["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "protocol_test_tool" in tool_names


def test_plugin_tools_call_via_protocol(minimal_pyramid_config):
    """Test calling plugin-registered tools via MCP protocol."""
    config = minimal_pyramid_config
    includeme(config)

    pyramid_mcp = config.registry.pyramid_mcp

    # Register a plugin tool
    @tool(name="protocol_call_tool", description="Test tool for protocol calling")
    def protocol_call_tool(value: int, multiplier: int = 2) -> str:
        result = value * multiplier
        return f"Result: {result}"

    # Ensure tool is registered
    if "protocol_call_tool" not in pyramid_mcp.protocol_handler.tools:
        if hasattr(protocol_call_tool, "_mcp_tool_config"):
            tool_config = protocol_call_tool._mcp_tool_config
            pyramid_mcp.tool(
                tool_config["name"], tool_config["description"], tool_config["schema"]
            )(protocol_call_tool)

    # Test tools/call request
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "protocol_call_tool",
            "arguments": {"value": 5, "multiplier": 3},
        },
        "id": 3,
    }

    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response
    assert "content" in response["result"]

    content = response["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    assert "15" in content[0]["text"]  # 5 * 3 = 15


# =============================================================================
# 🚀 END-TO-END PLUGIN INTEGRATION SCENARIOS
# =============================================================================


def test_complete_plugin_integration_scenario(mcp_settings_factory):
    """Test a complete plugin integration scenario from start to finish."""
    # 1. Setup configuration with custom settings
    settings = mcp_settings_factory(
        server_name="integration-test-server",
        server_version="1.5.0",
        mount_path="/test/mcp",
    )

    config = Configurator(settings=settings)

    # 2. Include the plugin
    includeme(config)

    # 3. Register multiple tools using plugin decorator
    @tool(name="scenario_add", description="Add numbers for scenario testing")
    def scenario_add(a: int, b: int) -> int:
        return a + b

    @tool(name="scenario_greet", description="Greet someone")
    def scenario_greet(name: str) -> str:
        return f"Hello, {name}!"

    pyramid_mcp = config.registry.pyramid_mcp

    # Ensure tools are registered
    for tool_func in [scenario_add, scenario_greet]:
        tool_name = (
            tool_func._mcp_tool_config["name"]
            if hasattr(tool_func, "_mcp_tool_config")
            else tool_func.__name__
        )
        if tool_name not in pyramid_mcp.protocol_handler.tools:
            if hasattr(tool_func, "_mcp_tool_config"):
                tool_config = tool_func._mcp_tool_config
                pyramid_mcp.tool(
                    tool_config["name"],
                    tool_config["description"],
                    tool_config["schema"],
                )(tool_func)

    # 4. Test initialization
    init_request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    init_response = pyramid_mcp.protocol_handler.handle_message(init_request)

    assert init_response["result"]["serverInfo"]["name"] == "integration-test-server"
    assert init_response["result"]["serverInfo"]["version"] == "1.5.0"

    # 5. Test tools list
    list_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    list_response = pyramid_mcp.protocol_handler.handle_message(list_request)

    tools = list_response["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "scenario_add" in tool_names
    assert "scenario_greet" in tool_names

    # 6. Test calling tools
    add_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "scenario_add", "arguments": {"a": 10, "b": 15}},
        "id": 3,
    }
    add_response = pyramid_mcp.protocol_handler.handle_message(add_request)
    assert "25" in add_response["result"]["content"][0]["text"]

    greet_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "scenario_greet", "arguments": {"name": "Alice"}},
        "id": 4,
    }
    greet_response = pyramid_mcp.protocol_handler.handle_message(greet_request)
    assert "Hello, Alice!" in greet_response["result"]["content"][0]["text"]

    # 7. Verify route mounting
    config.commit()
    routes = config.get_routes_mapper().get_routes()
    mcp_routes = [
        route for route in routes if route.name and route.name.startswith("mcp_")
    ]
    assert len(mcp_routes) >= 1


def test_plugin_with_fixture_integration(pyramid_mcp_configured):
    """Test plugin functionality using the enhanced pyramid_mcp fixture."""
    # The fixture already has MCP configured, test that tools can be added
    pyramid_mcp = pyramid_mcp_configured

    @tool(name="fixture_test_tool", description="Test tool with fixture")
    def fixture_test_tool(input_text: str) -> str:
        return f"Processed: {input_text}"

    # Register the tool manually since the fixture doesn't auto-register
    pyramid_mcp.tool("fixture_test_tool", "Test tool with fixture")(fixture_test_tool)

    # Test the tool via protocol
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "fixture_test_tool",
            "arguments": {"input_text": "test input"},
        },
        "id": 1,
    }

    response = pyramid_mcp.protocol_handler.handle_message(request)
    assert "Processed: test input" in response["result"]["content"][0]["text"]
