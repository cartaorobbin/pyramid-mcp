"""
Tests for MCP Security Authentication Parameters feature.

This module tests the authentication parameter functionality including:
- BearerAuthSchema and BasicAuthSchema validation
- Tool security parameter integration
- Authentication credential extraction and validation
- HTTP header generation from credentials
- Error handling for authentication failures
"""

import pytest
from marshmallow import ValidationError

from pyramid_mcp.security import (
    BasicAuthSchema,
    BearerAuthSchema,
    create_auth_headers,
    extract_auth_credentials,
    merge_auth_into_schema,
    remove_auth_from_tool_args,
    validate_auth_credentials,
)

# =============================================================================
# 🔧 FIXTURES
# =============================================================================


@pytest.fixture
def bearer_auth_schema():
    """Bearer authentication schema fixture."""
    return BearerAuthSchema()


@pytest.fixture
def basic_auth_schema():
    """Basic authentication schema fixture."""
    return BasicAuthSchema()


@pytest.fixture
def valid_bearer_args():
    """Valid tool arguments with Bearer token."""
    return {"data": "test_data", "auth_token": "abc123"}


@pytest.fixture
def valid_basic_args():
    """Valid tool arguments with Basic auth credentials."""
    return {"data": "test_data", "username": "testuser", "password": "testpass"}


@pytest.fixture
def missing_bearer_args():
    """Tool arguments missing Bearer token."""
    return {"data": "test_data"}


@pytest.fixture
def empty_bearer_args():
    """Tool arguments with empty Bearer token."""
    return {"data": "test_data", "auth_token": ""}


@pytest.fixture
def missing_basic_username_args():
    """Tool arguments missing username for Basic auth."""
    return {"data": "test_data", "password": "testpass"}


@pytest.fixture
def empty_basic_password_args():
    """Tool arguments with empty password for Basic auth."""
    return {"data": "test_data", "username": "testuser", "password": ""}


@pytest.fixture
def pyramid_mcp_with_auth_tool(pyramid_config_with_routes):
    """PyramidMCP instance with authentication-enabled tools."""
    from pyramid_mcp.core import MCPConfiguration, PyramidMCP

    config = MCPConfiguration()
    pyramid_mcp = PyramidMCP(pyramid_config_with_routes, config=config)

    @pyramid_mcp.tool(
        name="secure_bearer_tool",
        description="Tool requiring Bearer authentication",
        security=BearerAuthSchema(),
    )
    def secure_bearer_tool(pyramid_request, data: str) -> dict:
        headers = getattr(pyramid_request, "mcp_auth_headers", {})
        return {"data": data, "auth_headers": headers}

    @pyramid_mcp.tool(
        name="secure_basic_tool",
        description="Tool requiring Basic authentication",
        security=BasicAuthSchema(),
    )
    def secure_basic_tool(pyramid_request, data: str) -> dict:
        headers = getattr(pyramid_request, "mcp_auth_headers", {})
        return {"data": data, "auth_headers": headers}

    @pyramid_mcp.tool(name="public_tool", description="Tool without authentication")
    def public_tool(data: str) -> dict:
        return {"data": data}

    return pyramid_mcp


# =============================================================================
# 🧪 SCHEMA VALIDATION TESTS
# =============================================================================


def test_bearer_auth_schema_validates_valid_token(bearer_auth_schema):
    """BearerAuthSchema should validate valid token."""
    data = {"auth_token": "valid_token_123"}
    result = bearer_auth_schema.load(data)
    assert result == data


def test_bearer_auth_schema_rejects_missing_token(bearer_auth_schema):
    """BearerAuthSchema should reject missing auth_token."""
    data = {}
    with pytest.raises(ValidationError):
        bearer_auth_schema.load(data)


def test_bearer_auth_schema_rejects_empty_token(bearer_auth_schema):
    """BearerAuthSchema should reject empty auth_token."""
    data = {"auth_token": ""}
    with pytest.raises(ValidationError):
        bearer_auth_schema.load(data)


def test_basic_auth_schema_validates_valid_credentials(basic_auth_schema):
    """BasicAuthSchema should validate valid username and password."""
    data = {"username": "testuser", "password": "testpass"}
    result = basic_auth_schema.load(data)
    assert result == data


def test_basic_auth_schema_rejects_missing_username(basic_auth_schema):
    """BasicAuthSchema should reject missing username."""
    data = {"password": "testpass"}
    with pytest.raises(ValidationError):
        basic_auth_schema.load(data)


