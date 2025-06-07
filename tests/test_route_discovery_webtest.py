"""
Test route discovery using webtest for end-to-end verification.
"""

import json
import pytest
from pyramid.config import Configurator
from pyramid.view import view_config
from webtest import TestApp

from pyramid_mcp import tool


@tool(name="manual_tool", description="A manually registered tool")
def manual_tool_func(text: str) -> str:
    """Echo text with prefix."""
    return f"Manual: {text}"


def test_api_view(request):
    """A simple test API endpoint."""
    return {"message": "Hello from test API", "id": 123}


def create_test_app():
    """Create a test Pyramid app with route discovery enabled."""
    settings = {
        'mcp.server_name': 'test-server',
        'mcp.server_version': '1.0.0', 
        'mcp.mount_path': '/mcp',
        'mcp.route_discovery.enabled': 'true',
        'mcp.route_discovery.include_patterns': 'api/*',
    }
    
    config = Configurator(settings=settings)
    
    # Add a test route
    config.add_route('api_test', '/api/test', request_method='GET')
    config.add_view(test_api_view, route_name='api_test', request_method='GET', renderer='json')
    
    # Include pyramid_mcp after adding routes/views
    config.include('pyramid_mcp')
    
    return config.make_wsgi_app()


def test_route_discovery_end_to_end():
    """Test that route discovery works end-to-end via webtest."""
    app = TestApp(create_test_app())
    
    # First, verify the original API endpoint works
    response = app.get('/api/test')
    assert response.status_code == 200
    data = response.json
    assert data['message'] == "Hello from test API"
    assert data['id'] == 123
    
    # Test MCP initialize
    mcp_init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        }
    }
    
    response = app.post_json('/mcp', mcp_init_request)
    assert response.status_code == 200
    data = response.json
    assert data['result']['serverInfo']['name'] == 'test-server'
    
    # Test MCP tools/list to see if route was discovered
    mcp_list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    response = app.post_json('/mcp', mcp_list_request)
    assert response.status_code == 200
    data = response.json
    
    tools = data['result']['tools']
    tool_names = [tool['name'] for tool in tools]
    
    print(f"Found tools: {tool_names}")
    
    # Should have both manual and auto-discovered tools
    assert 'manual_tool' in tool_names, "Manual tool should be registered"
    
    # Check for auto-discovered route tools
    # The route discovery should create tools from the /api/test endpoint
    route_tools = [name for name in tool_names if 'api' in name or 'test' in name]
    assert len(route_tools) > 0, f"Expected auto-discovered tools from route, got tools: {tool_names}"
    
    # Test calling the manual tool
    mcp_call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "manual_tool",
            "arguments": {"text": "hello"}
        }
    }
    
    response = app.post_json('/mcp', mcp_call_request)
    assert response.status_code == 200
    data = response.json
    assert data['result']['content'][0]['text'] == "Manual: hello"


def test_route_discovery_with_filtering():
    """Test route discovery with include/exclude patterns."""
    settings = {
        'mcp.server_name': 'filter-test',
        'mcp.route_discovery.enabled': 'true',
        'mcp.route_discovery.include_patterns': 'api/*',
        'mcp.route_discovery.exclude_patterns': 'admin/*',
    }
    
    config = Configurator(settings=settings)
    
    # Add routes - some should be included, some excluded
    config.add_route('api_users', '/api/users', request_method='GET')
    config.add_route('admin_users', '/admin/users', request_method='GET')
    config.add_route('home', '/', request_method='GET')
    
    @view_config(route_name='api_users', renderer='json')
    def api_users_view(request):
        return {"users": []}
    
    @view_config(route_name='admin_users', renderer='json') 
    def admin_users_view(request):
        return {"admin": "secret"}
    
    @view_config(route_name='home', renderer='json')
    def home_view(request):
        return {"message": "home"}
    
    config.add_view(api_users_view, route_name='api_users')
    config.add_view(admin_users_view, route_name='admin_users')
    config.add_view(home_view, route_name='home')
    
    config.include('pyramid_mcp')
    
    app = TestApp(config.make_wsgi_app())
    
    # Get list of tools
    mcp_list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    response = app.post_json('/mcp', mcp_list_request)
    assert response.status_code == 200
    
    tools = response.json['result']['tools']
    tool_names = [tool['name'] for tool in tools]
    
    print(f"Filtered tools: {tool_names}")
    
    # Should include API routes
    api_tools = [name for name in tool_names if 'api' in name.lower()]
    assert len(api_tools) > 0, "Should have tools from API routes"
    
    # Should exclude admin routes
    admin_tools = [name for name in tool_names if 'admin' in name.lower()]
    assert len(admin_tools) == 0, f"Should not have admin tools, found: {admin_tools}"


if __name__ == '__main__':
    # Run the tests manually for debugging
    print("Testing route discovery end-to-end...")
    test_route_discovery_end_to_end()
    print("✅ End-to-end test passed!")
    
    print("\nTesting route discovery filtering...")
    test_route_discovery_with_filtering()
    print("✅ Filtering test passed!")
    
    print("\n🎉 All route discovery tests passed!") 