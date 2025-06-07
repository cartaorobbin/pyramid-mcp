"""
Basic unit tests for pyramid_mcp core functionality.
"""

# Removed unused import

from pyramid_mcp import PyramidMCP, __version__
from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.protocol import MCPError, MCPErrorCode, MCPProtocolHandler, MCPTool
from pyramid_mcp.wsgi import MCPWSGIApp


# Import tests
def test_main_package_imports():
    """Test main package imports."""
    assert PyramidMCP is not None
    assert __version__ is not None
    assert isinstance(__version__, str)


def test_protocol_imports():
    """Test protocol module imports."""
    assert MCPProtocolHandler is not None
    assert MCPTool is not None
    assert MCPError is not None
    assert MCPErrorCode is not None


def test_core_imports():
    """Test core module imports."""
    assert MCPConfiguration is not None


def test_introspection_imports():
    """Test introspection module imports."""
    assert PyramidIntrospector is not None


def test_wsgi_imports():
    """Test WSGI module imports."""
    assert MCPWSGIApp is not None


# MCP Protocol tests
def test_protocol_handler_creation():
    """Test creating a protocol handler."""
    handler = MCPProtocolHandler("test-server", "1.0.0")
    assert handler.server_name == "test-server"
    assert handler.server_version == "1.0.0"
    assert len(handler.tools) == 0
    assert "tools" in handler.capabilities


def test_tool_registration():
    """Test registering an MCP tool."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    def add_numbers(a: int, b: int) -> int:
        return a + b

    tool = MCPTool(name="add", description="Add two numbers", handler=add_numbers)

    handler.register_tool(tool)

    assert "add" in handler.tools
    assert handler.tools["add"].description == "Add two numbers"
    assert handler.tools["add"].handler == add_numbers


def test_initialize_request():
    """Test MCP initialize request."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

    response = handler.handle_message(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["serverInfo"]["name"] == "test-server"
    assert response["result"]["serverInfo"]["version"] == "1.0.0"
    assert "capabilities" in response["result"]


def test_list_tools_request():
    """Test MCP tools/list request."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    # Register a tool
    def test_func():
        return "test"

    tool = MCPTool(name="test_tool", handler=test_func)
    handler.register_tool(tool)

    request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}

    response = handler.handle_message(request)

    assert "result" in response
    assert "tools" in response["result"]
    assert len(response["result"]["tools"]) == 1
    assert response["result"]["tools"][0]["name"] == "test_tool"


def test_call_tool_request():
    """Test MCP tools/call request."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    def multiply(x: int, y: int) -> int:
        return x * y

    tool = MCPTool(name="multiply", handler=multiply)
    handler.register_tool(tool)

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "multiply", "arguments": {"x": 5, "y": 3}},
        "id": 3,
    }

    response = handler.handle_message(request)

    assert "result" in response
    assert "content" in response["result"]
    assert response["result"]["content"][0]["text"] == "15"


def test_unknown_method_error():
    """Test error handling for unknown methods."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    request = {"jsonrpc": "2.0", "method": "unknown/method", "id": 1}

    response = handler.handle_message(request)

    assert "error" in response
    assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value
    assert "unknown/method" in response["error"]["message"]


def test_tool_not_found_error():
    """Test error when calling non-existent tool."""
    handler = MCPProtocolHandler("test-server", "1.0.0")

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "nonexistent", "arguments": {}},
        "id": 1,
    }

    response = handler.handle_message(request)

    assert "error" in response
    assert response["error"]["code"] == MCPErrorCode.METHOD_NOT_FOUND.value
    assert "nonexistent" in response["error"]["message"]


# MCP Configuration tests
def test_default_configuration():
    """Test default configuration values."""
    config = MCPConfiguration()

    assert config.server_name == "pyramid-mcp"
    assert config.server_version == "1.0.0"
    assert config.mount_path == "/mcp"
    assert config.include_patterns is None
    assert config.exclude_patterns is None
    assert config.enable_sse is True
    assert config.enable_http is True


def test_custom_configuration():
    """Test custom configuration values."""
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
