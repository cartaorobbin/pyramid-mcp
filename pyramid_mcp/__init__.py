"""
Pyramid MCP - Expose Pyramid web application endpoints as MCP tools.

A library inspired by fastapi_mcp but designed specifically for the Pyramid
web framework, providing seamless integration between Pyramid applications
and the Model Context Protocol.

Usage as a Pyramid plugin:
    config.include('pyramid_mcp')

Or with settings:
    config.include('pyramid_mcp', mcp_settings={
        'mcp.server_name': 'my-api',
        'mcp.server_version': '1.0.0',
        'mcp.mount_path': '/mcp',
        'mcp.enable_sse': True,
        'mcp.enable_http': True
    })

Registering tools:
    @tool(name="calculate", description="Calculate math operations")
    def calculate(operation: str, a: float, b: float) -> float:
        # Tool implementation
        pass
"""

from typing import Any, Callable, List, Optional, Type

from marshmallow import Schema
from pyramid.config import Configurator
from pyramid.threadlocal import get_current_registry

from pyramid_mcp.core import MCPConfiguration, PyramidMCP
from pyramid_mcp.version import __version__

__all__ = ["PyramidMCP", "MCPConfiguration", "__version__", "includeme", "tool"]


def includeme(config: Configurator) -> None:
    """
    Pyramid plugin entry point - include pyramid_mcp in your Pyramid application.

    This function configures the MCP server and mounts it to your Pyramid application.

    Args:
        config: Pyramid configurator instance

    Usage:
        # Basic usage
        config.include('pyramid_mcp')

        # With custom settings
        config.include('pyramid_mcp')
        config.registry.settings.update({
            'mcp.server_name': 'my-api',
            'mcp.mount_path': '/mcp'
        })

        # Or include with settings directly
        config.include('pyramid_mcp', mcp_settings={
            'mcp.server_name': 'my-api',
            'mcp.server_version': '1.0.0'
        })
    """
    settings = config.registry.settings

    # Extract MCP settings from pyramid settings
    mcp_config = _extract_mcp_config_from_settings(settings)

    # Create PyramidMCP instance
    pyramid_mcp = PyramidMCP(config, config=mcp_config)

    # Store the instance in registry for access by application code
    config.registry.pyramid_mcp = pyramid_mcp

    # Store registry for tool decorator in testing scenarios
    _tool_registry_storage.registry = config.registry

    # Auto-mount MCP endpoints
    pyramid_mcp.mount()

    # Add a directive to access pyramid_mcp from configurator
    config.add_directive("get_mcp", _get_mcp_directive)

    # Add request method to access MCP tools
    config.add_request_method(_get_mcp_from_request, "mcp", reify=True)

    # Register a post-configure hook to register any pending tools
    config.action(
        "pyramid_mcp.register_pending_tools", _register_pending_tools, args=(config,)
    )


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    schema: Optional[Type[Schema]] = None,
) -> Callable:
    """
    Decorator to register a function as an MCP tool using the current Pyramid registry.

    This decorator can be used after including pyramid_mcp in your Pyramid application.
    It will automatically register the decorated function with the MCP server.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        schema: Marshmallow schema for input validation

    Returns:
        Decorated function

    Example:
        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__

        # Store the tool configuration on the function for later registration
        func._mcp_tool_config = {
            "name": tool_name,
            "description": tool_description,
            "schema": schema,
        }

        # Try to register immediately if registry is available
        registry = get_current_registry()
        if registry is not None:
            pyramid_mcp = getattr(registry, "pyramid_mcp", None)
            if pyramid_mcp:
                pyramid_mcp.tool(name, description, schema)(func)
        else:
            # Check if we have a stored registry for testing
            stored_registry = getattr(_tool_registry_storage, "registry", None)
            if stored_registry:
                pyramid_mcp = getattr(stored_registry, "pyramid_mcp", None)
                if pyramid_mcp:
                    pyramid_mcp.tool(name, description, schema)(func)

        return func

    return decorator


class _ToolRegistryStorage:
    """Helper class to store registry for tool registration in testing."""

    registry = None


_tool_registry_storage = _ToolRegistryStorage()


def _extract_mcp_config_from_settings(settings: dict) -> MCPConfiguration:
    """Extract MCP configuration from Pyramid settings."""
    return MCPConfiguration(
        server_name=settings.get("mcp.server_name", "pyramid-mcp"),
        server_version=settings.get("mcp.server_version", "1.0.0"),
        mount_path=settings.get("mcp.mount_path", "/mcp"),
        include_patterns=_parse_list_setting(settings.get("mcp.include_patterns")),
        exclude_patterns=_parse_list_setting(settings.get("mcp.exclude_patterns")),
        enable_sse=_parse_bool_setting(settings.get("mcp.enable_sse", "true")),
        enable_http=_parse_bool_setting(settings.get("mcp.enable_http", "true")),
    )


def _parse_list_setting(value: Any) -> Optional[List[str]]:
    """Parse a list setting from string format."""
    if not value:
        return None
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _parse_bool_setting(value: Any) -> bool:
    """Parse a boolean setting from string format."""
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


def _get_mcp_directive(config: Configurator) -> PyramidMCP:
    """Directive to get PyramidMCP instance from configurator."""
    return config.registry.pyramid_mcp


def _get_mcp_from_request(request: Any) -> PyramidMCP:
    """Request method to get PyramidMCP instance."""
    return request.registry.pyramid_mcp


def _register_pending_tools(config: Configurator) -> None:
    """Register any tools that were decorated but not immediately registered."""
    # This is called after all configuration is done
    # Scan for any functions with _mcp_tool_config that need registration
    import gc
    import types

    pyramid_mcp = config.registry.pyramid_mcp

    # Find all functions with _mcp_tool_config attribute
    for obj in gc.get_objects():
        if (
            isinstance(obj, types.FunctionType)
            and hasattr(obj, "_mcp_tool_config")
            and obj.__name__ not in pyramid_mcp.protocol_handler.tools
        ):
            tool_config = obj._mcp_tool_config
            pyramid_mcp.tool(
                tool_config["name"], tool_config["description"], tool_config["schema"]
            )(obj)
