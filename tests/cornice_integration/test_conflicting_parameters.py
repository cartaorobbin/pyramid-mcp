"""
Test for conflicting Cornice parameter handling.

This module tests parameter name conflicts between locations:
- Same parameter name in multiple locations (path, query, body)
- UUID parameter in path AND body with different values
- Parameter precedence and conflict resolution
- Error handling for parameter conflicts
- Naming collision edge cases
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_validator
from marshmallow import EXCLUDE, Schema, fields
from pyramid.response import Response

# =============================================================================
# 🧪 UUID CONFLICT SCHEMAS (path + body)
# =============================================================================


class UuidPathSchema(Schema):
    """Schema for path parameters with UUID."""

    class Meta:
        unknown = EXCLUDE

    uuid = fields.UUID(required=True, metadata={"description": "Item UUID in path"})


class UuidBodySchema(Schema):
    """Schema for body parameters with UUID."""

    uuid = fields.UUID(required=True, metadata={"description": "Related UUID in body"})
    name = fields.Str(required=True, metadata={"description": "Item name"})
    action = fields.Str(
        required=False,
        dump_default="update",
        metadata={"description": "Action to perform"},
    )


class UuidConflictSchema(Schema):
    """Schema with UUID in both path and body."""

    class Meta:
        unknown = EXCLUDE

    path = fields.Nested(UuidPathSchema, required=True)
    body = fields.Nested(UuidBodySchema, required=True)


# =============================================================================
# 🧪 MULTI-LOCATION CONFLICT SCHEMAS
# =============================================================================


class IdPathSchema(Schema):
    """Schema for path parameters with id."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(required=True, metadata={"description": "Item ID in path"})


class IdQuerySchema(Schema):
    """Schema for query parameters with id."""

    id = fields.Int(required=False, metadata={"description": "Filter ID in query"})
    include_related = fields.Bool(
        required=False,
        dump_default=False,
        metadata={"description": "Include related items"},
    )


class IdBodySchema(Schema):
    """Schema for body parameters with id."""

    id = fields.Int(required=False, metadata={"description": "Reference ID in body"})
    data = fields.Str(required=True, metadata={"description": "Item data"})


class TripleConflictSchema(Schema):
    """Schema with 'id' in path, querystring, and body."""

    class Meta:
        unknown = EXCLUDE

    path = fields.Nested(IdPathSchema, required=True)
    querystring = fields.Nested(IdQuerySchema, required=False)
    body = fields.Nested(IdBodySchema, required=True)


# =============================================================================
# 🧪 DATA_KEY CONFLICT SCHEMAS
# =============================================================================


class DataKeyPathSchema(Schema):
    """Schema with data_key in path."""

    class Meta:
        unknown = EXCLUDE

    item_uuid = fields.UUID(
        required=True,
        data_key="itemId",  # Conflicts with body data_key
        metadata={"description": "Item UUID with data_key"},
    )


class DataKeyBodySchema(Schema):
    """Schema with conflicting data_key in body."""

    related_item = fields.UUID(
        required=True,
        data_key="itemId",  # Same data_key as path
        metadata={"description": "Related item UUID with same data_key"},
    )
    description = fields.Str(
        required=False, metadata={"description": "Item description"}
    )


class DataKeyConflictSchema(Schema):
    """Schema with same data_key in path and body."""

    class Meta:
        unknown = EXCLUDE

    path = fields.Nested(DataKeyPathSchema, required=True)
    body = fields.Nested(DataKeyBodySchema, required=True)


# =============================================================================
# 🧪 TEST FIXTURES
# =============================================================================


@pytest.fixture
def uuid_conflict_service():
    """Create a service with UUID in both path and body."""

    conflict_service = Service(
        name="uuid_conflict_service",
        path="/api/v1/items/{uuid}",
        description="Service with UUID conflict between path and body",
    )

    @conflict_service.post(
        schema=UuidConflictSchema,
        validators=(marshmallow_validator,),
    )
    def handle_uuid_conflict(request):
        """Handle request with UUID in both path and body."""
        path_uuid = request.validated["path"]["uuid"]
        body_uuid = request.validated["body"]["uuid"]
        body_data = request.validated["body"]

        return Response(
            json={
                "path_uuid": str(path_uuid),
                "body_uuid": str(body_uuid),
                "are_same": path_uuid == body_uuid,
                "body_data": {
                    "name": body_data["name"],
                    "action": body_data.get("action", "update"),
                },
                "status": "processed",
            }
        )

    return conflict_service


@pytest.fixture
def triple_conflict_service():
    """Create a service with 'id' in path, querystring, and body."""

    triple_service = Service(
        name="triple_conflict_service",
        path="/api/v1/resources/{id}",
        description="Service with 'id' in path, query, and body",
    )

    @triple_service.put(
        schema=TripleConflictSchema,
        validators=(marshmallow_validator,),
    )
    def handle_triple_conflict(request):
        """Handle request with 'id' in all three locations."""
        path_id = request.validated["path"]["id"]
        query_data = request.validated.get("querystring", {})
        body_data = request.validated["body"]

        return Response(
            json={
                "path_id": path_id,
                "query_id": query_data.get("id"),
                "body_id": body_data.get("id"),
                "include_related": query_data.get("include_related", False),
                "data": body_data["data"],
                "status": "processed",
            }
        )

    return triple_service


