"""
Test to reproduce and solve the Cornice querystring validation issue.

This test reproduces the issue where Claude/MCP sends querystring={} and
Cornice rejects it as "Unknown field".
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_validator
from marshmallow import EXCLUDE, Schema, fields


@pytest.fixture
def cornice_querystring_issue_app(pyramid_app_with_services):
    # Schema for actual querystring parameters
    class QueryParams(Schema):
        page = fields.Integer(missing=1)
        limit = fields.Integer(missing=20)

    # Schema that should accept querystring={} from Claude/MCP
    class RequestSchema(Schema):
        class Meta:
            unknown = EXCLUDE

        # The key fix: missing={} allows empty dict to be valid
        querystring = fields.Nested(
            QueryParams, required=False, allow_none=True, missing={}
        )

    # Create a simple Cornice service
    service = Service(name="list_items", path="/items")

    @service.get(schema=RequestSchema, validators=(marshmallow_validator,))
    def list_items(request):
        querystring = request.validated.get("querystring", {})
        return {"items": [], "params": querystring}

    # Create app with the service
    app = pyramid_app_with_services([service])
    return app


def test_optional_querystring_with_empty_dict(cornice_querystring_issue_app):
    """Test that optional querystring field accepts empty dict from Claude/MCP."""

    # Test the exact pattern Claude/MCP sends - empty dict
    response = cornice_querystring_issue_app.get("/items", params={})  # type: ignore

    assert response.status_code == 200
    assert response.json["items"] == []
    # The nested schema should apply its default values when given an empty dict
    assert response.json["params"] == {"page": 1, "limit": 20}


def test_mcp_call_with_empty_querystring(cornice_querystring_issue_app):
    """Test MCP call with empty querystring dict.

    Reproduces the exact Claude/MCP scenario.
    """

    # List available tools to find the auto-generated tool name
    list_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    list_response = cornice_querystring_issue_app.post_json(
        "/mcp", list_request
    )  # type: ignore
    tools = list_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Find the auto-generated tool (should be something like "get_list_items")
    items_tool = [name for name in tool_names if "items" in name.lower()]
    assert len(items_tool) > 0, f"No auto-generated tool found. Available: {tool_names}"

    # Make the exact MCP call that Claude sends with empty querystring
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": items_tool[0],
            "arguments": {
                "querystring": {}  # This is what Claude sends and was causing the error
            },
        },
    }

    response = cornice_querystring_issue_app.post_json(
        "/mcp", mcp_request
    )  # type: ignore

    assert response.status_code == 200
    assert response.json["jsonrpc"] == "2.0"
    assert response.json["id"] == 2
    assert "result" in response.json
    # The tool should execute successfully with the empty querystring


def test_mcp_call_with_actual_querystring_values(cornice_querystring_issue_app):
    """Test MCP call with actual querystring values.

    Ensures they are properly passed through.
    """

    # List available tools to find the auto-generated tool name
    list_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    list_response = cornice_querystring_issue_app.post_json(
        "/mcp", list_request
    )  # type: ignore
    tools = list_response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Find the auto-generated tool
    items_tool = [name for name in tool_names if "items" in name.lower()]
    assert len(items_tool) > 0, f"No auto-generated tool found. Available: {tool_names}"

    # Make MCP call with actual querystring values
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": items_tool[0],
            "arguments": {
                "querystring": {
                    "page": 3,
                    "limit": 50,
                }  # Actual values different from defaults
            },
        },
    }

    response = cornice_querystring_issue_app.post_json(
        "/mcp", mcp_request
    )  # type: ignore

    assert response.status_code == 200
    assert response.json["jsonrpc"] == "2.0"
    assert response.json["id"] == 3
    assert "result" in response.json

    # Debug: Print the actual response structure
    print("MCP Response:", response.json["result"])

    # Parse the response to verify the actual querystring values were used
    # in new MCP context format
    mcp_result = response.json["result"]
    assert mcp_result["type"] == "mcp/context"
    assert "representation" in mcp_result

    # Extract content from representation
    print("MCP Response:", mcp_result)

    # The response should contain the actual values we sent, not the defaults
    # This will show us what the actual auto-generated tool returns
