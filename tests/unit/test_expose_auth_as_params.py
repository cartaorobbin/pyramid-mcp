"""
Tests for the expose_auth_as_params configuration option.

This module tests that the new mcp.expose_auth_as_params configuration
properly controls whether authentication parameters are exposed in tool schemas.
"""

import pytest

from pyramid_mcp import _extract_mcp_config_from_settings
from pyramid_mcp.core import MCPConfiguration
from pyramid_mcp.protocol import MCPTool
from pyramid_mcp.security import BasicAuthSchema, BearerAuthSchema


def test_mcp_configuration_default_expose_auth_as_params():
    """Test that MCPConfiguration defaults expose_auth_as_params to True."""
    config = MCPConfiguration()
    assert config.expose_auth_as_params is True


def test_mcp_configuration_custom_expose_auth_as_params():
    """Test that MCPConfiguration accepts custom expose_auth_as_params value."""
    config = MCPConfiguration(expose_auth_as_params=False)
    assert config.expose_auth_as_params is False


@pytest.mark.parametrize(
    "expose_auth,security_schema,expected_fields",
    [
        # Bearer auth with expose=True should include auth_token
        (True, BearerAuthSchema(), ["auth_token"]),
        # Bearer auth with expose=False should not include auth_token
        (False, BearerAuthSchema(), []),
        # Basic auth with expose=True should include username and password
        (True, BasicAuthSchema(), ["username", "password"]),
        # Basic auth with expose=False should not include username and password
        (False, BasicAuthSchema(), []),
    ],
)
def test_mcp_tool_auth_param_exposure(expose_auth, security_schema, expected_fields):
    """Test MCPTool.to_dict() with different auth schemas and expose settings."""
    config = MCPConfiguration(expose_auth_as_params=expose_auth)

    tool = MCPTool(
        name="test_tool",
        description="Test tool with auth",
        security=security_schema,
        config=config,
    )

    tool_dict = tool.to_dict()

    # Verify schema structure
    assert "inputSchema" in tool_dict
    schema = tool_dict["inputSchema"]
    assert "properties" in schema
    assert "required" in schema

    # Check expected fields presence/absence
    for field in expected_fields:
        assert field in schema["properties"], f"Expected field '{field}' in properties"
        assert field in schema["required"], f"Expected field '{field}' in required"

    # Check that no unexpected auth fields are present
    auth_fields = ["auth_token", "username", "password"]
    unexpected_fields = set(auth_fields) - set(expected_fields)
    for field in unexpected_fields:
        assert (
            field not in schema["properties"]
        ), f"Unexpected field '{field}' in properties"
        assert (
            field not in schema["required"]
        ), f"Unexpected field '{field}' in required"


def test_mcp_tool_no_security_expose_setting_irrelevant():
    """Test that expose_auth_as_params setting doesn't affect tools without security."""
    config_true = MCPConfiguration(expose_auth_as_params=True)
    config_false = MCPConfiguration(expose_auth_as_params=False)

    tool_true = MCPTool(
        name="test_tool", description="Test tool without auth", config=config_true
    )

    tool_false = MCPTool(
        name="test_tool", description="Test tool without auth", config=config_false
    )

    dict_true = tool_true.to_dict()
    dict_false = tool_false.to_dict()

    # Both should produce identical schemas when no security is specified
    assert dict_true["inputSchema"] == dict_false["inputSchema"]

    # Neither should have auth parameters
    schema = dict_true["inputSchema"]
    assert "auth_token" not in schema["properties"]
    assert "username" not in schema["properties"]
    assert "password" not in schema["properties"]


def test_mcp_tool_default_config_creation():
    """Test that MCPTool creates default config when none provided."""
    tool = MCPTool(name="test_tool", description="Test tool")

    # Should have created a default config
    assert tool.config is not None
    assert tool.config.expose_auth_as_params is True


@pytest.mark.parametrize(
    "expose_auth,should_include_auth",
    [
        (True, True),
        (False, False),
    ],
)
def test_mcp_tool_existing_schema_with_auth(expose_auth, should_include_auth):
    """Test auth params merged/not merged with existing schema based on expose."""
    config = MCPConfiguration(expose_auth_as_params=expose_auth)
    security = BearerAuthSchema()

    existing_schema = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "Search query"}},
        "required": ["query"],
    }

    tool = MCPTool(
        name="test_tool",
        description="Test tool with existing schema",
        input_schema=existing_schema,
        security=security,
        config=config,
    )

    tool_dict = tool.to_dict()
    schema = tool_dict["inputSchema"]

    # Should always have original parameters
    assert "query" in schema["properties"]
    assert "query" in schema["required"]

    # Auth parameters should be present/absent based on setting
    if should_include_auth:
        assert "auth_token" in schema["properties"]
        assert "auth_token" in schema["required"]
    else:
        assert "auth_token" not in schema["properties"]
        assert "auth_token" not in schema["required"]


@pytest.mark.parametrize(
    "settings,expected",
    [
        # Default when no setting provided
        ({}, True),
        # Explicit true setting
        ({"mcp.expose_auth_as_params": "true"}, True),
        # Explicit false setting
        ({"mcp.expose_auth_as_params": "false"}, False),
    ],
)
def test_settings_parsing_expose_auth_as_params_basic(settings, expected):
    """Test basic settings parsing for expose_auth_as_params."""
    config = _extract_mcp_config_from_settings(settings)
    assert config.expose_auth_as_params is expected


@pytest.mark.parametrize(
    "setting_value,expected",
    [
        # Values that should evaluate to True (according to _parse_bool_setting)
        ("true", True),
        ("True", True),  # Gets lowercased to "true"
        ("TRUE", True),  # Gets lowercased to "true"
        ("1", True),
        ("yes", True),
        ("YES", True),  # Gets lowercased to "yes"
        ("on", True),
        ("ON", True),  # Gets lowercased to "on"
        # Values that should evaluate to False
        ("false", False),
        ("False", False),  # Gets lowercased to "false"
        ("FALSE", False),  # Gets lowercased to "false"
        ("0", False),
        ("no", False),
        ("NO", False),  # Gets lowercased to "no"
        ("off", False),
        ("OFF", False),  # Gets lowercased to "off"
        ("disabled", False),  # Not in allowed list
        ("enabled", False),  # Not in allowed list
        ("random", False),  # Not in allowed list
    ],
)
def test_settings_parsing_expose_auth_as_params_values(setting_value, expected):
    """Test that settings parsing handles various string values correctly."""
    settings = {"mcp.expose_auth_as_params": setting_value}
    config = _extract_mcp_config_from_settings(settings)
    assert config.expose_auth_as_params is expected