@pytest.fixture
def data_key_conflict_service():
    """Create a service with same data_key in path and body."""

    data_key_service = Service(
        name="data_key_conflict_service",
        path="/api/v1/links/{item_uuid}",
        description="Service with same data_key in path and body",
    )

    @data_key_service.post(
        schema=DataKeyConflictSchema,
        validators=(marshmallow_validator,),
    )
    def handle_data_key_conflict(request):
        """Handle request with same data_key in path and body."""
        path_item = request.validated["path"]["item_uuid"]
        body_item = request.validated["body"]["related_item"]
        body_description = request.validated["body"].get("description")

        return Response(
            json={
                "path_item_uuid": str(path_item),
                "body_related_item": str(body_item),
                "description": body_description,
                "are_same": path_item == body_item,
                "status": "linked",
            }
        )

    return data_key_service


# =============================================================================
# 🧪 UUID CONFLICT TESTS
# =============================================================================


def test_uuid_conflict_schema_generation(
    pyramid_app_with_services, uuid_conflict_service
):
    """Test that UUID conflict service generates correct schema structure."""

    services = [uuid_conflict_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_uuid_conflict_service",
                    "description": "Handle request with UUID in both path and body.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "uuid": {
                                        "type": "string",
                                        "format": "uuid",
                                        "description": "Item UUID in path",
                                    }
                                },
                                "required": ["uuid"],
                                "additionalProperties": False,
                            },
                            "body": {
                                "type": "object",
                                "properties": {
                                    "uuid": {
                                        "type": "string",
                                        "format": "uuid",
                                        "description": "Related UUID in body",
                                    },
                                    "name": {
                                        "type": "string",
                                        "description": "Item name",
                                    },
                                    "action": {
                                        "type": "string",
                                        "description": "Action to perform",
                                        "default": "update",
                                    },
                                },
                                "required": ["uuid", "name"],
                                "additionalProperties": False,
                            },
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


def test_uuid_conflict_execution_same_values(
    pyramid_app_with_services, uuid_conflict_service
):
    """Test UUID conflict service execution with same UUID values."""

    services = [uuid_conflict_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test with same UUID in path and body
    test_uuid = "550e8400-e29b-41d4-a716-446655440000"
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "path": {"uuid": test_uuid},
                "body": {
                    "uuid": test_uuid,  # Same UUID
                    "name": "Test Item",
                    "action": "create",
                },
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed
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
                        "path_uuid": test_uuid,
                        "body_uuid": test_uuid,
                        "are_same": True,
                        "body_data": {"name": "Test Item", "action": "create"},
                        "status": "processed",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": f"http://localhost/api/v1/items/{test_uuid}",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


def test_uuid_conflict_execution_different_values(
    pyramid_app_with_services, uuid_conflict_service
):
    """Test UUID conflict service execution with different UUID values."""

    services = [uuid_conflict_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test with different UUIDs in path and body
    path_uuid = "550e8400-e29b-41d4-a716-446655440000"
    body_uuid = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "path": {"uuid": path_uuid},
                "body": {
                    "uuid": body_uuid,  # Different UUID
                    "name": "Related Item"
                    # action omitted (should use default)
                },
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed
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
                        "path_uuid": path_uuid,
                        "body_uuid": body_uuid,
                        "are_same": False,
                        "body_data": {"name": "Related Item", "action": "update"},
                        "status": "processed",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": f"http://localhost/api/v1/items/{path_uuid}",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


# =============================================================================
# 🧪 TRIPLE CONFLICT TESTS (path + query + body)
# =============================================================================


def test_triple_conflict_schema_generation(
    pyramid_app_with_services, triple_conflict_service
):
    """Test that triple conflict service generates correct schema structure."""

    services = [triple_conflict_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "update_triple_conflict_service",
                    "description": "Handle request with 'id' in all three locations.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Item ID in path",
                                    }
                                },
                                "required": ["id"],
                                "additionalProperties": False,
                            },
                            "querystring": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Filter ID in query",
                                    },
                                    "include_related": {
                                        "type": "boolean",
                                        "description": "Include related items",
                                        "default": False,
                                    },
                                },
                                "required": [],
                                "additionalProperties": False,
                            },
                            "body": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "integer",
                                        "description": "Reference ID in body",
                                    },
                                    "data": {
                                        "type": "string",
                                        "description": "Item data",
                                    },
                                },
                                "required": ["data"],
                                "additionalProperties": False,
                            },
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


