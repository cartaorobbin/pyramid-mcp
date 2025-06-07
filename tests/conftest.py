"""
Pytest configuration and fixtures for pyramid_mcp tests.

This file provides comprehensive fixtures for testing pyramid_mcp functionality.
Fixtures are organized by category:
- Core Pyramid fixtures: Basic pyramid setup and configuration
- MCP Configuration fixtures: MCP-specific configuration and settings  
- MCP Integration fixtures: PyramidMCP instances and protocol handlers
- WebTest Application fixtures: TestApp instances for HTTP testing
- Test Data fixtures: Sample data and utilities for testing
"""

import pytest
from marshmallow import Schema, ValidationError, fields
from pyramid.config import Configurator

# Removed unused imports
from webtest import TestApp

from pyramid_mcp import tool
from pyramid_mcp.core import MCPConfiguration, PyramidMCP
from pyramid_mcp.protocol import MCPProtocolHandler


# Test schemas
class UserCreateSchema(Schema):
    """Schema for creating users."""

    name = fields.Str(required=True, validate=lambda x: len(x) > 0)
    email = fields.Email(required=True)
    age = fields.Int(required=False, validate=lambda x: x >= 0)


class UserUpdateSchema(Schema):
    """Schema for updating users."""

    name = fields.Str(required=False, validate=lambda x: len(x) > 0)
    email = fields.Email(required=False)
    age = fields.Int(required=False, validate=lambda x: x >= 0)


# =============================================================================
# 🏗️ CORE PYRAMID FIXTURES
# =============================================================================

@pytest.fixture  
def minimal_pyramid_config():
    """Basic Pyramid Configurator without routes or MCP."""
    return Configurator()


@pytest.fixture
def pyramid_config_with_routes(users_db, user_id_counter):
    """Pyramid configuration with standard test routes but no MCP."""
    config = Configurator()
    
    # Add test routes
    config.add_route("create_user", "/users", request_method="POST")
    config.add_route("get_user", "/users/{id}", request_method="GET") 
    config.add_route("update_user", "/users/{id}", request_method="PUT")
    config.add_route("delete_user", "/users/{id}", request_method="DELETE")
    config.add_route("list_users", "/users", request_method="GET")
    
    # Add view configurations
    config.add_view(create_user_view, route_name="create_user", renderer="json")
    config.add_view(get_user_view, route_name="get_user", renderer="json")
    config.add_view(update_user_view, route_name="update_user", renderer="json") 
    config.add_view(delete_user_view, route_name="delete_user", renderer="json")
    config.add_view(list_users_view, route_name="list_users", renderer="json")
    
    # Store test data in registry
    config.registry.users_db = users_db
    config.registry.user_id_counter = user_id_counter
    
    return config


@pytest.fixture
def pyramid_config_committed(pyramid_config_with_routes):
    """Pre-committed Pyramid config for introspection testing."""
    pyramid_config_with_routes.commit()
    return pyramid_config_with_routes


@pytest.fixture
def pyramid_app_factory():
    """Factory for creating Pyramid WSGI apps with different configurations."""
    def _create_app(config):
        return config.make_wsgi_app()
    return _create_app


# =============================================================================
# ⚙️ MCP CONFIGURATION FIXTURES  
# =============================================================================

@pytest.fixture
def minimal_mcp_config():
    """Basic MCP configuration with minimal settings."""
    return MCPConfiguration()


@pytest.fixture  
def custom_mcp_config(request):
    """Parameterized MCP configuration fixture.
    
    Use with pytest.mark.parametrize or direct calls.
    """
    # Get parameters from pytest.mark.parametrize or use defaults
    params = getattr(request, 'param', {})
    if not isinstance(params, dict):
        params = {}
        
    server_name = params.get('server_name', 'test-server')
    server_version = params.get('server_version', '1.0.0')
    mount_path = params.get('mount_path', '/mcp')
    
    return MCPConfiguration(
        server_name=server_name,
        server_version=server_version, 
        mount_path=mount_path
    )


@pytest.fixture
def mcp_config_with_patterns():
    """MCP configuration with include/exclude patterns."""
    return MCPConfiguration(
        server_name="pattern-test",
        include_patterns=["api/*", "users/*"],
        exclude_patterns=["admin/*", "internal/*"]
    )


