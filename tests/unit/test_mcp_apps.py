"""MCP Apps transport: resources, tool metadata, and a passthrough result."""

from marshmallow import Schema, fields

from pyramid_mcp import resource, tool
from pyramid_mcp.result import MCPToolResult

CARD_URI = "ui://example/card.html"


class CardSchema(Schema):
    """Output schema advertised on the tool. The library does not interpret it."""

    name = fields.Str(required=True)


@resource(
    uri=CARD_URI,
    mime_type="text/html;profile=mcp-app",
    description="Example interface.",
    name="Example card",
)
def example_card(request):
    """HTML the host draws. The library only transports the text."""
    return "<html>card</html>"


@tool(
    name="get_example",
    description="Return an example card.",
    output_schema=CardSchema,
    meta={"ui": {"resourceUri": CARD_URI}},
    title="Get example",
    annotations={"title": "Get example", "readOnlyHint": True},
)
def get_example(request, name: str) -> MCPToolResult:
    """Tool whose result opens the resource above."""
    return MCPToolResult(
        content=[{"type": "text", "text": f"Card for {name}"}],
        structured_content={"card": {"name": name}},
        meta={"example/photo": "data:image/png;base64,aaa"},
    )


@tool(name="plain_example", description="Keep the context envelope.")
def plain_example(name: str) -> str:
    """A tool that does not opt into the standard result."""
    return f"Hello {name}"


def test_mcp_apps_transport(pyramid_app):
    """List the resource, read it, and call both kinds of tool."""
    app = pyramid_app(scan_path="tests.unit.test_mcp_apps")

    listed = app.post_json("/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools = {item["name"]: item for item in listed.json["result"]["tools"]}
    card_tool = tools["get_example"]
    assert card_tool["outputSchema"]["properties"]["name"]["type"] == "string"
    assert card_tool["_meta"]["ui"]["resourceUri"] == CARD_URI
    assert card_tool["title"] == "Get example"
    assert card_tool["annotations"]["readOnlyHint"] is True
    assert "request" not in card_tool["inputSchema"]["properties"]
    assert card_tool["inputSchema"]["properties"]["body"]["properties"]["name"]

    resources = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 2, "method": "resources/list"}
    )
    assert resources.json["result"]["resources"] == [
        {
            "uri": CARD_URI,
            "name": "Example card",
            "mimeType": "text/html;profile=mcp-app",
            "description": "Example interface.",
        }
    ]

    read = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "resources/read",
            "params": {"uri": CARD_URI},
        },
    )
    assert read.json["result"]["contents"] == [
        {
            "uri": CARD_URI,
            "mimeType": "text/html;profile=mcp-app",
            "text": "<html>card</html>",
        }
    ]

    missing = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {"uri": "ui://missing"},
        },
    )
    assert missing.json["error"]["message"] == "Resource not found: ui://missing"

    called = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "get_example",
                "arguments": {"body": {"name": "Ada"}},
            },
        },
    )
    assert called.json["result"] == {
        "content": [{"type": "text", "text": "Card for Ada"}],
        "structuredContent": {"card": {"name": "Ada"}},
        "_meta": {"example/photo": "data:image/png;base64,aaa"},
    }
    assert "__pyramid_mcp_result__" not in called.json["result"]

    plain = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "plain_example",
                "arguments": {"body": {"name": "Ada"}},
            },
        },
    )
    assert plain.json["result"]["type"] == "mcp/context"
    assert plain.json["result"]["content"][0]["text"] == "Hello Ada"
