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

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_user_profile",
                    "description": "Create user profile with data_key field mapping.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "object",
                                "properties": {
                                    "fullName": {
                                        "type": "string",
                                        "description": "User's full name",
                                    },
                                    "emailAddress": {
                                        "type": "string",
                                        "format": "email",
                                        "description": "User's email address",
                                    },
                                    "userId": {
                                        "type": "integer",
                                        "description": "User ID number",
                                    },
                                    "accountType": {
                                        "type": "string",
                                        "description": "Type of user account",
                                        "default": "standard",
                                    },
                                    "status": {
                                        "type": "string",
                                        "description": "User status",
                                        "default": "active",
                                    },
                                },
                                "required": ["fullName", "emailAddress"],
                                "additionalProperties": False,
                                "description": "Request body parameters",
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


# Note: test_data_key_required_fields_mapping,
# test_data_key_field_descriptions_preserved,
# and test_data_key_field_types_correct are now covered by
# test_data_key_fields_appear_in_tool_schema which tests the complete schema
# structure including field types, descriptions, and required fields.


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

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_mixed_service",
                    "description": "Create with mixed field names.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "object",
                                "properties": {
                                    "firstName": {
                                        "type": "string",
                                        "description": "First name",
                                    },
                                    "age": {
                                        "type": "integer",
                                        "description": "User age",
                                    },
                                    "lastLogin": {
                                        "type": "string",
                                        "format": "date-time",
                                        "description": "Last login timestamp",
                                    },
                                },
                                "required": ["firstName", "age"],
                                "additionalProperties": False,
                                "description": "Request body parameters",
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


# Note: test_tool_parameter_names_use_data_key_values is now covered by
# test_data_key_fields_appear_in_tool_schema which tests the complete tool schema
# structure.


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

    # Assert the complete response structure
    actual_response = response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": {
                        "message": "Hello World",
                        "priority": 5,
                        "status": "created",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/simple-body",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


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

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_simple_body",
                    "description": "Create simple message with body validation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "Test message",
                                    },
                                    "priority": {
                                        "type": "integer",
                                        "default": 1,
                                        "description": "Message priority",
                                    },
                                },
                                "required": ["message"],
                                "additionalProperties": False,
                                "description": "Request body parameters",
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


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

    # Assert the complete response structure
    actual_response = response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": {
                        "user": {
                            "name": "John Doe",
                            "email": "john@example.com",
                            "address": {
                                "street": "123 Main St",
                                "city": "Anytown",
                                "zip_code": "12345",
                            },
                        },
                        "status": "created",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/nested-body",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


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

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_nested_body",
                    "description": "Create user with nested address validation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Full name",
                                    },
                                    "email": {
                                        "type": "string",
                                        "format": "email",
                                        "description": "Email address",
                                    },
                                    "address": {
                                        "type": "object",
                                        "properties": {
                                            "street": {
                                                "type": "string",
                                                "description": "Street address",
                                            },
                                            "city": {
                                                "type": "string",
                                                "description": "City",
                                            },
                                            "zip_code": {
                                                "type": "string",
                                                "description": "ZIP code",
                                            },
                                        },
                                        "required": ["street", "city", "zip_code"],
                                        "additionalProperties": False,
                                        "description": "Address information",
                                    },
                                },
                                "required": ["name", "email", "address"],
                                "additionalProperties": False,
                                "description": "Request body parameters",
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }


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
    # Assert the complete response structure
    actual_response = response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": {
                        "body": {
                            "name": "John Doe",
                            "response": {
                                "path": "/api/v1/users",
                                "method": "POST",
                                "sub": {"path": "/api/v1/users"},
                            },
                        }
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/api/v1/users",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


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

    # Assert the complete tools list response structure
    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "create_users_complex",
                    "description": "Create users with complex schema validation.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "body": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                    },
                                    "response": {
                                        "type": "object",
                                        "properties": {
                                            "path": {
                                                "type": "string",
                                            },
                                            "method": {
                                                "type": "string",
                                            },
                                            "sub": {
                                                "type": "object",
                                                "properties": {
                                                    "path": {
                                                        "type": "string",
                                                    }
                                                },
                                                "required": ["path"],
                                                "additionalProperties": False,
                                            },
                                        },
                                        "required": ["path", "method"],
                                        "additionalProperties": False,
                                    },
                                },
                                "required": ["name"],
                                "additionalProperties": False,
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                }
            ]
        },
    }