def test_triple_conflict_execution_all_different_ids(
    pyramid_app_with_services, triple_conflict_service
):
    """Test triple conflict service execution with different IDs."""

    services = [triple_conflict_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test with different IDs in path, query, and body
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "path": {"id": 123},
                "querystring": {"id": 456, "include_related": True},
                "body": {"id": 789, "data": "test data"},
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed
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
                        "path_id": 123,
                        "query_id": 456,
                        "body_id": 789,
                        "include_related": True,
                        "data": "test data",
                        "status": "processed",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/api/v1/resources/123?"
                "id=456&include_related=True",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


def test_triple_conflict_execution_partial_ids(
    pyramid_app_with_services, triple_conflict_service
):
    """Test triple conflict service execution with IDs only in some locations."""

    services = [triple_conflict_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test with ID only in path (required) and body (optional)
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "path": {"id": 100},
                "querystring": {"include_related": False},  # No ID in query
                "body": {"data": "minimal data"},  # No ID in body
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed
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
                        "path_id": 100,
                        "query_id": None,
                        "body_id": None,
                        "include_related": False,
                        "data": "minimal data",
                        "status": "processed",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/api/v1/resources/100?include_related=False",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


# =============================================================================
# 🧪 DATA_KEY CONFLICT TESTS
# =============================================================================


def test_data_key_conflict_schema_generation(
    pyramid_app_with_services, data_key_conflict_service
):
    """Test that data_key conflict service generates correct schema structure."""

    services = [data_key_conflict_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_data_key_conflict_service",
                    "description": "Handle request with same data_key in "
                    "path and body.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "itemId": {
                                        "type": "string",
                                        "format": "uuid",
                                        "description": "Item UUID with data_key",
                                    }
                                },
                                "required": ["itemId"],
                                "additionalProperties": False,
                            },
                            "body": {
                                "type": "object",
                                "properties": {
                                    "itemId": {
                                        "type": "string",
                                        "format": "uuid",
                                        "description": "Related item UUID with "
                                        "same data_key",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Item description",
                                    },
                                },
                                "required": ["itemId"],
                                "additionalProperties": False,
                            },
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


def test_data_key_conflict_execution(
    pyramid_app_with_services, data_key_conflict_service
):
    """Test data_key conflict service execution with same data_key in path and body."""

    services = [data_key_conflict_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test with same data_key but different UUID values
    path_uuid = "550e8400-e29b-41d4-a716-446655440000"
    body_uuid = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "path": {"item_uuid": path_uuid},
                "body": {"itemId": body_uuid, "description": "Link between items"},
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed
    assert response.status_code == 200

    # Assert the complete response structure (this test expects an error response)
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
                        "status": "error",
                        "errors": actual_response["result"]["content"][0]["data"][
                            "errors"
                        ],
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": f"http://localhost/api/v1/links/{path_uuid}",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


# =============================================================================
# 🧪 ERROR HANDLING TESTS
# =============================================================================


def test_parameter_conflict_resolution(pyramid_app_with_services):
    """Test that parameter conflicts are resolved correctly by location."""

    # Create a service that tests the limits of parameter conflict resolution
    extreme_service = Service(
        name="extreme_conflict",
        path="/extreme/{name}",
        description="Service with extreme parameter conflicts",
    )

    class ExtremeConflictSchema(Schema):
        class Meta:
            unknown = EXCLUDE

        path = fields.Nested(lambda: ExtremePathSchema())
        querystring = fields.Nested(lambda: ExtremeQuerySchema())
        body = fields.Nested(lambda: ExtremeBodySchema())

    class ExtremePathSchema(Schema):
        name = fields.Str(required=True)

    class ExtremeQuerySchema(Schema):
        name = fields.Str(required=False)
        id = fields.Int(required=False)

    class ExtremeBodySchema(Schema):
        name = fields.Str(required=False)
        id = fields.Int(required=False)
        data = fields.Dict(required=True)

    @extreme_service.post(
        schema=ExtremeConflictSchema,
        validators=(marshmallow_validator,),
    )
    def handle_extreme_conflict(request):
        """Handle extreme parameter conflicts."""
        path_data = request.validated["path"]
        query_data = request.validated.get("querystring", {})
        body_data = request.validated["body"]

        return Response(
            json={
                "conflicts_resolved": {
                    "path_name": path_data["name"],
                    "query_name": query_data.get("name"),
                    "body_name": body_data.get("name"),
                    "query_id": query_data.get("id"),
                    "body_id": body_data.get("id"),
                },
                "body_data": body_data["data"],
                "status": "conflicts_resolved",
            }
        )

    services = [extreme_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test with conflicts in all parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "path": {"name": "path_name"},
                "querystring": {"name": "query_name", "id": 100},
                "body": {"name": "body_name", "id": 200, "data": {"test": "value"}},
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed - conflicts resolved by location
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
                        "conflicts_resolved": {
                            "path_name": "path_name",
                            "query_name": "query_name",
                            "body_name": "body_name",
                            "query_id": 100,
                            "body_id": 200,
                        },
                        "body_data": {"test": "value"},
                        "status": "conflicts_resolved",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/extreme/path_name?name=query_name&id=100",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }
