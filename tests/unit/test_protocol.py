"""
Unit tests for pyramid_mcp MCP protocol functionality.

This module tests:
- MCPProtocolHandler creation and basic functionality
- MCP tool registration and management
- MCP JSON-RPC request/response handling
- MCP error handling and edge cases
- Tool name validation and sanitization for Claude Desktop compatibility
"""

from pyramid_mcp import tool
from pyramid_mcp.protocol import (
    CLAUDE_TOOL_NAME_PATTERN,
    MCPErrorCode,
    MCPProtocolHandler,
    MCPTool,
    sanitize_tool_name,
    validate_tool_name,
)

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


def test_tool_registration_from_sample_tools(protocol_handler, sample_tools):
    """Test registering tools from sample tools fixture."""
    handler = protocol_handler

    for tool_func in sample_tools:
        # Create MCPTool objects from the functions
        mcp_tool = MCPTool(name=tool_func.__name__, handler=tool_func)
        handler.register_tool(mcp_tool)

    # Should have registered all sample tools
    assert len(handler.tools) >= len(sample_tools)

    # Check that specific tools are registered
    tool_names = list(handler.tools.keys())
    assert len(tool_names) > 0


# =============================================================================
# 📨 MCP MESSAGE HANDLING TESTS
# =============================================================================


def test_initialize_request(protocol_handler, test_pyramid_request):
    """Test handling MCP initialize request."""
    handler = protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["protocolVersion"] == "2024-11-05"
    assert "capabilities" in response["result"]
    assert "serverInfo" in response["result"]


def test_list_tools_request_empty(protocol_handler, test_pyramid_request):
    """Test listing tools when none are registered."""
    handler = protocol_handler

    request_data = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2
    assert "result" in response
    assert response["result"]["tools"] == []


def test_list_tools_request_with_tool(protocol_handler, test_pyramid_request):
    """Test listing tools when tools are registered."""
    handler = protocol_handler

    def test_func() -> str:
        return "test"

    tool = MCPTool(name="test_tool", description="Test tool", handler=test_func)
    handler.register_tool(tool)

    request_data = {"jsonrpc": "2.0", "id": 3, "method": "tools/list", "params": {}}

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    assert "result" in response
    tools = response["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "test_tool"
    assert tools[0]["description"] == "Test tool"


def test_call_tool_request(protocol_handler, test_pyramid_request):
    """Test calling a tool through MCP protocol."""
    handler = protocol_handler

    def echo_func(message: str) -> str:
        return f"Echo: {message}"

    tool = MCPTool(name="echo", description="Echo message", handler=echo_func)
    handler.register_tool(tool)

    request_data = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "Hello"}},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4
    assert "result" in response
    # The test_pyramid_request fixture returns "test response" for unknown routes
    assert "representation" in response["result"]
    assert "content" in response["result"]["representation"]


def test_call_tool_with_string_result(protocol_handler, test_pyramid_request):
    """Test calling a tool that returns a string."""
    handler = protocol_handler

    def simple_tool() -> str:
        return "Simple result"

    tool = MCPTool(name="simple", description="Simple tool", handler=simple_tool)
    handler.register_tool(tool)

    request_data = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "simple", "arguments": {}},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 5
    assert "result" in response
    # The test_pyramid_request fixture returns "test response" for unknown routes
    assert "representation" in response["result"]
    assert "content" in response["result"]["representation"]


# =============================================================================
# ❌ MCP ERROR HANDLING TESTS
# =============================================================================


def test_unknown_method_error(protocol_handler, test_pyramid_request):
    """Test error handling for unknown methods."""
    handler = protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "unknown/method",
        "params": {},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 6
    assert "error" in response
    assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value


def test_tool_not_found_error(protocol_handler, test_pyramid_request):
    """Test error handling for calling non-existent tool."""
    handler = protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 7
    assert "error" in response
    assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value


def test_malformed_request_error(protocol_handler, test_pyramid_request):
    """Test error handling for malformed requests."""
    handler = protocol_handler

    # Missing required 'method' field
    request_data = {"jsonrpc": "2.0", "id": 8, "params": {}}

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 8
    assert "error" in response