@pytest.fixture
def mcp_settings_factory():
    """Factory for creating MCP settings dictionaries."""
    def _create_settings(**kwargs):
        defaults = {
            'mcp.server_name': 'test-server',
            'mcp.server_version': '1.0.0', 
            'mcp.mount_path': '/mcp',
            'mcp.enable_sse': 'true',
            'mcp.enable_http': 'true'
        }
        defaults.update({f'mcp.{k}': v for k, v in kwargs.items()})
        return defaults
    return _create_settings


# =============================================================================
# 🔧 MCP INTEGRATION FIXTURES
# =============================================================================

@pytest.fixture
def protocol_handler():
    """Standalone MCP protocol handler for unit testing."""
    return MCPProtocolHandler("test-protocol", "1.0.0")


@pytest.fixture
def pyramid_mcp_basic(minimal_pyramid_config, minimal_mcp_config):
    """PyramidMCP instance with minimal configuration."""
    return PyramidMCP(minimal_pyramid_config, config=minimal_mcp_config)


@pytest.fixture
def pyramid_mcp_configured(pyramid_config_with_routes, custom_mcp_config):
    """PyramidMCP instance with full configuration."""
    return PyramidMCP(pyramid_config_with_routes, config=custom_mcp_config)


# =============================================================================
# 🌐 WEBTEST APPLICATION FIXTURES
# =============================================================================

@pytest.fixture  
def testapp_basic(pyramid_config_with_routes):
    """Basic TestApp without MCP integration."""
    app = pyramid_config_with_routes.make_wsgi_app()
    return TestApp(app)


@pytest.fixture
def testapp_with_mcp(pyramid_config_with_routes):
    """TestApp with MCP integration using default settings."""
    pyramid_config_with_routes.include("pyramid_mcp")
    app = pyramid_config_with_routes.make_wsgi_app()
    return TestApp(app)


@pytest.fixture
def testapp_custom_mount(pyramid_config_with_routes, mcp_settings_factory):
    """TestApp with MCP mounted at custom path."""
    settings = mcp_settings_factory(mount_path='/api/mcp')
    pyramid_config_with_routes.registry.settings.update(settings)
    pyramid_config_with_routes.include("pyramid_mcp")
    app = pyramid_config_with_routes.make_wsgi_app()
    return TestApp(app)


@pytest.fixture
def testapp_factory(pyramid_app_factory):
    """Factory for creating TestApp instances."""
    def _create_testapp(config):
        app = pyramid_app_factory(config)
        return TestApp(app)
    return _create_testapp


# =============================================================================
# 📊 TEST DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_tools():
    """Collection of sample MCP tools for testing."""
    tools = []
    
    @tool(name="add", description="Add two numbers")
    def add_tool(a: int, b: int) -> int:
        return a + b
    
    @tool(name="multiply", description="Multiply two numbers") 
    def multiply_tool(x: int, y: int) -> int:
        return x * y
        
    tools.extend([add_tool, multiply_tool])
    return tools


@pytest.fixture
def test_route_scenarios():
    """Various route configuration scenarios for testing."""
    return {
        'basic_crud': [
            ("create_item", "/items", "POST"),
            ("get_item", "/items/{id}", "GET"),
            ("update_item", "/items/{id}", "PUT"), 
            ("delete_item", "/items/{id}", "DELETE"),
            ("list_items", "/items", "GET")
        ],
        'api_routes': [
            ("api_users", "/api/users", "GET"),
            ("api_user_detail", "/api/users/{id}", "GET"),
            ("api_posts", "/api/posts", "GET")
        ],
        'admin_routes': [
            ("admin_dashboard", "/admin", "GET"),
            ("admin_users", "/admin/users", "GET") 
        ]
    }


# =============================================================================
# 📁 LEGACY FIXTURES (for backward compatibility during migration)
# =============================================================================

# Sample data and utilities
@pytest.fixture
def users_db():
    """Mock users database."""
    return {}


@pytest.fixture
def user_id_counter():
    """Mock user ID counter."""
    return {"value": 0}


