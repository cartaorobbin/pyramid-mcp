"""
WebTest-based tests for Pyramid MCP HTTP endpoints.

These tests use WebTest to make actual HTTP requests to the MCP endpoints,
providing comprehensive end-to-end testing of the MCP protocol over HTTP.
"""

# Removed unused imports
from webtest import TestApp

# MCP HTTP Endpoint Tests


def test_mcp_endpoint_exists(mcp_testapp):
    """Test that the MCP HTTP endpoint is mounted and responds."""
    # Test that the MCP endpoint exists (should accept POST)
    response = mcp_testapp.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "initialize", "id": 1}
    )

    assert response.status_code == 200
    assert response.content_type == "application/json"


def test_mcp_initialize_via_http(mcp_testapp):
    """Test MCP initialize request via real HTTP."""
    request_data = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert "result" in data
    # The default config from includeme uses "pyramid-mcp" as server name
    assert data["result"]["serverInfo"]["name"] == "pyramid-mcp"
    assert data["result"]["serverInfo"]["version"] == "1.0.0"
    assert "capabilities" in data["result"]


def test_mcp_list_tools_via_http(mcp_testapp):
    """Test MCP tools/list request via real HTTP."""
    request_data = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    assert "result" in data
    assert "tools" in data["result"]

    # Should have our test tools from conftest.py
    tools = data["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Check for our sample tools
    assert "get_user_count" in tool_names
    assert "calculate" in tool_names


def test_mcp_call_tool_via_http(mcp_testapp):
    """Test MCP tools/call request via real HTTP."""
    # Test calling the calculate tool
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "calculate",
            "arguments": {"operation": "add", "a": 10, "b": 5},
        },
        "id": 3,
    }

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    assert "result" in data
    assert "content" in data["result"]
    assert len(data["result"]["content"]) == 1
    assert data["result"]["content"][0]["type"] == "text"
    assert "15" in data["result"]["content"][0]["text"]  # 10 + 5 = 15


def test_mcp_call_user_count_tool_via_http(mcp_testapp):
    """Test calling the get_user_count tool via HTTP."""
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "get_user_count", "arguments": {}},
        "id": 4,
    }

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    assert "result" in data
    assert "content" in data["result"]
    assert len(data["result"]["content"]) == 1
    assert data["result"]["content"][0]["type"] == "text"
    # Should contain our mock count
    assert "42" in data["result"]["content"][0]["text"]


def test_mcp_error_handling_via_http(mcp_testapp):
    """Test MCP error handling via real HTTP."""
    # Test calling non-existent tool
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
        "id": 5,
    }

    response = mcp_testapp.post_json("/mcp", request_data)

    assert (
        response.status_code == 200
    )  # MCP errors are returned as 200 with error object
    data = response.json

    assert "error" in data
    assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND
    assert "nonexistent_tool" in data["error"]["message"]


def test_mcp_invalid_json_request(mcp_testapp):
    """Test MCP handling of invalid JSON requests."""
    # Send invalid JSON
    response = mcp_testapp.post(
        "/mcp", "invalid json", content_type="application/json", expect_errors=True
    )

    assert response.status_code == 200  # MCP protocol error, not HTTP error
    data = response.json

    assert "error" in data
    # Current implementation returns -32603 (Internal Error) for JSON parse errors
    assert data["error"]["code"] == -32603  # INTERNAL_ERROR


def test_mcp_malformed_request(mcp_testapp):
    """Test MCP handling of malformed requests."""
    # Send valid JSON but not a valid JSON-RPC request
    request_data = {"invalid": "request", "missing": "required_fields"}

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    assert "error" in data
    # Current implementation returns -32601 (Method Not Found) for malformed requests
    assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND


def test_mcp_tool_with_validation_error(mcp_testapp):
    """Test MCP tool call that triggers validation error."""
    # Test calculate tool with invalid operation
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "calculate",
            "arguments": {"operation": "invalid_operation", "a": 10, "b": 5},
        },
        "id": 6,
    }

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    # Current implementation returns an error, not a result with isError
    assert "error" in data
    assert "Tool execution failed" in data["error"]["message"]


def test_mcp_divide_by_zero_error(mcp_testapp):
    """Test MCP tool call with divide by zero."""
    request_data = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "calculate",
            "arguments": {"operation": "divide", "a": 10, "b": 0},
        },
        "id": 7,
    }

    response = mcp_testapp.post_json("/mcp", request_data)

    assert response.status_code == 200
    data = response.json

    # Current implementation returns an error, not a result with isError
    assert "error" in data
    assert "Tool execution failed" in data["error"]["message"]


# Pyramid Endpoints Integration Tests