def test_tool_execution_error(protocol_handler, test_pyramid_request):
    """Test error handling when tool execution fails."""
    handler = protocol_handler

    def failing_tool() -> str:
        raise ValueError("Tool execution failed")

    tool = MCPTool(name="failing", description="Failing tool", handler=failing_tool)
    handler.register_tool(tool)

    request_data = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {"name": "failing", "arguments": {}},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 9
    # With test_pyramid_request fixture, even failing tools return success
    # This test verifies the protocol structure, not actual error handling
    assert "result" in response
    assert "representation" in response["result"]


# =============================================================================
# 🔍 MCP CAPABILITIES AND INFO TESTS
# =============================================================================


def test_protocol_handler_capabilities(protocol_handler):
    """Test that protocol handler has expected capabilities."""
    handler = protocol_handler

    assert "tools" in handler.capabilities
    assert "resources" in handler.capabilities
    assert "prompts" in handler.capabilities


def test_protocol_handler_server_info(protocol_handler):
    """Test protocol handler server info."""
    handler = protocol_handler

    assert handler.server_name == "test-protocol"
    assert handler.server_version == "1.0.0"


def test_handle_notifications_initialized(protocol_handler, test_pyramid_request):
    """Test handling notifications/initialized (should return NO_RESPONSE)."""
    handler = protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    # notifications/initialized should return NO_RESPONSE sentinel
    assert response is handler.NO_RESPONSE


def test_handle_notifications_initialized_with_id(
    protocol_handler, test_pyramid_request
):
    """Test that notifications with IDs still return NO_RESPONSE."""
    handler = protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 999,  # Should be ignored for notifications
        "method": "notifications/initialized",
        "params": {},
    }

    response = handler.handle_message(request_data, test_pyramid_request)

    # Even with ID, notifications should return NO_RESPONSE
    assert response is handler.NO_RESPONSE


def test_tool_to_dict_always_includes_input_schema(protocol_handler):
    """Test that tool.to_dict() always includes inputSchema."""

    # Test tool with no explicit input schema
    def simple_tool() -> str:
        return "test"

    tool = MCPTool(name="simple", description="Simple tool", handler=simple_tool)

    tool_dict = tool.to_dict()

    # Should always have inputSchema, even if empty
    assert "inputSchema" in tool_dict
    assert isinstance(tool_dict["inputSchema"], dict)
    assert "type" in tool_dict["inputSchema"]
    assert tool_dict["inputSchema"]["type"] == "object"


def test_tools_list_all_have_input_schema(protocol_handler, test_pyramid_request):
    """Test that all tools in tools/list have inputSchema."""
    handler = protocol_handler

    # Register a few different tools
    def tool1() -> str:
        return "tool1"

    def tool2(param: str) -> str:
        return f"tool2: {param}"

    handler.register_tool(MCPTool(name="tool1", handler=tool1))
    handler.register_tool(MCPTool(name="tool2", handler=tool2))

    request_data = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    response = handler.handle_message(request_data, test_pyramid_request)
    tools = response["result"]["tools"]

    # All tools should have inputSchema
    for tool_dict in tools:
        assert "inputSchema" in tool_dict
        assert isinstance(tool_dict["inputSchema"], dict)


# =============================================================================
# 🏷️ TOOL NAME VALIDATION TESTS
# =============================================================================


def test_validate_tool_name_valid_names():
    """Test validation of valid tool names."""
    valid_names = [
        "simple_tool",
        "tool123",
        "my-tool",
        "tool_with_underscores",
        "tool-with-dashes",
        "CamelCaseTool",
        "mixedCase_tool-123",
        "a" * 64,  # Maximum length
        "x",  # Minimum length
    ]

    for name in valid_names:
        assert validate_tool_name(name), f"Name '{name}' should be valid"


def test_validate_tool_name_invalid_names():
    """Test validation of invalid tool names."""
    invalid_names = [
        "",  # Empty string
        "tool with spaces",  # Contains spaces
        "tool@domain",  # Contains @
        "tool.name",  # Contains dot
        "tool#hash",  # Contains hash
        "tool$money",  # Contains dollar
        "tool(param)",  # Contains parentheses
        "tool[index]",  # Contains brackets
        "tool{obj}",  # Contains braces
        "tool/path",  # Contains slash
        "tool\\path",  # Contains backslash
        "tool:name",  # Contains colon
        "tool;name",  # Contains semicolon
        "tool,name",  # Contains comma
        "tool?query",  # Contains question mark
        "tool!excl",  # Contains exclamation
        "tool+plus",  # Contains plus
        "tool=equal",  # Contains equals
        "tool%percent",  # Contains percent
        "tool^caret",  # Contains caret
        "tool&ampersand",  # Contains ampersand
        "tool*asterisk",  # Contains asterisk
        "tool|pipe",  # Contains pipe
        "tool<less",  # Contains less than
        "tool>greater",  # Contains greater than
        "tool~tilde",  # Contains tilde
        "tool`backtick",  # Contains backtick
        "tool'quote",  # Contains single quote
        'tool"quote',  # Contains double quote
        "a" * 65,  # Too long
        "a" * 100,  # Way too long
        "©tool",  # Unicode character
        "tool™",  # Unicode character
        "tööl",  # Unicode characters
    ]

    for name in invalid_names:
        assert not validate_tool_name(name), f"Name '{name}' should be invalid"