# Pyramid configuration fixtures
@pytest.fixture
def pyramid_config(users_db, user_id_counter):
    """Pyramid configuration fixture."""
    config = Configurator()

    # Add routes
    config.add_route("create_user", "/users", request_method="POST")
    config.add_route("get_user", "/users/{id}", request_method="GET")
    config.add_route("update_user", "/users/{id}", request_method="PUT")
    config.add_route("delete_user", "/users/{id}", request_method="DELETE")
    config.add_route("list_users", "/users", request_method="GET")

    # Add view configurations
    config.add_view(create_user_view, route_name="create_user", renderer="json")
    config.add_view(get_user_view, route_name="get_user", renderer="json")
    config.add_view(update_user_view, route_name="update_user", renderer="json")
    config.add_view(delete_user_view, route_name="delete_user", renderer="json")
    config.add_view(list_users_view, route_name="list_users", renderer="json")

    # Store test data in registry for views to access
    config.registry.users_db = users_db
    config.registry.user_id_counter = user_id_counter

    config.include("pyramid_mcp")

    return config


@pytest.fixture
def pyramid_app(pyramid_config):
    """Pyramid WSGI application fixture."""
    return pyramid_config.make_wsgi_app()


@pytest.fixture
def testapp(pyramid_app):
    """WebTest TestApp fixture for HTTP testing."""
    return TestApp(pyramid_app)


@pytest.fixture
def mcp_config():
    """Fixture providing MCP configuration."""
    return MCPConfiguration(
        server_name="test-user-api", server_version="1.0.0", mount_path="/mcp"
    )


@pytest.fixture
def pyramid_mcp(pyramid_config, mcp_config):
    """PyramidMCP fixture."""
    return PyramidMCP(pyramid_config, config=mcp_config)


@pytest.fixture
def mcp_app(pyramid_app):
    """Pyramid application with MCP mounted."""
    # Include pyramid_mcp plugin
    return pyramid_app


@pytest.fixture
def mcp_testapp(mcp_app):
    """WebTest TestApp fixture with MCP endpoints mounted."""
    return TestApp(mcp_app)


# View functions for testing
def create_user_view(request):
    """Create a new user."""
    try:
        # Get data from request
        data = request.json_body

        # Validate with schema
        schema = UserCreateSchema()
        validated_data = schema.load(data)

        # Access shared data from registry
        users_db = request.registry.users_db
        user_id_counter = request.registry.user_id_counter

        # Create user
        user_id_counter["value"] += 1
        user_id = user_id_counter["value"]

        user = {
            "id": user_id,
            "name": validated_data["name"],
            "email": validated_data["email"],
            "age": validated_data.get("age"),
        }

        users_db[user_id] = user

        return {"user": user}

    except ValidationError as e:
        request.response.status = 400
        return {"error": "Validation failed", "details": e.messages}
    except Exception as e:
        request.response.status = 500
        return {"error": str(e)}


def get_user_view(request):
    """Get a user by ID."""
    try:
        user_id = int(request.matchdict["id"])
        users_db = request.registry.users_db

        user = users_db.get(user_id)
        if not user:
            request.response.status = 404
            return {"error": "User not found"}

        return {"user": user}
    except ValueError:
        request.response.status = 400
        return {"error": "Invalid user ID"}


def update_user_view(request):
    """Update a user."""
    try:
        user_id = int(request.matchdict["id"])
        users_db = request.registry.users_db

        user = users_db.get(user_id)
        if not user:
            request.response.status = 404
            return {"error": "User not found"}

        # Validate data
        schema = UserUpdateSchema()
        validated_data = schema.load(request.json_body)

        # Update user
        user.update(validated_data)

        return {"user": user}

    except ValidationError as e:
        request.response.status = 400
        return {"error": "Validation failed", "details": e.messages}
    except ValueError:
        request.response.status = 400
        return {"error": "Invalid user ID"}


def delete_user_view(request):
    """Delete a user."""
    try:
        user_id = int(request.matchdict["id"])
        users_db = request.registry.users_db

        user = users_db.get(user_id)
        if not user:
            request.response.status = 404
            return {"error": "User not found"}

        del users_db[user_id]
        return {"message": "User deleted"}

    except ValueError:
        request.response.status = 400
        return {"error": "Invalid user ID"}


def list_users_view(request):
    """List all users."""
    users_db = request.registry.users_db
    return {"users": list(users_db.values())}


# Sample MCP tools for testing
@tool(name="get_user_count", description="Get the total number of users")
def get_user_count_tool(request=None):
    """Get the total number of users in the system."""
    # In a real implementation, this would access the database
    # For testing, we'll return a static count
    return {"count": 42}


@tool(name="calculate", description="Perform basic math operations")
def calculate_tool(operation: str, a: float, b: float) -> float:
    """Perform basic math operations."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")
