#!/usr/bin/env python3
"""
Test Security Context Factory Bug with MCP Tools

This test suite demonstrates that MCP tools don't respect Pyramid's context factory
security system. The context factory security works perfectly for regular HTTP
endpoints, but MCP tools use pyramid-mcp's built-in security system which is separate.

Bug Summary:
1. Pyramid context factories work for regular views ✅
2. MCP tools ignore context factory ACLs ❌
3. MCP tools only check the permission parameter, not context ACLs ❌
4. No integration between context factory system and MCP security ❌
"""

import pytest
from pyramid.authorization import ALL_PERMISSIONS, Allow, Authenticated, Deny, Everyone
from pyramid.config import Configurator
from webtest import TestApp

# =============================================================================
# 🏗️ CONTEXT FACTORY FIXTURES
# =============================================================================


class PublicContext:
    """Public context - no authentication required."""

    __acl__ = [
        (Allow, Everyone, "view"),
    ]

    def __init__(self, request):
        self.request = request


class AuthenticatedContext:
    """Authenticated context - requires authentication."""

    __acl__ = [
        (Allow, Authenticated, "view"),
        (Allow, Authenticated, "edit"),
        (Deny, Everyone, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class AdminContext:
    """Admin context - only admin role allowed."""

    __acl__ = [
        (Allow, "role:admin", "view"),
        (Allow, "role:admin", "edit"),
        (Allow, "role:admin", "admin"),
        (Deny, Everyone, ALL_PERMISSIONS),
    ]

    def __init__(self, request):
        self.request = request


class MockSecurityPolicy:
    """Mock security policy for testing."""

    def __init__(self):
        self.authenticated_user = None
        self.principals = []

    def identity(self, request):
        """Return the current identity."""
        return self.authenticated_user

    def authenticated_userid(self, request):
        """Return the authenticated user ID."""
        return self.authenticated_user

    def effective_principals(self, request):
        """Return effective principals for the user."""
        if self.authenticated_user:
            return ["system.Authenticated"] + self.principals
        return ["system.Everyone"]

    def permits(self, request, context, permission):
        """Check if permission is allowed."""
        from pyramid.authorization import ACLHelper

        helper = ACLHelper()
        return helper.permits(context, self.effective_principals(request), permission)

    def set_user(self, user_id, principals=None):
        """Set the current user for testing."""
        self.authenticated_user = user_id
        self.principals = principals or []


@pytest.fixture
def mock_security_policy():
    """Mock security policy fixture."""
    return MockSecurityPolicy()


@pytest.fixture
def context_factory_config(mock_security_policy):
    """Pyramid configuration with context factory security."""
    config = Configurator()

    # Set security policy
    config.set_security_policy(mock_security_policy)

    # Add routes with different context factories
    config.add_route("public_endpoint", "/public", factory=PublicContext)
    config.add_route("auth_endpoint", "/auth-required", factory=AuthenticatedContext)
    config.add_route("admin_endpoint", "/admin-only", factory=AdminContext)

    return config


# =============================================================================
# 📝 VIEW DEFINITIONS FOR TESTING
# =============================================================================


def public_view(request):
    """Public view accessible to everyone."""
    return {"message": "Public data", "user": request.identity}


def auth_view(request):
    """View requiring authentication."""
    return {"message": "Authenticated data", "user": request.identity}


def admin_view(request):
    """View requiring admin role."""
    return {"message": "Admin data", "user": request.identity}


# =============================================================================
# 🔧 MCP TOOL DEFINITIONS
# =============================================================================


def setup_mcp_tools(pyramid_mcp):
    """Set up MCP tools for testing."""

    @pyramid_mcp.tool(name="public_tool", description="Public MCP tool")
    def public_tool(message: str = "hello") -> str:
        """Public tool that should be accessible to everyone."""
        return f"Public tool response: {message}"

    @pyramid_mcp.tool(name="auth_tool", description="Auth MCP tool", permission="view")
    def auth_tool(message: str = "secure") -> str:
        """Tool that should require authentication."""
        return f"Auth tool response: {message}"

    @pyramid_mcp.tool(
        name="admin_tool", description="Admin MCP tool", permission="admin"
    )
    def admin_tool(action: str = "status") -> str:
        """Tool that should require admin role."""
        return f"Admin tool response: {action}"


# =============================================================================
# ✅ TESTS: CONTEXT FACTORY SECURITY WORKS FOR REGULAR VIEWS
# =============================================================================


def test_context_factory_security_works_for_regular_views(
    context_factory_config, mock_security_policy
):
    """Test that context factory security works correctly for regular Pyramid views."""
    config = context_factory_config

    # Add views to config with proper route names and renderers
    config.add_view(
        public_view, route_name="public_endpoint", renderer="json", permission="view"
    )
    config.add_view(
        auth_view, route_name="auth_endpoint", renderer="json", permission="view"
    )
    config.add_view(
        admin_view, route_name="admin_endpoint", renderer="json", permission="admin"
    )

    # Need to commit the configuration for views to be properly registered
    config.commit()
    app = TestApp(config.make_wsgi_app())

    # 🟢 PUBLIC ENDPOINT - Everyone can access
    response = app.get("/public")
    assert response.status_code == 200
    assert response.json["message"] == "Public data"

    # 🔴 AUTH ENDPOINT - Anonymous user should be denied
    response = app.get("/auth-required", expect_errors=True)
    assert response.status_code == 403  # Forbidden

    # 🔴 ADMIN ENDPOINT - Anonymous user should be denied
    response = app.get("/admin-only", expect_errors=True)
    assert response.status_code == 403  # Forbidden

    # 🟢 AUTH ENDPOINT - Set authenticated user
    mock_security_policy.set_user("alice", ["role:user"])
    response = app.get("/auth-required")
    assert response.status_code == 200
    assert response.json["message"] == "Authenticated data"

    # 🔴 ADMIN ENDPOINT - Regular user should be denied
    response = app.get("/admin-only", expect_errors=True)
    assert response.status_code == 403  # Forbidden

    # 🟢 ADMIN ENDPOINT - Set admin user
    mock_security_policy.set_user("bob", ["role:admin"])
    response = app.get("/admin-only")
    assert response.status_code == 200
    assert response.json["message"] == "Admin data"


# =============================================================================
# ❌ TESTS: MCP TOOLS IGNORE CONTEXT FACTORY SECURITY (THE BUG!)
# =============================================================================


def test_mcp_tools_ignore_context_factory_security_BUG(
    context_factory_config, mock_security_policy
):
    """
    BUG DEMONSTRATION: MCP tools don't respect Pyramid's security system!

    This test demonstrates that MCP tools don't integrate with Pyramid's
    context factory security system at all.
    """
    config = context_factory_config

    # Include pyramid_mcp - uses default route without context factory
    config.include("pyramid_mcp")

    # Get the pyramid_mcp instance and set up tools
    pyramid_mcp = config.registry.pyramid_mcp
    setup_mcp_tools(pyramid_mcp)

    app = TestApp(config.make_wsgi_app())

    # 🔴 BUG: MCP tools don't check any security context at all
    # Anonymous user (no authentication)
    mock_security_policy.set_user(None)

    # Tools without permission parameter work even with no authentication
    call_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "public_tool", "arguments": {"message": "test"}},
    }

    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200  # Works fine - no security checking
    assert "result" in response.json
    assert "Public tool response" in response.json["result"]["content"][0]["text"]

    # 🔴 BUG: Even tools with permission parameter only use basic permission checking
    # not context factory ACLs
    call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "auth_tool", "arguments": {"message": "test"}},
    }

    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200
    assert "error" in response.json  # Fails due to permission parameter only
    assert "Authentication required" in response.json["error"]["message"]

    # 🔴 BUG: Even when we set authenticated user, it doesn't work!
    # This proves the MCP system doesn't integrate with Pyramid security
    mock_security_policy.set_user("alice", ["role:user"])

    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200
    # This still fails because MCP doesn't see the authenticated user!
    # The auth_context only contains the raw request, not the security context
    assert "error" in response.json  # STILL FAILS - proves the bug!
    assert "Authentication required" in response.json["error"]["message"]

    # 🔴 BUG: This shows MCP tools can't access Pyramid's security system at all!


def test_mcp_tools_only_check_permission_parameter_not_context_acl(
    context_factory_config, mock_security_policy
):
    """
    Demonstrate that MCP tools only check the permission parameter,
    not the context factory ACLs.
    """
    config = context_factory_config
    config.include("pyramid_mcp")

    pyramid_mcp = config.registry.pyramid_mcp
    setup_mcp_tools(pyramid_mcp)

    app = TestApp(config.make_wsgi_app())

    # Anonymous user
    mock_security_policy.set_user(None)

    # Tools without permission parameter work (ignoring context factory)
    call_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "public_tool", "arguments": {"message": "test"}},
    }
    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200  # Works despite AuthenticatedContext!

    # Tools with permission parameter fail (respecting permission parameter)
    call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "auth_tool", "arguments": {"message": "test"}},
    }
    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200
    assert "error" in response.json  # Fails due to permission parameter
    assert "Authentication required" in response.json["error"]["message"]


def test_mcp_context_factory_integration_FIXED(
    context_factory_config, mock_security_policy
):
    """
    Test that demonstrates the fix - MCP tools now respect context factories!

    This test configures a custom MCP route with AuthenticatedContext and verifies
    that our fix allows MCP tools to integrate with Pyramid's security system.
    """
    config = context_factory_config

    # Include pyramid_mcp first
    config.include("pyramid_mcp")
    pyramid_mcp = config.registry.pyramid_mcp

    # Create a custom MCP route with a context factory
    config.add_route("mcp_secure", "/mcp-secure", factory=AuthenticatedContext)
    config.add_view(
        pyramid_mcp._handle_mcp_http,
        route_name="mcp_secure",
        request_method="POST",
        renderer="json",
    )

    # Set up a tool that requires authentication
    @pyramid_mcp.tool(
        name="secure_context_tool",
        description="Tool with context factory security",
        permission="view",
    )
    def secure_context_tool(message: str = "secure") -> str:
        """Tool that should require authentication via context factory."""
        return f"Secure response: {message}"

    app = TestApp(config.make_wsgi_app())

    # 🔴 Test 1: Anonymous user should be denied by context factory
    mock_security_policy.set_user(None)

    call_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "secure_context_tool", "arguments": {"message": "test"}},
    }

    response = app.post_json("/mcp-secure", call_request)
    assert response.status_code == 200
    assert "error" in response.json  # Should be denied by context factory
    assert "Authentication required" in response.json["error"]["message"]

    # 🟢 Test 2: Authenticated user should be allowed
    mock_security_policy.set_user("alice", ["role:user"])

    response = app.post_json("/mcp-secure", call_request)
    assert response.status_code == 200
    # ✅ Fix is working! Authenticated user can access the tool
    assert (
        "result" in response.json
    ), "Fix should allow authenticated users through context factory ACL"
    assert "Secure response" in response.json["result"]["content"][0]["text"]


