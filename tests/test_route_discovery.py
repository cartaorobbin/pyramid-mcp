"""
Tests for Pyramid route discovery functionality.
"""

import pytest
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.core import MCPConfiguration


def test_discover_routes_basic(pyramid_config):
    """Test basic route discovery functionality."""
    # Commit the configuration so routes are available for introspection
    pyramid_config.commit()
    introspector = PyramidIntrospector(pyramid_config)
    
    routes_info = introspector.discover_routes()
    
    # Should discover our test routes
    assert len(routes_info) > 0
    
    # Check for expected routes from conftest.py
    route_names = [route['name'] for route in routes_info]
    expected_routes = ['create_user', 'get_user', 'update_user', 'delete_user', 'list_users']
    
    for expected in expected_routes:
        assert expected in route_names, f"Expected route {expected} not found in {route_names}"


def test_route_info_structure(pyramid_config):
    """Test that route info has the expected structure."""
    # Commit the configuration so routes are available for introspection
    pyramid_config.commit()
    introspector = PyramidIntrospector(pyramid_config)
    routes_info = introspector.discover_routes()
    
    # Get the first route
    route_info = routes_info[0]
    
    # Check required fields
    assert 'name' in route_info
    assert 'pattern' in route_info
    assert 'request_methods' in route_info
    assert 'views' in route_info
    assert 'predicates' in route_info
    
    # Check predicates structure
    predicates = route_info['predicates']
    assert isinstance(predicates, dict)
    
    # Check views structure
    views = route_info['views']
    assert isinstance(views, list)
    
    if views:  # If there are views
        view = views[0]
        assert 'callable' in view
        assert 'request_methods' in view
        assert 'predicates' in view


def test_discover_tools_from_pyramid(pyramid_config):
    """Test conversion of routes to MCP tools."""
    # Commit the configuration so routes are available for introspection
    pyramid_config.commit()
    config = MCPConfiguration()
    introspector = PyramidIntrospector(pyramid_config)
    
    tools = introspector.discover_tools_from_pyramid(None, config)
    
    # Should create tools for our routes
    assert len(tools) > 0
    
    # Check tool structure
    tool = tools[0]
    assert hasattr(tool, 'name')
    assert hasattr(tool, 'description')
    assert hasattr(tool, 'input_schema')
    assert hasattr(tool, 'handler')
    
    # Test tool name generation
    tool_names = [tool.name for tool in tools]
    # Should have tools like 'create_user', 'get_user', etc.
    assert any('user' in name for name in tool_names)


def test_tool_name_generation():
    """Test tool name generation logic."""
    introspector = PyramidIntrospector()
    
    # Test various scenarios
    assert introspector._generate_tool_name('get_user', 'GET', '/users/{id}') == 'get_user'
    assert introspector._generate_tool_name('users', 'GET', '/users') == 'list_users'
    assert introspector._generate_tool_name('user', 'POST', '/users') == 'create_user'
    assert introspector._generate_tool_name('user', 'PUT', '/users/{id}') == 'update_user'
    assert introspector._generate_tool_name('user', 'DELETE', '/users/{id}') == 'delete_user'


def test_input_schema_generation():
    """Test JSON schema generation from route patterns."""
    introspector = PyramidIntrospector()
    
    # Test route with path parameters
    def sample_view(request):
        return Response('test')
    
    schema = introspector._generate_input_schema('/users/{id}', sample_view, 'GET')
    
    assert schema is not None
    assert schema['type'] == 'object'
    assert 'id' in schema['properties']
    assert 'id' in schema['required']
    assert schema['properties']['id']['type'] == 'string'
    assert 'Path parameter' in schema['properties']['id']['description']


def test_input_schema_with_annotations():
    """Test schema generation with type annotations."""
    introspector = PyramidIntrospector()
    
    def annotated_view(request, user_id: int, active: bool = True):
        return Response('test')
    
    schema = introspector._generate_input_schema('/users/{user_id}', annotated_view, 'POST')
    
    assert schema is not None
    assert 'user_id' in schema['properties']
    assert 'active' in schema['properties']
    
    # user_id should be string (path param) despite int annotation
    assert schema['properties']['user_id']['type'] == 'string'
    
    # active should be boolean
    assert schema['properties']['active']['type'] == 'boolean'
    
    # user_id should be required, active should not be (has default)
    assert 'user_id' in schema['required']
    assert 'active' not in schema['required']


def test_pattern_matching():
    """Test pattern matching for include/exclude functionality."""
    introspector = PyramidIntrospector()
    
    # Test exact matches
    assert introspector._pattern_matches('api', '/api/users', 'api_users')
    assert introspector._pattern_matches('users', '/users', 'users')
    
    # Test wildcard matches
    assert introspector._pattern_matches('api/*', '/api/users', 'api_users')
    assert introspector._pattern_matches('api/*', '/api/posts/comments', 'api_posts')
    assert not introspector._pattern_matches('api/*', '/auth/login', 'auth_login')
    
    # Test route name matching
    assert introspector._pattern_matches('user*', '/some/path', 'user_management')


def test_route_exclusion():
    """Test route exclusion logic."""
    introspector = PyramidIntrospector()
    
    # Test MCP route exclusion
    mcp_route = {'name': 'mcp_http', 'pattern': '/mcp'}
    config = MCPConfiguration()
    assert introspector._should_exclude_route(mcp_route, config)
    
    # Test static route exclusion
    static_route = {'name': 'static_assets', 'pattern': '/static/css'}
    assert introspector._should_exclude_route(static_route, config)
    
    # Test normal route inclusion
    normal_route = {'name': 'user_list', 'pattern': '/users'}
    assert not introspector._should_exclude_route(normal_route, config)


