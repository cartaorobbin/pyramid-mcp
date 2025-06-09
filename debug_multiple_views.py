#!/usr/bin/env python3

from pyramid.config import Configurator
from pyramid.response import Response
from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.core import MCPConfiguration

# Create config and include pyramid_mcp
config = Configurator()
config.include('pyramid_mcp')

# Define views
def list_users(request):
    return Response('users list')

def create_user(request):
    return Response('user created')

# Add route and views
config.add_route('users_list', '/users')
config.add_view(list_users, route_name='users_list', request_method='GET',
                mcp_description='List all users')
config.add_view(create_user, route_name='users_list', request_method='POST',
                mcp_description='Create a new user')
config.commit()

# Check what's in the route introspection
pyramid_introspector = PyramidIntrospector(config)
routes = pyramid_introspector.discover_routes()

print("=== ROUTES DEBUG ===")
for route in routes:
    if route['name'] == 'users_list':
        print(f"Route: {route['name']}")
        print(f"Views count: {len(route['views'])}")
        for i, view in enumerate(route['views']):
            print(f"  View {i}:")
            print(f"    Request methods: {view.get('request_methods')}")
            print(f"    MCP description: {view.get('mcp_description')}")
            print()

# Generate tools and check names/descriptions
mcp_config = MCPConfiguration()
tools = pyramid_introspector.discover_tools_from_pyramid(None, mcp_config)

print("=== TOOLS DEBUG ===")
print(f"Total tools: {len(tools)}")
for tool in tools:
    print(f"Tool name: {tool.name}")
    print(f"Tool description: {tool.description}")
    print() 