# =============================================================================
# 📊 TESTS: METADATA SHOWS MISSING SECURITY INFORMATION
# =============================================================================


def test_mcp_tools_metadata_missing_security_info(
    context_factory_config, mock_security_policy
):
    """Test that MCP tools don't show context factory security in their metadata."""
    config = context_factory_config
    config.include("pyramid_mcp")

    pyramid_mcp = config.registry.pyramid_mcp
    setup_mcp_tools(pyramid_mcp)

    app = TestApp(config.make_wsgi_app())

    # Get tools list
    list_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    response = app.post_json("/mcp", list_request)
    assert response.status_code == 200

    tools = response.json["result"]["tools"]

    # Check each tool's metadata
    for tool in tools:
        # 🐛 BUG: No security information from context factory!
        assert "security" not in tool
        assert "context_factory" not in tool
        assert "acl" not in tool
        assert "required_permissions" not in tool

        # Only permission parameter is available (if set)
        if tool["name"] == "auth_tool":
            # Even tools with permission parameter don't show it in metadata!
            # This is another issue - security info not exposed
            pass


# =============================================================================
# 🎯 TESTS: WHAT SHOULD HAPPEN (EXPECTED BEHAVIOR)
# =============================================================================


@pytest.mark.xfail(
    reason="Security integration bug: MCP tools don't respect context factory ACLs yet"
)
def test_what_mcp_security_should_look_like_EXPECTED():
    """
    This test shows what the expected behavior should be when the bug is fixed.

    NOTE: This test currently FAILS because the bug exists.
    When the bug is fixed, this test should PASS and show as XPASS.
    """
    # This is a specification test - it shows what we want to achieve
    # Currently all these assertions would fail due to the bug

    # Expected: MCP tools should respect context factory ACLs
    # Expected: MCP route with AuthenticatedContext should deny anonymous users
    # Expected: MCP tools should have access to security context
    # Expected: Tool metadata should show security requirements

    # When implemented, this should work:
    assert (
        False
    ), "This test needs actual implementation when security integration is added"


# =============================================================================
# 🔍 DIAGNOSTIC TESTS: UNDERSTANDING THE BUG
# =============================================================================


def test_diagnostic_mcp_request_flow(context_factory_config, mock_security_policy):
    """Diagnostic test to understand how MCP requests are processed."""
    config = context_factory_config
    config.include("pyramid_mcp")

    pyramid_mcp = config.registry.pyramid_mcp

    @pyramid_mcp.tool(name="diagnostic_tool", description="Diagnostic tool")
    def diagnostic_tool() -> str:
        """Tool for diagnostics."""
        return "Diagnostic response"

    app = TestApp(config.make_wsgi_app())

    # Anonymous user
    mock_security_policy.set_user(None)

    # The issue: MCP view _handle_mcp_http creates auth_context
    # but it only contains the request, not the context factory result
    call_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "diagnostic_tool", "arguments": {}},
    }

    # This works because:
    # 1. MCP view doesn't check context factory before handling message
    # 2. auth_context only contains raw request, not security context
    # 3. Protocol handler only checks permission parameter, not ACLs
    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200

    # 🐛 The bug is in pyramid_mcp/core.py _handle_mcp_http method:
    # It creates auth_context = {'request': request} but doesn't:
    # 1. Check if the route's context factory allows this request
    # 2. Pass context factory information to the protocol handler
    # 3. Integrate with Pyramid's security system properly


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
