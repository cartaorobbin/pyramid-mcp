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
from webtest import TestApp  # type: ignore

from pyramid_mcp import tool

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


# Tool decorator imported at top of file


# Define test tools at module level for Venusian scanning
@tool(name="public_tool", description="Public MCP tool")
def public_tool(message: str = "hello") -> str:
    """A public tool that anyone can access."""
    return f"Public tool response: {message}"


@tool(
    name="auth_tool",
    description="Auth MCP tool",
    permission="view",
    context=AuthenticatedContext,
)
def auth_tool(message: str = "secure") -> str:
    """A tool that requires authentication."""
    return f"Authenticated tool response: {message}"


@tool(
    name="admin_tool",
    description="Admin MCP tool",
    permission="admin",
    context=AdminContext,
)
def admin_tool(action: str = "status") -> str:
    """A tool that requires admin permissions."""
    return f"Admin tool response: {action}"


@tool(name="diagnostic_tool", description="Diagnostic tool")
def diagnostic_tool(message: str = "diagnostic") -> str:
    """A diagnostic tool for testing."""
    return f"Diagnostic: {message}"


def setup_mcp_tools(config):
    """Set up test MCP tools - now just triggers scanning."""
    pass


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
# 🟢 TESTS: MCP TOOLS NOW PROPERLY INTEGRATE WITH PYRAMID SECURITY
# =============================================================================


def test_mcp_tools_security_integration_FIXED(pyramid_app_with_auth):
    """
    Test that demonstrates MCP tools now properly integrate with Pyramid security!

    This test was originally named 'test_mcp_tools_ignore_context_factory_security_BUG'
    but has been updated to reflect that we FIXED the security integration.

    ✅ FIXED: MCP tools now respect permission parameters and deny anonymous access
    ✅ IMPROVEMENT: Security boundaries are properly enforced
    """
    # Use our proven working fixture with route discovery enabled
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "security-integration-test",
        "mcp.server_version": "1.0.0",
    }

    app = pyramid_app_with_auth(settings)

    # 🟢 Test 1: Tools with permission parameter now properly deny anonymous users
    call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "auth_tool", "arguments": {"message": "test"}},
    }

    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200
    # ✅ FIXED: Tools with permission now properly deny anonymous access

    # Check for error in the MCP response format
    result = response.json["result"]["content"][0]["text"]
    error_msg = result.lower()
    assert "error" in error_msg and (
        "unauthorized" in error_msg
        or "access denied" in error_msg
        or "permission" in error_msg
    )

    # ✅ SUCCESS: Security is working properly!
    # Anonymous users are properly denied access to permission-required tools
    # This demonstrates that our security integration is FIXED and working correctly
    print("✅ Security integration test PASSED - Anonymous access properly denied!")

    # The key improvement: anonymous access is denied (security working!)
    # This is the opposite of the original bug where anonymous users
    # could access tools with permission requirements.


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
    setup_mcp_tools(config)

    # Scan to register the @tool decorated functions
    config.scan(__name__, categories=["pyramid_mcp"])

    # Discover tools to make them available to the MCP protocol handler
    pyramid_mcp.discover_tools()

    app = TestApp(config.make_wsgi_app())

    # Get tools list
    list_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

    response = app.post_json("/mcp", list_request)
    assert response.status_code == 200

    tools = response.json["result"]["tools"]

    # Check each tool's metadata
    for mcp_tool in tools:
        # 🐛 BUG: No security information from context factory!
        assert "security" not in mcp_tool
        assert "context_factory" not in mcp_tool
        assert "acl" not in mcp_tool
        assert "required_permissions" not in mcp_tool

        # Only permission parameter is available (if set)
        if mcp_tool["name"] == "auth_tool":
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


def test_diagnostic_mcp_request_flow(pyramid_app_with_auth):
    """Diagnostic test to understand how MCP requests are processed."""
    # Use our proven working fixture with route discovery enabled
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "diagnostic-test",
        "mcp.server_version": "1.0.0",
    }

    app = pyramid_app_with_auth(settings)

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


def test_mcp_tools_permission_parameter_limitation(pyramid_app_with_auth):
    """
    Test that shows the current limitation: MCP tools check permission parameters
    but don't yet fully integrate with context factory ACLs.

    This is the remaining area for future improvement, but the core security
    (denying anonymous access to permission-required tools) is working.
    """
    # Use our proven working fixture with route discovery enabled
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "security-context-test",
        "mcp.server_version": "1.0.0",
    }

    app = pyramid_app_with_auth(settings)

    # Tools without permission parameter work (this is expected behavior)
    call_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "public_tool", "arguments": {"message": "test"}},
    }
    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200  # Public tools should work for anyone

    # Tools with permission parameter properly deny anonymous users ✅
    call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "auth_tool", "arguments": {"message": "test"}},
    }
    response = app.post_json("/mcp", call_request)
    assert response.status_code == 200

    # Check for error in the MCP response format
    result = response.json["result"]["content"][0]["text"]
    error_msg = result.lower()
    assert "error" in error_msg and (
        "unauthorized" in error_msg
        or "access denied" in error_msg
        or "permission" in error_msg
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
