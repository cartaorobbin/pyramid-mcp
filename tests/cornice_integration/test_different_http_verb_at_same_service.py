"""
Test different HTTP verbs with different schemas at the same Cornice service.

This demonstrates the bug where the same service with different schemas
per HTTP verb doesn't generate correctly differentiated MCP tools.
"""

from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields


class GetUserSchema(Schema):
    """Schema for GET requests."""

    include_details = fields.Bool(load_default=False)


class UpdateUserSchema(Schema):
    """Schema for PUT requests."""

    name = fields.Str(required=True)
    email = fields.Email(required=True)


# Single service with two different schemas for different HTTP verbs
user_service = Service(
    name="user_detail",
    path="/api/users/{id}",
    description="User service with different schemas per HTTP verb",
)


@user_service.get(schema=GetUserSchema(), validators=(marshmallow_body_validator,))
def get_user(request):
    """Get user details with optional query parameters."""
    return {"id": request.matchdict["id"], "name": "John"}


@user_service.put(schema=UpdateUserSchema(), validators=(marshmallow_body_validator,))
def update_user(request):
    """Update user with body parameters."""
    return {"id": request.matchdict["id"], "updated": True}


def test_different_schemas_generate_different_tools(pyramid_app_with_services):
    """Test that GET and PUT generate tools with different schemas."""
    app = pyramid_app_with_services(services=[user_service], scan_path=__name__)

    # Get tools list via MCP
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )

    assert response.status_code == 200

    # Assert the complete expected result structure
    expected_result = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "get_user_detail",
                    "description": "Get user details with optional query parameters.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Path parameter: id",
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": False,
                                "description": "Path parameters for the request",
                            },
                            "querystring": {
                                "type": "object",
                                "properties": {
                                    "include_details": {
                                        "type": "boolean",
                                        "default": False,
                                    }
                                },
                                "required": [],
                                "additionalProperties": False,
                                "description": "Query parameters for the request",
                            },
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                },
                {
                    "name": "update_user_detail",
                    "description": "Update user with body parameters.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Path parameter: id",
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": False,
                                "description": "Path parameters for the request",
                            },
                            "body": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                },
                                "required": ["name", "email"],
                                "additionalProperties": False,
                                "description": "Request body parameters",
                            },
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            ]
        },
    }

    assert response.json == expected_result
