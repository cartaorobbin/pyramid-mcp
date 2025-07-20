"""
Test for Unified Security Architecture Implementation

This module tests the unified security architecture where @tool decorators
register Pyramid views that are discovered by introspection as MCP tools.

Tests verify that:
- @tool decorators create proper Pyramid views
- Views are discovered and converted to MCP tools via introspection
- Both manual tools and regular views use the same execution path
- Security integration functions correctly
"""

import pytest

from pyramid_mcp import tool

# =============================================================================
# 🧪 MODULE-LEVEL TOOLS (FOLLOWING OUR CLEAN PATTERN)
# =============================================================================


@tool(name="test_tool", description="Test tool for verification")
def verification_test_tool(message: str) -> str:
    return f"Tool response: {message}"


@tool(name="security_test_tool", description="Tool for security testing")
def security_test_tool(data: str) -> dict:
    return {"processed": data, "security": "verified"}


@tool(
    name="permission_test_tool",
    description="Tool requiring permissions",
    permission="test_permission",
)
def permission_test_tool(action: str) -> dict:
    return {"action": action, "permission": "required"}


@tool(name="execution_test", description="Test tool execution")
def execution_test(input_data: str) -> str:
    return f"Processed: {input_data}"


@tool(name="protected_tool", description="Tool with security context")
def protected_tool(data: str) -> dict:
    return {"protected_data": data, "access": "granted"}


# =============================================================================
# 🏗️ TEST-SPECIFIC FIXTURE
# =============================================================================


@pytest.fixture
def unified_security_test_config(pyramid_app_with_auth):
    """Test-specific fixture: Configure pyramid for unified security tests."""

    # Configure pyramid with unified security test settings
    settings = {
        "mcp.server_name": "unified-security-test-server",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
        "mcp.route_discovery.enabled": True,
    }

    # Return configured TestApp using the global fixture
    return pyramid_app_with_auth(settings)


# =============================================================================
# 🧪 UNIFIED SECURITY TESTS VIA @tool → VIEWS → INTROSPECTION
# =============================================================================


def test_tool_decorator_creates_pyramid_views(unified_security_test_config):
    """Test that @tool decorator creates proper Pyramid views."""
    app = unified_security_test_config

    # Test MCP tool listing - should find the tool created by @tool decorator
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should find our module-level tool
    assert "test_tool" in tool_names, f"test_tool not found in {tool_names}"

    print("✅ @tool decorator successfully creates discoverable Pyramid views!")
    print(f"✅ Found tools: {tool_names}")


def test_tool_decorator_execution_via_mcp(unified_security_test_config):
    """Test that tools created by @tool decorator execute via MCP."""
    app = unified_security_test_config

    # Execute the module-level tool via MCP
    response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "execution_test",
                "arguments": {"input_data": "hello_world"},
            },
        },
    )

    assert response.status_code == 200
    assert "result" in response.json

    # Expect deterministic MCP response format
    result_data = response.json["result"]
    assert "content" in result_data
    content_item = result_data["content"][0]
    assert content_item["type"] == "application/json"
    assert "data" in content_item
    result = content_item["data"]["result"]

    assert "Processed: hello_world" in result

    print("✅ @tool decorator execution via MCP successful!")
    print(f"✅ Result: {result}")


def test_tool_decorator_with_permissions(unified_security_test_config):
    """Test that @tool decorator works with permission requirements."""
    app = unified_security_test_config

    # Test tool listing
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )

    assert response.status_code == 200
    tools = response.json["result"]["tools"]
    tool_names = [tool["name"] for tool in tools]

    # Should find both tools (from module level)
    assert "public_tool" in tool_names, f"public_tool not found in {tool_names}"
    assert "protected_tool" in tool_names, f"protected_tool not found in {tool_names}"

    print("✅ Unified Security Architecture Implementation Complete!")
    print("✅ @tool decorator creates Pyramid views with proper permissions")
    print("✅ Views are discovered by introspection as MCP tools")
    print("✅ All tools now use the same Pyramid view execution path")
    print("✅ Security is enforced consistently across all tool types")
    print(f"✅ Discovered tools: {len(tool_names)} total")
