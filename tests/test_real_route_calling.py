"""
Test that auto-discovered MCP tools now call actual Pyramid views.
"""

import json
import pytest
from pyramid.config import Configurator
from pyramid.view import view_config
from webtest import TestApp

from pyramid_mcp import tool


@tool(name="manual_calculator", description="Manual calculator tool")
def calculator_tool(operation: str, a: float, b: float) -> str:
    """Manual calculator tool for comparison."""
    if operation == "add":
        return f"{a} + {b} = {a + b}"
    elif operation == "multiply":
        return f"{a} * {b} = {a * b}"
    else:
        return f"Unknown operation: {operation}"


def test_auto_discovered_tools_call_real_views():
    """Test that auto-discovered tools call actual Pyramid views, not simulations."""
    settings = {
        'mcp.server_name': 'real-test-server',
        'mcp.server_version': '1.0.0', 
        'mcp.mount_path': '/mcp',
        'mcp.route_discovery.enabled': 'true',
        'mcp.route_discovery.include_patterns': 'api/*',
    }
    
    config = Configurator(settings=settings)
    
    # Add real API endpoints
    config.add_route('api_hello', '/api/hello', request_method='GET')
    config.add_route('api_user', '/api/user/{id}', request_method='GET')
    config.add_route('api_create_post', '/api/posts', request_method='POST')
    
    @view_config(route_name='api_hello', renderer='json')
    def hello_view(request):
        """Say hello with optional name parameter."""
        name = request.params.get('name', 'World')
        return {
            "message": f"Hello, {name}!",
            "timestamp": "2024-12-28T15:30:00Z",
            "source": "real_pyramid_view"
        }
    
    @view_config(route_name='api_user', renderer='json')
    def user_view(request):
        """Get user information by ID."""
        user_id = request.matchdict.get('id')
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "active": True,
            "source": "real_pyramid_view"
        }
    
    @view_config(route_name='api_create_post', renderer='json')
    def create_post_view(request):
        """Create a new post."""
        # Access JSON body data
        title = getattr(request, 'json_body', {}).get('title', 'Default Title')
        content = getattr(request, 'json_body', {}).get('content', 'Default Content')
        
        return {
            "id": 12345,
            "title": title,
            "content": content,
            "status": "created",
            "source": "real_pyramid_view"
        }
    
    # Add views to config
    config.add_view(hello_view, route_name='api_hello', renderer='json')
    config.add_view(user_view, route_name='api_user', renderer='json')
    config.add_view(create_post_view, route_name='api_create_post', renderer='json')
    
    # Include pyramid_mcp after adding routes/views
    config.include('pyramid_mcp')
    
    app = TestApp(config.make_wsgi_app())
    
    # First verify the direct API endpoints work
    hello_response = app.get('/api/hello?name=DirectAPI')
    assert hello_response.json['message'] == "Hello, DirectAPI!"
    assert hello_response.json['source'] == "real_pyramid_view"
    
    user_response = app.get('/api/user/42')
    assert user_response.json['id'] == "42"
    assert user_response.json['name'] == "User 42"
    assert user_response.json['source'] == "real_pyramid_view"
    
    # Initialize MCP
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
    
    # Get list of tools
    mcp_list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    response = app.post_json('/mcp', mcp_list_request)
    assert response.status_code == 200
    tools = response.json['result']['tools']
    tool_names = [tool['name'] for tool in tools]
    
    print(f"Available tools: {tool_names}")
    
    # Should have both manual and auto-discovered tools
    assert 'manual_calculator' in tool_names
    
    # Find auto-discovered tools
    auto_tools = [name for name in tool_names if 'api' in name.lower()]
    assert len(auto_tools) >= 2, f"Expected auto-discovered tools, got: {tool_names}"
    
    # Test calling auto-discovered GET tool (api_hello)
    hello_tool_name = next(name for name in tool_names if 'hello' in name.lower())
    
    mcp_call_hello = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": hello_tool_name,
            "arguments": {"name": "MCP_Client"}
        }
    }
    
    response = app.post_json('/mcp', mcp_call_hello)
    assert response.status_code == 200
    
    # Parse the response - should be real JSON from view, not simulation
    result = response.json['result']['content'][0]['text']
    
    # Should be JSON string from the actual view
    parsed_result = json.loads(result)
    assert parsed_result['message'] == "Hello, MCP_Client!"
    assert parsed_result['source'] == "real_pyramid_view"
    assert parsed_result['timestamp'] is not None
    
    # Test calling auto-discovered GET tool with path parameter (api_user)
    user_tool_name = next(name for name in tool_names if 'user' in name.lower() and 'create' not in name.lower())
    
    mcp_call_user = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": user_tool_name,
            "arguments": {"id": "999"}
        }
    }
    
    response = app.post_json('/mcp', mcp_call_user)
    assert response.status_code == 200
    
    result = response.json['result']['content'][0]['text']
    parsed_result = json.loads(result)
    assert parsed_result['id'] == "999"
    assert parsed_result['name'] == "User 999"
    assert parsed_result['source'] == "real_pyramid_view"
    
    # Test calling auto-discovered POST tool (api_create_post)
    post_tool_name = next(name for name in tool_names if 'post' in name.lower())
    
    mcp_call_post = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": post_tool_name,
            "arguments": {
                "title": "My Amazing Post",
                "content": "This post was created via MCP!"
            }
        }
    }
    
    response = app.post_json('/mcp', mcp_call_post)
    assert response.status_code == 200
    
    result = response.json['result']['content'][0]['text']
    parsed_result = json.loads(result)
    assert parsed_result['title'] == "My Amazing Post"
    assert parsed_result['content'] == "This post was created via MCP!"
    assert parsed_result['status'] == "created"
    assert parsed_result['source'] == "real_pyramid_view"
    
    # Test manual tool still works
    mcp_call_manual = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "manual_calculator",
            "arguments": {"operation": "add", "a": 10, "b": 5}
        }
    }
    
    response = app.post_json('/mcp', mcp_call_manual)
    assert response.status_code == 200
    
    result = response.json['result']['content'][0]['text']
    assert result == "10 + 5 = 15"


