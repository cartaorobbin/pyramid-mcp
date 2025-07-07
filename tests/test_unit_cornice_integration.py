"""
Unit tests for pyramid_mcp Cornice integration functionality.

This module tests:
- Cornice service discovery
- Integration with PyramidIntrospector
- Enhanced MCP tool generation with Cornice metadata
- Backward compatibility when Cornice is not installed

Tests use real Cornice services for comprehensive testing.
"""

import pytest
from pyramid.config import Configurator
from pyramid.response import Response
from cornice import Service  # type: ignore

from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.introspection import PyramidIntrospector


# =============================================================================
# 📋 REAL CORNICE FIXTURES
# =============================================================================


@pytest.fixture
def users_service():
    """Real Cornice service for testing."""
    users = Service(
        name='users',
        path='/users',
        description='User management service',
        cors_origins=['*'],
        cors_credentials=True
    )
    
    @users.get()
    def get_users(request):
        """Get all users"""
        return {'users': []}
    
    @users.post(validators=['validate_json'], permission='create')
    def create_user(request):
        """Create a new user"""
        return {'user': 'created'}
    
    return users


@pytest.fixture
def pyramid_config_with_cornice(users_service):
    """Pyramid configuration with real Cornice services."""
    config = Configurator()
    config.include('cornice')
    
    # Add the services to the config
    config.add_cornice_service(users_service)
    
    config.commit()
    return config


# =============================================================================
# 🔍 CORNICE DISCOVERY TESTS
# =============================================================================


def test_discover_cornice_services_with_real_services(pyramid_config_with_cornice):
    """Test Cornice service discovery with real services."""
    introspector = PyramidIntrospector(pyramid_config_with_cornice)
    services = introspector._discover_cornice_services(pyramid_config_with_cornice.registry)
    
    assert len(services) >= 1
    service_names = [s.get("name", "") for s in services]
    assert 'users' in service_names


# =============================================================================
# 🔄 INTEGRATION TESTS WITH EXISTING FUNCTIONALITY
# =============================================================================


def test_discover_routes_with_cornice_integration(pyramid_config_with_cornice):
    """Test that discover_routes integrates real Cornice metadata."""
    introspector = PyramidIntrospector(pyramid_config_with_cornice)
    routes_info = introspector.discover_routes()
    
    # Should have routes with Cornice metadata
    assert len(routes_info) > 0
    
    # Find the users route
    users_route = next((r for r in routes_info if r["name"] == "users"), None)
    assert users_route is not None
    
    # Check that cornice_service is populated
    assert "cornice_service" in users_route
    assert users_route["cornice_service"] is not None
    assert users_route["cornice_service"].get("name") == "users"


def test_discover_routes_with_non_cornice_routes():
    """Test that discover_routes works with regular Pyramid routes when Cornice is available."""
    config = Configurator()
    config.add_route("test_route", "/test")
    
    def dummy_view(request):
        return Response("test")
    
    config.add_view(dummy_view, route_name="test_route")
    config.commit()
    
    introspector = PyramidIntrospector(config)
    routes_info = introspector.discover_routes()
    
    # Should still discover routes
    assert len(routes_info) > 0
    
    # Routes should not have cornice_service since they're regular routes
    for route in routes_info:
        assert "cornice_service" not in route or route["cornice_service"] is None


def test_tool_generation_with_cornice_metadata(pyramid_config_with_cornice):
    """Test that MCP tool generation benefits from real Cornice metadata."""
    introspector = PyramidIntrospector(pyramid_config_with_cornice)
    mcp_config = MCPConfiguration()
    
    tools = introspector.discover_tools_from_pyramid(None, mcp_config)
    
    # Should create tools with enhanced metadata
    assert len(tools) > 0
    
    # Find tools related to users
    user_tools = [t for t in tools if "users" in t.name]
    assert len(user_tools) > 0
    
    # Tools should have descriptions from Cornice service
    for tool in user_tools:
        assert hasattr(tool, "description")
        assert tool.description  # Should not be empty


# =============================================================================
# 🔧 UTILITY FUNCTION TESTS
# =============================================================================


def test_normalize_path_pattern():
    """Test path pattern normalization for matching."""
    introspector = PyramidIntrospector()
    
    # Test various path patterns
    assert introspector._normalize_path_pattern("/users") == "/users"
    assert introspector._normalize_path_pattern("/users/{id}") == "/users/{id}"
    assert introspector._normalize_path_pattern("/users/{id:[0-9]+}") == "/users/{id}"
    assert introspector._normalize_path_pattern("/api/v1/users") == "/api/v1/users"
    
    # Test with regex patterns
    assert introspector._normalize_path_pattern("/users/{id:\\d+}") == "/users/{id}"
    assert introspector._normalize_path_pattern("/files/{filename:.+}") == "/files/{filename}"


def test_extract_service_level_metadata_with_real_service(users_service):
    """Test extraction of service-level metadata from real service."""
    introspector = PyramidIntrospector()
    
    metadata = introspector._extract_service_level_metadata(users_service)
    
    assert metadata["cors_origins"] == ["*"]
    assert metadata["cors_credentials"] is True
    assert metadata["description"] == "User management service"
    assert isinstance(metadata["validators"], list)
    assert isinstance(metadata["filters"], list)


def test_extract_service_level_metadata_with_minimal_service():
    """Test extraction of service-level metadata with minimal service object."""
    introspector = PyramidIntrospector()
    
    # Create a minimal service-like object
    class MinimalService:
        def __init__(self):
            self.cors_origins = ["https://example.com"]
            # Missing other attributes to test defaults
    
    service = MinimalService()
    metadata = introspector._extract_service_level_metadata(service)
    
    assert metadata["cors_origins"] == ["https://example.com"]
    assert metadata["cors_credentials"] is False  # Default
    assert metadata["content_type"] == "application/json"  # Default
    assert metadata["accept"] == "application/json"  # Default
    assert metadata["validators"] == []  # Default
    assert metadata["filters"] == []  # Default
    assert metadata["description"] == ""  # Default


# =============================================================================
# 🧪 REAL INTEGRATION TESTS
# =============================================================================


def test_end_to_end_cornice_integration():
    """Test complete end-to-end Cornice integration."""
    config = Configurator()
    config.include('cornice')
    
    # Create a realistic API service
    api_service = Service(
        name='api_items',
        path='/api/items',
        description='Items API',
        cors_origins=['*'],
        validators=['validate_json']
    )
    
    @api_service.get()
    def list_items(request):
        """List all items"""
        return {'items': []}
    
    @api_service.post(permission='create_item')
    def create_item(request):
        """Create a new item"""
        return {'item': 'created'}
    
    config.add_cornice_service(api_service)
    config.commit()
    
    # Test the full integration
    introspector = PyramidIntrospector(config)
    
    # Discover routes with Cornice metadata
    routes = introspector.discover_routes()
    assert len(routes) >= 1
    
    # Generate MCP tools
    mcp_config = MCPConfiguration()
    tools = introspector.discover_tools_from_pyramid(None, mcp_config)
    assert len(tools) >= 2  # At least 2 tools for the 2 methods
    
    # Check that tools have proper descriptions from Cornice
    tool_descriptions = [tool.description for tool in tools if tool.description]
    assert any("List all items" in desc for desc in tool_descriptions)
    assert any("Create a new item" in desc for desc in tool_descriptions) 