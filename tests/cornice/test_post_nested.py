"""
Test for Cornice query string validation.

This test explores how Cornice implements validation of query string parameters
using Marshmallow schemas with the marshmallow_querystring_validator.
"""

from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields, pre_load
from pyramid.response import Response


class SubSchema(Schema):
    path = fields.Str(required=True)

    @pre_load
    def pre_load(self, data, **kwargs):
        data["path"] = self.context["request"].path
        return data


class RequetsSchema(Schema):
    path = fields.Str(required=True)
    method = fields.Str(required=True)
    sub = fields.Nested(SubSchema, required=False)

    @pre_load
    def pre_load(self, data, **kwargs):
        data["path"] = self.context["request"].path
        data["sub"] = {"path": "sub"}
        return data


class ParentSchema(Schema):
    """Schema for pagination query parameters."""

    # child = fields.Nested(ChildSchema, required=True)
    name = fields.Str(required=True)
    request = fields.Nested(RequetsSchema, required=False)


def test_cornice_post(pyramid_app_with_services, logs):
    """Test that Cornice validates query string parameters using Marshmallow schema."""

    # Create a Cornice service with querystring validation
    users_service = Service(
        name="users",
        path="/api/v1/users",
        description="List users with pagination query parameters",
    )

    @users_service.post(schema=ParentSchema, validators=(marshmallow_body_validator,))
    def create_users(request):
        """List users with validated pagination parameters."""
        # Return validated parameters directly
        return Response(json=request.validated)

    # Create test app with the service
    app = pyramid_app_with_services([users_service])

    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    # Test MCP tool call with valid querystring parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tools_response.json["result"]["tools"][0]["name"],
            "arguments": {"name": "John Doe", "request": {"method": "POST"}},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed with validated query parameters
    assert response.status_code == 200
    result = response.json
    assert result["id"] == 1
    assert "result" in result
    # The actual response data should be in the MCP context format
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"

    # Verify the response has the expected structure
    assert "representation" in mcp_result
    assert "content" in mcp_result["representation"]

    app.post_json("/api/v1/users", {"name": "John Doe", "request": {"method": "POST"}})
