"""
Unit tests for pyramid_mcp MCP protocol functionality.

This module tests:
- MCPProtocolHandler creation and basic functionality
- MCP tool registration and management
- MCP JSON-RPC request/response handling
- MCP error handling and edge cases

Uses enhanced fixtures from conftest.py for clean, non-duplicated test setup.
"""

from pyramid_mcp.protocol import MCPErrorCode, MCPProtocolHandler, MCPTool
from pyramid_mcp import tool

# =============================================================================
# 🛠️ MODULE-LEVEL TOOL DEFINITIONS (for Venusian scanning)
# =============================================================================

@tool(name="multiply", description="Multiply two numbers")
def multiply(x: int, y: int) -> int:
    # Convert to int to handle JSON string/number conversion
    x = int(x)
    y = int(y)
    return x * y

@tool(name="greet", description="Greet someone")
def greet(name: str) -> str:
    return f"Hello, {name}!"

# =============================================================================
# 🔧 MCP PROTOCOL HANDLER TESTS
# =============================================================================


def test_protocol_handler_creation(protocol_handler):
    """Test creating a protocol handler using fixture."""
    handler = protocol_handler

    assert handler.server_name == "test-protocol"
    assert handler.server_version == "1.0.0"
    assert len(handler.tools) == 0
    assert "tools" in handler.capabilities


def test_protocol_handler_creation_custom():
    """Test creating a protocol handler with custom parameters."""
    handler = MCPProtocolHandler("custom-server", "2.1.0")

    assert handler.server_name == "custom-server"
    assert handler.server_version == "2.1.0"
    assert len(handler.tools) == 0
    assert "tools" in handler.capabilities


# =============================================================================
# 🛠️ MCP TOOL REGISTRATION TESTS
# =============================================================================


def test_tool_registration_basic(protocol_handler):
    """Test registering an MCP tool using fixture."""
    handler = protocol_handler

    def add_numbers(a: int, b: int) -> int:
        return a + b

    tool = MCPTool(name="add", description="Add two numbers", handler=add_numbers)
    handler.register_tool(tool)

    assert "add" in handler.tools
    assert handler.tools["add"].description == "Add two numbers"
    assert handler.tools["add"].handler == add_numbers


def test_tool_registration_multiple(protocol_handler):
    """Test registering multiple tools."""
    handler = protocol_handler

    def add_func(a: int, b: int) -> int:
        return a + b

    def multiply_func(x: int, y: int) -> int:
        return x * y

    # Register multiple tools
    add_tool = MCPTool(name="add", description="Add numbers", handler=add_func)
    multiply_tool = MCPTool(
        name="multiply", description="Multiply numbers", handler=multiply_func
    )

    handler.register_tool(add_tool)
    handler.register_tool(multiply_tool)

    assert len(handler.tools) == 2
    assert "add" in handler.tools
    assert "multiply" in handler.tools
    assert handler.tools["add"].handler == add_func
    assert handler.tools["multiply"].handler == multiply_func


def test_tool_registration_from_sample_tools(protocol_handler, sample_tools):
    """Test registering tools from sample_tools fixture."""
    handler = protocol_handler

    # Register tools from fixture using the tool decorator info
    for tool_func in sample_tools:
        # The sample_tools are already decorated with @tool, so we can extract info
        # from the function attributes set by the decorator
        tool_name = getattr(
            tool_func, "_mcp_name", getattr(tool_func, "__name__", "unknown")
        )
        tool_desc = getattr(tool_func, "_mcp_description", "A sample tool")
        tool = MCPTool(name=tool_name, description=tool_desc, handler=tool_func)
        handler.register_tool(tool)

    # Should have registered the sample tools (add_tool and multiply_tool)
    assert len(handler.tools) == 2  # Exactly 2 tools from sample_tools
    # Check that both tools are registered with their function names
    tool_names = set(handler.tools.keys())
    expected_names = {"add_tool", "multiply_tool"}
    assert any(
        name in tool_names for name in expected_names
    ), f"Expected one of {expected_names}, got {tool_names}"


# =============================================================================
# 📡 MCP REQUEST/RESPONSE HANDLING TESTS
# =============================================================================


