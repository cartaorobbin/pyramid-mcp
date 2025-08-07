"""
Test for Cornice exclude filter functionality.

This test verifies that the exclude patterns work correctly with Cornice services
when route discovery is enabled.
"""


from cornice import Service  # type: ignore
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields


class SimpleSchema(Schema):
    """Simple schema for testing."""

    message = fields.Str(required=True, metadata={"description": "Test message"})


# Create Cornice services - one to be excluded, one to be included
admin_service = Service(
    name="admin",
    path="/admin/users",
    description="Admin service that should be excluded",
)

public_service = Service(
    name="public",
    path="/public/info",
    description="Public service that should be included",
)


@admin_service.post(schema=SimpleSchema(), validators=(marshmallow_body_validator,))
def admin_post(request):
    """Admin endpoint that should be excluded from MCP tools."""
    return {"admin": "secret", "message": request.validated["message"]}


@public_service.post(schema=SimpleSchema(), validators=(marshmallow_body_validator,))
def public_post(request):
    """Public endpoint that should be included in MCP tools."""
    return {"public": "info", "message": request.validated["message"]}


def test_exclude_filter_excludes_admin_service(pyramid_app_with_services):
    """Test that exclude patterns properly exclude admin services from MCP tools."""
    # Configure settings with route discovery enabled and admin exclusion
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.route_discovery.exclude_patterns": "*admin*",
        "mcp.server_name": "test-exclude-server",
        "mcp.server_version": "1.0.0",
    }

    # Create app with both admin and public services
    services = [admin_service, public_service]
    app = pyramid_app_with_services(services, settings)

    # Get list of MCP tools
    mcp_list_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    response = app.post_json("/mcp", mcp_list_request)
    assert response.status_code == 200

    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Verify admin service is excluded but public service is included
    admin_tools = [name for name in tool_names if "admin" in name.lower()]
    public_tools = [name for name in tool_names if "public" in name.lower()]

    assert (
        len(admin_tools) == 0
    ), f"Admin tools should be excluded, but found: {admin_tools}"
    assert (
        len(public_tools) > 0
    ), f"Public tools should be included, but found: {public_tools}"

    # Debug: Print all discovered tools for verification
    print(f"All discovered tools: {tool_names}")
    print(f"Admin tools (should be empty): {admin_tools}")
    print(f"Public tools (should have at least one): {public_tools}")

    # The exclude filter test passes if admin tools are excluded and public tools
    # are included
