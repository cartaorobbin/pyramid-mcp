"""
Unit tests for pyramid_mcp auth parameter extraction.

This module tests:
- BearerAuthSchema for token extraction
- BasicAuthSchema for username/password extraction
- Dynamic authentication parameter conversion from tool arguments
- Auth header creation for subrequests
- Tool argument cleaning (removing auth params after processing)

Uses enhanced fixtures from conftest.py for clean, non-duplicated test setup.
"""

from pyramid_mcp.security import (
    BasicAuthSchema,
    BearerAuthSchema,
    create_auth_headers,
    extract_auth_credentials,
    remove_auth_from_tool_args,
)

# =============================================================================
# 🔧 AUTHENTICATION PARAMETER EXTRACTION TESTS
# =============================================================================


def test_extract_auth_credentials_bearer_success():
    """Test successful extraction of Bearer auth credentials."""
    tool_args = {"data": "test", "auth_token": "bearer_token_123"}
    schema = BearerAuthSchema()

    credentials = extract_auth_credentials(tool_args, schema)

    assert credentials["bearer_token"] == "bearer_token_123"


def test_extract_auth_credentials_basic_success():
    """Test successful extraction of Basic auth credentials."""
    tool_args = {"data": "test", "username": "testuser", "password": "testpass"}
    schema = BasicAuthSchema()

    credentials = extract_auth_credentials(tool_args, schema)

    assert credentials["username"] == "testuser"
    assert credentials["password"] == "testpass"


def test_extract_auth_credentials_bearer_missing_token():
    """Test extraction with missing Bearer token."""
    tool_args = {"data": "test"}
    schema = BearerAuthSchema()

    credentials = extract_auth_credentials(tool_args, schema)

    # Missing token should return empty credentials
    assert credentials == {}


def test_extract_auth_credentials_basic_missing_credentials():
    """Test extraction with missing Basic auth credentials."""
    tool_args = {"data": "test", "username": "testuser"}  # Missing password
    schema = BasicAuthSchema()

    credentials = extract_auth_credentials(tool_args, schema)

    # Missing password should return empty credentials
    assert credentials == {}


def test_extract_auth_credentials_with_none_schema():
    """Test extraction with None schema returns empty dict."""
    tool_args = {"data": "test", "some_param": "value"}

    credentials = extract_auth_credentials(tool_args, None)

    assert credentials == {}


def test_extract_auth_credentials_partial_bearer():
    """Test extraction with partial Bearer credentials."""
    tool_args = {"data": "test", "auth_token": ""}  # Empty token
    schema = BearerAuthSchema()

    credentials = extract_auth_credentials(tool_args, schema)

    # Empty token should return empty credentials
    assert credentials == {}


def test_extract_auth_credentials_extra_fields():
    """Test extraction ignores extra fields not in schema."""
    tool_args = {
        "data": "test",
        "auth_token": "token123",
        "extra_field": "ignored",
        "another_field": "also_ignored",
    }
    schema = BearerAuthSchema()

    credentials = extract_auth_credentials(tool_args, schema)

    assert credentials == {"bearer_token": "token123"}
    assert "extra_field" not in credentials
    assert "another_field" not in credentials


# =============================================================================
# 🔧 HTTP HEADER GENERATION TESTS
# =============================================================================


def test_create_auth_headers_bearer_success():
    """Test successful creation of Bearer auth headers."""
    credentials = {"bearer_token": "test_bearer_token"}
    schema = BearerAuthSchema()

    headers = create_auth_headers(credentials, schema)

    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test_bearer_token"


def test_create_auth_headers_basic_success():
    """Test successful creation of Basic auth headers."""
    credentials = {"username": "testuser", "password": "testpass"}
    schema = BasicAuthSchema()

    headers = create_auth_headers(credentials, schema)

    assert "Authorization" in headers
    # Basic auth should be base64 encoded
    import base64

    expected_encoded = base64.b64encode(b"testuser:testpass").decode("ascii")
    assert headers["Authorization"] == f"Basic {expected_encoded}"