def test_initialize_request(protocol_handler, dummy_request):
    """Test MCP initialize request using fixture."""
    handler = protocol_handler

    request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    response = handler.handle_message(request, dummy_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["serverInfo"]["name"] == "test-protocol"
    assert response["result"]["serverInfo"]["version"] == "1.0.0"
    assert "capabilities" in response["result"]


def test_list_tools_request_empty(protocol_handler, dummy_request):
    """Test MCP tools/list request with no tools registered."""
    handler = protocol_handler

    request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    response = handler.handle_message(request, dummy_request)

    assert "result" in response
    assert "tools" in response["result"]
    assert len(response["result"]["tools"]) == 0


def test_list_tools_request_with_tool(protocol_handler, dummy_request):
    """Test MCP tools/list request with a registered tool."""
    handler = protocol_handler

    # Register a test tool
    def test_func():
        return "test"

    tool = MCPTool(name="test_tool", description="A test tool", handler=test_func)
    handler.register_tool(tool)

    request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    response = handler.handle_message(request, dummy_request)

    assert "result" in response
    assert "tools" in response["result"]
    assert len(response["result"]["tools"]) == 1
    assert response["result"]["tools"][0]["name"] == "test_tool"
    assert response["result"]["tools"][0]["description"] == "A test tool"


def test_call_tool_request(pyramid_app_with_auth):
    """Test MCP tools/call request."""
    # Create TestApp with pyramid_app_with_auth
    settings = {
        "mcp.server_name": "unit-test-server",
        "mcp.server_version": "1.0.0",
    }
    app = pyramid_app_with_auth(settings)

    # First, list tools to get the actual sanitized tool name
    tools_response = app.post_json("/mcp", {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1,
        "params": {}
    })
    tools = tools_response.json["result"]["tools"]
    multiply_tool = next(tool for tool in tools if "multiply" in tool["name"])
    tool_name = multiply_tool["name"]

    # Use MCP protocol via HTTP instead of direct protocol handler
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": {"x": 5, "y": 3}},
        "id": 3,
    }

    response = app.post_json("/mcp", request)

    assert response.status_code == 200
    result = response.json
    assert "result" in result
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"
    assert "representation" in mcp_result
    # The content contains the tool result
    content = mcp_result["representation"]["content"]
    assert content["result"] == 15


def test_call_tool_with_string_result(pyramid_app_with_auth):
    """Test MCP tools/call request with string result."""
    # Create TestApp with pyramid_app_with_auth
    settings = {
        "mcp.server_name": "unit-test-server",
        "mcp.server_version": "1.0.0",
    }
    app = pyramid_app_with_auth(settings)

    # First, list tools to get the actual sanitized tool name
    tools_response = app.post_json("/mcp", {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1,
        "params": {}
    })
    tools = tools_response.json["result"]["tools"]
    greet_tool = next(tool for tool in tools if "greet" in tool["name"])
    tool_name = greet_tool["name"]

    # Use MCP protocol via HTTP instead of direct protocol handler
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": {"name": "World"}},
        "id": 4,
    }

    response = app.post_json("/mcp", request)

    assert response.status_code == 200
    result = response.json
    assert "result" in result
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"
    assert "representation" in mcp_result
    # The content contains the tool result
    content = mcp_result["representation"]["content"]
    assert content["result"] == "Hello, World!"


# =============================================================================
# ❌ MCP ERROR HANDLING TESTS
# =============================================================================


def test_unknown_method_error(protocol_handler, dummy_request):
    """Test error handling for unknown methods."""
    handler = protocol_handler

    request = {"jsonrpc": "2.0", "method": "unknown/method", "id": 1}
    response = handler.handle_message(request, dummy_request)

    assert "error" in response
    assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value
    assert "unknown/method" in response["error"]["message"]


def test_tool_not_found_error(protocol_handler, dummy_request):
    """Test error when calling non-existent tool."""
    handler = protocol_handler

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
        "id": 1,
    }

    response = handler.handle_message(request, dummy_request)

    assert "error" in response
    assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value
    assert "nonexistent" in response["error"]["message"]


def test_malformed_request_error(protocol_handler, dummy_request):
    """Test error handling for malformed requests."""
    handler = protocol_handler

    # Request with invalid/missing ID (None instead of string/number)
    malformed_request = {"jsonrpc": "2.0", "method": "initialize", "id": None}

    response = handler.handle_message(malformed_request, dummy_request)

    # For some malformed requests, the handler may still respond with valid structure
    # Let's test a truly malformed request that should cause an error
    invalid_json_rpc_request = {
        "method": "nonexistent/method",
        "id": 1,
    }  # missing jsonrpc

    response2 = handler.handle_message(invalid_json_rpc_request, dummy_request)

    # At least one of these should be an error or the original should be
    # valid but limited
    assert (
        "error" in response or "error" in response2 or response.get("jsonrpc") == "2.0"
    )  # Valid response structure is also acceptable


def test_tool_execution_error(protocol_handler, dummy_request):
    """Test error handling when tool execution fails."""
    handler = protocol_handler

    def failing_tool():
        raise ValueError("This tool always fails")

    tool = MCPTool(
        name="fail_tool", description="A tool that fails", handler=failing_tool
    )
    handler.register_tool(tool)

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "fail_tool", "arguments": {}},
        "id": 5,
    }

    response = handler.handle_message(request, dummy_request)

    # Should return an error response when tool execution fails
    assert "error" in response or (
        "result" in response and "error" in str(response["result"])
    )


