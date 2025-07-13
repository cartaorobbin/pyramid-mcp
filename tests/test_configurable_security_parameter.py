"""Test configurable security parameter feature."""

from pyramid.config import Configurator

from pyramid_mcp import MCPConfiguration
from pyramid_mcp.core import PyramidMCP
from pyramid_mcp.introspection import PyramidIntrospector


def test_default_security_parameter():
    """Test that default security parameter is mcp_security."""
    config = MCPConfiguration()
    assert config.security_parameter == "mcp_security"


def test_custom_security_parameter_in_config():
    """Test setting custom security parameter in configuration."""
    config = MCPConfiguration(security_parameter="pcm_security")
    assert config.security_parameter == "pcm_security"


def test_extract_config_from_settings_default():
    """Test extracting configuration from settings with default security parameter."""
    from pyramid_mcp import _extract_mcp_config_from_settings

    settings = {
        "mcp.server_name": "test-server",
        "mcp.server_version": "1.0.0",
    }

    config = _extract_mcp_config_from_settings(settings)
    assert config.security_parameter == "mcp_security"


def test_extract_config_from_settings_custom():
    """Test extracting configuration from settings with custom security parameter."""
    from pyramid_mcp import _extract_mcp_config_from_settings

    settings = {
        "mcp.server_name": "test-server",
        "mcp.security_parameter": "pcm_security",
    }

    config = _extract_mcp_config_from_settings(settings)
    assert config.security_parameter == "pcm_security"


def test_introspector_uses_configurable_parameter(pyramid_config_with_routes):
    """Test that introspector uses configurable security parameter."""

    # Create a real MCP configuration with custom security parameter
    mcp_config = MCPConfiguration(
        security_parameter="pcm_security", route_discovery_enabled=True
    )

    # Create PyramidMCP instance and test through the real workflow
    pyramid_mcp = PyramidMCP(pyramid_config_with_routes, config=mcp_config)

    # Discover tools - this will set the security parameter in the introspector
    pyramid_mcp.discover_tools()

    # Check that the introspector gets the security parameter correctly
    assert pyramid_mcp.introspector._security_parameter == "pcm_security"


def test_convert_security_type_bearer_variations():
    """Test conversion of various bearer auth security types."""
    introspector = PyramidIntrospector()

    # Test different bearer auth variations
    variations = ["bearer", "BearerAuth", "Bearer", "BEARER", "bearer_auth", "jwt"]

    for variation in variations:
        result = introspector._convert_security_type_to_schema(variation)
        assert result is not None
        assert result.__class__.__name__ == "BearerAuthSchema"


def test_convert_security_type_basic_variations():
    """Test conversion of various basic auth security types."""
    introspector = PyramidIntrospector()

    # Test different basic auth variations
    variations = ["basic", "BasicAuth", "Basic", "BASIC", "basic_auth"]

    for variation in variations:
        result = introspector._convert_security_type_to_schema(variation)
        assert result is not None
        assert result.__class__.__name__ == "BasicAuthSchema"


def test_convert_security_type_unknown():
    """Test conversion of unknown security types."""
    introspector = PyramidIntrospector()

    # Test unknown security type
    result = introspector._convert_security_type_to_schema("unknown_auth")
    assert result is None


def test_end_to_end_with_custom_security_parameter():
    """Test end-to-end functionality with custom security parameter."""

    # Test that custom security parameter is stored correctly
    mcp_config = MCPConfiguration(security_parameter="pcm_security")
    assert mcp_config.security_parameter == "pcm_security"

    # Test that introspector can handle custom security parameter
    introspector = PyramidIntrospector()

    # Mock view_info with custom security parameter
    view_info = {"pcm_security": "BearerAuth"}

    # Set the security parameter in the introspector
    introspector._security_parameter = "pcm_security"

    # Test that it can extract the security type
    security_type = view_info.get(introspector._security_parameter)
    assert security_type == "BearerAuth"

    # Test that it can convert the security type
    security_schema = introspector._convert_security_type_to_schema(security_type)
    assert security_schema is not None
    assert security_schema.__class__.__name__ == "BearerAuthSchema"


