"""
Tests for excluding OPTIONS and HEAD HTTP methods from MCP tool generation.

This module tests that the route discovery system properly excludes OPTIONS
and HEAD HTTP methods while preserving all other HTTP methods.
"""


# Define view functions for different HTTP methods
def test_view_get(request):
    return {"method": "GET"}


def test_view_post(request):
    return {"method": "POST"}


def test_view_put(request):
    return {"method": "PUT"}


def test_view_delete(request):
    return {"method": "DELETE"}


def test_view_patch(request):
    return {"method": "PATCH"}


def test_view_options(request):
    return {"method": "OPTIONS"}


def test_view_head(request):
    return {"method": "HEAD"}


def test_options_and_head_methods_are_excluded(pyramid_app):
    """Test that OPTIONS and HEAD methods are not exposed as MCP tools."""
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-exclude-methods",
    }

    # Define views with all HTTP methods including OPTIONS and HEAD
    # Use unique route names to avoid conflicts
    views = [
        (
            test_view_get,
            "multi_method_route_get",
            {"request_method": "GET", "renderer": "json"},
        ),
        (
            test_view_post,
            "multi_method_route_post",
            {"request_method": "POST", "renderer": "json"},
        ),
        (
            test_view_put,
            "multi_method_route_put",
            {"request_method": "PUT", "renderer": "json"},
        ),
        (
            test_view_delete,
            "multi_method_route_delete",
            {"request_method": "DELETE", "renderer": "json"},
        ),
        (
            test_view_patch,
            "multi_method_route_patch",
            {"request_method": "PATCH", "renderer": "json"},
        ),
        (
            test_view_options,
            "multi_method_route_options",
            {"request_method": "OPTIONS", "renderer": "json"},
        ),
        (
            test_view_head,
            "multi_method_route_head",
            {"request_method": "HEAD", "renderer": "json"},
        ),
    ]

    app = pyramid_app(settings=settings, views=views)

    # List available MCP tools
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]

    # Get tools for our test routes
    test_tools = [tool for tool in tools if "multi_method_route" in tool["name"]]
    tool_names = [tool["name"] for tool in test_tools]

    # Verify that no tool names contain 'options' or 'head'
    options_tools = [name for name in tool_names if "options" in name.lower()]
    head_tools = [name for name in tool_names if "head" in name.lower()]

    assert len(options_tools) == 0, f"Found OPTIONS tools: {options_tools}"
    assert len(head_tools) == 0, f"Found HEAD tools: {head_tools}"

    # Verify that other HTTP methods are still included
    # We should have exactly 5 tools (GET, POST, PUT, DELETE, PATCH) and no OPTIONS/HEAD
    assert len(test_tools) == 5, (
        f"Expected 5 tools (GET, POST, PUT, DELETE, PATCH), got {len(test_tools)}: "
        f"{tool_names}"
    )

    # Verify we have the expected tool names (exact names may vary)
    # But we should have 5 unique tools
    assert len(set(tool_names)) == 5, f"Expected 5 unique tool names, got: {tool_names}"


def test_case_insensitive_method_filtering(pyramid_app):
    """Test that method filtering works regardless of case."""
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-case-insensitive",
    }

    def test_view(request):
        return {"method": "test"}

    # Add views with different case variations - use unique route names
    views = [
        (
            test_view,
            "case_test_route_options",
            {"request_method": "options", "renderer": "json"},
        ),  # lowercase
        (
            test_view,
            "case_test_route_head",
            {"request_method": "HEAD", "renderer": "json"},
        ),  # uppercase
        (
            test_view,
            "case_test_route_options2",
            {"request_method": "Options", "renderer": "json"},
        ),  # mixed case
        (
            test_view,
            "case_test_route_get",
            {"request_method": "get", "renderer": "json"},
        ),  # lowercase GET (should be included)
    ]

    app = pyramid_app(settings=settings, views=views)

    # List available MCP tools
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]

    # Get tools for our test route
    test_tools = [tool for tool in tools if "case_test_route" in tool["name"]]

    # Should only have GET method, all OPTIONS/HEAD variants excluded
    assert len(test_tools) == 1, (
        f"Expected 1 tool (GET), got {len(test_tools)}: "
        f"{[t['name'] for t in test_tools]}"
    )

    # Verify it's a GET tool (should be the GET route)
    tool_name = test_tools[0]["name"]
    assert (
        "case_test_route_get" in tool_name
    ), f"Expected GET tool name to contain 'case_test_route_get', got {tool_name}"


