#!/usr/bin/env python3

from pyramid.config import Configurator
from pyramid.response import Response

# Create config and include pyramid_mcp
config = Configurator()
config.include('pyramid_mcp')

# Define a simple view
def test_view(request):
    return Response('test')

# Add route and view with mcp_description
config.add_route('test_route', '/test')
config.add_view(test_view, route_name='test_route', mcp_description='Test description')
config.commit()

# Check what's in the introspectables
introspector = config.introspector
view_category = introspector.get_category("views") or []

print("=== VIEW INTROSPECTABLES ===")
for item in view_category:
    view_intr = item["introspectable"]
    route_name = view_intr.get("route_name")
    mcp_description = view_intr.get("mcp_description")
    print(f"Route: {route_name}")
    print(f"MCP Description: {mcp_description}")
    print(f"All keys: {list(view_intr.keys())}")
    print("---")

# Check using PyramidIntrospector
from pyramid_mcp.introspection import PyramidIntrospector

pyramid_introspector = PyramidIntrospector(config)
routes = pyramid_introspector.discover_routes()

print("\n=== PYRAMID INTROSPECTOR ROUTES ===")
for route in routes:
    if route['name'] == 'test_route':
        print(f"Route: {route['name']}")
        print(f"Views: {len(route['views'])}")
        for view in route['views']:
            view_info = view.get('view_info', view)
            mcp_desc = view_info.get('mcp_description')
            print(f"  View MCP Description: {mcp_desc}")
            print(f"  View keys: {list(view_info.keys())}") 