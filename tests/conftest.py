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

import datetime

import jwt
import pytest
from marshmallow import Schema, ValidationError, fields
from pyramid.config import Configurator

# Removed unused imports
from webtest import TestApp  # type: ignore

from pyramid_mcp import tool
from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.protocol import MCPProtocolHandler

# =============================================================================
# 🔧 PYTEST CONFIGURATION HOOKS
# =============================================================================


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-openai-tests",
        action="store_true",
        default=False,
        help="Run OpenAI integration tests (requires OPENAI_API_KEY and costs money)",
    )


def pytest_configure(config):
    """Configure pytest markers and collection."""
    config.addinivalue_line("markers", "openai: marks tests that require OpenAI API")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle OpenAI tests."""
    if config.getoption("--run-openai-tests"):
        # When --run-openai-tests is specified, run all tests including OpenAI
        return

    # By default, skip OpenAI tests
    skip_openai = pytest.mark.skip(reason="need --run-openai-tests option to run")
    for item in items:
        if "openai" in item.keywords:
            item.add_marker(skip_openai)


# Permission constants
PERMISSIONS = {"VIEW": "view", "EDIT": "edit", "ADMIN": "admin", "DELETE": "delete"}

# User roles and permissions
USER_ROLES = {
    "anonymous": [],
    "viewer": ["view"],
    "editor": ["view", "edit"],
    "admin": ["view", "edit", "admin", "delete"],
}

# JWT configuration
JWT_SECRET = "test-secret-key-for-jwt-tokens"
JWT_ALGORITHM = "HS256"


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
    params = getattr(request, "param", {})
    if not isinstance(params, dict):
        params = {}

    server_name = params.get("server_name", "test-server")
    server_version = params.get("server_version", "1.0.0")
    mount_path = params.get("mount_path", "/mcp")

    return MCPConfiguration(
        server_name=server_name, server_version=server_version, mount_path=mount_path
    )


@pytest.fixture
def mcp_config_with_patterns():
    """MCP configuration with include/exclude patterns."""
    return MCPConfiguration(
        server_name="pattern-test",
        include_patterns=["api/*", "users/*"],
        exclude_patterns=["admin/*", "internal/*"],
    )


@pytest.fixture
def mcp_settings_factory():
    """Factory for creating MCP settings dictionaries."""

    def _create_settings(**kwargs):
        defaults = {
            "mcp.server_name": "test-server",
            "mcp.server_version": "1.0.0",
            "mcp.mount_path": "/mcp",
            "mcp.enable_sse": "true",
            "mcp.enable_http": "true",
        }
        defaults.update({f"mcp.{k}": v for k, v in kwargs.items()})
        return defaults

    return _create_settings


# =============================================================================
# 🔧 MCP INTEGRATION FIXTURES
# =============================================================================


@pytest.fixture
def dummy_request():
    """Create a dummy pyramid request for protocol handler calls."""
    from pyramid.config import Configurator
    from pyramid.scripting import prepare

    # Create minimal configuration
    config = Configurator()
    config.commit()

    # Use pyramid.scripting.prepare to get a proper request
    env = prepare(registry=config.registry)
    return env["request"]


@pytest.fixture
def test_pyramid_request():
    """Create a test pyramid request with subrequest capability for testing."""
    from pyramid.response import Response
    from pyramid.testing import DummyRequest

    class TestPyramidRequest(DummyRequest):
        def invoke_subrequest(self, subrequest):
            """Simulate subrequest behavior for testing.

            This test implementation simulates the subrequest execution by:
            1. Extracting parameters from the subrequest URL
            2. Returning a test response based on the URL pattern
            """
            # Extract basic info from subrequest
            url = subrequest.url if hasattr(subrequest, "url") else subrequest.path_url
            method = subrequest.method

            # Simple test responses based on URL patterns
            if "/users/" in url and method == "GET":
                # Extract user ID from URL pattern
                import re

                match = re.search(r"/users/(\w+)", url)
                user_id = match.group(1) if match else "unknown"
                return Response(f"User {user_id}")
            elif "/users" in url and method == "GET":
                return Response("Users list")
            elif "/users" in url and method == "POST":
                return Response("User created")
            elif "/test" in url:
                return Response("test response")
            elif "/json" in url:
                # Return a response that will be converted to JSON format
                return Response('{"message": "json response"}')
            else:
                # Default response
                return Response("test response")

    return TestPyramidRequest()


@pytest.fixture
def protocol_handler():
    """Standalone MCP protocol handler for unit testing."""
    return MCPProtocolHandler("test-protocol", "1.0.0")


# =============================================================================
# 🔒 JWT AUTHENTICATION FIXTURES
# =============================================================================


@pytest.fixture
def valid_jwt_token():
    """Generate a valid JWT token for testing."""
    payload = {
        "user_id": "test_user",
        "username": "testuser",
        "roles": ["authenticated"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def expired_jwt_token():
    """Generate an expired JWT token for testing."""
    payload = {
        "user_id": "test_user",
        "username": "testuser",
        "roles": ["authenticated"],
        "exp": datetime.datetime.utcnow()
        - datetime.timedelta(hours=1),  # Expired 1h ago
        "iat": datetime.datetime.utcnow() - datetime.timedelta(hours=2),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# =============================================================================
# 🎯 UNIFIED PYRAMID FIXTURE: MAIN PYRAMID SETUP
# =============================================================================


class TestSecurityPolicy:
    """Unified test security policy for all pyramid-mcp tests.

    Handles HTTP Authorization headers for authentication.
    This is the SINGLE security policy used across all tests.
    """

    def identity(self, request):
        """Extract identity from auth headers."""
        # Check HTTP Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            if token and self._is_valid_token(token):
                return self._create_identity(token)

        return None

    def _is_valid_token(self, token):
        """Simple token validation for testing."""
        # Reject obvious invalid tokens
        if token in ["invalid.jwt.token", "expired-test-jwt-token-456"]:
            return False
        # Accept other tokens (including valid_bearer_token_123)
        return True

    def _create_identity(self, token):
        """Create consistent identity object for testing."""
        # Determine roles based on token type
        roles = ["authenticated"]  # Default role for any valid token

        # Admin tokens get admin role
        if "admin" in token.lower():
            roles.append("admin")

        return {
            "user_id": "test_user",
            "username": "testuser",
            "token": token,
            "roles": roles,
        }

    def authenticated_userid(self, request):
        """Get the authenticated user ID."""
        identity = self.identity(request)
        return identity.get("user_id") if identity else None

    def permits(self, request, context, permission):
        """Check if current user has the given permission."""
        from pyramid.authorization import ACLHelper, Authenticated, Everyone

        # Get effective principals for current user
        principals = self.effective_principals(request)

        # For backward compatibility with "authenticated" permission
        if permission == "authenticated":
            return Authenticated in principals

        # Use context ACL if available
        if hasattr(context, "__acl__"):
            acl_helper = ACLHelper()
            # Convert principal names to match Pyramid's format
            pyramid_principals = []
            for principal in principals:
                if principal == "system.Everyone":
                    pyramid_principals.append(Everyone)
                elif principal == "system.Authenticated":
                    pyramid_principals.append(Authenticated)
                else:
                    pyramid_principals.append(principal)

            # Check ACL permissions
            return acl_helper.permits(context, pyramid_principals, permission)

        # If no ACL and not "authenticated" permission, deny by default
        return False

    def effective_principals(self, request):
        """Get all effective principals for the current request."""
        identity = self.identity(request)
        if not identity:
            return ["system.Everyone"]

        principals = ["system.Everyone", "system.Authenticated"]
        if "user_id" in identity:
            principals.append(f"userid:{identity['user_id']}")

        # Add roles from identity
        for role in identity.get("roles", []):
            principals.append(f"role:{role}")

        return principals


@pytest.fixture
def pyramid_config():
    """
    Create a Pyramid configurator with comprehensive setup.

    This fixture builds and configures a Pyramid configurator but doesn't create
    the WSGI app. Use this when you need direct access to the configurator for
    testing.

    Args:
        settings (dict, optional): Pyramid settings to merge with defaults
        views (list, optional): List of (view_callable, route_name, view_kwargs)
            tuples to add
        scan_path (str, optional): Package path to scan for @tool decorators
            (default: "tests")
        ignore (list, optional): List of module patterns to ignore when scanning
        commit (bool, optional): Whether to commit configuration (default: False)

    Returns:
        Configurator: Configured Pyramid configurator
    """

    def _create_config(
        settings=None, views=None, scan_path=None, ignore=None, commit=False
    ):
        # Merge settings with defaults (don't replace)
        default_settings = {
            "mcp.route_discovery.enabled": True,
            "mcp.server_name": "test-server",
            "mcp.server_version": "1.0.0",
            "mcp.mount_path": "/mcp",
            "jwt.secret": "test-secret-key",
            "jwt.algorithm": "HS256",
            "jwt.expiration_delta": 3600,
        }
        if settings:
            default_settings.update(settings)
        final_settings = default_settings

        # Create Pyramid configurator
        config = Configurator(settings=final_settings)

        # Set security policy using the shared TestSecurityPolicy class
        config.set_security_policy(TestSecurityPolicy())

        # Include pyramid_mcp
        config.include("pyramid_mcp")

        # Add views if provided
        if views:
            for view_config in views:
                view_callable, route_name, view_kwargs = view_config
                # Add route first (required for Pyramid)
                config.add_route(route_name, f"/{route_name}")
                # Then add view
                config.add_view(view_callable, route_name=route_name, **view_kwargs)

        # Scan for @tool decorators with configurable path and ignore patterns
        scan_target = scan_path if scan_path else "tests"

        # Set default ignore patterns for "tests" scan to avoid import conflicts
        if ignore is None and scan_target == "tests":
            ignore = ["tests.cornice_integration"]

        # Scan with ignore patterns if provided
        if ignore:
            config.scan(scan_target, categories=["pyramid_mcp"], ignore=ignore)
        else:
            config.scan(scan_target, categories=["pyramid_mcp"])

        # Commit configuration if requested (needed for introspection)
        if commit:
            config.commit()

        return config

    return _create_config


@pytest.fixture
def pyramid_wsgi_app(pyramid_config):
    """
    Create a WSGI app from a Pyramid configurator.

    This fixture takes a configurator and creates the WSGI application.
    Use this when you need the WSGI app but not the TestApp wrapper.

    Args:
        Same as pyramid_config fixture

    Returns:
        WSGI application
    """

    def _create_wsgi_app(
        settings=None, views=None, scan_path=None, ignore=None, commit=None
    ):
        # WSGI app creation requires committed configuration
        if commit is None:
            commit = True
        config = pyramid_config(
            settings=settings,
            views=views,
            scan_path=scan_path,
            ignore=ignore,
            commit=commit,
        )
        return config.make_wsgi_app()

    return _create_wsgi_app


@pytest.fixture
def pyramid_app(pyramid_wsgi_app):
    """
    Create a TestApp from a WSGI application.

    This fixture creates a WebTest TestApp for HTTP testing.
    Use this for most tests that need to make HTTP requests.

    Args:
        Same as pyramid_config fixture

    Returns:
        TestApp: WebTest TestApp instance
    """

    def _create_testapp(
        settings=None, views=None, scan_path=None, ignore=None, commit=None
    ):
        wsgi_app = pyramid_wsgi_app(
            settings=settings,
            views=views,
            scan_path=scan_path,
            ignore=ignore,
            commit=commit,
        )
        return TestApp(wsgi_app)

    return _create_testapp


# =============================================================================
# 📊 TEST DATA FIXTURES
# =============================================================================


@pytest.fixture
def users_db():
    """Mock users database for view functions."""
    return {}


@pytest.fixture
def user_id_counter():
    """Mock user ID counter for view functions."""
    return {"value": 0}


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
        "basic_crud": [
            ("create_item", "/items", "POST"),
            ("get_item", "/items/{id}", "GET"),
            ("update_item", "/items/{id}", "PUT"),
            ("delete_item", "/items/{id}", "DELETE"),
            ("list_items", "/items", "GET"),
        ],
        "api_routes": [
            ("api_users", "/api/users", "GET"),
            ("api_user_detail", "/api/users/{id}", "GET"),
            ("api_posts", "/api/posts", "GET"),
        ],
        "admin_routes": [
            ("admin_dashboard", "/admin", "GET"),
            ("admin_users", "/admin/users", "GET"),
        ],
    }


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


# JWT-enabled views for authentication testing
def get_protected_user_view(request):
    """Protected view that requires authentication."""
    user_id = int(request.matchdict["id"])
    users_db = request.registry.users_db

    # This view requires authentication - it should only be callable with valid JWT
    user = users_db.get(user_id)
    if not user:
        request.response.status = 404
        return {"error": "User not found"}

    return {"user": user, "protected": True, "authenticated": True}


def get_public_info_view(request):
    """Public view accessible without authentication."""
    return {
        "message": "This is public information",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "public": True,
    }
