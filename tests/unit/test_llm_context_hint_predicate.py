"""
Unit tests for llm_context_hint view predicate functionality.

This module contains a single, well-designed test that demonstrates:
- Proper Pyramid setup with MCP integration
- View with llm_context_hint predicate
- MCP tool call verification that the custom hint is returned
"""

from pyramid.view import view_config


# Define a view with custom llm_context_hint at module level
@view_config(
    route_name="financial_data",
    renderer="json",
    llm_context_hint="Sensitive financial account information from banking system",
)
def financial_view(request):
    """Get financial data."""
    return {"balance": 1234.56, "currency": "USD"}


def test_llm_context_hint_predicate_end_to_end(pyramid_app_with_views):
    """Test that llm_context_hint predicate works end-to-end with MCP tool calls."""

    # Create Pyramid app with the route and scan for the view
    routes = [("financial_data", "/api/financial")]
    settings = {"mcp.route_discovery.enabled": "true"}

    # The pyramid_app_with_views fixture will scan this module for @view_config
    # decorators
    app = pyramid_app_with_views(routes, ignore=None, settings=settings)

    # Make MCP tool call (tool name is derived from function name:
    # financial_view -> get_financial_data)
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "get_financial_data", "arguments": {}},
    }

    response = app.post_json("/mcp", mcp_request)

    # Verify the MCP call succeeded
    assert response.status_code == 200
    assert "result" in response.json

    # Verify the custom llm_context_hint is returned in the MCP response
    result = response.json["result"]
    assert result["type"] == "mcp/context"
    assert result["llm_context_hint"] == (
        "Sensitive financial account information from banking system"
    )
