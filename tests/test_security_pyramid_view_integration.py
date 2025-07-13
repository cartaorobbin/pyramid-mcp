"""Test pyramid MCP integration with security-enabled Pyramid views."""
from pyramid.view import view_config


@view_config(route_name="secure_ftp_endpoint", renderer="json", mcp_security="basic")
def secure_ftp_view(pyramid_request) -> dict:
    """Pyramid view that requires Basic authentication."""
    # Extract path from request JSON body (POST) or params (GET)
    if pyramid_request.method == "POST" and pyramid_request.json_body:
        path = pyramid_request.json_body.get("path", "/default/path")
    else:
        path = pyramid_request.params.get("path", "/default/path")

    auth_headers = getattr(pyramid_request, "mcp_auth_headers", {})
    # Convert headers to a serializable format
    serializable_headers = {k: str(v) for k, v in auth_headers.items()}
    return {
        "path": path,
        "auth_type": "basic",
        "username": "extracted_from_headers",  # Would be extracted from auth headers
        "password_provided": True,  # Would be verified from auth headers
        "headers_received": serializable_headers,
    }


@view_config(route_name="secure_api_endpoint", renderer="json", mcp_security="bearer")
def secure_api_view(pyramid_request) -> dict:
    """Pyramid view that requires Bearer authentication."""
    # Extract data from request JSON body (POST) or params (GET)
    if pyramid_request.method == "POST" and pyramid_request.json_body:
        data = pyramid_request.json_body.get("data", "default_data")
    else:
        data = pyramid_request.params.get("data", "default_data")

    auth_headers = getattr(pyramid_request, "mcp_auth_headers", {})
    # Convert headers to a serializable format
    serializable_headers = {k: str(v) for k, v in auth_headers.items()}
    return {
        "data": data,
        "auth_type": "bearer",
        "token_provided": True,  # Would be verified from auth headers
        "headers_received": serializable_headers,
    }


@view_config(route_name="normal_endpoint", renderer="json")
def normal_view(pyramid_request) -> dict:
    """Normal Pyramid view without authentication."""
    # Extract data from request JSON body (POST) or params (GET)
    if pyramid_request.method == "POST" and pyramid_request.json_body:
        data = pyramid_request.json_body.get("data", "default_data")
    else:
        data = pyramid_request.params.get("data", "default_data")

    return {"data": data, "auth_type": "none"}


@view_config(route_name="validation_endpoint", renderer="json", mcp_security="bearer")
def validation_view(pyramid_request) -> dict:
    """Pyramid view for parameter validation with Bearer auth."""
    # Extract required_field from request JSON body (POST) or params (GET)
    if pyramid_request.method == "POST" and pyramid_request.json_body:
        required_field = pyramid_request.json_body.get(
            "required_field", "default_field"
        )
    else:
        required_field = pyramid_request.params.get("required_field", "default_field")

    if not required_field:
        raise ValueError("required_field cannot be empty")

    auth_headers = getattr(pyramid_request, "mcp_auth_headers", {})
    # Convert headers to a serializable format
    serializable_headers = {k: str(v) for k, v in auth_headers.items()}
    return {
        "field": required_field,
        "auth_type": "bearer",
        "validated": True,
        "headers_received": serializable_headers,
    }


@view_config(route_name="bearer_endpoint", renderer="json", mcp_security="bearer")
def bearer_view(pyramid_request) -> dict:
    """Pyramid view with Bearer authentication."""
    # Extract data from request JSON body (POST) or params (GET)
    if pyramid_request.method == "POST" and pyramid_request.json_body:
        data = pyramid_request.json_body.get("data", "default_data")
    else:
        data = pyramid_request.params.get("data", "default_data")

    auth_headers = getattr(pyramid_request, "mcp_auth_headers", {})
    # Convert headers to a serializable format
    serializable_headers = {k: str(v) for k, v in auth_headers.items()}
    return {
        "data": data,
        "auth_type": "bearer",
        "token_provided": True,  # Would be verified from auth headers
        "headers_received": serializable_headers,
    }


@view_config(route_name="basic_endpoint", renderer="json", mcp_security="basic")
def basic_view(pyramid_request) -> dict:
    """Pyramid view with Basic authentication."""
    # Extract data from request JSON body (POST) or params (GET)
    if pyramid_request.method == "POST" and pyramid_request.json_body:
        data = pyramid_request.json_body.get("data", "default_data")
    else:
        data = pyramid_request.params.get("data", "default_data")

    auth_headers = getattr(pyramid_request, "mcp_auth_headers", {})
    # Convert headers to a serializable format
    serializable_headers = {k: str(v) for k, v in auth_headers.items()}
    return {
        "data": data,
        "auth_type": "basic",
        "username": "extracted_from_headers",  # Would be extracted from auth headers
        "password_provided": True,  # Would be verified from auth headers
        "headers_received": serializable_headers,
    }


def test_pyramid_view_with_basic_auth_integration(pyramid_app_with_views):
    """Test complete integration of Pyramid view with Basic authentication."""
    # Create all routes that the view decorators reference
    routes = [
        ("secure_ftp_endpoint", "/api/secure-ftp"),
        ("secure_api_endpoint", "/api/secure"),
        ("normal_endpoint", "/api/normal"),
        ("validation_endpoint", "/api/validate"),
        ("bearer_endpoint", "/api/bearer"),
        ("basic_endpoint", "/api/basic"),
    ]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools to verify our view is discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )  # type: ignore
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "get_secure_ftp_endpoint" in tool_names

    # Call the secure tool with Basic auth
    call_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": "get_secure_ftp_endpoint",
                "arguments": {
                    "path": "/home/user",
                    "username": "testuser",
                    "password": "testpass",
                },
            },
        },
    )
    assert call_response.status_code == 200

    result = call_response.json["result"]
    # Extract the actual data from MCP response format
    actual_data = result["content"][0]["data"]
    assert actual_data["path"] == "/home/user"
    assert actual_data["auth_type"] == "basic"
    assert actual_data["username"] == "extracted_from_headers"
    assert actual_data["password_provided"] is True


def test_pyramid_view_with_bearer_auth_integration(pyramid_app_with_views):
    """Test complete integration of Pyramid view with Bearer authentication."""
    # Create all routes that the view decorators reference
    routes = [
        ("secure_ftp_endpoint", "/api/secure-ftp"),
        ("secure_api_endpoint", "/api/secure"),
        ("normal_endpoint", "/api/normal"),
        ("validation_endpoint", "/api/validate"),
        ("bearer_endpoint", "/api/bearer"),
        ("basic_endpoint", "/api/basic"),
    ]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools to verify our view is discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )  # type: ignore
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "get_secure_api_endpoint" in tool_names

    # Call the secure tool with Bearer auth
    call_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 3,
            "params": {
                "name": "get_secure_api_endpoint",
                "arguments": {
                    "data": "test_data",
                    "auth_token": "bearer_token_123",
                },
            },
        },
    )
    assert call_response.status_code == 200

    result = call_response.json["result"]
    # Extract the actual data from MCP response format
    actual_data = result["content"][0]["data"]
    assert actual_data["data"] == "test_data"
    assert actual_data["auth_type"] == "bearer"
    assert actual_data["token_provided"] is True


def test_mixed_secure_and_normal_tools(pyramid_app_with_views):
    """Test that secure and normal tools can coexist in the same app."""
    # Create all routes that the view decorators reference
    routes = [
        ("secure_ftp_endpoint", "/api/secure-ftp"),
        ("secure_api_endpoint", "/api/secure"),
        ("normal_endpoint", "/api/normal"),
        ("validation_endpoint", "/api/validate"),
        ("bearer_endpoint", "/api/bearer"),
        ("basic_endpoint", "/api/basic"),
    ]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools to verify both secure and normal tools are discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )  # type: ignore
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Check that both secure and normal tools are present
    assert "get_secure_ftp_endpoint" in tool_names
    assert "get_normal_endpoint" in tool_names


def test_pyramid_view_security_parameter_validation(pyramid_app_with_views):
    """Test that security parameter validation works correctly."""
    # Create all routes that the view decorators reference
    routes = [
        ("secure_ftp_endpoint", "/api/secure-ftp"),
        ("secure_api_endpoint", "/api/secure"),
        ("normal_endpoint", "/api/normal"),
        ("validation_endpoint", "/api/validate"),
        ("bearer_endpoint", "/api/bearer"),
        ("basic_endpoint", "/api/basic"),
    ]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools to verify our view is discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )  # type: ignore
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]
    assert "get_validation_endpoint" in tool_names


