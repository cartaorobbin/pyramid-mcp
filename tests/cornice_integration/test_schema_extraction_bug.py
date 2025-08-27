"""Test schema extraction bug reproduction with explicit prefix sharing."""

from cornice import Service
from cornice.validators import marshmallow_validator
from marshmallow import Schema, fields


class SchemaA(Schema):
    """First schema with specific fields."""

    querystring = fields.Nested(lambda: QueryStringSchemaA())


class QueryStringSchemaA(Schema):
    """Query string schema for SchemaA."""

    name = fields.Str(required=False, metadata={"description": "Name filter"})
    status = fields.Str(required=False, metadata={"description": "Status filter"})


class SchemaB(Schema):
    """Second schema with different fields."""

    querystring = fields.Nested(lambda: QueryStringSchemaB())


class QueryStringSchemaB(Schema):
    """Query string schema for SchemaB."""

    category = fields.Str(required=False, metadata={"description": "Category filter"})
    limit = fields.Int(
        required=False, default=20, metadata={"description": "Limit results"}
    )


def test_schema_extraction_bug(pyramid_app_with_services):
    """
    Test schema extraction with 3 services sharing /buggy prefix.

    Services:
    1. /buggy - with SchemaA (name, status)
    2. /buggy/detail - with SchemaB (category, limit)
    3. /buggy/{uuid:.*} - no schema (only path params)

    This test verifies each service gets its correct schema, not mixed up schemas.
    """

    # Service 1: /buggy with SchemaA
    service1 = Service(
        name="buggy_list", path="/buggy", description="List service with SchemaA"
    )

    @service1.get(schema=SchemaA, validators=(marshmallow_validator,))
    def list_view(request):
        return {"type": "list"}

    # Service 2: /buggy/detail with SchemaB
    service2 = Service(
        name="buggy_detail",
        path="/buggy/detail",
        description="Detail service with SchemaB",
    )

    @service2.get(schema=SchemaB, validators=(marshmallow_validator,))
    def detail_view(request):
        return {"type": "detail"}

    # Service 3: /buggy/{uuid:.*} with NO schema
    service3 = Service(
        name="buggy_item",
        path="/buggy/{uuid:.*}",
        description="Item service with no schema",
    )

    @service3.get()  # NO SCHEMA
    def item_view(request):
        return {"type": "item", "uuid": request.matchdict.get("uuid")}

    # Create app with all 3 services
    services = [service1, service2, service3]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    # Create dictionary with tool name as key
    tools_by_name = {
        tool["name"]: tool for tool in tools_response.json["result"]["tools"]
    }

    # Assert complete inputSchema for each of the 3 services

    # Service 1: /buggy with SchemaA - should have querystring field
    # GET requests with Marshmallow schemas create structured querystring
    list_tool = tools_by_name["buggy_list"]
    list_schema = list_tool["inputSchema"]

    # Should have querystring structure
    assert list_schema["type"] == "object"
    assert "querystring" in list_schema["properties"]
    assert list_schema["properties"]["querystring"]["type"] == "object"
    assert "properties" in list_schema["properties"]["querystring"]
    assert list_schema["additionalProperties"] is False

    # Service 2: /buggy/detail with SchemaB - should have querystring field
    # GET requests with Marshmallow schemas create structured querystring
    detail_tool = tools_by_name["get_buggy_detail"]
    detail_schema = detail_tool["inputSchema"]

    # Should have querystring structure
    assert detail_schema["type"] == "object"
    assert "querystring" in detail_schema["properties"]
    assert detail_schema["properties"]["querystring"]["type"] == "object"
    assert "properties" in detail_schema["properties"]["querystring"]
    assert detail_schema["additionalProperties"] is False

    # Service 3: /buggy/{uuid:.*} with no schema
    # Should have only uuid path param under path object
    item_tool = tools_by_name["get_buggy_item"]
    expected_item_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "object",
                "properties": {
                    "uuid": {
                        "type": "string",
                        "description": "Path parameter: uuid",
                        "default": None,
                    }
                },
                "required": [],
                "additionalProperties": False,
                "description": "Path parameters for the request",
            }
        },
        "required": [],
        "additionalProperties": False,
    }
    assert item_tool["inputSchema"] == expected_item_schema
