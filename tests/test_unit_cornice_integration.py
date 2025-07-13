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
from cornice import Service  # type: ignore
from pyramid.config import Configurator
from pyramid.response import Response

from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.introspection import PyramidIntrospector

# =============================================================================
# 📋 REAL CORNICE FIXTURES
# =============================================================================


@pytest.fixture
def users_service():
    """Real Cornice service for testing."""
    users = Service(
        name="users",
        path="/users",
        description="User management service",
        cors_origins=["*"],
        cors_credentials=True,
    )

    @users.get()
    def get_users(request):
        """Get all users"""
        return {"users": []}

    @users.post(validators=["validate_json"], permission="create")
    def create_user(request):
        """Create a new user"""
        return {"user": "created"}

    return users


@pytest.fixture
def pyramid_config_with_cornice(users_service):
    """Pyramid configuration with real Cornice services."""
    config = Configurator()
    config.include("cornice")

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
    services = introspector._discover_cornice_services(
        pyramid_config_with_cornice.registry
    )

    assert len(services) >= 1
    service_names = [s.get("name", "") for s in services]
    assert "users" in service_names


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
    """Test discover_routes works with regular Pyramid routes with Cornice."""
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
        has_cornice = "cornice_service" in route and route["cornice_service"]
        assert not has_cornice


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
    assert (
        introspector._normalize_path_pattern("/files/{filename:.+}")
        == "/files/{filename}"
    )


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
    config.include("cornice")

    # Create a realistic API service
    api_service = Service(
        name="api_items",
        path="/api/items",
        description="Items API",
        cors_origins=["*"],
        validators=["validate_json"],
    )

    @api_service.get()
    def list_items(request):
        """List all items"""
        return {"items": []}

    @api_service.post(permission="create_item")
    def create_item(request):
        """Create a new item"""
        return {"item": "created"}

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


def test_extract_service_level_metadata():
    """Test extracting service-level metadata from Cornice services."""
    # Create a service with metadata
    service = Service(name="test_service", path="/test", description="Test service")

    # Create introspector and extract metadata
    config = Configurator()
    introspector = PyramidIntrospector(config)

    metadata = introspector._extract_service_level_metadata(service)

    # Verify metadata extraction
    assert metadata["name"] == "test_service"
    assert metadata["path"] == "/test"
    assert metadata["description"] == "Test service"


# =============================================================================
# 🧪 MARSHMALLOW SCHEMA INTEGRATION TESTS
# =============================================================================


def test_extract_marshmallow_schema_info():
    """Test extracting field information from Marshmallow schemas."""
    import marshmallow
    from marshmallow import fields

    # Create a test schema
    class UserSchema(marshmallow.Schema):
        name = fields.String(
            required=True, metadata={"description": "User's full name"}
        )
        email = fields.Email(
            required=True, metadata={"description": "User's email address"}
        )
        age = fields.Integer(validate=marshmallow.validate.Range(min=0, max=150))
        is_active = fields.Boolean(default=True)

    # Create introspector and extract schema info
    config = Configurator()
    introspector = PyramidIntrospector(config)

    schema_info = introspector._extract_marshmallow_schema_info(UserSchema())

    # Verify schema structure
    assert schema_info["type"] == "object"
    assert "properties" in schema_info
    assert "required" in schema_info
    assert schema_info["additionalProperties"] is False

    # Verify required fields
    assert "name" in schema_info["required"]
    assert "email" in schema_info["required"]
    assert "age" not in schema_info["required"]

    # Verify field types
    properties = schema_info["properties"]
    assert properties["name"]["type"] == "string"
    assert properties["email"]["type"] == "string"
    assert properties["email"]["format"] == "email"
    assert properties["age"]["type"] == "integer"
    assert properties["is_active"]["type"] == "boolean"

    # Verify field descriptions
    assert properties["name"]["description"] == "User's full name"
    assert properties["email"]["description"] == "User's email address"

    # Verify validation constraints
    assert properties["age"]["minimum"] == 0
    assert properties["age"]["maximum"] == 150

    # Verify default values
    assert properties["is_active"]["default"] is True