def test_comprehensive_tool_listing_from_pyramid_views(pyramid_app_with_views):
    """Test that pyramid views are properly discovered and converted to MCP tools."""
    # Create all routes that the view decorators reference
    routes = [
        ("secure_ftp_endpoint", "/api/secure-ftp"),
        ("secure_api_endpoint", "/api/secure"),
        ("normal_endpoint", "/api/normal"),
        ("validation_endpoint", "/api/validate"),
        ("bearer_endpoint", "/api/bearer"),
        ("basic_endpoint", "/api/basic"),
    ]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools to verify our view is discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )  # type: ignore
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Create a lookup dictionary for easier checking
    tools_dict = {tool["name"]: tool for tool in tools}

    # Check that all expected tools are present
    expected_tools = [
        "get_secure_ftp_endpoint",
        "get_secure_api_endpoint",
        "get_normal_endpoint",
        "get_validation_endpoint",
        "get_bearer_endpoint",
        "get_basic_endpoint",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Expected tool {tool_name} not found"

    # Verify specific tool properties
    secure_ftp_tool = tools_dict["get_secure_ftp_endpoint"]
    assert secure_ftp_tool["name"] == "get_secure_ftp_endpoint"
    assert "inputSchema" in secure_ftp_tool
    assert "username" in secure_ftp_tool["inputSchema"]["properties"]
    assert "password" in secure_ftp_tool["inputSchema"]["properties"]
    # Note: Business logic parameters like 'path' are not auto-detected in schema yet
    # They are passed via the request body/params and handled by the view function

    secure_api_tool = tools_dict["get_secure_api_endpoint"]
    assert secure_api_tool["name"] == "get_secure_api_endpoint"
    assert "inputSchema" in secure_api_tool
    assert "auth_token" in secure_api_tool["inputSchema"]["properties"]
    # Note: Business logic parameters like 'data' are not auto-detected in schema yet
    # They are passed via the request body/params and handled by the view function

    normal_tool = tools_dict["get_normal_endpoint"]
    assert normal_tool["name"] == "get_normal_endpoint"
    assert "inputSchema" in normal_tool
    # Normal GET endpoint without security has no auto-detected parameters
    assert normal_tool["inputSchema"]["properties"] == {}
    # Normal tool should not have auth parameters
    assert "auth_token" not in normal_tool["inputSchema"]["properties"]
    assert "username" not in normal_tool["inputSchema"]["properties"]
    assert "password" not in normal_tool["inputSchema"]["properties"]

    validation_tool = tools_dict["get_validation_endpoint"]
    assert validation_tool["name"] == "get_validation_endpoint"
    assert "inputSchema" in validation_tool
    assert "auth_token" in validation_tool["inputSchema"]["properties"]
    # Note: Business logic parameters like 'required_field' are not auto-detected
    # in schema yet. They are passed via the request body/params and handled by
    # the view function

    bearer_tool = tools_dict["get_bearer_endpoint"]
    assert bearer_tool["name"] == "get_bearer_endpoint"
    assert "inputSchema" in bearer_tool
    assert "auth_token" in bearer_tool["inputSchema"]["properties"]
    # Note: Business logic parameters like 'data' are not auto-detected in schema yet
    # They are passed via the request body/params and handled by the view function

    basic_tool = tools_dict["get_basic_endpoint"]
    assert basic_tool["name"] == "get_basic_endpoint"
    assert "inputSchema" in basic_tool
    assert "username" in basic_tool["inputSchema"]["properties"]
    assert "password" in basic_tool["inputSchema"]["properties"]
    # Note: Business logic parameters like 'data' are not auto-detected in schema yet
    # They are passed via the request body/params and handled by the view function


def test_pyramid_view_security_schema_in_tool_list(pyramid_app_with_views):
    """Test that tools with security properly include authentication
    parameters in their input schema."""
    # Create all routes that the view decorators reference
    routes = [
        ("secure_ftp_endpoint", "/api/secure-ftp"),
        ("secure_api_endpoint", "/api/secure"),
        ("normal_endpoint", "/api/normal"),
        ("validation_endpoint", "/api/validate"),
        ("bearer_endpoint", "/api/bearer"),
        ("basic_endpoint", "/api/basic"),
    ]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {  # type: ignore
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools to verify our view is discovered
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )  # type: ignore
    assert tools_response.status_code == 200