def test_include_patterns():
    """Test include pattern functionality."""
    introspector = PyramidIntrospector()
    
    config = MCPConfiguration(include_patterns=['api/*', 'users'])
    
    # Should include matching routes
    api_route = {'name': 'api_users', 'pattern': '/api/users'}
    assert not introspector._should_exclude_route(api_route, config)
    
    users_route = {'name': 'users', 'pattern': '/users'}
    assert not introspector._should_exclude_route(users_route, config)
    
    # Should exclude non-matching routes
    auth_route = {'name': 'auth_login', 'pattern': '/auth/login'}
    assert introspector._should_exclude_route(auth_route, config)


def test_exclude_patterns():
    """Test exclude pattern functionality."""
    introspector = PyramidIntrospector()
    
    config = MCPConfiguration(exclude_patterns=['internal/*', 'admin'])
    
    # Should exclude matching routes
    internal_route = {'name': 'internal_stats', 'pattern': '/internal/stats'}
    assert introspector._should_exclude_route(internal_route, config)
    
    admin_route = {'name': 'admin', 'pattern': '/admin'}
    assert introspector._should_exclude_route(admin_route, config)
    
    # Should include non-matching routes
    public_route = {'name': 'public_info', 'pattern': '/info'}
    assert not introspector._should_exclude_route(public_route, config)


def test_tool_handler_creation():
    """Test MCP tool handler creation."""
    introspector = PyramidIntrospector()
    
    def sample_view(request):
        return Response('test')
    
    route_info = {
        'name': 'test_route',
        'pattern': '/test/{id}',
        'views': []
    }
    
    view_info = {
        'callable': sample_view,
        'request_methods': ['GET']
    }
    
    handler = introspector._create_route_handler(route_info, view_info, 'GET')
    
    # Test handler execution
    result = handler(id='123', param='value')
    
    assert isinstance(result, dict)
    assert 'action' in result
    assert 'parameters' in result
    assert 'route' in result
    assert 'method' in result
    
    assert result['parameters'] == {'id': '123', 'param': 'value'}
    assert result['route'] == 'test_route'
    assert result['method'] == 'GET'


def test_integration_with_complex_routes():
    """Test route discovery with more complex route configurations."""
    config = Configurator()
    
    # Add routes with various configurations
    config.add_route('api_users_list', '/api/users', request_method='GET')
    config.add_route('api_user_detail', '/api/users/{id}', request_method=['GET', 'PUT', 'DELETE'])
    config.add_route('api_user_posts', '/api/users/{user_id}/posts', request_method='GET')
    config.add_route('static_files', '/static/*filepath')
    
    @view_config(route_name='api_users_list', renderer='json')
    def list_users(request):
        """List all users."""
        return {'users': []}
    
    @view_config(route_name='api_user_detail', request_method='GET', renderer='json')
    def get_user(request):
        """Get user by ID."""
        return {'user': {}}
    
    @view_config(route_name='api_user_detail', request_method='PUT', renderer='json')
    def update_user(request):
        """Update user by ID."""
        return {'updated': True}
    
    @view_config(route_name='api_user_posts', renderer='json')
    def get_user_posts(request):
        """Get posts for a user."""
        return {'posts': []}
    
    # Manually add views since scan() won't find local functions
    config.add_view(list_users, route_name='api_users_list', renderer='json')
    config.add_view(get_user, route_name='api_user_detail', request_method='GET', renderer='json')
    config.add_view(update_user, route_name='api_user_detail', request_method='PUT', renderer='json')
    config.add_view(get_user_posts, route_name='api_user_posts', renderer='json')
    
    # Commit configuration to make introspection work
    config.commit()
    
    # Test route discovery
    introspector = PyramidIntrospector(config)
    routes_info = introspector.discover_routes()
    
    # Should find our routes
    route_names = [r['name'] for r in routes_info]
    assert 'api_users_list' in route_names
    assert 'api_user_detail' in route_names
    assert 'api_user_posts' in route_names
    assert 'static_files' in route_names
    
    # Test tool generation with filtering
    mcp_config = MCPConfiguration(
        include_patterns=['api/*'],
        exclude_patterns=['static/*']
    )
    
    tools = introspector.discover_tools_from_pyramid(None, mcp_config)
    
    # Should create tools for API routes but not static
    tool_names = [tool.name for tool in tools]
    assert len(tools) > 0
    assert any('users' in name for name in tool_names)
    assert not any('static' in name for name in tool_names)
    
    # Should have multiple tools for routes with multiple methods
    user_detail_tools = [tool for tool in tools if 'user_detail' in tool.name or 'get_user' in tool.name]
    assert len(user_detail_tools) >= 2  # GET and PUT methods


def test_description_generation():
    """Test tool description generation."""
    introspector = PyramidIntrospector()
    
    def documented_view(request):
        """This is a well-documented view function."""
        return Response('test')
    
    def undocumented_view(request):
        return Response('test')
    
    # Should use docstring when available
    desc1 = introspector._generate_tool_description(
        'test_route', 'GET', '/test', documented_view
    )
    assert desc1 == "This is a well-documented view function."
    
    # Should generate description when no docstring
    desc2 = introspector._generate_tool_description(
        'user_list', 'GET', '/users', undocumented_view
    )
    assert 'Retrieve' in desc2
    assert 'User List' in desc2
    assert 'GET' in desc2
    assert '/users' in desc2 