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

from typing import Any, Callable, List, Optional, Type, cast

from marshmallow import Schema
from pyramid.config import Configurator
from pyramid.threadlocal import get_current_registry

from pyramid_mcp.core import (
    MCPConfiguration,
    MCPDescriptionPredicate,
    MCPSecurityPredicate,
    PyramidMCP,
)
from pyramid_mcp.security import MCPSecurityType
from pyramid_mcp.version import __version__

__all__ = [
    "PyramidMCP",
    "MCPConfiguration",
    "MCPDescriptionPredicate",
    "MCPSecurityPredicate",
    "__version__",
    "includeme",
    "tool",
]


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
    settings = config.registry.settings  # type: ignore

    # Extract MCP settings from pyramid settings
    mcp_config = _extract_mcp_config_from_settings(settings)

    # Create PyramidMCP instance
    pyramid_mcp = PyramidMCP(config, config=mcp_config)

    # Store the instance in registry for access by application code
    config.registry.pyramid_mcp = pyramid_mcp  # type: ignore

    # Store registry for tool decorator in testing scenarios
    _tool_registry_storage.registry = config.registry  # type: ignore

    # Add MCP routes immediately (before action execution)
    pyramid_mcp._add_mcp_routes_only()

    # Add a directive to access pyramid_mcp from configurator
    config.add_directive("get_mcp", _get_mcp_directive)

    # Add request method to access MCP tools
    config.add_request_method(_get_mcp_from_request, "mcp", reify=True)

    # Register the MCP description view predicate
    config.add_view_predicate("mcp_description", MCPDescriptionPredicate)

    # Register the MCP security view predicate
    config.add_view_predicate("mcp_security", MCPSecurityPredicate)

    # Register a post-configure hook to discover routes and register tools
    # Use order=999999 to ensure this runs after all other configuration including scans
    config.action(
        "pyramid_mcp.setup_complete",
        _setup_mcp_complete,
        args=(config, pyramid_mcp),
        order=999999,  # Run this very late in the configuration process
    )


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    schema: Optional[Type[Schema]] = None,
    permission: Optional[str] = None,
    security: Optional[MCPSecurityType] = None,
) -> Callable:
    """
    Decorator to register a function as an MCP tool using the current Pyramid registry.

    This decorator can be used after including pyramid_mcp in your Pyramid application.
    It will automatically register the decorated function with the MCP server.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        schema: Marshmallow schema for input validation
        permission: Pyramid permission requirement for this tool

    Returns:
        Decorated function

    Example:
        @tool(description="Add two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        @tool(description="Get user info", permission="authenticated")
        def get_user(id: int) -> dict:
            return {"id": id, "name": "User"}
    """

    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__

        # Store the tool configuration on the function for later registration
        setattr(
            func,
            "_mcp_tool_config",
            {
                "name": tool_name,
                "description": tool_description,
                "schema": schema,
                "permission": permission,
                "security": security,
            },
        )

        # Try to register immediately if registry is available
        registry = get_current_registry()
        if registry is not None:
            pyramid_mcp = getattr(registry, "pyramid_mcp", None)
            if pyramid_mcp:
                pyramid_mcp.tool(
                    name, description, schema, permission, security=security
                )(func)
        else:
            # Check if we have a stored registry for testing
            stored_registry = getattr(_tool_registry_storage, "registry", None)
            if stored_registry:
                pyramid_mcp = getattr(stored_registry, "pyramid_mcp", None)
                if pyramid_mcp:
                    pyramid_mcp.tool(
                        name, description, schema, permission, security=security
                    )(func)

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
        # Route discovery settings
        route_discovery_enabled=_parse_bool_setting(
            settings.get("mcp.route_discovery.enabled", "false")
        ),
        route_discovery_include_patterns=_parse_list_setting(
            settings.get("mcp.route_discovery.include_patterns")
        ),
        route_discovery_exclude_patterns=_parse_list_setting(
            settings.get("mcp.route_discovery.exclude_patterns")
        ),
        # Security parameter settings
        security_parameter=settings.get("mcp.security_parameter", "mcp_security"),
    )


def _parse_list_setting(value: Any) -> Optional[List[str]]:
    """Parse a list setting from string format."""
    if not value:
        return None
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value) if value else None


def _parse_bool_setting(value: Any) -> bool:
    """Parse a boolean setting from string format."""
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


def _get_mcp_directive(config: Configurator) -> PyramidMCP:
    """Directive to get PyramidMCP instance from configurator."""
    return cast(PyramidMCP, config.registry.pyramid_mcp)  # type: ignore


def _get_mcp_from_request(request: Any) -> PyramidMCP:
    """Request method to get PyramidMCP instance."""
    return cast(PyramidMCP, request.registry.pyramid_mcp)


def _setup_mcp_complete(config: Configurator, pyramid_mcp: PyramidMCP) -> None:
    """Complete MCP setup after all configuration is done."""
    # This is called after all configuration is done via Pyramid's action system
    # At this point, all routes and views have been added and committed

    # Discover and register tools from routes (routes were already added in includeme)
    pyramid_mcp.discover_tools()

    # Register any pending manual tools that weren't caught earlier
    _register_pending_tools(pyramid_mcp)


def _register_pending_tools(pyramid_mcp: PyramidMCP) -> None:
    """Register any tools that were decorated but not immediately registered."""
    import gc
    import types

    # Find all functions with _mcp_tool_config attribute
    for obj in gc.get_objects():
        if (
            isinstance(obj, types.FunctionType)
            and hasattr(obj, "_mcp_tool_config")
            and obj.__name__ not in pyramid_mcp.protocol_handler.tools
        ):
            tool_config = obj._mcp_tool_config
            pyramid_mcp.tool(
                tool_config["name"],
                tool_config["description"],
                tool_config["schema"],
                tool_config.get("permission", None),
                security=tool_config.get("security", None),
            )(obj)
