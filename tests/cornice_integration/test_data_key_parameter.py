"""
Test Marshmallow data_key parameter handling in Cornice MCP tools.

This module tests that when a Marshmallow field has a data_key parameter,
the generated MCP tool schema uses the data_key as the field name, not
the Python attribute name.
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_body_validator
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

    # Verify data_key field names are used (camelCase), not Python names (snake_case)
    assert "fullName" in properties, "Should use data_key 'fullName', not 'full_name'"
    assert (
        "emailAddress" in properties
    ), "Should use data_key 'emailAddress', not 'email_address'"
    assert "userId" in properties, "Should use data_key 'userId', not 'user_id'"
    assert (
        "accountType" in properties
    ), "Should use data_key 'accountType', not 'account_type'"

    # Field without data_key should use Python name
    assert (
        "status" in properties
    ), "Field without data_key should use Python name 'status'"

    # Verify Python names are NOT in the schema
    assert (
        "full_name" not in properties
    ), "Python name 'full_name' should not appear in schema"
    assert (
        "email_address" not in properties
    ), "Python name 'email_address' should not appear in schema"
    assert (
        "user_id" not in properties
    ), "Python name 'user_id' should not appear in schema"
    assert (
        "account_type" not in properties
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
    required = input_schema.get("required", [])

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

    # Verify descriptions are preserved for data_key fields
    assert properties["fullName"]["description"] == "User's full name"
    assert properties["emailAddress"]["description"] == "User's email address"
    assert properties["userId"]["description"] == "User ID number"
    assert properties["accountType"]["description"] == "Type of user account"
    assert properties["status"]["description"] == "User status"


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

    # Verify field types are correct
    assert properties["fullName"]["type"] == "string"
    assert (
        properties["emailAddress"]["type"] == "string"
    )  # Email field should be string type
    assert properties["userId"]["type"] == "integer"
    assert properties["accountType"]["type"] == "string"
    assert properties["status"]["type"] == "string"


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
    required = input_schema.get("required", [])

    # data_key field should use the key name
    assert "firstName" in properties
    assert "firstName" in required
    assert "first_name" not in properties
    assert "first_name" not in required

    # Regular field should use Python name
    assert "age" in properties
    assert "age" in required

    # Optional data_key field should use key name
    assert "lastLogin" in properties
    assert "lastLogin" not in required
    assert "last_login" not in properties
