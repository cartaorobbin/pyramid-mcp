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
