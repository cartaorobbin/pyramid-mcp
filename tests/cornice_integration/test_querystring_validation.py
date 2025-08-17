"""
Test for Cornice query string validation.

This test explores how Cornice implements validation of query string parameters
using Marshmallow schemas with the marshmallow_querystring_validator.
"""

from cornice import Service
from cornice.validators import marshmallow_querystring_validator
from marshmallow import Schema, fields
from pyramid.response import Response


class PaginationQuerySchema(Schema):
    """Schema for pagination query parameters."""

    page = fields.Int(
        required=False,
        load_default=1,
        validate=lambda x: x > 0,
        metadata={"description": "Page number (must be positive)"},
    )
    limit = fields.Int(
        required=False,
        load_default=10,
        validate=lambda x: 1 <= x <= 100,
        metadata={"description": "Items per page (1-100)"},
    )
    sort = fields.Str(
        required=False,
        load_default="created_at",
        validate=lambda x: x in ["created_at", "name", "id"],
        metadata={"description": "Sort field"},
    )


def test_cornice_querystring_validation(pyramid_app_with_services, logs):
    """Test that Cornice validates query string parameters using Marshmallow schema."""

    # Create a Cornice service with querystring validation
    users_service = Service(
        name="list_users_with_pagination",
        path="/api/v1/users",
        description="List users with pagination query parameters",
    )

    @users_service.get(
        schema=PaginationQuerySchema, validators=(marshmallow_querystring_validator,)
    )
    def list_users_with_pagination(request):
        """List users with validated pagination parameters."""
        # Access validated query parameters
        validated_params = request.validated
        return Response(
            json={
                "users": [
                    {"id": 1, "name": "John Doe"},
                    {"id": 2, "name": "Jane Smith"},
                ],
                "pagination": {
                    "page": validated_params.get("page", 1),
                    "limit": validated_params.get("limit", 10),
                    "sort": validated_params.get("sort", "created_at"),
                    "total": 2,
                },
            }
        )

    # Create test app with the service
    app = pyramid_app_with_services([users_service])

    # Test MCP tool call with valid querystring parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_users_with_pagination",
            "arguments": {"querystring": {"page": 2, "limit": 5, "sort": "name"}},
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

    # Extract the actual response content
    actual_content = mcp_result["representation"]["content"]

    # Verify that the validated query parameters were used
    assert actual_content["pagination"]["page"] == 2
    assert actual_content["pagination"]["limit"] == 5
    assert actual_content["pagination"]["sort"] == "name"
    assert actual_content["pagination"]["total"] == 2

    # Verify query parameters were processed correctly by checking logs
    # contain key indicators
    assert "Added query params:" in logs.debug
    assert "FINAL URL: /api/v1/users" in logs.debug
