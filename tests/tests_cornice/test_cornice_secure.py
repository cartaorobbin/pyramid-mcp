"""
Test for secure Cornice service with real authentication.

This test demonstrates:
- One permission-protected Cornice service
- Real JWT authentication (no mocking)
- Tool listing functionality with security integration
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields

# =============================================================================
# 📊 MARSHMALLOW SCHEMA
# =============================================================================


class CreateUserSchema(Schema):
    """Schema for user creation."""

    username = fields.Str(required=True, metadata={"description": "Username"})
    email = fields.Email(required=True, metadata={"description": "User email"})
    role = fields.Str(missing="user", metadata={"description": "User role"})


# =============================================================================
# 🏗️ SECURE CORNICE SERVICE
# =============================================================================


@pytest.fixture
def secure_user_service():
    """Create a secure user management service."""
    users = Service(
        name="secure_users",
        path="/secure/users",
        description="Secure user management service",
        mcp_security="bearer",
    )

    @users.post(
        schema=CreateUserSchema,
        validators=(marshmallow_body_validator,),
        permission="authenticated",
    )
    def create_secure_user(request):
        """Create user (requires authentication)."""
        validated_data = request.validated
        user = {
            "id": 42,
            "username": validated_data["username"],
            "email": validated_data["email"],
            "role": validated_data.get("role", "user"),
            "status": "created",
            "secure": True,
        }
        return {"user": user, "message": "Secure user created successfully"}

    @users.get(permission="authenticated")
    def get_secure_users(request):
        """Get users list (requires authentication)."""
        users_list = [
            {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "role": "admin",
            },
            {"id": 2, "username": "bob", "email": "bob@example.com", "role": "user"},
            {
                "id": 3,
                "username": "charlie",
                "email": "charlie@example.com",
                "role": "user",
            },
        ]
        return {"users": users_list, "total": len(users_list), "secure": True}

    return users


# =============================================================================
# 🧪 SECURITY TEST
# =============================================================================


def test_secure_cornice_service_tools_list(
    pyramid_app_with_services, secure_user_service
):
    """Test that secure Cornice service appears in MCP tools list."""
    app = pyramid_app_with_services([secure_user_service])

    # Test MCP tools list
    list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
    }

    response = app.post_json("/mcp", list_request)
    assert response.status_code == 200
    assert "result" in response.json

    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should find the secure user creation tool
    assert "create_secure_users" in tool_names

    # Find the specific tool and verify it has proper schema
    secure_tool = None
    for tool in tools:
        if tool["name"] == "create_secure_users":
            secure_tool = tool
            break

    assert secure_tool is not None
    assert "inputSchema" in secure_tool
    assert "description" in secure_tool

    # Verify schema has expected fields
    schema = secure_tool["inputSchema"]
    assert "properties" in schema
    assert "username" in schema["properties"]
    assert "email" in schema["properties"]
    assert "role" in schema["properties"]

    # Verify Bearer auth requirement is exposed in schema
    assert "auth_token" in schema["properties"]
    assert schema["properties"]["auth_token"]["type"] == "string"

    # Verify the schema has correct type field
    assert (
        schema.get("type") == "object"
    ), f"Schema type is '{schema.get('type')}', expected 'object'"


def test_secure_get_endpoint_requires_auth(
    pyramid_app_with_services, secure_user_service
):
    """Test that GET endpoint requires authentication and fails without it."""
    app = pyramid_app_with_services([secure_user_service])

    # First verify the GET tool appears in tools list
    list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
    }

    response = app.post_json("/mcp", list_request)
    assert response.status_code == 200
    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should find both POST and GET tools
    assert "create_secure_users" in tool_names
    assert "list_secure_users" in tool_names

    # Try to call the GET endpoint without authentication - should fail
    call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "list_secure_users", "arguments": {}},
    }

    response = app.post_json("/mcp", call_request, expect_errors=True)

    # Should get an authentication error - handled at permission check level
    assert response.status_code == 200  # JSON-RPC always returns 200
    assert "error" in response.json  # Permission check fails

    error = response.json["error"]
    assert error["code"] == -32603  # INTERNAL_ERROR (permission denied)

    # Should contain authentication/permission error
    assert "unauthorized" in error["message"].lower()


def test_secure_endpoints_authentication_integration(
    pyramid_app_with_services, secure_user_service
):
    """Test that secure endpoints properly integrate with authentication system.

    This test demonstrates that:
    1. Tools with permissions are discovered correctly
    2. Authentication tokens are processed by pyramid-mcp
    3. The request reaches the Pyramid view (where actual authorization happens)
    """
    app = pyramid_app_with_services([secure_user_service])

    # Test that authentication tokens are properly processed
    create_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_secure_users",
            "arguments": {
                "username": "testuser",
                "email": "testuser@example.com",
                "role": "admin",
                "auth_token": "valid_bearer_token_123",
            },
        },
    }

    response = app.post_json("/mcp", create_request)
    assert response.status_code == 200
    assert "result" in response.json

    # The tool should execute and reach the Pyramid view
    # (even though the view may still fail authorization in this test setup)
    result = response.json["result"]
    assert result["type"] == "mcp/context"
    assert "representation" in result

    # This proves that:
    # 1. The MCP tool was found and has proper permissions
    # 2. The auth_token was processed and removed from arguments
    # 3. The request reached the actual Pyramid view and succeeded
    content = result["representation"]["content"]

    # Should show successful user creation (authentication worked)
    assert "user" in content  # User was created successfully
    assert "testuser" in str(content)  # Shows the correct user was created
    assert "auth_token" not in str(
        content
    )  # Auth token was properly removed from params
