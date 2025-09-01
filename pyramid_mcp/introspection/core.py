"""
Core Introspection Module

This module contains the main PyramidIntrospector class that coordinates
all other introspection modules to discover routes and convert them to MCP tools.
"""

import logging
from typing import Any, Callable, Dict, List

from pyramid_mcp.introspection.cornice import discover_cornice_services
from pyramid_mcp.introspection.filters import should_exclude_route, should_exclude_tool
from pyramid_mcp.introspection.requests import create_route_handler
from pyramid_mcp.introspection.routes import discover_routes, extract_permission
from pyramid_mcp.introspection.schemas import (
    determine_location_from_schema_structure,
    determine_parameter_location_from_validators,
)
from pyramid_mcp.introspection.security import convert_security_type_to_schema
from pyramid_mcp.introspection.tools import convert_route_to_tools
from pyramid_mcp.protocol import MCPTool
from pyramid_mcp.schemas import extract_marshmallow_schema_info

logger = logging.getLogger(__name__)


class PyramidIntrospector:
    """Handles introspection of Pyramid applications to discover routes and views."""

    def __init__(self, configurator: Any):
        """Initialize the introspector.

        Args:
            configurator: Pyramid configurator instance
        """
        self.configurator = configurator
        self._security_parameter = (
            "mcp_security"  # Will be overridden by discover_tools
        )

    def discover_routes(self) -> List[Dict[str, Any]]:
        """Discover routes from the Pyramid application.

        Returns:
            List of route information dictionaries containing route metadata,
            view callables, and other relevant information for MCP tool generation.
            Enhanced with Cornice service information when available.
        """
        return discover_routes(self.configurator, discover_cornice_services)

    def discover_tools(self, config: Any) -> List[MCPTool]:
        """Discover routes and convert them to MCP tools.

        Args:
            config: Configuration object with include/exclude patterns

        Returns:
            List of MCPTool objects
        """
        # Store the security parameter for use in other methods
        self._security_parameter = config.security_parameter

        tools: List[MCPTool] = []

        # Discover routes using our comprehensive discovery method
        routes_info = self.discover_routes()

        for route_info in routes_info:
            # Skip routes that should be excluded (keep route-level filtering for
            # backwards compatibility)
            if should_exclude_route(route_info, config):
                continue

            # Convert route to MCP tools (one per HTTP method)
            route_tools = convert_route_to_tools(
                route_info,
                config,
                self._create_permission_extractor(),
                self._create_route_handler_creator(),
                convert_security_type_to_schema,
                extract_marshmallow_schema_info,
                determine_parameter_location_from_validators,
                determine_location_from_schema_structure,
            )

            # Apply tool-level filtering on generated tool names
            for tool in route_tools:
                if not should_exclude_tool(tool, config):
                    tools.append(tool)

        return tools

    def _create_permission_extractor(self) -> Callable:
        """Create a permission extractor function with access to configurator."""

        def permission_extractor(view_intr: Any) -> Any:
            return extract_permission(view_intr, self.configurator)

        return permission_extractor

    def _create_route_handler_creator(self) -> Callable:
        """Create a route handler creator function with access to security parameter."""

        def route_handler_creator(route_info: Any, view_info: Any, method: Any) -> Any:
            return create_route_handler(
                route_info,
                view_info,
                method,
                self._security_parameter,
                convert_security_type_to_schema,
            )

        return route_handler_creator