def test_basic_auth_schema_rejects_missing_password(basic_auth_schema):
    """BasicAuthSchema should reject missing password."""
    data = {"username": "testuser"}
    with pytest.raises(ValidationError):
        basic_auth_schema.load(data)


def test_basic_auth_schema_rejects_empty_username(basic_auth_schema):
    """BasicAuthSchema should reject empty username."""
    data = {"username": "", "password": "testpass"}
    with pytest.raises(ValidationError):
        basic_auth_schema.load(data)


def test_basic_auth_schema_rejects_empty_password(basic_auth_schema):
    """BasicAuthSchema should reject empty password."""
    data = {"username": "testuser", "password": ""}
    with pytest.raises(ValidationError):
        basic_auth_schema.load(data)


# =============================================================================
# 🔗 SCHEMA MERGING TESTS
# =============================================================================


def test_merge_auth_into_schema_with_bearer_auth(bearer_auth_schema):
    """merge_auth_into_schema should add Bearer auth parameters."""
    base_schema = {
        "type": "object",
        "properties": {"data": {"type": "string"}},
        "required": ["data"],
    }

    result = merge_auth_into_schema(base_schema, bearer_auth_schema)

    assert "auth_token" in result["properties"]
    assert result["properties"]["auth_token"]["type"] == "string"
    assert "auth_token" in result["required"]
    assert "data" in result["required"]


def test_merge_auth_into_schema_with_basic_auth(basic_auth_schema):
    """merge_auth_into_schema should add Basic auth parameters."""
    base_schema = {
        "type": "object",
        "properties": {"data": {"type": "string"}},
        "required": ["data"],
    }

    result = merge_auth_into_schema(base_schema, basic_auth_schema)

    assert "username" in result["properties"]
    assert "password" in result["properties"]
    assert "username" in result["required"]
    assert "password" in result["required"]
    assert "data" in result["required"]


def test_merge_auth_into_schema_with_none_security():
    """merge_auth_into_schema should return base schema when security is None."""
    base_schema = {
        "type": "object",
        "properties": {"data": {"type": "string"}},
        "required": ["data"],
    }

    result = merge_auth_into_schema(base_schema, None)

    assert result == base_schema


def test_merge_auth_into_schema_with_none_base_schema(bearer_auth_schema):
    """merge_auth_into_schema should create schema when base is None."""
    result = merge_auth_into_schema(None, bearer_auth_schema)

    assert result["type"] == "object"
    assert "auth_token" in result["properties"]
    assert "auth_token" in result["required"]


# =============================================================================
# 🔍 CREDENTIAL EXTRACTION TESTS
# =============================================================================


def test_extract_auth_credentials_bearer_success(bearer_auth_schema, valid_bearer_args):
    """extract_auth_credentials should extract Bearer token."""
    result = extract_auth_credentials(valid_bearer_args, bearer_auth_schema)

    assert result == {"bearer_token": "abc123"}


def test_extract_auth_credentials_basic_success(basic_auth_schema, valid_basic_args):
    """extract_auth_credentials should extract Basic auth credentials."""
    result = extract_auth_credentials(valid_basic_args, basic_auth_schema)

    assert result == {"username": "testuser", "password": "testpass"}


def test_extract_auth_credentials_with_none_security(valid_bearer_args):
    """extract_auth_credentials should return empty dict when security is None."""
    result = extract_auth_credentials(valid_bearer_args, None)

    assert result == {}


def test_extract_auth_credentials_missing_bearer_token(
    bearer_auth_schema, missing_bearer_args
):
    """extract_auth_credentials should return empty dict when Bearer token missing."""
    result = extract_auth_credentials(missing_bearer_args, bearer_auth_schema)

    assert result == {}


def test_extract_auth_credentials_missing_basic_username(
    basic_auth_schema, missing_basic_username_args
):
    """extract_auth_credentials should return empty dict when username missing."""
    result = extract_auth_credentials(missing_basic_username_args, basic_auth_schema)

    assert result == {}


# =============================================================================
# 🧹 PARAMETER REMOVAL TESTS
# =============================================================================


def test_remove_auth_from_tool_args_bearer(bearer_auth_schema, valid_bearer_args):
    """remove_auth_from_tool_args should remove Bearer auth parameters."""
    result = remove_auth_from_tool_args(valid_bearer_args, bearer_auth_schema)

    assert result == {"data": "test_data"}
    assert "auth_token" not in result


def test_remove_auth_from_tool_args_basic(basic_auth_schema, valid_basic_args):
    """remove_auth_from_tool_args should remove Basic auth parameters."""
    result = remove_auth_from_tool_args(valid_basic_args, basic_auth_schema)

    assert result == {"data": "test_data"}
    assert "username" not in result
    assert "password" not in result


