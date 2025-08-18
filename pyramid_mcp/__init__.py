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

import logging
from typing import Any, List, Optional, cast

from pyramid.config import Configurator
from pyramid.settings import asbool

from pyramid_mcp.core import (
    MCPConfiguration,
    MCPDescriptionPredicate,
    MCPLLMContextHintPredicate,
    MCPSecurityPredicate,
    PyramidMCP,
)
from pyramid_mcp.decorators import tool
from pyramid_mcp.version import __version__

logger = logging.getLogger(__name__)

__all__ = [
    "PyramidMCP",
    "MCPConfiguration",
    "MCPDescriptionPredicate",
    "MCPLLMContextHintPredicate",
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

        # Disable MCP endpoints (only register view predicates)
        config.include('pyramid_mcp')
        config.registry.settings.update({
            'mcp.enable': 'false'
        })
    """
    settings = cast(Any, config.registry).settings

    # Extract MCP settings from pyramid settings
    mcp_config = _extract_mcp_config_from_settings(settings)

    # Include cornice for tool decorator support
    config.include("cornice")

    # Always register view predicates (they're useful even when MCP is disabled)
    # Register the MCP description view predicate
    config.add_view_predicate("mcp_description", MCPDescriptionPredicate)

    # Register the MCP llm_context_hint view predicate
    config.add_view_predicate("llm_context_hint", MCPLLMContextHintPredicate)

    # Register the MCP security view predicate using configurable parameter name
    if mcp_config.add_security_predicate:
        config.add_view_predicate(mcp_config.security_parameter, MCPSecurityPredicate)
    else:
        # User disabled security predicate registration
        logger.info(
            "Security predicate registration disabled via "
            "mcp.add_security_predicate=false"
        )

    # If MCP is disabled, skip endpoint creation and tool discovery
    if not mcp_config.enable:
        logger.info(
            "MCP endpoints disabled via mcp.enable=false - "
            "only view predicates registered"
        )
        return

    # Create PyramidMCP instance
    pyramid_mcp = PyramidMCP(config, config=mcp_config)

    # Store the instance in registry for access by application code
    cast(Any, config.registry).pyramid_mcp = pyramid_mcp

    # Add MCP routes immediately (before action execution)
    pyramid_mcp._add_mcp_routes_only()

    # Add a directive to access pyramid_mcp from configurator
    config.add_directive("get_mcp", _get_mcp_directive)

    # Add request method to access MCP tools
    config.add_request_method(_get_mcp_from_request, "mcp", reify=True)

    # Register a post-configure hook to discover routes and register tools
    # Use order=999999 to ensure this runs after all other configuration including scans
    config.action(
        "pyramid_mcp.setup_complete",
        _setup_mcp_complete,
        args=(config, pyramid_mcp),
        order=999999,  # Run this very late in the configuration process
    )


# The standalone tool function is imported at the top


def _extract_mcp_config_from_settings(settings: dict) -> MCPConfiguration:
    """Extract MCP configuration from Pyramid settings."""
    return MCPConfiguration(
        server_name=settings.get("mcp.server_name", "pyramid-mcp"),
        server_version=settings.get("mcp.server_version", "1.0.0"),
        mount_path=settings.get("mcp.mount_path", "/mcp"),
        include_patterns=_parse_list_setting(settings.get("mcp.include_patterns")),
        exclude_patterns=_parse_list_setting(settings.get("mcp.exclude_patterns")),
        enable_sse=asbool(settings.get("mcp.enable_sse", "true")),
        enable_http=asbool(settings.get("mcp.enable_http", "true")),
        # Main enable/disable switch
        enable=asbool(settings.get("mcp.enable", "true")),
        # Route discovery settings
        route_discovery_enabled=asbool(
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
        add_security_predicate=asbool(
            settings.get("mcp.add_security_predicate", "true")
        ),
        # Authentication parameter exposure settings
        expose_auth_as_params=asbool(settings.get("mcp.expose_auth_as_params", "true")),
        # Tool filtering settings
        filter_forbidden_tools=asbool(
            settings.get("mcp.filter_forbidden_tools", "true")
        ),
    )


def _parse_list_setting(value: Any) -> Optional[List[str]]:
    """Parse a list setting from string format."""
    if not value:
        return None
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value) if value else None


def _get_mcp_directive(config: Configurator) -> PyramidMCP:
    """Directive to get PyramidMCP instance from configurator."""
    return cast(PyramidMCP, cast(Any, config.registry).pyramid_mcp)


def _get_mcp_from_request(request: Any) -> Optional[PyramidMCP]:
    """Get PyramidMCP instance from request registry."""
    return getattr(cast(Any, request.registry), "pyramid_mcp", None)


def _setup_mcp_complete(config: Configurator, pyramid_mcp: PyramidMCP) -> None:
    """Complete MCP setup after all configuration is done."""
    # This is called after all configuration is done via Pyramid's action system
    # At this point, all routes and views have been added and committed

    # Scan for @tool decorated functions
    config.scan(categories=["pyramid_mcp"])

    # Discover and register tools from routes (routes were already added in includeme)
    pyramid_mcp.discover_tools()

    # Manual tools are now registered as Pyramid views directly via @tool decorator
    logger.debug("Manual tools registered as Pyramid views for unified security")
