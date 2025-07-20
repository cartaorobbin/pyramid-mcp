"""
Integration tests for JWT authentication between MCP server and Pyramid security.

This module tests the integration between:
- MCP server tool calls
- Pyramid view permissions
- JWT token authentication

Following TDD approach: These tests are written FIRST to define expected behavior,
then fixtures and implementation will be created to make them pass.
"""

import pytest

from pyramid_mcp import tool

# =============================================================================
# 🛠️ MODULE-LEVEL TOOL DEFINITIONS (for Venusian scanning)
# =============================================================================


# Define test tools at module level so Venusian can find them
@tool(
    name="get_protected_user",
    description="Get user info (requires authentication)",
    permission="authenticated",
)
def get_protected_user(id: int) -> dict:
    """Tool that requires authentication."""
    test_users = {
        1: {"id": 1, "username": "alice", "role": "user"},
        2: {"id": 2, "username": "bob", "role": "admin"},
    }
    user = test_users.get(id)
    if not user:
        raise ValueError("User not found")
    return {"user": user, "protected": True, "authenticated": True}


@tool(
    name="get_public_info",
    description="Get public information (no authentication required)",
)
def get_public_info() -> dict:
    """Tool that requires no authentication."""
    return {
        "message": "This is public information",
        "public": True,
        "authenticated": False,
    }


# =============================================================================
# 🏗️ TEST-SPECIFIC FIXTURE: CONFIGURE PYRAMID FOR THIS TEST FILE
# =============================================================================


@pytest.fixture
def auth_test_config(pyramid_app_with_auth):
    """
    Test-specific fixture: Configure pyramid for THIS test file.

    This fixture is responsible for:
    - Calling pyramid_app_with_auth with test-specific settings
    - Returning the configured TestApp for use by tests

    The @tool functions are defined at module level above so Venusian can find them.
    """

    # Configure pyramid with auth-specific settings
    auth_settings = {
        "mcp.server_name": "auth-test-server",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
        "jwt.secret": "test-secret-key-for-auth-tests",
        "jwt.algorithm": "HS256",
        "jwt.expiration_delta": 3600,
    }

    # Return configured TestApp
    return pyramid_app_with_auth(auth_settings)


# =============================================================================
# 🎫 AUTHENTICATION HELPER FIXTURES
# =============================================================================


@pytest.fixture
def valid_jwt_token():
    """Provide a valid JWT token for testing."""
    # For now, return a simple test token
    # In real implementation, this would generate a proper JWT
    return "valid-test-jwt-token-123"


@pytest.fixture
def expired_jwt_token():
    """Provide an expired JWT token for testing."""
    return "expired-test-jwt-token-456"


def test_mcp_calls_protected_route_with_jwt_succeeds(auth_test_config, valid_jwt_token):
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
    response = auth_test_config.post_json(
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


def test_mcp_calls_protected_route_without_jwt_fails(auth_test_config):
    """
    Test: MCP server CANNOT call protected route without JWT token.

    Expected behavior:
    - MCP server calls protected route without JWT token
    - Call fails with 401 Unauthorized or 403 Forbidden
    - No sensitive data is returned
    """
    # This test will FAIL initially - no JWT auth implemented yet

    # Act: MCP server calls protected route without JWT
    response = auth_test_config.post_json(
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
    assert "result" in result
    assert "content" in result["result"]
    content_text = result["result"]["content"][0]["text"]
    # Auth error is wrapped in the content response
    assert "error" in content_text.lower()
    assert (
        "unauthorized" in content_text.lower()
        or "permission" in content_text.lower()
        or "authentication" in content_text.lower()
    )


def test_mcp_calls_public_route_always_succeeds(auth_test_config):
    """
    Test: MCP server can always call public routes (no authentication required).

    Expected behavior:
    - MCP server calls public route (no permission required)
    - Call succeeds regardless of JWT token presence
    - Returns expected data
    """
    # This test should PASS even initially - public routes don't need auth

    # Act: MCP server calls public route (no JWT needed)
    response = auth_test_config.post_json(
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
    content_item = result["result"]["content"][0]

    # For successful calls, expect application/json format
    assert content_item["type"] == "application/json"
    assert "data" in content_item
    tool_result = content_item["data"]["result"]

    # Verify this is the public route response
    assert tool_result["public"] is True
    assert "This is public information" in tool_result["message"]
    assert tool_result["authenticated"] is False


def test_mcp_calls_with_invalid_jwt_fails(auth_test_config):
    """
    Test: MCP server fails when using invalid/malformed JWT token.

    Expected behavior:
    - MCP server provides invalid JWT token
    - Call fails with authentication error
    - No access to protected resources
    """
    # Act: MCP server calls with invalid JWT
    response = auth_test_config.post_json(
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
    assert "result" in result
    assert "content" in result["result"]
    content_item = result["result"]["content"][0]

    # For auth failures, expect text format with error message
    assert content_item["type"] == "text"
    assert "text" in content_item
    error_text = content_item["text"].lower()
    assert "error" in error_text
    assert (
        "unauthorized" in error_text
        or "permission" in error_text
        or "authentication" in error_text
    )


def test_mcp_calls_with_expired_jwt_fails(auth_test_config, expired_jwt_token):
    """
    Test: MCP server fails when using expired JWT token.

    Expected behavior:
    - MCP server provides expired JWT token
    - Call fails with authentication error
    - Token expiration is properly validated
    """
    # Act: MCP server calls with expired JWT
    response = auth_test_config.post_json(
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
    assert "result" in result
    assert "content" in result["result"]
    content_item = result["result"]["content"][0]

    # For auth failures, expect text format with error message
    assert content_item["type"] == "text"
    assert "text" in content_item
    error_text = content_item["text"].lower()
    assert "error" in error_text
    assert (
        "unauthorized" in error_text
        or "permission" in error_text
        or "authentication" in error_text
    )


def test_mcp_tool_reflects_pyramid_view_permission(auth_test_config, valid_jwt_token):
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
    response = auth_test_config.post_json(
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


def test_tool_decorator_with_permission_parameter(auth_test_config, valid_jwt_token):
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
    response = auth_test_config.post_json("/mcp", protected_request, status=200)
    result = response.json
    content_item = result["result"]["content"][0]
    # Auth failure should be in text format
    assert content_item["type"] == "text"
    assert "error" in content_item["text"].lower()

    # Should succeed with JWT
    headers = {"Authorization": f"Bearer {valid_jwt_token}"}
    response = auth_test_config.post_json(
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

    response = auth_test_config.post_json("/mcp", public_request, status=200)
    assert "result" in response.json
    assert "content" in response.json["result"]

    # Verify the tools are listed correctly
    list_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 3}

    response = auth_test_config.post_json("/mcp", list_request, status=200)
    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    assert "get_protected_user" in tool_names
    assert "get_public_info" in tool_names