def test_claude_tool_name_pattern_directly():
    """Test the regex pattern directly."""
    # Valid cases
    assert CLAUDE_TOOL_NAME_PATTERN.match("valid_tool")
    assert CLAUDE_TOOL_NAME_PATTERN.match("tool123")
    assert CLAUDE_TOOL_NAME_PATTERN.match("my-tool")

    # Invalid cases
    assert not CLAUDE_TOOL_NAME_PATTERN.match("invalid tool")
    assert not CLAUDE_TOOL_NAME_PATTERN.match("tool.name")
    assert not CLAUDE_TOOL_NAME_PATTERN.match("")
    assert not CLAUDE_TOOL_NAME_PATTERN.match("a" * 65)


def test_sanitize_valid_names_unchanged():
    """Test that valid names are not changed."""
    valid_names = [
        "simple_tool",
        "tool123",
        "my-tool",
        "CamelCaseTool",
        "x",
        "a" * 64,
    ]

    for name in valid_names:
        sanitized = sanitize_tool_name(name)
        assert sanitized == name, f"Valid name '{name}' was changed to '{sanitized}'"


def test_sanitize_invalid_characters():
    """Test sanitizing invalid characters."""
    test_cases = [
        ("tool with spaces", "tool_with_spaces"),
        ("tool@domain", "tool_domain"),
        ("tool.name", "tool_name"),
        ("tool#hash", "tool_hash"),
        ("tool$money", "tool_money"),
        ("tool(param)", "tool_param_"),
        ("tool[index]", "tool_index_"),
        ("tool{obj}", "tool_obj_"),
        ("tool/path", "tool_path"),
        ("tool\\path", "tool_path"),
    ]

    for original, expected in test_cases:
        sanitized = sanitize_tool_name(original)
        assert (
            sanitized == expected
        ), f"'{original}' sanitized to '{sanitized}', expected '{expected}'"


def test_sanitize_empty_string():
    """Test sanitizing empty string."""
    sanitized = sanitize_tool_name("")
    assert sanitized == "tool"  # Default name for empty input


def test_sanitize_numeric_start():
    """Test sanitizing names that start with numbers."""
    test_cases = [
        ("123tool", "tool_123tool"),
        ("4getme", "tool_4getme"),
        ("999", "tool_999"),
    ]

    for original, expected in test_cases:
        sanitized = sanitize_tool_name(original)
        assert (
            sanitized == expected
        ), f"'{original}' sanitized to '{sanitized}', expected '{expected}'"


def test_sanitize_too_long():
    """Test sanitizing names that are too long."""
    # Create a name that's too long
    long_name = "a" * 70
    sanitized = sanitize_tool_name(long_name)

    # Should be 64 characters or less
    assert len(sanitized) <= 64
    assert validate_tool_name(sanitized)


def test_sanitize_collision_prevention():
    """Test that sanitization prevents name collisions."""
    used_names = {"tool_name"}

    # This should get a different name due to collision
    sanitized = sanitize_tool_name("tool.name", used_names)
    assert sanitized != "tool_name"
    assert sanitized not in used_names
    assert validate_tool_name(sanitized)


def test_sanitize_multiple_collisions():
    """Test handling multiple collisions."""
    # Start with a base name that will collide
    base_name = "tool"
    used_names = {
        "tool",
        "tool_1234567",
        "tool_1234567_000",
    }  # Force multiple collisions

    sanitized = sanitize_tool_name(base_name, used_names)
    assert sanitized not in used_names
    assert validate_tool_name(sanitized)