def test_remove_auth_from_tool_args_with_none_security(valid_bearer_args):
    """remove_auth_from_tool_args should return original args when security is None."""
    result = remove_auth_from_tool_args(valid_bearer_args, None)

    assert result == valid_bearer_args


def test_remove_auth_from_tool_args_does_not_modify_original(
    bearer_auth_schema, valid_bearer_args
):
    """remove_auth_from_tool_args should not modify original arguments."""
    original_args = valid_bearer_args.copy()
    remove_auth_from_tool_args(valid_bearer_args, bearer_auth_schema)

    assert valid_bearer_args == original_args


# =============================================================================
# 🔐 HEADER CREATION TESTS
# =============================================================================


def test_create_auth_headers_bearer_success(bearer_auth_schema):
    """create_auth_headers should create Bearer authorization header."""
    credentials = {"bearer_token": "abc123"}
    result = create_auth_headers(credentials, bearer_auth_schema)

    assert result == {"Authorization": "Bearer abc123"}


def test_create_auth_headers_basic_success(basic_auth_schema):
    """create_auth_headers should create Basic authorization header."""
    credentials = {"username": "testuser", "password": "testpass"}
    result = create_auth_headers(credentials, basic_auth_schema)

    # Basic auth should be base64 encoded
    import base64

    expected_encoded = base64.b64encode(b"testuser:testpass").decode()
    expected_header = f"Basic {expected_encoded}"

    assert result == {"Authorization": expected_header}


def test_create_auth_headers_with_none_security():
    """create_auth_headers should return empty dict when security is None."""
    credentials = {"bearer_token": "abc123"}
    result = create_auth_headers(credentials, None)

    assert result == {}


def test_create_auth_headers_with_empty_credentials(bearer_auth_schema):
    """create_auth_headers should return empty dict when credentials are empty."""
    result = create_auth_headers({}, bearer_auth_schema)

    assert result == {}


def test_create_auth_headers_bearer_missing_token(bearer_auth_schema):
    """create_auth_headers should return empty dict when Bearer token missing."""
    credentials = {"some_other_field": "value"}
    result = create_auth_headers(credentials, bearer_auth_schema)

    assert result == {}


# =============================================================================
# ✅ VALIDATION TESTS
# =============================================================================


def test_validate_auth_credentials_bearer_success(
    bearer_auth_schema, valid_bearer_args
):
    """validate_auth_credentials should return None for valid Bearer credentials."""
    result = validate_auth_credentials(valid_bearer_args, bearer_auth_schema)

    assert result is None


def test_validate_auth_credentials_basic_success(basic_auth_schema, valid_basic_args):
    """validate_auth_credentials should return None for valid Basic credentials."""
    result = validate_auth_credentials(valid_basic_args, basic_auth_schema)

    assert result is None


def test_validate_auth_credentials_with_none_security(valid_bearer_args):
    """validate_auth_credentials should return None when security is None."""
    result = validate_auth_credentials(valid_bearer_args, None)

    assert result is None


def test_validate_auth_credentials_missing_bearer_token(
    bearer_auth_schema, missing_bearer_args
):
    """validate_auth_credentials should return error for missing Bearer token."""
    result = validate_auth_credentials(missing_bearer_args, bearer_auth_schema)

    assert result is not None
    assert result["type"] == "missing_credentials"
    assert "auth_token" in result["details"]["missing_fields"]


def test_validate_auth_credentials_empty_bearer_token(
    bearer_auth_schema, empty_bearer_args
):
    """validate_auth_credentials should return error for empty Bearer token."""
    result = validate_auth_credentials(empty_bearer_args, bearer_auth_schema)

    assert result is not None
    assert result["type"] == "empty_credentials"
    assert "auth_token" in result["details"]["empty_fields"]


def test_validate_auth_credentials_missing_basic_username(
    basic_auth_schema, missing_basic_username_args
):
    """validate_auth_credentials should return error for missing username."""
    result = validate_auth_credentials(missing_basic_username_args, basic_auth_schema)

    assert result is not None
    assert result["type"] == "missing_credentials"
    assert "username" in result["details"]["missing_fields"]


def test_validate_auth_credentials_empty_basic_password(
    basic_auth_schema, empty_basic_password_args
):
    """validate_auth_credentials should return error for empty password."""
    result = validate_auth_credentials(empty_basic_password_args, basic_auth_schema)

    assert result is not None
    assert result["type"] == "empty_credentials"
    assert "password" in result["details"]["empty_fields"]


# =============================================================================
# 🛠️ TOOL INTEGRATION TESTS
# =============================================================================


