"""
Unit tests for pyramid_mcp security schema functionality.

This module tests:
- BearerAuthSchema and BasicAuthSchema validation
- Schema validation functions
- Schema integration with tool input schemas

No tool definitions to avoid configuration conflicts.
"""

import pytest
from marshmallow import ValidationError

from pyramid_mcp.security import (
    BasicAuthSchema,
    BearerAuthSchema,
    merge_auth_into_schema,
    validate_auth_credentials,
)

# =============================================================================
# 🔧 SECURITY SCHEMA FIXTURES
# =============================================================================


@pytest.fixture
def bearer_auth_schema():
    """Bearer authentication schema fixture."""
    return BearerAuthSchema()


@pytest.fixture
def basic_auth_schema():
    """Basic authentication schema fixture."""
    return BasicAuthSchema()


# =============================================================================
# 🔐 SECURITY SCHEMA VALIDATION TESTS
# =============================================================================


def test_bearer_auth_schema_valid_token(bearer_auth_schema):
    """Test Bearer auth schema with valid token."""
    data = {"auth_token": "valid_bearer_token_123"}
    result = bearer_auth_schema.load(data)
    assert result["auth_token"] == "valid_bearer_token_123"


def test_bearer_auth_schema_missing_token(bearer_auth_schema):
    """Test Bearer auth schema with missing token."""
    data = {}
    with pytest.raises(ValidationError) as exc_info:
        bearer_auth_schema.load(data)
    assert "auth_token" in exc_info.value.messages


def test_bearer_auth_schema_empty_token(bearer_auth_schema):
    """Test Bearer auth schema with empty token."""
    data = {"auth_token": ""}
    with pytest.raises(ValidationError) as exc_info:
        bearer_auth_schema.load(data)
    assert "auth_token" in exc_info.value.messages


def test_basic_auth_schema_valid_credentials(basic_auth_schema):
    """Test Basic auth schema with valid credentials."""
    data = {"username": "test_user", "password": "test_pass"}
    result = basic_auth_schema.load(data)
    assert result["username"] == "test_user"
    assert result["password"] == "test_pass"


def test_basic_auth_schema_missing_username(basic_auth_schema):
    """Test Basic auth schema with missing username."""
    data = {"password": "test_pass"}
    with pytest.raises(ValidationError) as exc_info:
        basic_auth_schema.load(data)
    assert "username" in exc_info.value.messages


def test_basic_auth_schema_missing_password(basic_auth_schema):
    """Test Basic auth schema with missing password."""
    data = {"username": "test_user"}
    with pytest.raises(ValidationError) as exc_info:
        basic_auth_schema.load(data)
    assert "password" in exc_info.value.messages


def test_basic_auth_schema_empty_credentials(basic_auth_schema):
    """Test Basic auth schema with empty credentials."""
    data = {"username": "", "password": ""}
    with pytest.raises(ValidationError) as exc_info:
        basic_auth_schema.load(data)
    errors = exc_info.value.messages
    assert "username" in errors
    assert "password" in errors


# =============================================================================
# 🔧 SECURITY UTILITY FUNCTION TESTS
# =============================================================================


def test_merge_auth_into_schema_with_bearer_auth(bearer_auth_schema):
    """Test merging Bearer auth into tool input schema."""
    base_schema = {
        "type": "object",
        "properties": {"data": {"type": "string"}},
        "required": ["data"],
    }

    result = merge_auth_into_schema(base_schema, bearer_auth_schema)

    assert "auth_token" in result["properties"]
    assert result["properties"]["auth_token"]["type"] == "string"
    assert "auth_token" in result["required"]
    assert "data" in result["properties"]  # Original field preserved
    assert "data" in result["required"]  # Original requirement preserved


def test_merge_auth_into_schema_with_basic_auth(basic_auth_schema):
    """Test merging Basic auth into tool input schema."""
    base_schema = {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }

    result = merge_auth_into_schema(base_schema, basic_auth_schema)

    assert "username" in result["properties"]
    assert "password" in result["properties"]
    assert result["properties"]["username"]["type"] == "string"
    assert result["properties"]["password"]["type"] == "string"
    assert "username" in result["required"]
    assert "password" in result["required"]
    assert "message" in result["properties"]  # Original field preserved


def test_merge_auth_into_schema_with_none():
    """Test merging with None schema returns original."""
    base_schema = {
        "type": "object",
        "properties": {"data": {"type": "string"}},
        "required": ["data"],
    }

    result = merge_auth_into_schema(base_schema, None)
    assert result == base_schema


def test_merge_auth_into_schema_empty_base():
    """Test merging auth into empty base schema."""
    base_schema = {"type": "object", "properties": {}, "required": []}

    result = merge_auth_into_schema(base_schema, BearerAuthSchema())

    assert "auth_token" in result["properties"]
    assert "auth_token" in result["required"]
    assert len(result["properties"]) == 1


def test_validate_auth_credentials_bearer_success():
    """Test successful Bearer auth credential validation."""
    schema = BearerAuthSchema()
    tool_args = {"auth_token": "valid_token_123"}

    error = validate_auth_credentials(tool_args, schema)

    # Should return None for successful validation
    assert error is None


def test_validate_auth_credentials_basic_success():
    """Test successful Basic auth credential validation."""
    schema = BasicAuthSchema()
    tool_args = {"username": "testuser", "password": "testpass"}

    error = validate_auth_credentials(tool_args, schema)

    # Should return None for successful validation
    assert error is None


def test_validate_auth_credentials_bearer_failure():
    """Test Bearer auth credential validation failure."""
    schema = BearerAuthSchema()
    tool_args = {"auth_token": ""}  # Empty token

    error = validate_auth_credentials(tool_args, schema)

    # Should return error dict for empty token
    assert error is not None
    assert error["type"] == "empty_credentials"


def test_validate_auth_credentials_basic_failure():
    """Test Basic auth credential validation failure."""
    schema = BasicAuthSchema()
    tool_args = {"username": "testuser"}  # Missing password

    error = validate_auth_credentials(tool_args, schema)

    # Should return error dict for missing password
    assert error is not None
    assert error["type"] == "missing_credentials"


def test_validate_auth_credentials_with_none():
    """Test validation with None schema should pass."""
    credentials = {"some_field": "some_value"}

    # Should not raise any exception
    validate_auth_credentials(credentials, None)
