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
from pyramid_mcp.security import MCPSecurityType
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
    # Security parameter configuration
    security_parameter: str = "mcp_security"
    add_security_predicate: bool = True


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
                    def __init__(self, mcp_config: Any) -> None:
                        self.include_patterns = (
                            mcp_config.route_discovery_include_patterns or []
                        )
                        self.exclude_patterns = (
                            mcp_config.route_discovery_exclude_patterns or []
                        )
                        self.security_parameter = mcp_config.security_parameter

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
        context: Optional[Any] = None,
        security: Optional[MCPSecurityType] = None,
    ) -> Callable:
        """Decorator to register a function as an MCP tool.

        Args:
            name: Tool name (defaults to function name)
            description: Tool description (defaults to function docstring)
            schema: Marshmallow schema for input validation
            permission: Pyramid permission requirement for this tool
            context: Context or context factory to use for permission checking
            security: Authentication parameter specification for this tool

        Returns:
            Decorated function

        Example:
            >>> @mcp.tool(description="Add two numbers")
            >>> def add(a: int, b: int) -> int:
            ...     return a + b

            >>> @mcp.tool(description="Get user info", permission="authenticated")
            >>> def get_user(id: int) -> dict:
            ...     return {"id": id, "name": "User"}

            >>> # With custom context
            >>> @mcp.tool(permission="view", context=AuthenticatedContext)
            >>> def secure_operation() -> str:
            ...     return "Secure data"

            >>> # With authentication parameters
            >>> from pyramid_mcp.security import BearerAuth
            >>> @mcp.tool(
            ...     description="Secure API call",
            ...     security=BearerAuth(
            ...         description="API token",
            ...         parameter_name="token"
            ...     )
            ... )
            >>> def secure_api_call(token: str, data: str) -> str:
            ...     return f"Secure API called with data: {data}"
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
                context=context,
                security=security,
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
        message_data = None
        try:
            # Parse JSON request body
            message_data = request.json_body

            # Get the context from the context factory (if any)
            # This integrates MCP with Pyramid's security system

            # Create authentication context for MCP protocol handler
            # Include both request and context for proper security integration

            # Handle the message through protocol handler
            response = self.protocol_handler.handle_message(message_data, request)

            # Check if this is a notification that should not receive a response
            if response is self.protocol_handler.NO_RESPONSE:
                # For HTTP, return minimal success response for notifications
                # (stdio transport handles this differently by not sending anything)
                return {"jsonrpc": "2.0", "result": "ok"}

            # Type cast since we know it's a dict if not NO_RESPONSE
            return response  # type: ignore

        except Exception as e:
            # Try to extract request ID if possible
            request_id = None
            try:
                if message_data and "id" in message_data:
                    request_id = message_data["id"]
            except (TypeError, KeyError, AttributeError):
                pass

            # Return error response
            return {
                "jsonrpc": "2.0",
                "id": request_id,
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
                message_data = None
                try:
                    message_data = request.json_body
                    response_data = self.protocol_handler.handle_message(
                        message_data, request
                    )

                    # Check if this is a notification that should not receive a response
                    if response_data is self.protocol_handler.NO_RESPONSE:
                        # Don't send any data for notifications in SSE
                        return

                    # Format as SSE
                    sse_data = f"data: {json.dumps(response_data)}\n\n"
                    yield sse_data.encode("utf-8")

                except Exception as e:
                    # Try to extract request ID if possible
                    request_id = None
                    try:
                        if message_data and "id" in message_data:
                            request_id = message_data["id"]
                    except (TypeError, KeyError, AttributeError):
                        pass

                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
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


class MCPSecurityPredicate:
    """
    View predicate class for mcp_security parameter.

    This is a non-filtering predicate that allows mcp_security
    to be used as a view configuration parameter without affecting
    view matching logic.
    """

    def __init__(self, val: Any, config: Any) -> None:
        """Initialize the predicate with the mcp_security value."""
        self.val = val
        self.config = config

    def text(self) -> str:
        """Return text representation for introspection."""
        return f"mcp_security = {self.val!r}"

    phash = text  # For compatibility with Pyramid's predicate system

    def __call__(self, context: Any, request: Any) -> bool:
        """Always return True - this is a non-filtering predicate."""
        return True


class MCPDescriptionPredicate:
    """
    View predicate class for mcp_description parameter.

    This is a non-filtering predicate that allows mcp_description
    to be used as a view configuration parameter without affecting
    view matching logic.
    """

    def __init__(self, val: Any, config: Any) -> None:
        """Initialize the predicate with the mcp_description value."""
        self.val = val
        self.config = config

    def text(self) -> str:
        """Return text representation for introspection."""
        return f"mcp_description = {self.val!r}"

    phash = text  # For compatibility with Pyramid's predicate system

    def __call__(self, context: Any, request: Any) -> bool:
        """Always return True - this is a non-filtering predicate."""
        return True