def test_tool_with_bearer_auth_schema_includes_auth_in_input_schema(
    pyramid_mcp_with_auth_tool,
):
    """Tool with Bearer auth should include auth_token in input schema."""
    tools = pyramid_mcp_with_auth_tool.get_tools()
    bearer_tool = next(tool for tool in tools if "secure_bearer_tool" in tool["name"])

    input_schema = bearer_tool["inputSchema"]
    assert "auth_token" in input_schema["properties"]
    assert "auth_token" in input_schema["required"]


def test_tool_with_basic_auth_schema_includes_auth_in_input_schema(
    pyramid_mcp_with_auth_tool,
):
    """Tool with Basic auth should include username and password in input schema."""
    tools = pyramid_mcp_with_auth_tool.get_tools()
    basic_tool = next(tool for tool in tools if "secure_basic_tool" in tool["name"])

    input_schema = basic_tool["inputSchema"]
    assert "username" in input_schema["properties"]
    assert "password" in input_schema["properties"]
    assert "username" in input_schema["required"]
    assert "password" in input_schema["required"]


def test_tool_without_auth_schema_excludes_auth_from_input_schema(
    pyramid_mcp_with_auth_tool,
):
    """Tool without auth should not include auth parameters in input schema."""
    tools = pyramid_mcp_with_auth_tool.get_tools()
    public_tool = next(tool for tool in tools if "public_tool" in tool["name"])

    input_schema = public_tool["inputSchema"]
    assert "auth_token" not in input_schema["properties"]
    assert "username" not in input_schema["properties"]
    assert "password" not in input_schema["properties"]


# =============================================================================
# 🔄 PROTOCOL HANDLER INTEGRATION TESTS
# =============================================================================


def test_protocol_handler_validates_bearer_auth_successfully(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should validate Bearer auth and execute tool successfully."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_bearer_tool",
            "arguments": {"data": "test_data", "auth_token": "valid_token_123"},
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" not in response
    assert "result" in response
    assert response["result"]["content"][0]["text"]


def test_protocol_handler_rejects_missing_bearer_token(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should reject request with missing Bearer token."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_bearer_tool",
            "arguments": {
                "data": "test_data"
                # Missing auth_token
            },
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" in response
    assert response["error"]["code"] == -32602  # INVALID_PARAMS
    assert "missing" in response["error"]["message"].lower()


def test_protocol_handler_rejects_empty_bearer_token(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should reject request with empty Bearer token."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_bearer_tool",
            "arguments": {"data": "test_data", "auth_token": ""},
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" in response
    assert response["error"]["code"] == -32602  # INVALID_PARAMS
    assert "empty" in response["error"]["message"].lower()


def test_protocol_handler_validates_basic_auth_successfully(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should validate Basic auth and execute tool successfully."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_basic_tool",
            "arguments": {
                "data": "test_data",
                "username": "testuser",
                "password": "testpass",
            },
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" not in response
    assert "result" in response
    assert response["result"]["content"][0]["text"]


def test_protocol_handler_rejects_missing_basic_username(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should reject request with missing username."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_basic_tool",
            "arguments": {
                "data": "test_data",
                "password": "testpass"
                # Missing username
            },
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" in response
    assert response["error"]["code"] == -32602  # INVALID_PARAMS
    assert "missing" in response["error"]["message"].lower()


def test_protocol_handler_allows_public_tool_without_auth(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should allow public tool without authentication."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "public_tool", "arguments": {"data": "test_data"}},
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" not in response
    assert "result" in response
    assert response["result"]["content"][0]["text"]


def test_protocol_handler_provides_auth_headers_to_tool(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should provide auth headers to tool via pyramid_request."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_bearer_tool",
            "arguments": {"data": "test_data", "auth_token": "test_token_456"},
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" not in response
    # Check that the tool received auth headers
    result_text = response["result"]["content"][0]["text"]
    assert "Bearer test_token_456" in result_text


def test_protocol_handler_removes_auth_params_from_tool_args(
    pyramid_mcp_with_auth_tool, dummy_request
):
    """Protocol handler should remove auth parameters before calling tool."""
    protocol_handler = pyramid_mcp_with_auth_tool.protocol_handler

    request_data = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "secure_bearer_tool",
            "arguments": {"data": "test_data", "auth_token": "test_token_789"},
        },
    }

    response = protocol_handler.handle_message(request_data, dummy_request)

    assert "error" not in response
    # Check that auth_token was not passed to the tool
    result_text = response["result"]["content"][0]["text"]
    assert "auth_token" not in result_text
    assert "test_data" in result_text
