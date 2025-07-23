"""
Unit tests for llm_context_hint view predicate functionality.

This module tests:
- MCPLLMContextHintPredicate class behavior
- View predicate registration
- Custom hint extraction during introspection
- Schema transformation with custom hints
- Backward compatibility with default hints

Tests cover both route-based tools and manual @tool decorated functions.
"""

from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.testing import DummyRequest

from pyramid_mcp import tool
from pyramid_mcp.core import MCPLLMContextHintPredicate
from pyramid_mcp.schemas import MCPContextResultSchema


# =============================================================================
# 🎨 LLM CONTEXT HINT PREDICATE TESTS
# =============================================================================


def test_mcp_llm_context_hint_predicate_class():
    """Test MCPLLMContextHintPredicate class behavior."""
    predicate = MCPLLMContextHintPredicate("Custom financial data hint", None)

    # Test predicate properties
    assert predicate.val == "Custom financial data hint"
    assert predicate.text() == "llm_context_hint = 'Custom financial data hint'"
    assert predicate.phash == predicate.text

    # Test non-filtering behavior (always returns True)
    assert predicate(None, None) is True


def test_llm_context_hint_predicate_registration():
    """Test that llm_context_hint predicate is properly registered."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Check that the predicate is registered
    predicates = config.registry._directives.get("add_view_predicate", {})
    predicate_names = list(predicates.keys()) if predicates else []

    # The predicate should be available for use
    assert any("llm_context_hint" in str(name) for name in predicate_names), (
        f"llm_context_hint predicate not found in registered predicates: "
        f"{predicate_names}"
    )


def test_custom_llm_context_hint_in_schema_transformation():
    """Test that custom llm_context_hint appears in MCP schema transformation."""
    schema = MCPContextResultSchema()

    # Mock response and view_info with custom hint
    mock_response = Response(json={"data": "test"})
    mock_response.headers["Content-Type"] = "application/json"

    view_info = {
        "llm_context_hint": "Financial data from secure banking API",
        "url": "https://api.bank.com/balance",
    }

    data = {"response": mock_response, "view_info": view_info}

    # Transform using schema
    result = schema.dump(data)

    # Verify custom hint is used
    assert result["type"] == "mcp/context"
    assert result["llm_context_hint"] == "Financial data from secure banking API"
    assert "banking API" in result["llm_context_hint"]


def test_default_llm_context_hint_when_not_specified():
    """Test that default hint is used when llm_context_hint predicate is not specified."""
    schema = MCPContextResultSchema()

    # Mock response without custom hint
    mock_response = Response(json={"data": "test"})
    mock_response.headers["Content-Type"] = "application/json"

    view_info = {
        "url": "https://api.example.com/data"
        # No llm_context_hint specified
    }

    data = {"response": mock_response, "view_info": view_info}

    # Transform using schema
    result = schema.dump(data)

    # Verify default hint is used
    assert result["llm_context_hint"] == "This is a response from a Pyramid API"


def test_llm_context_hint_with_manual_tool():
    """Test llm_context_hint with @tool decorated functions."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Create a manual tool with custom hint
    @tool(name="custom_calculator", description="Calculator with custom hint")
    def calculator_tool(operation: str, a: int, b: int) -> int:
        """Perform mathematical operations."""
        if operation == "add":
            return a + b
        elif operation == "multiply":
            return a * b
        return 0

    # Get the MCP instance and verify tool registration
    pyramid_mcp = config.registry.pyramid_mcp

    # Simulate tool discovery
    config.scan(categories=["pyramid_mcp"])
    pyramid_mcp.discover_tools()

    # Verify tool is registered
    tools = pyramid_mcp.protocol_handler.tools
    assert "custom_calculator" in tools

    # The tool should work even without explicit llm_context_hint
    # (this tests compatibility with existing manual tools)
    tool_obj = tools["custom_calculator"]
    assert tool_obj.name == "custom_calculator"
    assert tool_obj.description == "Calculator with custom hint"