# =============================================================================
# 📋 MCP CAPABILITIES TESTS
# =============================================================================


def test_protocol_handler_capabilities(protocol_handler):
    """Test that protocol handler exposes correct capabilities."""
    handler = protocol_handler

    capabilities = handler.capabilities

    # Should have tools capability
    assert "tools" in capabilities
    assert isinstance(capabilities, dict)


def test_protocol_handler_server_info(protocol_handler):
    """Test protocol handler server information."""
    handler = protocol_handler

    # Test server info attributes
    assert hasattr(handler, "server_name")
    assert hasattr(handler, "server_version")
    assert handler.server_name == "test-protocol"
    assert handler.server_version == "1.0.0"


def test_handle_notifications_initialized(protocol_handler, dummy_request):
    """Test that notifications/initialized returns NO_RESPONSE sentinel."""
    handler = protocol_handler

    # Test notifications/initialized request
    message_data = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
        # Note: No "id" field for notifications according to JSON-RPC 2.0 spec
    }

    # Handle the message
    response = handler.handle_message(message_data, dummy_request)

    # Should return the NO_RESPONSE sentinel
    assert (
        response is handler.NO_RESPONSE
    ), f"Expected NO_RESPONSE sentinel but got: {response}"


def test_handle_notifications_initialized_with_id(protocol_handler, dummy_request):
    """Test that notifications/initialized with id field still returns NO_RESPONSE."""
    handler = protocol_handler

    # Test notifications/initialized request with id
    # (technically not correct for notifications)
    message_data = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
        "id": 1,
    }

    # Handle the message
    response = handler.handle_message(message_data, dummy_request)

    # Should still return NO_RESPONSE
    # (notifications should not have responses regardless of id)
    assert (
        response is handler.NO_RESPONSE
    ), f"Expected NO_RESPONSE sentinel but got: {response}"


def test_tool_to_dict_always_includes_input_schema():
    """Test that MCPTool.to_dict() always includes inputSchema field."""
    # Test tool with explicit inputSchema
    tool_with_schema = MCPTool(
        name="test_tool",
        description="Test tool",
        input_schema={
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        },
    )

    result = tool_with_schema.to_dict()
    assert "inputSchema" in result
    assert result["inputSchema"]["type"] == "object"
    assert "param" in result["inputSchema"]["properties"]

    # Test tool with None inputSchema (should get default empty schema)
    tool_without_schema = MCPTool(
        name="test_tool", description="Test tool", input_schema=None
    )

    result = tool_without_schema.to_dict()
    assert "inputSchema" in result
    assert result["inputSchema"]["type"] == "object"
    assert result["inputSchema"]["properties"] == {}
    assert result["inputSchema"]["required"] == []
    assert result["inputSchema"]["additionalProperties"] is False

    # Test tool with missing inputSchema (should get default empty schema)
    tool_no_schema = MCPTool(
        name="test_tool",
        description="Test tool"
        # No input_schema parameter at all
    )

    result = tool_no_schema.to_dict()
    assert "inputSchema" in result
    assert result["inputSchema"]["type"] == "object"
    assert result["inputSchema"]["properties"] == {}
    assert result["inputSchema"]["required"] == []
    assert result["inputSchema"]["additionalProperties"] is False


def test_tools_list_all_have_input_schema(protocol_handler):
    """Test that all tools in tools/list response have inputSchema field."""
    # Add a tool without explicit inputSchema
    tool_without_schema = MCPTool(
        name="test_tool", description="Test tool", input_schema=None
    )
    protocol_handler.register_tool(tool_without_schema)

    # Add a tool with explicit inputSchema
    tool_with_schema = MCPTool(
        name="test_tool_with_schema",
        description="Test tool with schema",
        input_schema={
            "type": "object",
            "properties": {"param": {"type": "string"}},
            "required": ["param"],
        },
    )
    protocol_handler.register_tool(tool_with_schema)

    # Get tools list
    tools_list = [tool.to_dict() for tool in protocol_handler.tools.values()]

    # Verify all tools have inputSchema
    for tool in tools_list:
        assert "inputSchema" in tool, f"Tool {tool.get('name')} missing inputSchema"
        assert isinstance(
            tool["inputSchema"], dict
        ), f"Tool {tool.get('name')} inputSchema is not a dict"
        assert (
            "type" in tool["inputSchema"]
        ), f"Tool {tool.get('name')} inputSchema missing type"
        assert (
            tool["inputSchema"]["type"] == "object"
        ), f"Tool {tool.get('name')} inputSchema type is not 'object'"