def test_create_auth_headers_bearer_empty_token():
    """Test header creation with empty Bearer token."""
    credentials = {"bearer_token": ""}
    schema = BearerAuthSchema()

    headers = create_auth_headers(credentials, schema)

    # Empty token should result in no headers
    assert headers == {}


def test_create_auth_headers_basic_missing_password():
    """Test header creation with missing Basic auth password."""
    credentials = {"username": "testuser"}
    schema = BasicAuthSchema()

    headers = create_auth_headers(credentials, schema)

    # Missing password should result in no headers
    assert headers == {}


def test_create_auth_headers_with_none_schema():
    """Test header creation with None schema returns empty dict."""
    credentials = {"some_field": "some_value"}

    headers = create_auth_headers(credentials, None)

    assert headers == {}


def test_create_auth_headers_bearer_whitespace_token():
    """Test header creation with whitespace-only Bearer token."""
    credentials = {"bearer_token": "   "}
    schema = BearerAuthSchema()

    headers = create_auth_headers(credentials, schema)

    # Whitespace-only token still creates a header (function doesn't strip)
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer    "


def test_create_auth_headers_basic_empty_credentials():
    """Test header creation with empty Basic auth credentials."""
    credentials = {"username": "", "password": ""}
    schema = BasicAuthSchema()

    headers = create_auth_headers(credentials, schema)

    # Empty credentials should result in no headers
    assert headers == {}


# =============================================================================
# 🔧 PARAMETER REMOVAL TESTS
# =============================================================================


def test_remove_auth_from_tool_args_bearer():
    """Test removal of Bearer auth parameters from tool arguments."""
    tool_args = {"data": "test", "auth_token": "token123", "other_param": "value"}
    schema = BearerAuthSchema()

    cleaned_args = remove_auth_from_tool_args(tool_args, schema)

    assert "auth_token" not in cleaned_args
    assert cleaned_args["data"] == "test"
    assert cleaned_args["other_param"] == "value"


def test_remove_auth_from_tool_args_basic():
    """Test removal of Basic auth parameters from tool arguments."""
    tool_args = {
        "data": "test",
        "username": "testuser",
        "password": "testpass",
        "other_param": "value",
    }
    schema = BasicAuthSchema()

    cleaned_args = remove_auth_from_tool_args(tool_args, schema)

    assert "username" not in cleaned_args
    assert "password" not in cleaned_args
    assert cleaned_args["data"] == "test"
    assert cleaned_args["other_param"] == "value"


def test_remove_auth_from_tool_args_with_none_schema():
    """Test removal with None schema returns original args."""
    tool_args = {"data": "test", "auth_token": "token123"}

    cleaned_args = remove_auth_from_tool_args(tool_args, None)

    assert cleaned_args == tool_args
    assert "auth_token" in cleaned_args


def test_remove_auth_from_tool_args_no_auth_fields():
    """Test removal when no auth fields are present."""
    tool_args = {"data": "test", "other_param": "value"}
    schema = BearerAuthSchema()

    cleaned_args = remove_auth_from_tool_args(tool_args, schema)

    assert cleaned_args == tool_args


def test_remove_auth_from_tool_args_empty_args():
    """Test removal with empty tool arguments."""
    tool_args = {}
    schema = BearerAuthSchema()

    cleaned_args = remove_auth_from_tool_args(tool_args, schema)

    assert cleaned_args == {}


def test_remove_auth_from_tool_args_preserves_original():
    """Test that removal doesn't modify the original tool_args."""
    original_args = {"data": "test", "auth_token": "token123"}
    tool_args = original_args.copy()
    schema = BearerAuthSchema()

    cleaned_args = remove_auth_from_tool_args(tool_args, schema)

    # Original should be unchanged
    assert tool_args == original_args
    assert "auth_token" in tool_args
    # Cleaned should not have auth fields
    assert "auth_token" not in cleaned_args