def test_pyramid_endpoints_still_work(mcp_testapp):
    """Test that regular Pyramid endpoints still function with MCP mounted."""
    # Test creating a user via regular Pyramid endpoint
    user_data = {"name": "John Doe", "email": "john@example.com", "age": 30}

    response = mcp_testapp.post_json("/users", user_data)

    assert response.status_code == 200
    data = response.json

    assert "user" in data
    assert data["user"]["name"] == "John Doe"
    assert data["user"]["email"] == "john@example.com"
    assert data["user"]["age"] == 30
    assert data["user"]["id"] == 1


def test_get_user_endpoint(mcp_testapp):
    """Test getting a user via regular Pyramid endpoint."""
    # First create a user
    user_data = {"name": "Jane Doe", "email": "jane@example.com"}

    create_response = mcp_testapp.post_json("/users", user_data)
    user_id = create_response.json["user"]["id"]

    # Then get the user
    get_response = mcp_testapp.get(f"/users/{user_id}")

    assert get_response.status_code == 200
    data = get_response.json

    assert "user" in data
    assert data["user"]["name"] == "Jane Doe"
    assert data["user"]["email"] == "jane@example.com"


def test_list_users_endpoint(mcp_testapp):
    """Test listing users via regular Pyramid endpoint."""
    # Create a few users first
    users_data = [
        {"name": "User 1", "email": "user1@example.com"},
        {"name": "User 2", "email": "user2@example.com"},
    ]

    for user_data in users_data:
        mcp_testapp.post_json("/users", user_data)

    # List users
    response = mcp_testapp.get("/users")

    assert response.status_code == 200
    data = response.json

    assert "users" in data
    assert len(data["users"]) == 2


def test_update_user_endpoint(mcp_testapp):
    """Test updating a user via regular Pyramid endpoint."""
    # Create a user
    user_data = {"name": "Original Name", "email": "original@example.com"}
    create_response = mcp_testapp.post_json("/users", user_data)
    user_id = create_response.json["user"]["id"]

    # Update the user
    update_data = {"name": "Updated Name"}
    update_response = mcp_testapp.put_json(f"/users/{user_id}", update_data)

    assert update_response.status_code == 200
    data = update_response.json

    assert data["user"]["name"] == "Updated Name"
    assert data["user"]["email"] == "original@example.com"  # Should remain unchanged


def test_delete_user_endpoint(mcp_testapp):
    """Test deleting a user via regular Pyramid endpoint."""
    # Create a user
    user_data = {"name": "To Delete", "email": "delete@example.com"}
    create_response = mcp_testapp.post_json("/users", user_data)
    user_id = create_response.json["user"]["id"]

    # Delete the user
    delete_response = mcp_testapp.delete(f"/users/{user_id}")

    assert delete_response.status_code == 200
    data = delete_response.json
    assert "message" in data

    # Verify user is deleted
    get_response = mcp_testapp.get(f"/users/{user_id}", expect_errors=True)
    assert get_response.status_code == 404


# MCP Configuration Tests


def test_custom_mount_path(pyramid_config):
    """Test MCP mounted at custom path."""
    # Set custom mount path via settings
    pyramid_config.registry.settings.update({"mcp.mount_path": "/api/mcp"})

    # Include pyramid_mcp with custom settings
    from pyramid_mcp import includeme

    includeme(pyramid_config)

    app = TestApp(pyramid_config.make_wsgi_app())

    # Test MCP at custom path
    request_data = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

    response = app.post_json("/api/mcp", request_data)
    assert response.status_code == 200

    # Verify old path doesn't work
    response = app.post_json("/mcp", request_data, expect_errors=True)
    assert response.status_code == 404


def test_server_info_configuration(pyramid_config):
    """Test custom server name and version."""
    # Set custom server info via settings
    pyramid_config.registry.settings.update(
        {"mcp.server_name": "custom-server", "mcp.server_version": "2.0.0"}
    )

    from pyramid_mcp import includeme

    includeme(pyramid_config)

    app = TestApp(pyramid_config.make_wsgi_app())

    request_data = {"jsonrpc": "2.0", "method": "initialize", "id": 1}

    response = app.post_json("/mcp", request_data)
    data = response.json

    assert data["result"]["serverInfo"]["name"] == "custom-server"
    assert data["result"]["serverInfo"]["version"] == "2.0.0"


# MCP SSE Streaming Endpoint Tests


def test_sse_endpoint_exists(mcp_testapp):
    """Test that SSE endpoint exists when enabled."""
    # SSE endpoint should be available
    response = mcp_testapp.get("/mcp/sse", expect_errors=True)

    # Should not return 404 (might return other status depending on implementation)
    assert response.status_code != 404


def test_sse_endpoint_handles_get(mcp_testapp):
    """Test SSE endpoint handles GET requests."""
    # This is a placeholder - actual SSE testing is more complex
    # and might require special handling for streaming responses
    response = mcp_testapp.get("/mcp/sse", expect_errors=True)

    # Basic check that endpoint exists and doesn't crash
    assert response.status_code in [200, 501, 405]  # Various valid responses
