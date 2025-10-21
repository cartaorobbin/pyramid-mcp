"""
Test for optional (non-required) path parameters in Cornice services.

This test verifies that path parameters with required=False are properly
handled in schema generation and tool definitions.
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_path_validator
from marshmallow import Schema, fields
from pyramid.response import Response


class OptionalPathSchema(Schema):
    """Schema with optional path parameters."""

    category = fields.Str(
        required=False,
        metadata={"description": "Optional category filter"},
    )
    subcategory = fields.Str(
        required=False,
        metadata={"description": "Optional subcategory filter"},
    )


@pytest.mark.parametrize("category", ["electronics"])
def test_list_tools_optional_path_parameters(category, pyramid_app_with_services):
    """Test that optional path parameters show required=[] in tool schema."""

    # Create a Cornice service with optional path parameters
    products_service = Service(
        name="get_products_by_category",
        path="/api/v1/products/{category}/{subcategory}",
        description="Get products by optional category and subcategory",
    )

    @products_service.get(
        schema=OptionalPathSchema,
        validators=(marshmallow_path_validator,),
    )
    def get_products_handler(request):
        """Get products by category and subcategory."""
        validated = request.validated
        category = validated.get("category", "all")
        subcategory = validated.get("subcategory", "all")

        return Response(
            json={
                "category": category,
                "subcategory": subcategory,
                "products": [f"Product in {category}/{subcategory}"],
                "status": "found",
            }
        )

    # Create test app with the service
    app = pyramid_app_with_services([products_service])

    # Test tools/list to verify schema generation
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "get_products_by_category",
                    "description": "Get products by category and subcategory.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "category": {
                                        "type": "string",
                                        "description": "Optional category filter",
                                    },
                                    "subcategory": {
                                        "type": "string",
                                        "description": "Optional subcategory filter",
                                    },
                                },
                                "required": [],  # Both fields are optional
                                "additionalProperties": False,
                                "description": "Path parameters for the request",
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


class MixedPathSchema(Schema):
    """Schema with both required and optional path parameters."""

    user_id = fields.Str(
        required=True,
        metadata={"description": "Required user ID"},
    )
    action = fields.Str(
        required=False,
        metadata={"description": "Optional action type"},
    )


@pytest.mark.parametrize("user_id", ["user123"])
def test_list_tools_mixed_required_optional_path_parameters(
    user_id, pyramid_app_with_services
):
    """Test that mixed required/optional path parameters show correct required array."""

    # Create a Cornice service with mixed required/optional path parameters
    user_actions_service = Service(
        name="get_user_actions",
        path="/api/v1/users/{user_id}/actions/{action}",
        description="Get user actions with required user_id and optional action",
    )

    @user_actions_service.get(
        schema=MixedPathSchema,
        validators=(marshmallow_path_validator,),
    )
    def get_user_actions_handler(request):
        """Get user actions."""
        validated = request.validated
        user_id = validated["user_id"]  # Required
        action = validated.get("action", "all")  # Optional

        return Response(
            json={
                "user_id": user_id,
                "action": action,
                "actions": [f"Action {action} for {user_id}"],
                "status": "found",
            }
        )

    # Create test app with the service
    app = pyramid_app_with_services([user_actions_service])

    # Test tools/list to verify schema generation
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "list_get_user_actions",
                    "description": "Get user actions.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "user_id": {
                                        "type": "string",
                                        "description": "Required user ID",
                                    },
                                    "action": {
                                        "type": "string",
                                        "description": "Optional action type",
                                    },
                                },
                                "required": ["user_id"],  # Only user_id is required
                                "additionalProperties": False,
                                "description": "Path parameters for the request",
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


def test_optional_path_parameter_tool_call(pyramid_app_with_services):
    """Test that optional path parameters work in actual tool calls."""

    # Create a Cornice service with optional path parameter
    items_service = Service(
        name="get_items",
        path="/api/v1/items/{category}",
        description="Get items by optional category",
    )

    @items_service.get(
        schema=OptionalPathSchema,
        validators=(marshmallow_path_validator,),
    )
    def get_items_handler(request):
        """Get items by category."""
        validated = request.validated
        category = validated.get("category", "all")

        return Response(
            json={
                "category": category,
                "items": [f"Item in {category}"],
                "count": 1,
            }
        )

    # Create test app with the service
    app = pyramid_app_with_services([items_service])

    # Test MCP tool call with optional path parameter provided
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "list_get_items",
            "arguments": {"path": {"category": "books"}},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed and return the items data
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
                    "data": {
                        "category": "books",
                        "items": ["Item in books"],
                        "count": 1,
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/api/v1/items/books",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }
