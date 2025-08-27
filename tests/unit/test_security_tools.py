"""
Unit tests for pyramid_mcp security tools integration.

This module tests:
- Tool decorator security parameter integration
- Input schema generation with authentication fields
- Tool execution with security context
- Permission-based tool access control

Uses unique tool definitions to avoid configuration conflicts.
"""

from pyramid_mcp import tool
from pyramid_mcp.security import BearerAuthSchema

# =============================================================================
# 🔧 TOOL DECORATOR UNIQUE TOOLS
# =============================================================================


@tool(
    name="decorator_verification_tool",
    description="Test tool for decorator verification",
)
def decorator_verification_tool(message: str) -> str:
    """Simple tool for verifying decorator functionality."""
    return f"Decorator tool response: {message}"


@tool(
    name="decorator_secure_data",
    description="Get secure data via decorator (requires authentication)",
    permission="authenticated",
    security=BearerAuthSchema(),
)
def decorator_secure_data(data_id: int) -> dict:
    """Tool that requires authentication via decorator."""
    if isinstance(data_id, str):
        data_id = int(data_id)

    secure_data = {
        1: {"id": 1, "value": "secure_value_1", "classification": "confidential"},
        2: {"id": 2, "value": "secure_value_2", "classification": "confidential"},
    }
    data = secure_data.get(data_id)
    if not data:
        raise ValueError("Secure data not found")
    return {"data": data, "secured_by": "decorator", "auth_required": True}


@tool(name="decorator_public_info", description="Get public info via decorator")
def decorator_public_info(info_id: int) -> dict:
    """Tool that doesn't require authentication."""
    if isinstance(info_id, str):
        info_id = int(info_id)

    public_info = {
        1: {"id": 1, "value": "public_value_1", "classification": "public"},
        2: {"id": 2, "value": "public_value_2", "classification": "public"},
    }
    info = public_info.get(info_id)
    if not info:
        raise ValueError("Public info not found")
    return {"data": info, "secured_by": "decorator", "auth_required": False}


# =============================================================================
# 🔗 UNIFIED SECURITY ARCHITECTURE TESTS
# =============================================================================


def test_tool_decorator_creates_pyramid_views(pyramid_app):
    """Test that @tool decorators create Pyramid views that are discoverable."""
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "decorator-test-server",
        "mcp.server_version": "1.0.0",
        "mcp.filter_forbidden_tools": "false",  # Disable filtering to test tools  # noqa: E501
    }

    app = pyramid_app(settings)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    )
    assert init_response.status_code == 200

    # List tools to verify our tools are discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    assert (
        "decorator_verification_tool" in tool_names
    ), f"decorator_verification_tool not found in {tool_names}"
    assert (
        "decorator_secure_data" in tool_names
    ), f"decorator_secure_data not found in {tool_names}"
    assert (
        "decorator_public_info" in tool_names
    ), f"decorator_public_info not found in {tool_names}"


def test_tool_decorator_execution_via_mcp(pyramid_app):
    """Test that tools created with @tool decorator can be executed via MCP."""
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "decorator-exec-server",
        "mcp.server_version": "1.0.0",
    }

    app = pyramid_app(settings)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    )
    assert init_response.status_code == 200

    # Test verification tool execution
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": "decorator_verification_tool",
                "arguments": {"body": {"message": "test_message"}},
            },
        },
    )
    assert call_response.status_code == 200
    result = call_response.json["result"]
    assert "Decorator tool response: test_message" in str(result)

    # Test public info tool execution
    public_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": "decorator_public_info",
                "arguments": {"info_id": 1},
            },
        },
    )
    assert public_response.status_code == 200
    result = public_response.json["result"]
    # The tool response is now in MCP context format
    assert "representation" in result
    assert "content" in result["representation"]


def test_tool_decorator_with_permissions(pyramid_app):
    """Test that @tool decorator respects permission settings."""
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "decorator-perm-server",
        "mcp.server_version": "1.0.0",
    }

    app = pyramid_app(settings)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    )
    assert init_response.status_code == 200

    # Test secure tool without authentication - should fail
    secure_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 2,
            "params": {
                "name": "decorator_secure_data",
                "arguments": {"data_id": 1},
            },
        },
    )
    assert secure_response.status_code == 200
    assert "error" in secure_response.json
    # Should get access denied due to missing authentication

    # Test secure tool with authentication - should work
    secure_with_auth_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": "decorator_secure_data",
                "arguments": {"data_id": 1, "auth": {"auth_token": "valid_jwt_token"}},
            },
        },
    )
    assert secure_with_auth_response.status_code == 200
    result = secure_with_auth_response.json["result"]
    # The tool response is now in MCP context format
    assert "representation" in result
    assert "content" in result["representation"]


def test_unified_security_architecture_tool_input_schemas(pyramid_app):
    """Test that unified security architecture properly modifies tool input schemas."""
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "schema-test-server",
        "mcp.server_version": "1.0.0",
        "mcp.filter_forbidden_tools": "false",  # Disable filtering to test schema  # noqa: E501
    }

    app = pyramid_app(settings)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    )
    assert init_response.status_code == 200

    # List tools to check input schemas
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tools_by_name = {tool["name"]: tool for tool in tools}

    # Check secure tool has auth_token in input schema under auth object
    secure_tool = tools_by_name.get("decorator_secure_data")
    assert secure_tool is not None
    input_schema = secure_tool["inputSchema"]

    # Auth parameters should be under auth object
    assert "auth" in input_schema["properties"]
    auth_props = input_schema["properties"]["auth"]["properties"]
    assert "auth_token" in auth_props  # Auth token under auth object

    # POST request parameters should be under body
    assert "body" in input_schema["properties"]
    body_props = input_schema["properties"]["body"]["properties"]
    assert "data_id" in body_props  # Original parameter preserved in body

    # Check public tool doesn't have auth object in input schema
    public_tool = tools_by_name.get("decorator_public_info")
    assert public_tool is not None
    input_schema = public_tool["inputSchema"]
    assert "auth" not in input_schema.get("properties", {})

    # POST request parameters should be under body
    assert "body" in input_schema["properties"]
    body_props = input_schema["properties"]["body"]["properties"]
    assert "info_id" in body_props  # Original parameter preserved in body


def test_tool_security_parameter_integration():
    """Test that security parameter is properly integrated with tool definitions."""
    # The @tool decorator doesn't add attributes to the original function
    # Instead, it uses Venusian for deferred registration during config.scan()
    # Test that the functions are still callable
    assert callable(decorator_secure_data)
    assert callable(decorator_public_info)

    # Test that functions can be called directly with required parameters
    result = decorator_secure_data(data_id=1)  # Use valid data_id
    assert (
        "secured_by" in result or "auth_required" in result
    )  # Check for security-related keys

    result = decorator_public_info(info_id=1)
    assert "public" in result or "auth_required" in result


def test_tool_decorator_metadata_storage():
    """Test that @tool decorator doesn't modify the original functions."""
    # The @tool decorator returns the original function unchanged
    # Metadata is stored via Venusian for deferred registration

    # Test that original functions are unchanged
    verification_tool = decorator_verification_tool
    assert callable(verification_tool)
    assert verification_tool(message="test") == "Decorator tool response: test"

    # Test secure tool function works
    secure_tool = decorator_secure_data
    assert callable(secure_tool)
    result = secure_tool(data_id=1)  # Use valid data_id
    assert (
        "secured_by" in result or "auth_required" in result
    )  # Check for security-related keys

    # Test public tool function works
    public_tool = decorator_public_info
    assert callable(public_tool)
    result = public_tool(info_id=1)
    assert "public" in result or "auth_required" in result