def test_comparison_simulation_vs_real():
    """Test to show the difference between old simulation and new real responses."""
    # This test documents the change from simulation to real responses
    
    # Old behavior would return:
    # {
    #     "action": "Would call hello_view for GET /api/hello",
    #     "parameters": {"name": "test"},
    #     "route": "api_hello",
    #     "method": "GET"
    # }
    
    # New behavior returns actual view response as JSON string:
    # '{"message": "Hello, test!", "timestamp": "...", "source": "real_pyramid_view"}'
    
    # This test confirms we're getting real responses
    settings = {
        'mcp.server_name': 'comparison-server',
        'mcp.route_discovery.enabled': 'true',
        'mcp.route_discovery.include_patterns': 'test/*',
    }
    
    config = Configurator(settings=settings)
    config.add_route('test_endpoint', '/test/endpoint', request_method='GET')
    
    @view_config(route_name='test_endpoint', renderer='json')
    def test_view(request):
        return {"real_response": True, "message": "This is real!"}
    
    config.add_view(test_view, route_name='test_endpoint', renderer='json')
    config.include('pyramid_mcp')
    
    app = TestApp(config.make_wsgi_app())
    
    # Get tools and call the auto-discovered one
    mcp_list_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    response = app.post_json('/mcp', mcp_list_request)
    tools = response.json['result']['tools']
    tool_names = [tool['name'] for tool in tools]
    
    test_tool_name = next(name for name in tool_names if 'test' in name.lower())
    
    mcp_call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": test_tool_name,
            "arguments": {}
        }
    }
    
    response = app.post_json('/mcp', mcp_call_request)
    result = response.json['result']['content'][0]['text']
    
    # Should be JSON string, not simulation object
    parsed_result = json.loads(result)
    
    # Verify we get real response, not simulation
    assert parsed_result['real_response'] is True
    assert parsed_result['message'] == "This is real!"
    
    # Verify we DON'T get simulation fields
    assert 'action' not in parsed_result
    assert 'parameters' not in parsed_result
    assert 'route' not in parsed_result


if __name__ == '__main__':
    # Run tests directly for debugging
    print("Testing real route calling...")
    test_auto_discovered_tools_call_real_views()
    print("✅ Real route calling test passed!")
    
    print("\nTesting simulation vs real comparison...")
    test_comparison_simulation_vs_real()
    print("✅ Comparison test passed!")
    
    print("\n🎉 All real route calling tests passed!") 