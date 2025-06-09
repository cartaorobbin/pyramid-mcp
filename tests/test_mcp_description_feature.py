"""
Tests for MCP description feature via view_config parameter.

This tests the functionality added to allow views to specify custom MCP descriptions:
@view_config(route_name="test", mcp_description="Custom description")
"""

from pyramid.config import Configurator
from pyramid.response import Response

from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.introspection import PyramidIntrospector


def test_view_config_accepts_mcp_description_parameter():
    """Test that view_config accepts mcp_description without errors."""
    config = Configurator()
    config.include("pyramid_mcp")

    def test_view(request):
        return Response("test")

    config.add_route("test", "/test")

    # Should not raise any errors with mcp_description parameter
    config.add_view(test_view, route_name="test", mcp_description="Test description")
    config.commit()


def test_mcp_description_stored_in_view_introspectable():
    """Test that mcp_description is stored in view introspectables."""
    config = Configurator()
    config.include("pyramid_mcp")

    def view_with_desc(request):
        return Response("with description")

    def view_without_desc(request):
        return Response("without description")

    config.add_route("with_desc", "/with_desc")
    config.add_route("without_desc", "/without_desc")

    config.add_view(
        view_with_desc, route_name="with_desc", mcp_description="Custom description"
    )
    config.add_view(view_without_desc, route_name="without_desc")

    config.commit()

    # Check view introspectables directly
    introspector = config.introspector
    view_category = introspector.get_category("views") or []

    with_desc_view = None
    without_desc_view = None

    for item in view_category:
        view_intr = item["introspectable"]
        route_name = view_intr.get("route_name")

        if route_name == "with_desc":
            with_desc_view = view_intr
        elif route_name == "without_desc":
            without_desc_view = view_intr

    # Verify findings
    assert with_desc_view is not None, "Could not find view with description"
    assert without_desc_view is not None, "Could not find view without description"

    # Test mcp_description storage
    mcp_desc_with = with_desc_view.get("mcp_description")
    mcp_desc_without = without_desc_view.get("mcp_description")

    assert mcp_desc_with == "Custom description"
    assert mcp_desc_without is None


def test_pyramid_introspector_extracts_mcp_description():
    """Test that PyramidIntrospector correctly extracts mcp_description."""
    config = Configurator()
    config.include("pyramid_mcp")

    def test_view(request):
        return Response("test")

    config.add_route("test_route", "/test")
    config.add_view(
        test_view, route_name="test_route", mcp_description="Route description"
    )
    config.commit()

    # Test via PyramidIntrospector
    pyramid_introspector = PyramidIntrospector(config)
    routes = pyramid_introspector.discover_routes()

    # Find our test route
    test_route = None
    for route in routes:
        if route["name"] == "test_route":
            test_route = route
            break

    assert test_route is not None, "Could not find test route"
    assert len(test_route.get("views", [])) > 0, "Route has no views"

    # Check that mcp_description is in view_info
    view_info = test_route["views"][0]
    mcp_desc = view_info.get("mcp_description")

    assert mcp_desc == "Route description"


def test_mcp_description_used_in_tool_generation():
    """Test that mcp_description is used when generating MCP tools."""
    config = Configurator()
    config.include("pyramid_mcp")

    def api_view(request):
        return {"status": "success"}

    config.add_route("api_endpoint", "/api/test")
    config.add_view(
        api_view,
        route_name="api_endpoint",
        renderer="json",
        mcp_description="API endpoint for testing MCP description feature",
    )
    config.commit()

    # Generate MCP tools
    pyramid_introspector = PyramidIntrospector(config)
    mcp_config = MCPConfiguration()
    tools = pyramid_introspector.discover_tools_from_pyramid(None, mcp_config)

    # Find our tool
    api_tool = None
    for tool in tools:
        if "api_endpoint" in tool.name or "api" in tool.name.lower():
            api_tool = tool
            break

    assert (
        api_tool is not None
    ), f"Could not find API tool. Available tools: {[t.name for t in tools]}"
    assert (
        api_tool.description
        and "API endpoint for testing MCP description feature" in api_tool.description
    )


def test_mcp_description_priority_over_docstring():
    """Test that mcp_description takes priority over function docstring."""
    config = Configurator()
    config.include("pyramid_mcp")

    def view_with_both(request):
        """This is the function docstring that should be overridden."""
        return Response("test")

    config.add_route("priority_test", "/priority")
    config.add_view(
        view_with_both,
        route_name="priority_test",
        mcp_description="Custom MCP description",
    )
    config.commit()

    # Test description generation directly
    pyramid_introspector = PyramidIntrospector(config)

    # Get the view info to pass to _generate_tool_description
    routes = pyramid_introspector.discover_routes()
    test_route = None
    for route in routes:
        if route["name"] == "priority_test":
            test_route = route
            break

    assert test_route is not None
    view_info = test_route["views"][0]

    description = pyramid_introspector._generate_tool_description(
        "priority_test", "GET", "/priority", view_with_both, view_info
    )

    # Should use mcp_description, not docstring
    assert "Custom MCP description" in description
    assert "function docstring" not in description


def test_empty_mcp_description_is_ignored():
    """Test that empty mcp_description is ignored and falls back to other methods."""
    config = Configurator()
    config.include("pyramid_mcp")

    def view_with_empty_desc(request):
        """This docstring should be used instead."""
        return Response("test")

    config.add_route("empty_desc", "/empty")
    config.add_view(view_with_empty_desc, route_name="empty_desc", mcp_description="")
    config.commit()

    # Test description generation
    pyramid_introspector = PyramidIntrospector(config)
    routes = pyramid_introspector.discover_routes()

    test_route = None
    for route in routes:
        if route["name"] == "empty_desc":
            test_route = route
            break

    assert test_route is not None
    view_info = test_route["views"][0]

    description = pyramid_introspector._generate_tool_description(
        "empty_desc", "GET", "/empty", view_with_empty_desc, view_info
    )

    # Should fall back to docstring when mcp_description is empty
    assert "docstring should be used" in description


def test_multiple_views_with_different_descriptions():
    """Test multiple views with different mcp_description values."""
    config = Configurator()
    config.include("pyramid_mcp")

    def list_users(request):
        return Response("users list")

    def create_user(request):
        return Response("user created")

    config.add_route("users_list", "/users")
    config.add_view(
        list_users,
        route_name="users_list",
        request_method="GET",
        mcp_description="List all users",
    )
    config.add_view(
        create_user,
        route_name="users_list",
        request_method="POST",
        mcp_description="Create a new user",
    )
    config.commit()

    # Generate tools and check descriptions
    pyramid_introspector = PyramidIntrospector(config)
    mcp_config = MCPConfiguration()
    tools = pyramid_introspector.discover_tools_from_pyramid(None, mcp_config)

    # Should have tools for both GET and POST
    get_tool = None
    post_tool = None

    for tool in tools:
        if "users" in tool.name.lower():
            if tool.name == "users_list":  # GET tool (no prefix)
                get_tool = tool
            elif "create" in tool.name.lower():  # POST tool (create prefix)
                post_tool = tool

    assert (
        get_tool is not None
    ), f"Could not find GET tool. Available: {[t.name for t in tools]}"
    assert (
        post_tool is not None
    ), f"Could not find POST tool. Available: {[t.name for t in tools]}"

    assert get_tool.description and "List all users" in get_tool.description
    assert post_tool.description and "Create a new user" in post_tool.description
