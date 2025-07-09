"""
Integration tests for JWT authentication between MCP server and Pyramid security.

This module tests the integration between:
- MCP server tool calls
- Pyramid view permissions
- JWT token authentication

Following TDD approach: These tests are written FIRST to define expected behavior,
then fixtures and implementation will be created to make them pass.
"""


def test_mcp_calls_protected_route_with_jwt_succeeds(
    testapp_with_jwt_auth, valid_jwt_token
):
    """
    Test: MCP server can call protected route when provided with valid JWT token.

    Expected behavior:
    - MCP server receives valid JWT token
    - MCP server calls protected route (requires authentication)
    - Call succeeds and returns expected data
    """
    # This test will FAIL initially - no JWT auth implemented yet

    # Arrange: Set up MCP call to protected route with JWT
    headers = {"Authorization": f"Bearer {valid_jwt_token}"}

    # Act: MCP server calls protected route
    response = testapp_with_jwt_auth.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_protected_user", "arguments": {"id": 1}},
            "id": 1,
        },
        headers=headers,
    )

    # Assert: Call succeeds
    assert response.status_code == 200
    result = response.json
    assert "result" in result
    assert "content" in result["result"]
    content = result["result"]["content"][0]["text"]
    assert "user" in content
    assert "protected" in content


def test_mcp_calls_protected_route_without_jwt_fails(testapp_with_jwt_auth):
    """
    Test: MCP server CANNOT call protected route without JWT token.

    Expected behavior:
    - MCP server calls protected route without JWT token
    - Call fails with 401 Unauthorized or 403 Forbidden
    - No sensitive data is returned
    """
    # This test will FAIL initially - no JWT auth implemented yet

    # Act: MCP server calls protected route without JWT
    response = testapp_with_jwt_auth.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_protected_user", "arguments": {"id": 1}},
            "id": 1,
        },
        # No Authorization header
    )

    # Assert: Call fails with authentication error
    assert response.status_code == 200  # MCP returns 200 with error in payload
    result = response.json
    assert result.get("error") is not None
    error_msg = result["error"]["message"].lower()
    expected_words = ["access denied", "authentication", "token", "permission"]
    assert any(word in error_msg for word in expected_words)


def test_mcp_calls_public_route_always_succeeds(testapp_with_jwt_auth):
    """
    Test: MCP server can always call public routes (no authentication required).

    Expected behavior:
    - MCP server calls public route (no permission required)
    - Call succeeds regardless of JWT token presence
    - Returns expected data
    """
    # This test should PASS even initially - public routes don't need auth

    # Act: MCP server calls public route (no JWT needed)
    response = testapp_with_jwt_auth.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_public_info", "arguments": {}},
            "id": 1,
        },
        # No Authorization header needed for public routes
    )

    # Assert: Call succeeds
    assert response.status_code == 200
    result = response.json
    assert "result" in result
    assert "content" in result["result"]
    content = result["result"]["content"][0]["text"]
    assert "public" in content
    assert "This is public information" in content


def test_mcp_calls_with_invalid_jwt_fails(testapp_with_jwt_auth):
    """
    Test: MCP server fails when using invalid/malformed JWT token.

    Expected behavior:
    - MCP server provides invalid JWT token
    - Call fails with authentication error
    - No access to protected resources
    """
    # Act: MCP server calls with invalid JWT
    response = testapp_with_jwt_auth.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_protected_user", "arguments": {"id": 1}},
            "id": 1,
        },
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )

    # Assert: Call fails
    assert response.status_code == 200  # MCP returns 200 with error in payload
    result = response.json
    assert result.get("error") is not None


def test_mcp_calls_with_expired_jwt_fails(testapp_with_jwt_auth, expired_jwt_token):
    """
    Test: MCP server fails when using expired JWT token.

    Expected behavior:
    - MCP server provides expired JWT token
    - Call fails with authentication error
    - Token expiration is properly validated
    """
    # Act: MCP server calls with expired JWT
    response = testapp_with_jwt_auth.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_protected_user", "arguments": {"id": 1}},
            "id": 1,
        },
        headers={"Authorization": f"Bearer {expired_jwt_token}"},
    )

    # Assert: Call fails due to expired token
    assert response.status_code == 200  # MCP returns 200 with error in payload
    result = response.json
    assert result.get("error") is not None
    error_msg = result["error"]["message"].lower()
    expected_words = ["access denied", "authentication", "token", "permission"]
    assert any(word in error_msg for word in expected_words)


def test_mcp_tool_reflects_pyramid_view_permission(
    testapp_with_jwt_auth, valid_jwt_token
):
    """
    Test: MCP tools respect the permission requirements of underlying Pyramid views.

    Expected behavior:
    - Pyramid view has permission requirement
      (e.g., @view_config(permission='authenticated'))
    - MCP tool for that route inherits the same permission requirement
    - Tool calls are validated against user's permissions
    """
    # This test validates our core integration requirement

    # Act: List available MCP tools
    response = testapp_with_jwt_auth.post_json(
        "/mcp",
        {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1},
        headers={"Authorization": f"Bearer {valid_jwt_token}"},
    )

    # Assert: Tools reflect permission requirements
    assert response.status_code == 200
    tools = response.json["result"]["tools"]

    # Find our protected tool
    protected_tool = next((t for t in tools if t["name"] == "get_protected_user"), None)
    assert protected_tool is not None

    # Verify tool exists and has description indicating authentication requirement
    assert (
        "authentication" in protected_tool["description"].lower()
        or "requires" in protected_tool["description"].lower()
    )


def test_tool_decorator_with_permission_parameter(
    testapp_with_jwt_auth, valid_jwt_token
):
    """Test that the new @tool decorator with permission parameter works correctly."""

    # Create a simple test to verify the decorator functionality
    # The tools are already registered in the fixture using the new decorator syntax

    # Test that the protected tool requires authentication
    protected_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_protected_user", "arguments": {"id": 1}},
        "id": 1,
    }

    # Should fail without JWT
    response = testapp_with_jwt_auth.post_json("/mcp", protected_request, status=200)
    assert "error" in response.json

    # Should succeed with JWT
    headers = {"Authorization": f"Bearer {valid_jwt_token}"}
    response = testapp_with_jwt_auth.post_json(
        "/mcp", protected_request, headers=headers, status=200
    )
    assert "result" in response.json
    assert "content" in response.json["result"]

    # Test that the public tool works without authentication
    public_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_public_info", "arguments": {}},
        "id": 2,
    }

    response = testapp_with_jwt_auth.post_json("/mcp", public_request, status=200)
    assert "result" in response.json
    assert "content" in response.json["result"]

    # Verify the tools are listed correctly
    list_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 3}

    response = testapp_with_jwt_auth.post_json("/mcp", list_request, status=200)
    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    assert "get_protected_user" in tool_names
    assert "get_public_info" in tool_names
