"""
Core PyramidMCP Implementation

This module provides the main PyramidMCP class that integrates Model Context Protocol
capabilities with Pyramid web applications.
"""

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

from marshmallow import Schema
from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.response import Response

from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.protocol import (
    MCPProtocolHandler,
    MCPTool,
    create_json_schema_from_marshmallow,
)
from pyramid_mcp.wsgi import MCPWSGIApp


@dataclass
class MCPConfiguration:
    """Configuration for PyramidMCP."""

    server_name: str = "pyramid-mcp"
    server_version: str = "1.0.0"
    mount_path: str = "/mcp"
    include_patterns: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    enable_sse: bool = True
    enable_http: bool = True
    # Route discovery configuration
    route_discovery_enabled: bool = False
    route_discovery_include_patterns: Optional[List[str]] = None
    route_discovery_exclude_patterns: Optional[List[str]] = None


class PyramidMCP:
    """Main class for integrating MCP capabilities with Pyramid applications.

    This class provides the primary interface for exposing Pyramid web application
    endpoints as MCP tools, following patterns similar to fastapi_mcp but adapted
    for Pyramid's architecture.

    Example:
        >>> from pyramid.config import Configurator
        >>> from pyramid_mcp import PyramidMCP
        >>>
        >>> config = Configurator()
        >>> config.add_route('users', '/users')
        >>> config.add_route('user', '/users/{id}')
        >>> config.scan()
        >>>
        >>> mcp = PyramidMCP(config)
        >>> mcp.mount()  # Mount at /mcp endpoint
        >>> app = config.make_wsgi_app()
    """

    def __init__(
        self,
        configurator: Optional[Configurator] = None,
        wsgi_app: Optional[Callable] = None,
        config: Optional[MCPConfiguration] = None,
    ):
        """Initialize PyramidMCP.

        Args:
            configurator: Pyramid configurator instance
            wsgi_app: Existing WSGI application to introspect
            config: MCP configuration options
        """
        if not configurator and not wsgi_app:
            raise ValueError("Either configurator or wsgi_app must be provided")

        self.configurator = configurator
        self.wsgi_app = wsgi_app
        self.config = config or MCPConfiguration()

        # Initialize MCP protocol handler
        self.protocol_handler = MCPProtocolHandler(
            self.config.server_name, self.config.server_version
        )

        # Initialize introspection
        self.introspector = PyramidIntrospector(configurator)

        # Storage for manually registered tools
        self.manual_tools: Dict[str, MCPTool] = {}

        # Track if tools have been discovered
        self._tools_discovered = False

    def mount(self, path: Optional[str] = None, auto_commit: bool = True) -> None:
        """Mount the MCP server to the Pyramid application.

        Args:
            path: Mount path (defaults to config.mount_path)
            auto_commit: Whether to automatically commit the configuration
        """
        if not self.configurator:
            raise RuntimeError("Cannot mount without a configurator")

        mount_path = path or self.config.mount_path

        # Discover tools if not already done
        if not self._tools_discovered:
            self.discover_tools()

        # Add MCP routes to the configurator
        self._add_mcp_routes(mount_path)

        # Auto-commit configuration if requested (default for plugin usage)
        if auto_commit:
            self.configurator.commit()

    def discover_tools(self) -> None:
        """Discover and register tools from Pyramid routes."""
        if self.configurator:
            # Route discovery - only if enabled
            if self.config.route_discovery_enabled:
                # Create a configuration object for route discovery
                class RouteDiscoveryConfig:
                    def __init__(self, mcp_config):
                        self.include_patterns = mcp_config.route_discovery_include_patterns or []
                        self.exclude_patterns = mcp_config.route_discovery_exclude_patterns or []
                
                discovery_config = RouteDiscoveryConfig(self.config)
                
                # Discover routes and convert to MCP tools
                tools = self.introspector.discover_tools(discovery_config)

                # Register discovered tools
                for tool in tools:
                    self.protocol_handler.register_tool(tool)

        elif self.wsgi_app:
            # For WSGI apps, we need a different approach
            # This would require more complex introspection
            pass

        # Register manually added tools
        for tool in self.manual_tools.values():
            self.protocol_handler.register_tool(tool)

        self._tools_discovered = True

    def _add_mcp_routes_only(self) -> None:
        """Add MCP routes without discovering tools (for includeme timing)."""
        if not self.configurator:
            raise RuntimeError("Cannot add routes without a configurator")

        mount_path = self.config.mount_path
        self._add_mcp_routes(mount_path)

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[Type[Schema]] = None,
        permission: Optional[str] = None,
    ) -> Callable:
        """Decorator to register a function as an MCP tool.

        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to function docstring)
            schema: Marshmallow schema for input validation
            permission: Pyramid permission requirement for this tool

        Returns:
            Decorated function

        Example:
            >>> @mcp.tool(description="Add two numbers")
            >>> def add(a: int, b: int) -> int:
            ...     return a + b
            
            >>> @mcp.tool(description="Get user info", permission="authenticated")
            >>> def get_user(id: int) -> dict:
            ...     return {"id": id, "name": "User"}
        """

        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__
            tool_description = description or func.__doc__

            # Generate input schema
            input_schema = None
            if schema:
                input_schema = create_json_schema_from_marshmallow(schema)
            else:
                # Try to generate schema from function signature
                input_schema = self._generate_schema_from_signature(func)

            # Create and register the tool
            tool = MCPTool(
                name=tool_name,
                description=tool_description,
                input_schema=input_schema,
                handler=func,
                permission=permission,
            )

            self.manual_tools[tool_name] = tool

            # Always register the tool immediately when using decorator
            self.protocol_handler.register_tool(tool)

            return func

        return decorator

    def make_mcp_server(self) -> MCPWSGIApp:
        """Create a standalone MCP WSGI server.

        Returns:
            WSGI application that serves MCP protocol
        """
        if not self._tools_discovered:
            self.discover_tools()

        return MCPWSGIApp(self.protocol_handler, self.config)

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of all registered MCP tools.

        Returns:
            List of tool definitions
        """
        if not self._tools_discovered:
            self.discover_tools()

        return [tool.to_dict() for tool in self.protocol_handler.tools.values()]

    def _add_mcp_routes(self, mount_path: str) -> None:
        """Add MCP routes to the Pyramid configurator.

        Args:
            mount_path: Base path for MCP routes
        """
        if not self.configurator:
            return

        # Remove leading/trailing slashes and ensure proper format
        mount_path = mount_path.strip("/")

        if self.config.enable_http:
            # Add HTTP endpoint for MCP messages
            route_name = "mcp_http"
            route_path = f"/{mount_path}"
            self.configurator.add_route(route_name, route_path)
            self.configurator.add_view(
                self._handle_mcp_http,
                route_name=route_name,
                request_method="POST",
                renderer="json",
            )

        if self.config.enable_sse:
            # Add SSE endpoint for MCP streaming
            sse_route_name = "mcp_sse"
            sse_route_path = f"/{mount_path}/sse"
            self.configurator.add_route(sse_route_name, sse_route_path)
            self.configurator.add_view(
                self._handle_mcp_sse,
                route_name=sse_route_name,
                request_method=["GET", "POST"],
            )

    def _handle_mcp_http(self, request: Request) -> Dict[str, Any]:
        """Handle HTTP-based MCP messages.

        Args:
            request: Pyramid request object

        Returns:
            MCP response as dictionary
        """
        try:
            # Parse JSON request body
            message_data = request.json_body

            # Create authentication context for MCP protocol handler
            auth_context = {
                'request': request
            }

            # Handle the message through protocol handler
            response = self.protocol_handler.handle_message(message_data, auth_context)
            return response

        except Exception as e:
            # Return error response
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }

    def _handle_mcp_sse(self, request: Request) -> Response:
        """Handle SSE-based MCP communication.

        Args:
            request: Pyramid request object

        Returns:
            SSE response
        """
        # This is a simplified SSE implementation
        # A production version would need proper SSE handling

        def generate_sse() -> Any:
            """Generate SSE events."""
            if request.method == "POST":
                try:
                    message_data = request.json_body
                    response_data = self.protocol_handler.handle_message(message_data)

                    # Format as SSE
                    sse_data = f"data: {json.dumps(response_data)}\n\n"
                    yield sse_data.encode("utf-8")

                except Exception as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}",
                        },
                    }
                    sse_data = f"data: {json.dumps(error_response)}\n\n"
                    yield sse_data.encode("utf-8")
            else:
                # GET request - send initial connection message
                welcome = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                }
                sse_data = f"data: {json.dumps(welcome)}\n\n"
                yield sse_data.encode("utf-8")

        response = Response(
            app_iter=generate_sse(), content_type="text/event-stream", charset="utf-8"
        )
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"

        return response

    def _generate_schema_from_signature(
        self, func: Callable
    ) -> Optional[Dict[str, Any]]:
        """Generate JSON schema from function signature.

        Args:
            func: Function to analyze

        Returns:
            JSON schema dictionary or None
        """
        try:
            sig = inspect.signature(func)
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                param_schema = {"type": "string"}  # Default type

                if param.annotation != inspect.Parameter.empty:
                    if param.annotation == int:
                        param_schema["type"] = "integer"
                    elif param.annotation == float:
                        param_schema["type"] = "number"
                    elif param.annotation == bool:
                        param_schema["type"] = "boolean"
                    elif param.annotation == list:
                        param_schema["type"] = "array"
                    elif param.annotation == dict:
                        param_schema["type"] = "object"

                properties[param_name] = param_schema

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            if properties:
                return {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }

        except Exception:
            pass

        return None

    @classmethod
    def from_wsgi_app(
        cls, wsgi_app: Callable, config: Optional[MCPConfiguration] = None
    ) -> "PyramidMCP":
        """Create PyramidMCP from an existing WSGI application.

        Args:
            wsgi_app: Existing WSGI application
            config: MCP configuration

        Returns:
            PyramidMCP instance
        """
        return cls(wsgi_app=wsgi_app, config=config)
