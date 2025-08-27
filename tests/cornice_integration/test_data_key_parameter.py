"""
Test Marshmallow data_key parameter handling in Cornice MCP tools.

This module tests that when a Marshmallow field has a data_key parameter,
the generated MCP tool schema uses the data_key as the field name, not
the Python attribute name.
"""

import pytest
from cornice import Service
from cornice.validators import (
    marshmallow_body_validator,
    marshmallow_querystring_validator,
    marshmallow_validator,
)
from marshmallow import Schema, fields


class UserProfileSchema(Schema):
    """Schema with data_key parameters to test field name mapping."""

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


@pytest.fixture
def data_key_service():
    """Create a Cornice service with schema that uses data_key parameters."""
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


def test_data_key_fields_appear_in_tool_schema(
    pyramid_app_with_services, data_key_service
):
    """Test that data_key field names appear in MCP tool schema, not Python names."""
    services = [data_key_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]

    # Find the user profile creation tool
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


def test_data_key_required_fields_mapping(pyramid_app_with_services, data_key_service):
    """Test that required fields with data_key are correctly mapped in required list."""
    services = [data_key_service]
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
    pyramid_app_with_services, data_key_service
):
    """Test that field descriptions are preserved when using data_key."""
    services = [data_key_service]
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


def test_data_key_field_types_correct(pyramid_app_with_services, data_key_service):
    """Test that field types are correctly determined for data_key fields."""
    services = [data_key_service]
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
    pyramid_app_with_services, data_key_service
):
    """Test that MCP tool parameter names use data_key values, not Python names."""
    services = [data_key_service]
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