def test_route_based_tool_with_llm_context_hint():
    """Test route-based tools with llm_context_hint predicate."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Add a route with custom llm_context_hint
    config.add_route("financial_data", "/api/financial/{account_id}")

    def financial_data_view(request):
        """Get financial data for account."""
        account_id = request.matchdict["account_id"]
        return {"account_id": account_id, "balance": 1234.56, "currency": "USD"}

    # Add view with llm_context_hint predicate
    config.add_view(
        financial_data_view,
        route_name="financial_data",
        renderer="json",
        llm_context_hint="Sensitive financial account information from banking system",
    )

    # Get MCP instance and discover tools
    pyramid_mcp = config.registry.pyramid_mcp
    pyramid_mcp.discover_tools()

    # Create a mock request to test introspection
    request = DummyRequest()
    request.matchdict = {"account_id": "12345"}

    # The introspection should capture the custom hint
    # This will be verified when the tool is actually called
    # For now, just verify the route was added
    routes = config.get_routes_mapper().get_routes()
    route_names = [route.name for route in routes]
    assert "financial_data" in route_names


def test_empty_llm_context_hint_falls_back_to_default():
    """Test that empty or None llm_context_hint values fall back to default."""
    schema = MCPContextResultSchema()

    test_cases = [
        None,  # None value
        "",  # Empty string
        "   ",  # Whitespace only
    ]

    for empty_hint in test_cases:
        mock_response = Response(json={"data": "test"})
        mock_response.headers["Content-Type"] = "application/json"

        view_info = {
            "llm_context_hint": empty_hint,
            "url": "https://api.example.com/data",
        }

        data = {"response": mock_response, "view_info": view_info}

        result = schema.dump(data)

        # Should fall back to default hint
        assert (
            result["llm_context_hint"] == "This is a response from a Pyramid API"
        ), f"Failed for empty hint value: {repr(empty_hint)}"


def test_llm_context_hint_with_non_json_response():
    """Test llm_context_hint with non-JSON responses."""
    schema = MCPContextResultSchema()

    # Mock text response
    mock_response = Response("Plain text response")
    mock_response.headers["Content-Type"] = "text/plain"

    view_info = {
        "llm_context_hint": "Plain text API response for data processing",
        "url": "https://api.example.com/text",
    }

    data = {"response": mock_response, "view_info": view_info}

    result = schema.dump(data)

    # Verify custom hint is used with text responses too
    assert result["llm_context_hint"] == "Plain text API response for data processing"
    assert result["representation"]["format"] == "text"
    assert result["representation"]["content"] == "Plain text response"


def test_llm_context_hint_predicate_integration_end_to_end():
    """Test complete integration of llm_context_hint predicate."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Add route with custom hint
    config.add_route("user_profile", "/users/{user_id}")

    def get_user_profile(request):
        """Get user profile information."""
        return {
            "user_id": request.matchdict["user_id"],
            "name": "John Doe",
            "email": "john@example.com",
        }

    # Add view with llm_context_hint predicate
    config.add_view(
        get_user_profile,
        route_name="user_profile",
        renderer="json",
        request_method="GET",
        llm_context_hint="User profile data containing personal information",
    )

    # Enable route discovery
    mcp_config = config.registry.pyramid_mcp.config
    mcp_config.route_discovery_enabled = True

    # Discover tools
    pyramid_mcp = config.registry.pyramid_mcp
    pyramid_mcp.discover_tools()

    # Verify the tool was created
    tools = pyramid_mcp.protocol_handler.tools

    # Look for the user profile tool (name will be generated)
    profile_tools = [name for name in tools.keys() if "user_profile" in name.lower()]
    assert (
        len(profile_tools) > 0
    ), f"No user profile tools found. Available tools: {list(tools.keys())}"

    # The tool should exist and be callable
    tool_name = profile_tools[0]
    tool_obj = tools[tool_name]
    assert tool_obj is not None

    # Test the actual tool execution would use the custom hint
    # This is handled by the schema transformation during actual execution


# =============================================================================
# 🧪 INTEGRATION TESTS
# =============================================================================


def test_multiple_views_with_different_hints():
    """Test multiple views with different llm_context_hint values."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Add multiple routes with different hints
    config.add_route("public_data", "/api/public")
    config.add_route("private_data", "/api/private")

    def public_data_view(request):
        return {"type": "public", "data": "accessible to all"}

    def private_data_view(request):
        return {"type": "private", "data": "restricted access"}

    # Add views with different llm_context_hint values
    config.add_view(
        public_data_view,
        route_name="public_data",
        renderer="json",
        llm_context_hint="Public information available to all users",
    )

    config.add_view(
        private_data_view,
        route_name="private_data",
        renderer="json",
        llm_context_hint="Confidential data requiring authorization",
    )

    # Test that each view would have its own custom hint
    # This is verified through the introspection mechanism
    routes = config.get_routes_mapper().get_routes()
    route_names = [route.name for route in routes]

    assert "public_data" in route_names
    assert "private_data" in route_names


def test_backward_compatibility_without_llm_context_hint():
    """Test that existing code without llm_context_hint still works."""
    schema = MCPContextResultSchema()

    # Test old-style view_info without llm_context_hint
    mock_response = Response(json={"legacy": "data"})
    mock_response.headers["Content-Type"] = "application/json"

    view_info = {
        "url": "https://legacy-api.example.com/data",
        "mcp_description": "Legacy endpoint description"
        # No llm_context_hint - should use default
    }

    data = {"response": mock_response, "view_info": view_info}

    result = schema.dump(data)

    # Should use default hint for backward compatibility
    assert result["llm_context_hint"] == "This is a response from a Pyramid API"
    assert result["type"] == "mcp/context"
    assert result["representation"]["content"]["legacy"] == "data"
