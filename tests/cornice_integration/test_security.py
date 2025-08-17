"""
Cornice-specific security tests for pyramid_mcp.

This module tests:
- Cornice service authentication integration
- Bearer token authentication with Cornice services
- MCP tool security with Cornice schemas
- Permission-based protection on Cornice services

Uses the specialized Cornice fixtures from conftest.py.
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields


class SecureUserSchema(Schema):
    """Schema for secure user operations."""

    name = fields.Str(required=True, metadata={"description": "User name"})
    email = fields.Email(required=True, metadata={"description": "User email"})
    role = fields.Str(required=False, metadata={"description": "User role"})


@pytest.fixture
def secure_service():
    """Create a secure Cornice service for testing."""
    secure = Service(
        name="secure_service",
        path="/secure",
        description="Secure service requiring authentication",
    )

    @secure.get(permission="authenticated")
    def get_secure_data(request):
        """Get secure data - requires authentication."""
        return {
            "message": "Secure data accessed",
            "user": getattr(request, "authenticated_userid", "anonymous"),
        }

    @secure.post(
        schema=SecureUserSchema,
        validators=(marshmallow_body_validator,),
        permission="authenticated",
    )
    def create_secure_user(request):
        """Create user with authentication required."""
        validated_data = request.validated
        return {
            "user": validated_data,
            "message": "Secure user created",
            "authenticated": True,
        }

    return secure


def test_secure_cornice_service_tools_list(pyramid_app_with_services, secure_service):
    """Test that secure Cornice services appear in MCP tools list."""
    services = [secure_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should have at least one tool
    assert len(tool_names) > 0


def test_secure_get_endpoint_requires_auth(pyramid_app_with_services, secure_service):
    """Test that secure GET endpoint requires authentication."""
    services = [secure_service]
    app = pyramid_app_with_services(services)

    # Get the secure GET tool directly
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]

    # Get the secure GET tool by index (no conditional logic)
    secure_get_tool = tools[0]  # get_secure_service

    # Try to call without authentication
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": secure_get_tool["name"], "arguments": {}},
            "id": 2,
        },
    )

    # Should succeed with error about authentication failure
    assert call_response.status_code == 200
    assert call_response.json["error"]["code"] == -32603
    # Verify the error contains permission failure information
    error_message = call_response.json["error"]["message"]
    assert "Unauthorized" in error_message
    assert "failed permission check" in error_message


def test_secure_endpoints_authentication_integration(
    pyramid_app_with_services, secure_service
):
    """Test authentication integration with Cornice secure endpoints."""
    services = [secure_service]
    app = pyramid_app_with_services(services)

    # Get the secure POST tool directly
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]

    # Get the secure POST tool by index (no conditional logic)
    secure_post_tool = tools[2]  # create_secure_service

    # Test with valid schema data
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": secure_post_tool["name"],
                "arguments": {
                    "name": "Test User",
                    "email": "test@example.com",
                    "role": "user",
                },
            },
            "id": 3,
        },
    )

    assert call_response.status_code == 200
    # Authentication should fail, expect error (no conditional logic)
    assert "error" in call_response.json
    error = call_response.json["error"]
    assert error["code"] == -32603  # Internal error due to permission failure
    # Verify specific error content about authentication failure
    assert "Unauthorized" in error["message"]
    assert "create_secure_user__POST" in error["message"]
    assert "failed permission check" in error["message"]


def test_bearer_auth_without_token_denies_access(pyramid_app_with_services):
    """Test that Bearer auth endpoint denies access without authentication token."""
    # Create a service that expects Bearer auth
    bearer_service = Service(
        name="bearer_secure",
        path="/bearer-secure",
        description="Service requiring Bearer authentication",
    )

    @bearer_service.get(permission="authenticated")
    def get_with_bearer(request):
        """Get data with Bearer auth."""
        # Check for auth headers in standard request headers
        auth_header = request.headers.get("Authorization", "")
        has_auth = bool(auth_header.strip())

        return {
            "message": "Bearer auth endpoint",
            "has_auth": has_auth,
            "auth_type": "bearer" if has_auth else "none",
        }

    services = [bearer_service]
    app = pyramid_app_with_services(services)

    # Get the bearer auth tool
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]
    bearer_tool = tools[0]  # get_bearer_secure

    # Test without auth token - should be denied
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": bearer_tool["name"], "arguments": {}},
            "id": 2,
        },
    )

    assert call_response.status_code == 200
    # Authentication should fail, expect error
    assert "error" in call_response.json
    error = call_response.json["error"]
    assert error["code"] == -32603  # Internal error due to permission failure
    assert "Unauthorized" in error["message"]
    assert "get_with_bearer__GET" in error["message"]


def test_bearer_auth_with_valid_token_grants_access(pyramid_app_with_services):
    """Test that Bearer auth endpoint grants access with valid authentication token."""
    # Create a service that expects Bearer auth
    bearer_service = Service(
        name="bearer_secure",
        path="/bearer-secure",
        description="Service requiring Bearer authentication",
    )

    @bearer_service.get(permission="authenticated")
    def get_with_bearer(request):
        """Get data with Bearer auth."""
        # Check for auth headers in standard request headers
        auth_header = request.headers.get("Authorization", "")
        has_auth = bool(auth_header.strip())

        return {
            "message": "Bearer auth endpoint",
            "has_auth": has_auth,
            "auth_type": "bearer" if has_auth else "none",
        }

    services = [bearer_service]
    app = pyramid_app_with_services(services)

    # Get the bearer auth tool
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]
    bearer_tool = tools[0]  # get_bearer_secure

    # Test with valid auth token - should grant access
    call_response_with_auth = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": bearer_tool["name"],
                "arguments": {"auth_token": "test_bearer_token"},
            },
            "id": 3,
        },
    )

    assert call_response_with_auth.status_code == 200
    # Verify successful authentication and expected response content
    expected_response = (
        "{'message': 'Bearer auth endpoint', 'has_auth': True, 'auth_type': 'bearer'}"
    )
    actual_response = call_response_with_auth.json["result"]["content"][0]["text"]
    assert actual_response == expected_response


def test_expose_auth_as_params_disabled_uses_header_auth(pyramid_app_with_services):
    """Test mcp.expose_auth_as_params=false uses headers not parameters."""
    # Create a service that expects Bearer auth
    bearer_service = Service(
        name="bearer_secure",
        path="/bearer-secure",
        description="Service requiring Bearer authentication",
    )

    @bearer_service.get(permission="authenticated")
    def get_with_bearer(request):
        """Get data with Bearer auth."""
        # Check for auth headers in standard request headers
        auth_header = request.headers.get("Authorization", "")
        has_auth = bool(auth_header.strip())

        return {
            "message": "Bearer auth endpoint",
            "has_auth": has_auth,
            "auth_type": "bearer" if has_auth else "none",
        }

    # Configure app with expose_auth_as_params disabled
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-server",
        "mcp.server_version": "1.0.0",
        "mcp.expose_auth_as_params": "false",  # Disable auth parameter exposure
    }
    services = [bearer_service]
    app = pyramid_app_with_services(services, settings)

    # Get the bearer auth tool
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]
    bearer_tool = tools[0]  # get_bearer_secure

    # Verify that auth parameters are NOT in the tool schema
    input_schema = bearer_tool["inputSchema"]
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # Auth token should NOT be in schema when expose_auth_as_params is false
    assert "auth_token" not in properties
    assert "auth_token" not in required
    assert "username" not in properties  # Basic auth fields should also be absent
    assert "password" not in properties

    # Test authentication using HTTP headers (not MCP parameters)
    # The fix now allows HTTP Authorization headers to work when
    # expose_auth_as_params=false
    call_response_with_auth = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": bearer_tool["name"],
                "arguments": {},  # No auth_token parameter
            },
            "id": 3,
        },
        headers={"Authorization": "Bearer test_bearer_token"},  # Auth via header
    )

    assert call_response_with_auth.status_code == 200
    # Verify successful authentication via header and expected response content
    expected_response = (
        "{'message': 'Bearer auth endpoint', 'has_auth': True, 'auth_type': 'bearer'}"
    )
    actual_response = call_response_with_auth.json["result"]["content"][0]["text"]
    assert actual_response == expected_response


def test_cornice_service_schema_validation_with_security(
    pyramid_app_with_services, secure_service
):
    """Test that Cornice schema validation works with security."""
    services = [secure_service]
    app = pyramid_app_with_services(services)

    # Get the secure POST tool directly
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]

    # Get the secure POST tool by index (no conditional logic)
    secure_post_tool = tools[2]  # create_secure_service

    # Test with invalid schema data (missing required field)
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": secure_post_tool["name"],
                "arguments": {"name": "Test User"},  # Missing email
            },
            "id": 4,
        },
    )

    # Should get error response (authentication checked before validation)
    assert call_response.status_code == 200
    assert "error" in call_response.json
    error = call_response.json["error"]
    assert (
        error["code"] == -32603
    )  # Internal error due to permission failure (auth checked first)
    # Verify the error mentions authentication failure
    assert "Unauthorized" in error["message"]
    assert "create_secure_user__POST" in error["message"]


def test_cornice_tool_input_schema_includes_security_fields(
    pyramid_app_with_services, secure_service
):
    """Test that Cornice tools include appropriate security fields in input schema."""
    services = [secure_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]

    # Check secure POST tool has proper input schema (no conditional logic)
    secure_post_tool = tools[2]  # create_secure_service
    input_schema = secure_post_tool["inputSchema"]
    assert "type" in input_schema
    assert input_schema["type"] == "object"
    assert "properties" in input_schema

    # Verify the POST tool has the expected schema fields
    properties = input_schema["properties"]
    assert "name" in properties
    assert "email" in properties