def test_querystring_data_key_parameters_exposed(pyramid_app_with_services):
    """Test that querystring schema with data_key parameters are properly exposed."""

    class QuerystringSchema(Schema):
        """Schema with data_key parameters for querystring validation."""

        legal_entity_id = fields.Str(
            required=False,
            data_key="legalEntityId",  # camelCase for API
            metadata={"description": "Legal entity UUID for filtering"},
        )
        page_number = fields.Int(
            required=False,
            data_key="pageNumber",  # camelCase for API
            dump_default=1,
            metadata={"description": "Page number for pagination"},
        )
        page_size = fields.Int(
            required=False,
            data_key="pageSize",  # camelCase for API
            dump_default=20,
            metadata={"description": "Number of items per page"},
        )
        # Field without data_key for comparison
        status = fields.Str(required=False, metadata={"description": "Status filter"})

    # Create service with querystring validation
    querystring_service = Service(
        name="list_workspace_parts",
        path="/workspace-parts",
        description="List workspace parts with querystring filtering",
    )

    @querystring_service.get(
        schema=QuerystringSchema(),
        validators=(marshmallow_querystring_validator,),
    )
    def list_parts(request):
        """List workspace parts with filtering."""
        validated_data = request.validated
        return {
            "parts": [],
            "filters": validated_data,
            "message": "Parts listed successfully",
        }

    services = [querystring_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    workspace_parts_tool = tools[0]  # list_workspace_parts

    # Get the tool's input schema
    input_schema = workspace_parts_tool["inputSchema"]
    properties = input_schema["properties"]

    # ASSERT: Querystring parameters should be under 'querystring' object
    assert (
        "querystring" in properties
    ), "GET request with schema should have querystring object"

    inner_querystring_props = properties["querystring"]["properties"]

    # ASSERT: Querystring parameters should use data_key names
    assert (
        "legalEntityId" in inner_querystring_props
    ), "Should use data_key 'legalEntityId', not 'legal_entity_id'"
    assert (
        "pageNumber" in inner_querystring_props
    ), "Should use data_key 'pageNumber', not 'page_number'"
    assert (
        "pageSize" in inner_querystring_props
    ), "Should use data_key 'pageSize', not 'page_size'"
    assert (
        "status" in inner_querystring_props
    ), "Field without data_key should use Python name 'status'"

    # ASSERT: Python field names should NOT be in the querystring schema
    assert (
        "legal_entity_id" not in inner_querystring_props
    ), "Python name should not appear when data_key exists"
    assert (
        "page_number" not in inner_querystring_props
    ), "Python name should not appear when data_key exists"
    assert (
        "page_size" not in inner_querystring_props
    ), "Python name should not appear when data_key exists"

    # ASSERT: Verify the parameter types and descriptions are correct
    assert inner_querystring_props["legalEntityId"]["type"] == "string"
    assert (
        inner_querystring_props["legalEntityId"]["description"]
        == "Legal entity UUID for filtering"
    )

    assert inner_querystring_props["pageNumber"]["type"] == "integer"
    assert inner_querystring_props["pageNumber"]["default"] == 1
    assert (
        inner_querystring_props["pageNumber"]["description"]
        == "Page number for pagination"
    )

    assert inner_querystring_props["pageSize"]["type"] == "integer"
    assert inner_querystring_props["pageSize"]["default"] == 20
    assert (
        inner_querystring_props["pageSize"]["description"] == "Number of items per page"
    )


def test_querystring_field_with_marshmallow_validator(pyramid_app_with_services):
    """Test schema with nested querystring field using marshmallow_validator."""

    # Define the querystring schema separately
    class QuerystringSchema(Schema):
        """Querystring schema with data_key parameters."""

        legal_entity_id = fields.Str(
            required=False,
            data_key="legalEntityId",  # camelCase for API
            metadata={"description": "Legal entity UUID for filtering"},
        )
        page_number = fields.Int(
            required=False,
            data_key="pageNumber",  # camelCase for API
            dump_default=1,
            metadata={"description": "Page number for pagination"},
        )
        page_size = fields.Int(
            required=False,
            data_key="pageSize",  # camelCase for API
            dump_default=20,
            metadata={"description": "Number of items per page"},
        )
        # Field without data_key for comparison
        status = fields.Str(required=False, metadata={"description": "Status filter"})

    # Main schema with nested querystring field
    class SchemaWithQuerystring(Schema):
        """Schema with nested querystring field."""

        querystring = fields.Nested(
            QuerystringSchema,
            metadata={"description": "Query parameters for filtering"},
        )

    # Create service with nested querystring field
    querystring_field_service = Service(
        name="list_workspace_parts_with_qs_field",
        path="/workspace-parts-qs-field",
        description="List workspace parts with nested querystring field",
    )

    @querystring_field_service.get(
        schema=SchemaWithQuerystring(),
        validators=(marshmallow_validator,),
    )
    def list_parts_with_qs_field(request):
        """List workspace parts with nested querystring field."""
        validated_data = request.validated
        return {
            "parts": [],
            "filters": validated_data,
            "message": "Parts listed successfully with nested querystring field",
        }

    services = [querystring_field_service]
    app = pyramid_app_with_services(services)

    # Get tools list
    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )
    assert tools_response.status_code == 200

    tools = tools_response.json["result"]["tools"]
    qs_field_tool = tools[0]  # list_workspace_parts_with_qs_field

    # Get the tool's input schema
    input_schema = qs_field_tool["inputSchema"]
    properties = input_schema["properties"]

    # ASSERT: GET requests with nested querystring schema create double-nested structure
    assert "querystring" in properties, "GET request should have querystring field"

    # The outer querystring is from our method-based wrapping
    outer_querystring = properties["querystring"]["properties"]

    # The inner querystring is from the original nested schema
    assert "querystring" in outer_querystring, "Should have nested querystring field"
    inner_inner_querystring_props = outer_querystring["querystring"]["properties"]

    # ASSERT: Parameters use data_key names within nested structure
    assert (
        "legalEntityId" in inner_inner_querystring_props
    ), "Should use data_key 'legalEntityId', not 'legal_entity_id'"
    assert (
        "pageNumber" in inner_inner_querystring_props
    ), "Should use data_key 'pageNumber', not 'page_number'"
    assert (
        "pageSize" in inner_inner_querystring_props
    ), "Should use data_key 'pageSize', not 'page_size'"
    assert (
        "status" in inner_inner_querystring_props
    ), "Field without data_key should use Python name 'status'"

    # ASSERT: Python field names should NOT be in the nested schema
    assert (
        "legal_entity_id" not in inner_inner_querystring_props
    ), "Python name should not appear when data_key exists"
    assert (
        "page_number" not in inner_inner_querystring_props
    ), "Python name should not appear when data_key exists"
    assert (
        "page_size" not in inner_inner_querystring_props
    ), "Python name should not appear when data_key exists"

    # ASSERT: Verify the parameter types and descriptions are correct
    assert inner_inner_querystring_props["legalEntityId"]["type"] == "string"
    assert (
        inner_inner_querystring_props["legalEntityId"]["description"]
        == "Legal entity UUID for filtering"
    )

    assert inner_inner_querystring_props["pageNumber"]["type"] == "integer"
    assert inner_inner_querystring_props["pageNumber"]["default"] == 1
    assert (
        inner_inner_querystring_props["pageNumber"]["description"]
        == "Page number for pagination"
    )

    assert inner_inner_querystring_props["pageSize"]["type"] == "integer"
    assert inner_inner_querystring_props["pageSize"]["default"] == 20
    assert (
        inner_inner_querystring_props["pageSize"]["description"]
        == "Number of items per page"
    )