def test_backward_compatibility_with_mcp_security():
    """Test that existing mcp_security parameter still works (backward compatibility)."""

    # Test that default configuration uses mcp_security
    config = MCPConfiguration()
    assert config.security_parameter == "mcp_security"

    # Test that introspector can handle mcp_security parameter
    introspector = PyramidIntrospector()

    # Test the security conversion works for traditional values
    bearer_result = introspector._convert_security_type_to_schema("bearer")
    assert bearer_result is not None
    assert bearer_result.__class__.__name__ == "BearerAuthSchema"


def test_multiple_views_with_different_security_parameters():
    """Test multiple views where some have security and some don't."""

    # Test that introspector can handle views with and without security
    introspector = PyramidIntrospector()
    introspector._security_parameter = "custom_security"

    # Test view with security
    view_with_security = {"custom_security": "BearerAuth"}
    security_type = view_with_security.get(introspector._security_parameter)
    assert security_type == "BearerAuth"

    # Test view without security
    view_without_security = {}
    security_type = view_without_security.get(introspector._security_parameter)
    assert security_type is None

    # Test that the security conversion works correctly
    auth_schema = introspector._convert_security_type_to_schema("BearerAuth")
    assert auth_schema is not None
    assert auth_schema.__class__.__name__ == "BearerAuthSchema"


def test_plugin_includeme_with_custom_security_parameter():
    """Test that includeme works with custom security parameter setting."""
    from pyramid_mcp import includeme

    # Create configurator with custom security parameter
    config = Configurator(
        settings={
            "mcp.security_parameter": "api_auth",
            "mcp.server_name": "test-server",
        }
    )

    # Include pyramid-mcp
    includeme(config)

    # Check that the PyramidMCP instance was created with correct config
    pyramid_mcp = config.registry.pyramid_mcp  # type: ignore
    assert pyramid_mcp.config.security_parameter == "api_auth"
    assert pyramid_mcp.config.server_name == "test-server"


def test_empty_security_parameter():
    """Test behavior with empty security parameter."""
    # Should accept empty string as configuration
    config = MCPConfiguration(security_parameter="")
    assert config.security_parameter == ""


def test_none_security_parameter():
    """Test behavior with None security parameter."""
    # MCPConfiguration should have default value
    config = MCPConfiguration()
    assert config.security_parameter == "mcp_security"


def test_case_sensitivity_in_security_types():
    """Test that security type matching is case-insensitive."""
    introspector = PyramidIntrospector()

    # Test various case combinations
    test_cases = [
        ("bearer", "BearerAuthSchema"),
        ("BEARER", "BearerAuthSchema"),
        ("BearerAuth", "BearerAuthSchema"),
        ("bearerauth", "BearerAuthSchema"),
        ("basic", "BasicAuthSchema"),
        ("BASIC", "BasicAuthSchema"),
        ("BasicAuth", "BasicAuthSchema"),
        ("basicauth", "BasicAuthSchema"),
    ]

    for input_type, expected_schema in test_cases:
        result = introspector._convert_security_type_to_schema(input_type)
        assert result is not None
        assert result.__class__.__name__ == expected_schema


def test_special_characters_in_security_parameter():
    """Test security parameter with special characters."""
    # This should work as long as it's a valid Python identifier
    config = MCPConfiguration(security_parameter="mcp_security_v2")
    assert config.security_parameter == "mcp_security_v2"

    # Test with settings extraction
    from pyramid_mcp import _extract_mcp_config_from_settings

    settings = {
        "mcp.security_parameter": "custom_security_param_123",
    }

    config = _extract_mcp_config_from_settings(settings)
    assert config.security_parameter == "custom_security_param_123"