def test_other_http_methods_preserved(pyramid_app):
    """Test that less common but valid HTTP methods are preserved."""
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-extended-methods",
    }

    def test_view(request):
        return {"method": "test"}

    # Add views for extended HTTP methods - use unique route names
    views = [
        (
            test_view,
            "extended_methods_route_connect",
            {"request_method": "CONNECT", "renderer": "json"},
        ),
        (
            test_view,
            "extended_methods_route_trace",
            {"request_method": "TRACE", "renderer": "json"},
        ),
        (
            test_view,
            "extended_methods_route_custom",
            {"request_method": "CUSTOM", "renderer": "json"},
        ),  # Custom method
    ]

    app = pyramid_app(settings=settings, views=views)

    # List available MCP tools
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]

    # Get tools for our test routes
    test_tools = [tool for tool in tools if "extended_methods_route" in tool["name"]]

    # All these methods should be preserved (only OPTIONS and HEAD are excluded)
    assert len(test_tools) == 3, (
        f"Expected 3 tools (CONNECT, TRACE, CUSTOM), got {len(test_tools)}: "
        f"{[t['name'] for t in test_tools]}"
    )

    # Verify all tools are present (they should have different naming patterns)
    tool_names = [tool["name"] for tool in test_tools]
    assert len(set(tool_names)) == 3, f"Expected 3 unique tool names, got: {tool_names}"


def test_mixed_routes_with_and_without_excluded_methods(pyramid_app):
    """Test filtering with mixed routes (some with excluded methods, some without)."""
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-mixed-routes",
    }

    def view_with_excluded(request):
        return {"type": "with_excluded"}

    def view_without_excluded(request):
        return {"type": "without_excluded"}

    # Route 1: Has OPTIONS and HEAD methods
    # Route 2: Only has standard methods
    # Use unique route names to avoid conflicts
    views = [
        (
            view_with_excluded,
            "route_with_excluded_get",
            {"request_method": "GET", "renderer": "json"},
        ),
        (
            view_with_excluded,
            "route_with_excluded_options",
            {"request_method": "OPTIONS", "renderer": "json"},
        ),
        (
            view_with_excluded,
            "route_with_excluded_head",
            {"request_method": "HEAD", "renderer": "json"},
        ),
        (
            view_without_excluded,
            "route_without_excluded_get",
            {"request_method": "GET", "renderer": "json"},
        ),
        (
            view_without_excluded,
            "route_without_excluded_post",
            {"request_method": "POST", "renderer": "json"},
        ),
    ]

    app = pyramid_app(settings=settings, views=views)

    # List available MCP tools
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]

    # Get tools for each route group
    route1_tools = [tool for tool in tools if "route_with_excluded" in tool["name"]]
    route2_tools = [tool for tool in tools if "route_without_excluded" in tool["name"]]

    # Route 1 should only have GET (OPTIONS and HEAD excluded)
    assert len(route1_tools) == 1, (
        f"Route 1 expected 1 tool (GET), got {len(route1_tools)}: "
        f"{[t['name'] for t in route1_tools]}"
    )
    assert (
        "route_with_excluded_get" in route1_tools[0]["name"]
    ), f"Route 1 tool should be GET, got {route1_tools[0]['name']}"

    # Route 2 should have both GET and POST
    assert len(route2_tools) == 2, (
        f"Route 2 expected 2 tools (GET, POST), got {len(route2_tools)}: "
        f"{[t['name'] for t in route2_tools]}"
    )

    route2_names = [tool["name"] for tool in route2_tools]
    has_get = any("route_without_excluded_get" in name for name in route2_names)
    has_post = any("route_without_excluded_post" in name for name in route2_names)

    assert has_get, f"Route 2 should have GET tool, got names: {route2_names}"
    assert has_post, f"Route 2 should have POST tool, got names: {route2_names}"


def test_no_tools_generated_for_options_head_only_routes(pyramid_app):
    """Test that routes with only OPTIONS and HEAD methods generate no tools."""
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-excluded-only-routes",
    }

    def options_only_view(request):
        return {"method": "OPTIONS"}

    def head_only_view(request):
        return {"method": "HEAD"}

    # Routes with only excluded methods - use unique route names
    views = [
        (
            options_only_view,
            "options_only_route",
            {"request_method": "OPTIONS", "renderer": "json"},
        ),
        (
            head_only_view,
            "head_only_route",
            {"request_method": "HEAD", "renderer": "json"},
        ),
        (
            options_only_view,
            "both_excluded_route_options",
            {"request_method": "OPTIONS", "renderer": "json"},
        ),
        (
            head_only_view,
            "both_excluded_route_head",
            {"request_method": "HEAD", "renderer": "json"},
        ),
    ]

    app = pyramid_app(settings=settings, views=views)

    # List available MCP tools
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]

    # Get tools for our test routes
    options_tools = [tool for tool in tools if "options_only_route" in tool["name"]]
    head_tools = [tool for tool in tools if "head_only_route" in tool["name"]]
    both_tools = [tool for tool in tools if "both_excluded_route" in tool["name"]]

    # No tools should be generated for any of these routes
    assert (
        len(options_tools) == 0
    ), f"Expected no tools for OPTIONS-only route, got {len(options_tools)}"
    assert (
        len(head_tools) == 0
    ), f"Expected no tools for HEAD-only route, got {len(head_tools)}"
    assert (
        len(both_tools) == 0
    ), f"Expected no tools for OPTIONS+HEAD route, got {len(both_tools)}"
