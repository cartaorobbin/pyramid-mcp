"""
Integration tests for pyramid_mcp with Pyramid applications.
"""

import pytest
from pyramid.testing import DummyRequest

from tests.conftest import UserCreateSchema, UserUpdateSchema


# Pyramid Setup tests
def test_pyramid_config_creation(pyramid_config):
    """Test that Pyramid config can be created."""
    assert pyramid_config is not None

    # Test that routes are registered
    app = pyramid_config.make_wsgi_app()
    assert app is not None


def test_pyramid_views_work(pyramid_config, users_db, user_id_counter):
    """Test that Pyramid views work correctly."""
    # Create a test request with proper registry
    request = DummyRequest()
    request.registry = pyramid_config.registry
    request.json_body = {"name": "John Doe", "email": "john@example.com", "age": 30}

    # Import the view function from conftest
    from tests.conftest import create_user_view

    # Call the view
    result = create_user_view(request)

    # Check the result
    assert "user" in result
    assert result["user"]["name"] == "John Doe"
    assert result["user"]["email"] == "john@example.com"
    assert result["user"]["age"] == 30
    assert result["user"]["id"] == 1


# PyramidMCP Integration tests
def test_pyramid_mcp_creation(pyramid_mcp):
    """Test that PyramidMCP can be created."""
    assert pyramid_mcp is not None
    assert pyramid_mcp.protocol_handler is not None
    assert pyramid_mcp.config.server_name == "test-user-api"


def test_manual_tool_registration(pyramid_mcp):
    """Test registering tools manually."""

    @pyramid_mcp.tool("calculate", "Simple calculator")
    def calculate(operation: str, a: float, b: float) -> float:
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

    # Check that the tool is registered
    assert "calculate" in pyramid_mcp.protocol_handler.tools
    tool = pyramid_mcp.protocol_handler.tools["calculate"]
    assert tool.name == "calculate"
    assert tool.description == "Simple calculator"

    # Test calling the tool
    result = tool.handler(operation="add", a=5, b=3)
    assert result == 8


def test_mount_mcp_endpoints(pyramid_config, pyramid_mcp):
    """Test mounting MCP endpoints to Pyramid config."""
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


# MCP Protocol Functionality tests
def test_mcp_initialize(pyramid_mcp):
    """Test MCP initialize request."""
    request = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert response["result"]["serverInfo"]["name"] == "test-user-api"
    assert response["result"]["serverInfo"]["version"] == "1.0.0"


def test_mcp_list_tools(pyramid_mcp):
    """Test MCP tools/list request."""

    # Register a test tool
    @pyramid_mcp.tool("test_tool", "A test tool")
    def test_tool(message: str) -> str:
        return f"Hello, {message}!"

    request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}

    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert "result" in response
    assert "tools" in response["result"]

    # Find our test tool
    tools = response["result"]["tools"]
    test_tools = [tool for tool in tools if tool["name"] == "test_tool"]
    assert len(test_tools) == 1
    assert test_tools[0]["description"] == "A test tool"


def test_mcp_call_tool(pyramid_mcp):
    """Test MCP tools/call request."""

    # Register a test tool
    @pyramid_mcp.tool("echo", "Echo a message")
    def echo_tool(message: str) -> str:
        return f"Echo: {message}"

    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "Hello, World!"}},
        "id": 3,
    }

    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert "result" in response
    assert "content" in response["result"]
    assert len(response["result"]["content"]) == 1
    assert response["result"]["content"][0]["type"] == "text"
    assert response["result"]["content"][0]["text"] == "Echo: Hello, World!"


def test_mcp_error_handling(pyramid_mcp):
    """Test MCP error handling."""
    # Test calling non-existent tool
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
        "id": 4,
    }

    response = pyramid_mcp.protocol_handler.handle_message(request)

    assert "error" in response
    assert response["error"]["code"] == -32601  # METHOD_NOT_FOUND
    assert "nonexistent_tool" in response["error"]["message"]


# Schema Integration tests
def test_user_create_schema():
    """Test UserCreateSchema validation."""
    schema = UserCreateSchema()

    # Valid data
    valid_data = {"name": "John Doe", "email": "john@example.com", "age": 30}

    result = schema.load(valid_data)
    assert result["name"] == "John Doe"
    assert result["email"] == "john@example.com"
    assert result["age"] == 30


def test_user_create_schema_validation():
    """Test UserCreateSchema validation errors."""
    schema = UserCreateSchema()

    # Missing required fields
    invalid_data = {"age": 30}

    with pytest.raises(Exception):  # ValidationError
        schema.load(invalid_data)


def test_user_update_schema():
    """Test UserUpdateSchema validation."""
    schema = UserUpdateSchema()

    # Partial update
    partial_data = {"name": "Jane Doe"}

    result = schema.load(partial_data)
    assert result["name"] == "Jane Doe"
    assert "email" not in result or result["email"] is None
    assert "age" not in result or result["age"] is None


# Route Discovery tests (placeholder for now)
def test_introspector_creation(pyramid_config):
    """Test that PyramidIntrospector can be created."""
    from pyramid_mcp.introspection import PyramidIntrospector

    introspector = PyramidIntrospector(pyramid_config)
    assert introspector is not None
    assert introspector.configurator == pyramid_config


def test_route_discovery_placeholder(pyramid_config):
    """Placeholder test for route discovery."""
    from pyramid_mcp.introspection import PyramidIntrospector

    introspector = PyramidIntrospector(pyramid_config)

    # This will be implemented later
    # For now, just test that the method exists
    assert hasattr(introspector, "discover_routes")

    # TODO: Implement actual route discovery tests
    # when PyramidIntrospector.discover_routes() is implemented