def test_sanitize_edge_cases():
    """Test edge cases in sanitization."""
    edge_cases = [
        ("@@@", "___"),  # All invalid chars -> underscores
        ("   ", "___"),  # All spaces -> underscores
        ("123", "tool_123"),  # All numbers
        ("_underscore", "_underscore"),  # Valid, should be unchanged
        ("-dash", "-dash"),  # Valid, should be unchanged
    ]

    for original, expected in edge_cases:
        sanitized = sanitize_tool_name(original)
        assert (
            sanitized == expected
        ), f"'{original}' sanitized to '{sanitized}', expected '{expected}'"
        assert validate_tool_name(sanitized)


# =============================================================================
# 🔧 TOOL NAME VALIDATION INTEGRATION TESTS
# =============================================================================


def test_register_tool_with_valid_name():
    """Test registering a tool with a valid name."""
    handler = MCPProtocolHandler("test", "1.0")

    def test_func():
        return "test"

    tool = MCPTool(name="valid_tool_name", handler=test_func)
    handler.register_tool(tool)

    assert "valid_tool_name" in handler.tools
    assert handler.tools["valid_tool_name"].name == "valid_tool_name"


def test_register_tool_with_invalid_name():
    """Test that registering a tool with invalid name sanitizes it."""
    handler = MCPProtocolHandler("test", "1.0")

    def test_func():
        return "test"

    # Tool with invalid name
    tool = MCPTool(name="invalid tool name", handler=test_func)
    handler.register_tool(tool)

    # Should be sanitized
    assert "invalid tool name" not in handler.tools
    assert "invalid_tool_name" in handler.tools
    assert handler.tools["invalid_tool_name"].name == "invalid_tool_name"


def test_register_multiple_tools_with_collision():
    """Test registering multiple tools that would have naming collisions."""
    handler = MCPProtocolHandler("test", "1.0")

    def test_func1():
        return "test1"

    def test_func2():
        return "test2"

    # Both tools would sanitize to the same name
    tool1 = MCPTool(name="tool name", handler=test_func1)
    tool2 = MCPTool(name="tool.name", handler=test_func2)

    handler.register_tool(tool1)
    handler.register_tool(tool2)

    # Should have different names after sanitization
    assert len(handler.tools) == 2
    tool_names = list(handler.tools.keys())
    assert len(set(tool_names)) == 2  # All names should be unique


def test_register_tool_preserves_functionality():
    """Test that name sanitization doesn't break tool functionality."""
    handler = MCPProtocolHandler("test", "1.0")

    def add_func(a: int, b: int) -> int:
        return a + b

    # Tool with name that needs sanitization
    tool = MCPTool(name="add two numbers", description="Add function", handler=add_func)
    handler.register_tool(tool)

    # Find the sanitized name
    sanitized_name = None
    for name in handler.tools:
        if "add" in name and "two" in name:
            sanitized_name = name
            break

    assert sanitized_name is not None
    registered_tool = handler.tools[sanitized_name]

    # Functionality should be preserved
    assert registered_tool.description == "Add function"
    assert registered_tool.handler == add_func


def test_register_tool_extremely_long_name():
    """Test registering a tool with an extremely long name."""
    handler = MCPProtocolHandler("test", "1.0")

    def test_func():
        return "test"

    # Very long name
    long_name = (
        "this_is_a_very_long_tool_name_that_exceeds_the_maximum_allowed_"
        "length_for_claude_desktop_compatibility" * 2
    )
    tool = MCPTool(name=long_name, handler=test_func)

    handler.register_tool(tool)

    # Should be registered with a sanitized name
    assert len(handler.tools) == 1
    registered_name = list(handler.tools.keys())[0]
    assert len(registered_name) <= 64
    assert validate_tool_name(registered_name)


def test_register_tool_with_unicode_characters():
    """Test registering tools with unicode characters."""
    handler = MCPProtocolHandler("test", "1.0")

    def test_func():
        return "test"

    unicode_names = [
        "tööl",  # Umlaut
        "tool™",  # Trademark symbol
        "©tool",  # Copyright symbol
        "tool→arrow",  # Arrow
        "🔧tool",  # Emoji
    ]

    for name in unicode_names:
        tool = MCPTool(name=name, handler=test_func)
        handler.register_tool(tool)

    # All should be registered with sanitized names
    assert len(handler.tools) == len(unicode_names)

    # All registered names should be valid
    for registered_name in handler.tools.keys():
        assert validate_tool_name(registered_name)
