"""
Core PyramidMCP Implementation

This module provides the main PyramidMCP class that integrates Model Context Protocol
capabilities with Pyramid web applications.
"""


import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.response import Response

from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.protocol import MCPProtocolHandler
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
    # Main enable/disable switch
    enable: bool = True
    # Route discovery configuration
    route_discovery_enabled: bool = False
    route_discovery_include_patterns: Optional[List[str]] = None
    route_discovery_exclude_patterns: Optional[List[str]] = None
    # Security parameter configuration
    security_parameter: str = "mcp_security"
    add_security_predicate: bool = True
    # Authentication parameter exposure configuration
    expose_auth_as_params: bool = True
    # Tool filtering configuration
    filter_forbidden_tools: bool = True


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
        configurator: Configurator,
        config: Optional[MCPConfiguration] = None,
    ):
        """Initialize PyramidMCP.

        Args:
            configurator: Pyramid configurator instance
            config: MCP configuration options
        """
        self.configurator = configurator
        self.config = config or MCPConfiguration()

        # Initialize MCP protocol handler
        self.protocol_handler = MCPProtocolHandler(
            self.config.server_name, self.config.server_version, self.config
        )

        # Initialize introspection
        self.introspector = PyramidIntrospector(configurator)

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
                        self.expose_auth_as_params = mcp_config.expose_auth_as_params

                discovery_config = RouteDiscoveryConfig(self.config)

                # Discover routes and convert to MCP tools
                tools = self.introspector.discover_tools(discovery_config)

                # Register discovered tools
                for tool in tools:
                    self.protocol_handler.register_tool(tool, self.config)

        # Manual tools are now registered as Pyramid views via introspection

        self._tools_discovered = True

    def _add_mcp_routes_only(self) -> None:
        """Add MCP routes without discovering tools (for includeme timing)."""
        if not self.configurator:
            raise RuntimeError("Cannot add routes without a configurator")

        mount_path = self.config.mount_path
        self._add_mcp_routes(mount_path)

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
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"

        return response


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


def normalize_llm_context_hint(hint: Any) -> Optional[str]:
    """Normalize LLM context hint value, handling empty/whitespace cases.

    Args:
        hint: The raw hint value from view configuration

    Returns:
        Normalized string hint or None if invalid/empty
    """
    if hint is None:
        return None

    if isinstance(hint, str):
        stripped = hint.strip()
        return stripped if stripped else None

    # Convert non-string values to string
    return str(hint).strip() if str(hint).strip() else None


class MCPLLMContextHintPredicate:
    """
    View predicate class for llm_context_hint parameter.

    This is a non-filtering predicate that allows llm_context_hint
    to be used as a view configuration parameter without affecting
    view matching logic.
    """

    def __init__(self, val: Any, config: Any) -> None:
        """Initialize the predicate with the llm_context_hint value."""
        self.val = val
        self.config = config
        # Normalize the value during initialization
        self._normalized_val = normalize_llm_context_hint(val)

    def _normalize_hint(self, hint: Any) -> Optional[str]:
        """Normalize the hint value, handling empty/whitespace cases.

        DEPRECATED: Use normalize_llm_context_hint() function instead.
        """
        return normalize_llm_context_hint(hint)

    def get_normalized_value(self) -> Optional[str]:
        """Get the normalized hint value.

        Returns:
            Normalized hint string or None if empty/invalid
        """
        return self._normalized_val

    def text(self) -> str:
        """Return text representation for introspection."""
        return f"llm_context_hint = {self.val!r}"

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