def test_marshmallow_field_to_mcp_type():
    """Test converting Marshmallow field types to MCP parameter types."""
    from marshmallow import fields

    config = Configurator()
    introspector = PyramidIntrospector(config)

    # Test various field types
    test_fields = {
        "string": fields.String(description="A string field"),
        "integer": fields.Integer(),
        "float": fields.Float(),
        "boolean": fields.Boolean(),
        "datetime": fields.DateTime(),
        "date": fields.Date(),
        "time": fields.Time(),
        "email": fields.Email(),
        "url": fields.Url(),
        "uuid": fields.UUID(),
        "list": fields.List(fields.String()),
        "dict": fields.Dict(),
    }

    for field_name, field_obj in test_fields.items():
        field_info = introspector._marshmallow_field_to_mcp_type(field_obj)

        # Verify basic type mapping
        if field_name == "string":
            assert field_info["type"] == "string"
            assert field_info["description"] == "A string field"
        elif field_name == "integer":
            assert field_info["type"] == "integer"
        elif field_name == "float":
            assert field_info["type"] == "number"
        elif field_name == "boolean":
            assert field_info["type"] == "boolean"
        elif field_name == "datetime":
            assert field_info["type"] == "string"
            assert field_info["format"] == "date-time"
        elif field_name == "date":
            assert field_info["type"] == "string"
            assert field_info["format"] == "date"
        elif field_name == "time":
            assert field_info["type"] == "string"
            assert field_info["format"] == "time"
        elif field_name == "email":
            assert field_info["type"] == "string"
            assert field_info["format"] == "email"
        elif field_name == "url":
            assert field_info["type"] == "string"
            assert field_info["format"] == "uri"
        elif field_name == "uuid":
            assert field_info["type"] == "string"
            assert field_info["format"] == "uuid"
        elif field_name == "list":
            assert field_info["type"] == "array"
            assert field_info["items"]["type"] == "string"
        elif field_name == "dict":
            assert field_info["type"] == "object"
            assert field_info["additionalProperties"] is True


def test_add_validation_constraints():
    """Test adding validation constraints from Marshmallow fields."""
    from marshmallow import fields, validate

    config = Configurator()
    introspector = PyramidIntrospector(config)

    # Test Length validator
    field_with_length = fields.String(validate=validate.Length(min=5, max=20))
    field_info = introspector._marshmallow_field_to_mcp_type(field_with_length)
    assert field_info["minLength"] == 5
    assert field_info["maxLength"] == 20

    # Test Range validator
    field_with_range = fields.Integer(validate=validate.Range(min=10, max=100))
    field_info = introspector._marshmallow_field_to_mcp_type(field_with_range)
    assert field_info["minimum"] == 10
    assert field_info["maximum"] == 100

    # Test OneOf validator (enum)
    field_with_choices = fields.String(
        validate=validate.OneOf(["draft", "published", "archived"])
    )
    field_info = introspector._marshmallow_field_to_mcp_type(field_with_choices)
    assert field_info["enum"] == ["draft", "published", "archived"]

    # Test multiple validators
    field_with_multiple = fields.String(
        validate=[validate.Length(min=3), validate.OneOf(["red", "green", "blue"])]
    )
    field_info = introspector._marshmallow_field_to_mcp_type(field_with_multiple)
    assert field_info["minLength"] == 3
    assert field_info["enum"] == ["red", "green", "blue"]


def test_nested_marshmallow_schema():
    """Test handling nested Marshmallow schemas."""
    from marshmallow import Schema, fields

    # Create nested schemas
    class AddressSchema(Schema):
        street = fields.String(required=True)
        city = fields.String(required=True)
        country = fields.String(default="USA")

    class UserSchema(Schema):
        name = fields.String(required=True)
        address = fields.Nested(AddressSchema)

    config = Configurator()
    introspector = PyramidIntrospector(config)

    schema_info = introspector._extract_marshmallow_schema_info(UserSchema())

    # Verify nested schema structure
    assert "address" in schema_info["properties"]
    address_field = schema_info["properties"]["address"]
    assert address_field["type"] == "object"
    assert "properties" in address_field

    # Verify nested field properties
    nested_props = address_field["properties"]
    assert nested_props["street"]["type"] == "string"
    assert nested_props["city"]["type"] == "string"
    assert nested_props["country"]["type"] == "string"

    # Verify nested field requirements
    assert "street" in address_field["required"]
    assert "city" in address_field["required"]
    assert "country" not in address_field["required"]

    # Verify nested default values
    assert nested_props["country"]["default"] == "USA"


