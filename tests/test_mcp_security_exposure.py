"""Test MCP security parameter exposure using the fixture."""

from pyramid.view import view_config


@view_config(route_name="test_secure", renderer="json", mcp_security="bearer")
def test_secure_view(request):
    """Test view with bearer auth."""
    return {"message": "secure view"}


def test_mcp_security_parameters_exposed(pyramid_app_with_views):
    """Test that mcp_security parameters are exposed in tool schemas."""

    routes = [("test_secure", "/test-secure")]
    app = pyramid_app_with_views(routes)

    # Initialize MCP
    init_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        },
    )
    assert init_response.status_code == 200

    # List tools
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 2, "params": {}}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    test_secure_tool = next(tool for tool in tools if tool["name"] == "get_test_secure")

    assert "inputSchema" in test_secure_tool
    properties = test_secure_tool["inputSchema"]["properties"]
    assert "auth_token" in properties
    assert properties["auth_token"]["type"] == "string"
