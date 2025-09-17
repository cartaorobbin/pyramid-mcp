"""
Test for Cornice querystring parameter handling.

This module tests querystring parameters across different scenarios:
- Marshmallow querystring schema validation
- data_key handling in query parameters
- Query parameter types and defaults
- URL encoding and special characters
- Pagination and filtering patterns
- Nested querystring schemas
"""

import json

import pytest
from cornice import Service
from cornice.validators import marshmallow_querystring_validator
from marshmallow import Schema, fields, pre_load
from pyramid.response import Response


class IntsQuerySchema(Schema):
    """Schema for pagination query parameters."""

    ints = fields.List(
        fields.Int,
        required=False,
        metadata={"description": "Page number (must be positive)"},
    )

    @pre_load
    def pre_load(self, data, **kwargs):
        data["ints"] = json.loads(data["ints"])

        return data


# =============================================================================
# 🧪 TEST FIXTURES
# =============================================================================


@pytest.fixture
def pagination_service():
    """Create a Cornice service with pagination querystring validation."""
    users_service = Service(
        name="list_list_ints_query_string",
        path="/api/v1/list_list_ints_query_string",
        description="List users with pagination query parameters",
    )

    @users_service.get(
        schema=IntsQuerySchema, validators=(marshmallow_querystring_validator,)
    )
    def list_users_with_pagination(request):
        """List users with validated pagination parameters."""
        # Access validated query parameters

        return Response(json=request.validated)

    return users_service


# =============================================================================
# 🧪 BASIC QUERYSTRING PARAMETER TESTS
# =============================================================================


def test_cornice_querystring_validation(
    pyramid_app_with_services, pagination_service, logs
):
    """Test that Cornice validates query string parameters using Marshmallow schema."""

    # Create test app with the service
    app = pyramid_app_with_services([pagination_service])

    # Test MCP tool call with valid querystring parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_list_ints_query_string",
            "arguments": {"querystring": {"ints": [2, 3]}},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed with validated query parameters
    assert response.status_code == 200

    # Assert the complete response structure
    actual_response = response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": {"ints": [2, 3]},
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": (
                    "http://localhost/api/v1/list_list_ints_query_string"
                    "?ints=%5B2%2C+3%5D"
                ),
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }

    # Verify query parameters were processed correctly by checking logs
    # contain key indicators
    assert "Added query params:" in logs.debug
    assert (
        "Created subrequest: GET http://localhost/api/v1/list_list_ints_query_string"
        in logs.debug
    )