def test_cornice_service_with_marshmallow_schema():
    """Test Cornice service integration with Marshmallow schemas."""
    from marshmallow import Schema, fields, validate

    # Create a test schema
    class CreateUserSchema(Schema):
        name = fields.String(required=True, metadata={"description": "User's name"})
        email = fields.Email(required=True, metadata={"description": "User's email"})
        age = fields.Integer(validate=validate.Range(min=18, max=120))

        # Create Cornice service with schema

    user_service = Service(
        name="create_users", path="/create_users", description="User management"
    )

    @user_service.post(schema=CreateUserSchema())
    def create_user(request):
        return {"message": "User created"}

    # Set up Pyramid configuration
    config = Configurator()
    config.include("cornice")
    config.add_cornice_service(user_service)
    config.commit()

    # Create introspector and discover routes
    introspector = PyramidIntrospector(config)
    routes = introspector.discover_routes()

    # Find the user route
    user_route = None
    for route in routes:
        if route["name"] == "create_users":
            user_route = route
            break

    assert user_route is not None

    # Verify schema information in view metadata
    views = user_route["views"]
    post_view = None
    for view in views:
        if "POST" in view["request_methods"]:
            post_view = view
            break

    assert post_view is not None
    assert "cornice_metadata" in post_view

    # Verify schema is captured in Cornice metadata
    cornice_metadata = post_view["cornice_metadata"]
    method_specific = cornice_metadata.get("method_specific", {})
    assert "POST" in method_specific
    assert "schema" in method_specific["POST"]

    # Test schema parsing through MCP tool generation
    from pyramid_mcp.core import MCPConfiguration

    config_obj = MCPConfiguration()
    tools = introspector.discover_tools(config_obj)

    # Find the create user tool
    create_tool = None
    for tool in tools:
        if "create" in tool.name and "user" in tool.name:
            create_tool = tool
            break

    assert create_tool is not None
    assert create_tool.input_schema is not None

    # Verify schema information in tool input schema
    schema = create_tool.input_schema
    assert schema is not None

    # New HTTPRequestSchema structure
    assert "path" in schema
    assert "query" in schema
    assert "body" in schema
    assert "headers" in schema

    # Check body parameters (POST method should have body field)
    assert len(schema["body"]) == 1
    body_param = schema["body"][0]
    assert body_param["name"] == "data"
    assert body_param["type"] == "string"
    assert body_param["required"] is True

    # TODO: Cornice Marshmallow schema integration is not yet implemented
    # The current implementation should be enhanced to extract schema fields from
    # Cornice service Marshmallow schemas and incorporate them into the body structure
    # Expected fields from CreateUserSchema: name, email, age


def test_marshmallow_schema_without_cornice():
    """Test that Marshmallow functionality is gracefully handled when not available."""
    # This test verifies that our code doesn't break when marshmallow is not available
    config = Configurator()
    introspector = PyramidIntrospector(config)

    # Mock schema object that's not actually a marshmallow schema
    fake_schema = {"not": "a marshmallow schema"}

    # Should return empty schema info for non-marshmallow objects
    schema_info = introspector._extract_marshmallow_schema_info(fake_schema)
    assert schema_info == {}


# =============================================================================
# 🔗 INTEGRATION TESTS WITH EXISTING FUNCTIONALITY
# =============================================================================


def test_discover_routes_with_marshmallow_integration(pyramid_config_with_cornice):
    """Test that discover_routes includes Marshmallow schema information."""
    import marshmallow
    from marshmallow import fields

    # Create schema
    class TestSchema(marshmallow.Schema):
        title = fields.String(required=True)
        content = fields.String()

    # Create service with schema
    blog_service = Service(name="blog", path="/blog", description="Blog service")

    @blog_service.post(schema=TestSchema())
    def create_post(request):
        return {"message": "Post created"}

    # Add service to configuration
    pyramid_config_with_cornice.add_cornice_service(blog_service)
    pyramid_config_with_cornice.commit()

    # Test route discovery
    introspector = PyramidIntrospector(pyramid_config_with_cornice)
    routes = introspector.discover_routes()

    # Find blog route
    blog_route = None
    for route in routes:
        if route["name"] == "blog":
            blog_route = route
            break

    assert blog_route is not None

    # Verify schema information is included
    post_view = None
    for view in blog_route["views"]:
        if "POST" in view["request_methods"]:
            post_view = view
            break

    assert post_view is not None
    assert "cornice_metadata" in post_view
    assert "method_specific" in post_view["cornice_metadata"]
    assert "POST" in post_view["cornice_metadata"]["method_specific"]
    assert "schema" in post_view["cornice_metadata"]["method_specific"]["POST"]
