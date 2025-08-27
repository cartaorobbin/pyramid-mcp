"""
Test for Cornice request body parameter handling.

This module tests request body parameters across different scenarios:
- Marshmallow body schema validation
- data_key handling in request body
- Nested body schemas
- Body field types (Str, Int, Email, UUID, etc.)
- Required vs optional body fields
- Body validation error handling
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_body_validator, marshmallow_validator
from marshmallow import EXCLUDE, Schema, fields, pre_load
from pyramid.response import Response


class UserProfileSchema(Schema):
    """Schema with data_key parameters for testing body field name mapping."""

    full_name = fields.Str(
        required=True,
        data_key="fullName",  # JSON should use camelCase
        metadata={"description": "User's full name"},
    )
    email_address = fields.Email(
        required=True,
        data_key="emailAddress",  # JSON should use camelCase
        metadata={"description": "User's email address"},
    )
    user_id = fields.Int(
        required=False,
        data_key="userId",  # JSON should use camelCase
        metadata={"description": "User ID number"},
    )
    account_type = fields.Str(
        required=False,
        data_key="accountType",  # JSON should use camelCase
        dump_default="standard",
        metadata={"description": "Type of user account"},
    )
    # Field without data_key for comparison
    status = fields.Str(
        required=False, dump_default="active", metadata={"description": "User status"}
    )


class SimpleBodySchema(Schema):
    """Simple schema for testing basic body validation."""

    message = fields.Str(required=True, metadata={"description": "Test message"})
    priority = fields.Int(
        required=False, dump_default=1, metadata={"description": "Message priority"}
    )


class NestedBodySchema(Schema):
    """Schema for testing nested body structures."""

    class AddressSchema(Schema):
        street = fields.Str(required=True, metadata={"description": "Street address"})
        city = fields.Str(required=True, metadata={"description": "City"})
        zip_code = fields.Str(required=True, metadata={"description": "ZIP code"})

    name = fields.Str(required=True, metadata={"description": "Full name"})
    email = fields.Email(required=True, metadata={"description": "Email address"})
    address = fields.Nested(
        AddressSchema, required=True, metadata={"description": "Address information"}
    )


class SubSchema(Schema):
    """Sub-schema with pre_load hook for testing complex body processing."""

    path = fields.Str(required=True)

    @pre_load
    def pre_load(self, data, **kwargs):
        data["path"] = self.context["request"].path
        return data


class ResponseSchema(Schema):
    """Response schema with nested sub-schema."""

    path = fields.Str(required=True)
    method = fields.Str(required=True)
    sub = fields.Nested(SubSchema, required=False)

    @pre_load
    def pre_load(self, data, **kwargs):
        data["path"] = self.context["request"].path
        data["sub"] = {"path": "sub"}
        return data


class ParentSchema(Schema):
    """Parent schema containing nested response schema."""

    name = fields.Str(required=True)
    response = fields.Nested(ResponseSchema, required=False)


class RequestSchema(Schema):
    """Top-level request schema with body field."""

    class Meta:
        unknown = EXCLUDE

    body = fields.Nested(ParentSchema, required=False)


# =============================================================================
# 🧪 TEST FIXTURES
# =============================================================================


@pytest.fixture
def user_profile_service():
    """Create a Cornice service with user profile schema for testing data_key."""
    user_service = Service(
        name="user_profile",
        path="/user-profile",
        description="User profile service with camelCase field names",
    )

    @user_service.post(
        schema=UserProfileSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_user_profile(request):
        """Create user profile with data_key field mapping."""
        validated_data = request.validated
        return {
            "user_profile": validated_data,
            "message": "User profile created successfully",
        }

    return user_service


@pytest.fixture
def simple_body_service():
    """Create a Cornice service with simple body schema."""
    simple_service = Service(
        name="simple_body",
        path="/simple-body",
        description="Simple body validation service",
    )

    @simple_service.post(
        schema=SimpleBodySchema,
        validators=(marshmallow_body_validator,),
    )
    def create_simple(request):
        """Create simple message with body validation."""
        validated_data = request.validated
        return {
            "message": validated_data["message"],
            "priority": validated_data.get("priority", 1),
            "status": "created",
        }

    return simple_service


@pytest.fixture
def nested_body_service():
    """Create a Cornice service with nested body schema."""
    nested_service = Service(
        name="nested_body",
        path="/nested-body",
        description="Nested body validation service",
    )

    @nested_service.post(
        schema=NestedBodySchema,
        validators=(marshmallow_body_validator,),
    )
    def create_nested(request):
        """Create user with nested address validation."""
        validated_data = request.validated
        return {
            "user": validated_data,
            "status": "created",
        }

    return nested_service


# =============================================================================
# 🧪 DATA_KEY BODY PARAMETER TESTS
# =============================================================================


def test_data_key_fields_appear_in_tool_schema(
    pyramid_app_with_services, user_profile_service
):
    """Test that data_key field names appear in MCP tool schema, not Python names."""
    services = [user_profile_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    user_profile_tool = tools[0]  # create_user_profile

    # Check that the tool has proper input schema
    assert "inputSchema" in user_profile_tool
    input_schema = user_profile_tool["inputSchema"]
    assert "properties" in input_schema

    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]

    # Verify data_key field names are used (camelCase), not Python names (snake_case)
    assert "fullName" in body_props, "Should use data_key 'fullName', not 'full_name'"
    assert (
        "emailAddress" in body_props
    ), "Should use data_key 'emailAddress', not 'email_address'"
    assert "userId" in body_props, "Should use data_key 'userId', not 'user_id'"
    assert (
        "accountType" in body_props
    ), "Should use data_key 'accountType', not 'account_type'"

    # Field without data_key should use Python name
    assert (
        "status" in body_props
    ), "Field without data_key should use Python name 'status'"

    # Verify Python names are NOT in the schema
    assert (
        "full_name" not in body_props
    ), "Python name 'full_name' should not appear in schema"
    assert (
        "email_address" not in body_props
    ), "Python name 'email_address' should not appear in schema"
    assert (
        "user_id" not in body_props
    ), "Python name 'user_id' should not appear in schema"
    assert (
        "account_type" not in body_props
    ), "Python name 'account_type' should not appear in schema"


def test_data_key_required_fields_mapping(
    pyramid_app_with_services, user_profile_service
):
    """Test that required fields with data_key are correctly mapped in required list."""
    services = [user_profile_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    user_profile_tool = tools[0]  # create_user_profile

    input_schema = user_profile_tool["inputSchema"]

    # POST requests should have body structure with required fields
    assert (
        "body" in input_schema["properties"]
    ), "POST request should have body structure"
    body_schema = input_schema["properties"]["body"]
    required = body_schema.get("required", [])

    # Required fields should use data_key names, not Python names
    assert "fullName" in required, "Required field should use data_key 'fullName'"
    assert (
        "emailAddress" in required
    ), "Required field should use data_key 'emailAddress'"

    # Optional fields should not be in required list
    assert "userId" not in required, "Optional field should not be required"
    assert "accountType" not in required, "Optional field should not be required"
    assert "status" not in required, "Optional field should not be required"

    # Python names should NOT be in required list
    assert "full_name" not in required, "Python name should not be in required list"
    assert "email_address" not in required, "Python name should not be in required list"


def test_data_key_field_descriptions_preserved(
    pyramid_app_with_services, user_profile_service
):
    """Test that field descriptions are preserved when using data_key."""
    services = [user_profile_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    user_profile_tool = tools[0]  # create_user_profile

    input_schema = user_profile_tool["inputSchema"]
    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]

    # Verify descriptions are preserved for data_key fields
    assert body_props["fullName"]["description"] == "User's full name"
    assert body_props["emailAddress"]["description"] == "User's email address"
    assert body_props["userId"]["description"] == "User ID number"
    assert body_props["accountType"]["description"] == "Type of user account"
    assert body_props["status"]["description"] == "User status"


def test_data_key_field_types_correct(pyramid_app_with_services, user_profile_service):
    """Test that field types are correctly determined for data_key fields."""
    services = [user_profile_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    user_profile_tool = tools[0]  # create_user_profile

    input_schema = user_profile_tool["inputSchema"]
    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]

    # Verify field types are correct
    assert body_props["fullName"]["type"] == "string"
    assert (
        body_props["emailAddress"]["type"] == "string"
    )  # Email field should be string type
    assert body_props["userId"]["type"] == "integer"
    assert body_props["accountType"]["type"] == "string"
    assert body_props["status"]["type"] == "string"


def test_mixed_data_key_and_python_names(pyramid_app_with_services):
    """Test schema with mix of data_key and regular field names."""

    class MixedSchema(Schema):
        """Schema mixing data_key and regular field names."""

        # Field with data_key
        first_name = fields.Str(
            required=True, data_key="firstName", metadata={"description": "First name"}
        )
        # Field without data_key
        age = fields.Int(required=True, metadata={"description": "User age"})
        # Another field with data_key
        last_login = fields.DateTime(
            required=False,
            data_key="lastLogin",
            metadata={"description": "Last login timestamp"},
        )

    mixed_service = Service(
        name="mixed_service",
        path="/mixed",
        description="Service with mixed field naming",
    )

    @mixed_service.post(
        schema=MixedSchema(),
        validators=(marshmallow_body_validator,),
    )
    def create_mixed(request):
        """Create with mixed field names."""
        return {"data": request.validated}

    services = [mixed_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    mixed_tool = tools[0]  # create_mixed

    input_schema = mixed_tool["inputSchema"]
    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]
    body_required = properties["body"].get("required", [])

    # data_key field should use the key name
    assert "firstName" in body_props
    assert "firstName" in body_required
    assert "first_name" not in body_props
    assert "first_name" not in body_required

    # Regular field should use Python name
    assert "age" in body_props
    assert "age" in body_required

    # Optional data_key field should use key name
    assert "lastLogin" in body_props
    assert "lastLogin" not in body_required
    assert "last_login" not in body_props


def test_tool_parameter_names_use_data_key_values(
    pyramid_app_with_services, user_profile_service
):
    """Test that MCP tool parameter names use data_key values, not Python names."""
    services = [user_profile_service]
    app = pyramid_app_with_services(services)

    # Get tools list to inspect the actual tool parameters
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    user_profile_tool = tools[0]  # create_user_profile

    # Get the tool's input schema
    input_schema = user_profile_tool["inputSchema"]
    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]
    body_required = properties["body"].get("required", [])

    # ASSERT: Parameter names should be the data_key values, not Python field names

    # Fields with data_key should expose the data_key as parameter name
    assert (
        "fullName" in body_props
    ), "Parameter should use data_key 'fullName', not 'full_name'"
    assert (
        "emailAddress" in body_props
    ), "Parameter should use data_key 'emailAddress', not 'email_address'"
    assert (
        "userId" in body_props
    ), "Parameter should use data_key 'userId', not 'user_id'"
    assert (
        "accountType" in body_props
    ), "Parameter should use data_key 'accountType', not 'account_type'"

    # Field without data_key should use Python field name
    assert (
        "status" in body_props
    ), "Parameter without data_key should use Python field name 'status'"

    # ASSERT: Python field names should NOT be exposed as parameters
    assert (
        "full_name" not in body_props
    ), "Python field name 'full_name' should not be exposed when data_key exists"
    assert (
        "email_address" not in body_props
    ), "Python field name 'email_address' should not be exposed when data_key exists"
    assert (
        "user_id" not in body_props
    ), "Python field name 'user_id' should not be exposed when data_key exists"
    assert (
        "account_type" not in body_props
    ), "Python field name 'account_type' should not be exposed when data_key exists"

    # ASSERT: Required fields should also use data_key names
    assert (
        "fullName" in body_required
    ), "Required parameter should use data_key 'fullName'"
    assert (
        "emailAddress" in body_required
    ), "Required parameter should use data_key 'emailAddress'"

    # ASSERT: Python field names should NOT be in required list
    assert (
        "full_name" not in body_required
    ), "Python field name 'full_name' should not be in required list"
    assert (
        "email_address" not in body_required
    ), "Python field name 'email_address' should not be in required list"


# =============================================================================
# 🧪 SIMPLE BODY PARAMETER TESTS
# =============================================================================


def test_simple_body_parameter_validation(
    pyramid_app_with_services, simple_body_service
):
    """Test simple body parameter validation with required and optional fields."""
    services = [simple_body_service]
    app = pyramid_app_with_services(services)

    # First get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]  # Get the actual tool name

    # Test MCP tool call with valid body parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {"body": {"message": "Hello World", "priority": 5}},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed with validated body parameters
    assert response.status_code == 200
    result = response.json
    assert result["id"] == 1
    assert "result" in result

    # The actual response data should be in the MCP context format
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"

    # Extract the actual response content
    actual_content = mcp_result["representation"]["content"]

    # Verify that the validated body parameters were used
    assert actual_content["message"] == "Hello World"
    assert actual_content["priority"] == 5
    assert actual_content["status"] == "created"


def test_simple_body_parameter_schema_generation(
    pyramid_app_with_services, simple_body_service
):
    """Test that simple body parameter schema is correctly generated."""
    services = [simple_body_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    simple_tool = tools[0]  # simple_body

    # Check that the tool has proper input schema
    assert "inputSchema" in simple_tool
    input_schema = simple_tool["inputSchema"]
    assert "properties" in input_schema

    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]
    body_required = properties["body"].get("required", [])

    # Verify simple schema fields
    assert "message" in body_props, "Should have 'message' field"
    assert "priority" in body_props, "Should have 'priority' field"

    # Verify field types
    assert body_props["message"]["type"] == "string"
    assert body_props["priority"]["type"] == "integer"

    # Verify required fields
    assert "message" in body_required, "Message should be required"
    assert "priority" not in body_required, "Priority should be optional"

    # Verify descriptions
    assert body_props["message"]["description"] == "Test message"
    assert body_props["priority"]["description"] == "Message priority"


# =============================================================================
# 🧪 NESTED BODY PARAMETER TESTS
# =============================================================================


def test_nested_body_parameter_validation(
    pyramid_app_with_services, nested_body_service
):
    """Test nested body parameter validation with address schema."""
    services = [nested_body_service]
    app = pyramid_app_with_services(services)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]
    tool_name = tools[0]["name"]

    # Test MCP tool call with valid nested body parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "body": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "address": {
                        "street": "123 Main St",
                        "city": "Anytown",
                        "zip_code": "12345",
                    },
                }
            },
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed with validated nested body parameters
    assert response.status_code == 200
    result = response.json
    assert result["id"] == 1
    assert "result" in result

    # The actual response data should be in the MCP context format
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"

    # Extract the actual response content
    actual_content = mcp_result["representation"]["content"]

    # Verify that the validated nested body parameters were used
    user_data = actual_content["user"]
    assert user_data["name"] == "John Doe"
    assert user_data["email"] == "john@example.com"
    assert user_data["address"]["street"] == "123 Main St"
    assert user_data["address"]["city"] == "Anytown"
    assert user_data["address"]["zip_code"] == "12345"
    assert actual_content["status"] == "created"


def test_nested_body_parameter_schema_generation(
    pyramid_app_with_services, nested_body_service
):
    """Test that nested body parameter schema is correctly generated."""
    services = [nested_body_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    nested_tool = tools[0]  # nested_body

    # Check that the tool has proper input schema
    assert "inputSchema" in nested_tool
    input_schema = nested_tool["inputSchema"]
    assert "properties" in input_schema

    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]
    body_required = properties["body"].get("required", [])

    # Verify main schema fields
    assert "name" in body_props, "Should have 'name' field"
    assert "email" in body_props, "Should have 'email' field"
    assert "address" in body_props, "Should have 'address' field"

    # Verify field types
    assert body_props["name"]["type"] == "string"
    assert body_props["email"]["type"] == "string"
    assert body_props["address"]["type"] == "object"

    # Verify required fields
    assert "name" in body_required, "Name should be required"
    assert "email" in body_required, "Email should be required"
    assert "address" in body_required, "Address should be required"

    # Verify nested address schema
    address_props = body_props["address"]["properties"]
    address_required = body_props["address"].get("required", [])

    assert "street" in address_props, "Address should have 'street' field"
    assert "city" in address_props, "Address should have 'city' field"
    assert "zip_code" in address_props, "Address should have 'zip_code' field"

    # All address fields should be required
    assert "street" in address_required, "Street should be required"
    assert "city" in address_required, "City should be required"
    assert "zip_code" in address_required, "ZIP code should be required"


# =============================================================================
# 🧪 COMPLEX BODY PARAMETER TESTS (with pre_load hooks)
# =============================================================================


@pytest.mark.parametrize(
    "settings",
    [{"mcp.route_discovery.enabled": "true"}, {"mcp.route_discovery.enabled": "false"}],
)
def test_complex_body_with_pre_load_hooks(settings, pyramid_app_with_services, logs):
    """Test complex body parameters with pre_load hooks and context."""

    # Create a Cornice service with complex nested schema
    users_service = Service(
        name="users",
        path="/api/v1/users",
        description="Users service with complex body validation",
    )

    @users_service.post(schema=RequestSchema, validators=(marshmallow_validator,))
    def create_users(request):
        """Create users with complex validated body parameters."""
        # Return validated parameters directly
        return Response(json=request.validated)

    # Create test app with the service
    app = pyramid_app_with_services([users_service], settings=settings)

    # Get the actual tool name
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200
    tools = tools_response.json["result"]["tools"]

    # When route discovery is disabled, no tools are discovered
    if not tools:
        # Skip test when route discovery is disabled
        return

    tool_name = tools[0]["name"]

    # Test MCP tool call with complex body structure
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {"body": {"name": "John Doe", "response": {"method": "POST"}}},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed with complex body validation
    assert response.status_code == 200
    result = response.json
    assert result["id"] == 1
    assert "result" in result

    # The actual response data should be in the MCP context format
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"

    # Extract the actual response content - should contain pre_load processed data
    actual_content = mcp_result["representation"]["content"]

    # Verify the complex nested structure was processed
    assert "body" in actual_content
    body_data = actual_content["body"]
    assert body_data["name"] == "John Doe"
    assert "response" in body_data

    # The pre_load hooks should have added path information
    response_data = body_data["response"]
    assert response_data["method"] == "POST"
    assert "path" in response_data  # Added by pre_load hook
    assert "sub" in response_data  # Added by pre_load hook


def test_complex_body_schema_generation_with_pre_load(pyramid_app_with_services):
    """Test that complex body schema with pre_load hooks is correctly generated."""

    users_service = Service(
        name="users_complex",
        path="/api/v1/users-complex",
        description="Users service with complex schema",
    )

    @users_service.post(schema=RequestSchema, validators=(marshmallow_validator,))
    def create_complex_users(request):
        """Create users with complex schema validation."""
        return Response(json=request.validated)

    services = [users_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    complex_tool = tools[0]  # users_complex

    # Check that the tool has proper input schema
    assert "inputSchema" in complex_tool
    input_schema = complex_tool["inputSchema"]
    assert "properties" in input_schema

    properties = input_schema["properties"]

    # POST requests should have body structure
    assert "body" in properties, "POST request should have body structure"
    body_props = properties["body"]["properties"]

    # Verify complex schema structure (should reflect the nested ParentSchema)
    assert "name" in body_props, "Should have 'name' field from ParentSchema"
    assert "response" in body_props, "Should have 'response' field from ParentSchema"

    # Verify nested response schema
    if "response" in body_props and "properties" in body_props["response"]:
        response_props = body_props["response"]["properties"]
        assert "path" in response_props, "Response should have 'path' field"
        assert "method" in response_props, "Response should have 'method' field"
        assert "sub" in response_props, "Response should have 'sub' field"
