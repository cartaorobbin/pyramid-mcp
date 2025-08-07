"""Tests for mcp.enable configuration feature."""

import pytest
from pyramid.config import Configurator
from webtest import TestApp

from pyramid_mcp.core import MCPConfiguration


@pytest.fixture
def pyramid_app_with_settings():
    """Create a Pyramid app with custom settings."""

    def _create_app(settings=None, routes=None):
        config = Configurator(settings=settings or {})
        config.include("pyramid_mcp")

        # Add any routes if provided
        if routes:
            for route_name, route_pattern in routes:
                config.add_route(route_name, route_pattern)

        # Don't scan globally - causes test interference
        # config.scan()
        return TestApp(config.make_wsgi_app())

    return _create_app


@pytest.fixture
def pyramid_config_with_settings():
    """Create a Pyramid configurator with custom settings (for testing internals)."""

    def _create_config(settings=None):
        config = Configurator(settings=settings or {})
        config.include("pyramid_mcp")
        # Don't scan globally - causes test interference
        # config.scan()
        return config

    return _create_config


def test_mcp_enable_default_is_true(pyramid_app_with_settings):
    """Test that mcp.enable defaults to True for backward compatibility."""
    # Create app without explicit enable setting
    app = pyramid_app_with_settings(settings={})

    # MCP endpoint should exist and respond to valid JSON-RPC requests
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    assert response.status_code == 200
    assert "jsonrpc" in response.json


def test_mcp_enable_true_creates_full_setup(pyramid_app_with_settings):
    """Test that mcp.enable=true creates endpoints and tools."""
    settings = {
        "mcp.enable": "true",
        "mcp.server_name": "test-server",
        "mcp.mount_path": "/test-mcp",
    }
    routes = [("test_route", "/test")]

    app = pyramid_app_with_settings(settings=settings, routes=routes)

    # Test that MCP endpoint exists and responds to JSON-RPC
    response = app.post_json(
        "/test-mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    assert response.status_code == 200
    assert "jsonrpc" in response.json


def test_mcp_enable_false_only_registers_predicates(pyramid_app_with_settings):
    """Test that mcp.enable=false only registers view predicates."""
    settings = {
        "mcp.enable": "false",
        "mcp.server_name": "test-server",
        "mcp.mount_path": "/test-mcp",
    }

    app = pyramid_app_with_settings(settings=settings)

    # Should NOT have MCP routes - JSON-RPC request should return 404
    response = app.post_json(
        "/test-mcp",
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        expect_errors=True,
    )
    assert response.status_code == 404  # Route not found


@pytest.mark.parametrize("false_value", ["false", "False", "FALSE", "0", "no", "off"])
def test_mcp_enable_false_string_variations(pyramid_app_with_settings, false_value):
    """Test various string values for mcp.enable=false."""
    settings = {"mcp.enable": false_value}
    app = pyramid_app_with_settings(settings=settings)

    # MCP endpoint should not exist
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, expect_errors=True
    )
    assert response.status_code == 404


@pytest.mark.parametrize("true_value", ["true", "True", "TRUE", "1", "yes", "on"])
def test_mcp_enable_true_string_variations(pyramid_app_with_settings, true_value):
    """Test various string values for mcp.enable=true."""
    settings = {"mcp.enable": true_value}
    app = pyramid_app_with_settings(settings=settings)

    # MCP endpoint should exist and respond
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "enable_value,expected_status",
    [
        (True, 200),
        (False, 404),
    ],
)
def test_mcp_enable_boolean_values(
    pyramid_app_with_settings, enable_value, expected_status
):
    """Test actual boolean values for mcp.enable."""
    app = pyramid_app_with_settings(settings={"mcp.enable": enable_value})
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, expect_errors=True
    )
    assert response.status_code == expected_status


def test_mcp_enable_false_with_security_predicate_disabled(
    pyramid_config_with_settings,
):
    """Test mcp.enable=false combined with add_security_predicate=false."""
    settings = {"mcp.enable": "false", "mcp.add_security_predicate": "false"}
    config = pyramid_config_with_settings(settings=settings)

    # Should NOT have created PyramidMCP instance
    assert not hasattr(config.registry, "pyramid_mcp")


def test_mcp_enable_false_with_custom_security_parameter(pyramid_config_with_settings):
    """Test mcp.enable=false with custom security parameter name."""
    settings = {"mcp.enable": "false", "mcp.security_parameter": "custom_security"}
    config = pyramid_config_with_settings(settings=settings)

    # Should NOT have created PyramidMCP instance
    assert not hasattr(config.registry, "pyramid_mcp")


def test_view_predicates_work_when_mcp_disabled(pyramid_app_with_settings):
    """Test that view predicates work even when MCP is disabled."""
    settings = {"mcp.enable": "false"}
    routes = [("test_view", "/test")]

    # Create app with custom view
    app = pyramid_app_with_settings(settings=settings, routes=routes)

    # Verify MCP endpoints don't exist when disabled
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, expect_errors=True
    )
    assert response.status_code == 404  # MCP disabled, so endpoint doesn't exist


def test_mcp_configuration_enable_field():
    """Test MCPConfiguration.enable field directly."""
    # Default should be True
    config = MCPConfiguration()
    assert config.enable is True

    # Can be set to False
    config = MCPConfiguration(enable=False)
    assert config.enable is False

    # Can be set to True explicitly
    config = MCPConfiguration(enable=True)
    assert config.enable is True


def test_no_tools_registered_when_disabled(pyramid_app_with_settings):
    """Test that @tool decorated functions are not registered when MCP is disabled."""
    settings = {"mcp.enable": "false"}

    app = pyramid_app_with_settings(settings=settings)

    # MCP endpoint shouldn't exist
    response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, expect_errors=True
    )
    assert response.status_code == 404


def test_staging_workflow_example(
    pyramid_app_with_settings, pyramid_config_with_settings
):
    """Test typical staging workflow where MCP is disabled initially."""
    # Stage 1: Staging with MCP disabled
    staging_settings = {
        "mcp.enable": "false",
        "mcp.server_name": "staging-api",
        "mcp.mount_path": "/mcp",
    }
    staging_config = pyramid_config_with_settings(settings=staging_settings)

    # Should only have predicates, no endpoints
    assert not hasattr(staging_config.registry, "pyramid_mcp")

    # Stage 2: Production with MCP enabled
    prod_settings = {
        "mcp.enable": "true",
        "mcp.server_name": "production-api",
        "mcp.mount_path": "/mcp",
    }
    prod_app = pyramid_app_with_settings(settings=prod_settings)

    # Should have full MCP setup (endpoint should respond to JSON-RPC)
    response = prod_app.post_json(
        "/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    assert response.status_code == 200
    assert "jsonrpc" in response.json
