"""
Core PyramidMCP Implementation

This module provides the main PyramidMCP class that integrates Model Context Protocol
capabilities with Pyramid web applications.
"""

import inspect
import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type

import venusian  # type: ignore[import-untyped]
from marshmallow import Schema
from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.response import Response

from pyramid_mcp.introspection import PyramidIntrospector
from pyramid_mcp.protocol import MCPProtocolHandler, create_json_schema_from_marshmallow
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

        elif self.wsgi_app:
            # For WSGI apps, we need a different approach
            # This would require more complex introspection
            pass

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


class tool:
    """A function decorator which allows a developer to register MCP tools
    nearer to the tool function definition than using imperative configuration.

    This decorator follows the same pattern as Pyramid's @view_config decorator,
    using Venusian for deferred registration until config.scan() is called.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        schema: Marshmallow schema for input validation
        permission: Pyramid permission requirement for this tool
        context: Context or context factory to use for permission checking
        security: Authentication parameter specification for this tool

    Usage:
        >>> @tool(name="add", description="Add two numbers")
        >>> def add_numbers(a: int, b: int) -> int:
        ...     return a + b
        >>>
        >>> @tool(description="Get user info", permission="authenticated")
        >>> def get_user(id: int) -> dict:
        ...     return {"id": id, "name": "User"}
    """

    venusian = venusian  # for testing injection

    def __init__(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        schema: Optional[Type[Schema]] = None,
        permission: Optional[str] = None,
        context: Optional[Any] = None,
        security: Optional[MCPSecurityType] = None,
        **settings: Any,
    ):
        # Store all settings for later use in callback
        if name is not None:
            settings["name"] = name
        if description is not None:
            settings["description"] = description
        if schema is not None:
            settings["schema"] = schema
        if permission is not None:
            settings["permission"] = permission
        if context is not None:
            settings["context"] = context
        if security is not None:
            settings["security"] = security

        self.__dict__.update(settings)

    def __call__(self, wrapped: Callable) -> Callable:
        settings = self.__dict__.copy()
        depth = settings.pop("_depth", 0)

        def callback(context: Any, name: str, ob: Callable[..., Any]) -> None:
            """Venusian callback to register the tool when config.scan() is called."""
            config = context.config

            tool_name = settings.get("name") or wrapped.__name__
            tool_description = settings.get("description") or wrapped.__doc__
            schema = settings.get("schema")
            permission = settings.get("permission")
            context_factory = settings.get("context")
            security = settings.get("security")

            # Generate unique route name and path for this tool
            # NOTE: Don't use "mcp_" prefix as introspection excludes those routes
            route_name = f"tool_{tool_name}"
            route_path = f"/mcp/tools/{tool_name}"

            # Create view wrapper that handles MCP tool execution
            def mcp_tool_view(request: Any) -> Dict[str, Any]:
                """Pyramid view wrapper for MCP tool function."""
                try:
                    # Extract arguments from request
                    # Support both query params (GET) and JSON body (POST)
                    if (
                        request.method == "POST"
                        and request.content_type == "application/json"
                    ):
                        args_data = request.json_body or {}
                    else:
                        args_data = dict(request.params)

                    # Call the original function with extracted arguments
                    result = wrapped(**args_data)

                    # Return result in proper format
                    return {"result": result, "tool_name": tool_name}

                except Exception as e:
                    # Return error in proper format
                    return {
                        "error": f"Tool execution failed: {str(e)}",
                        "tool_name": tool_name,
                    }

            # Add MCP metadata to the view function for introspection discovery
            mcp_tool_view.__mcp_tool_name__ = tool_name  # type: ignore[attr-defined]
            mcp_tool_view.__mcp_tool_description__ = tool_description  # type: ignore
            mcp_tool_view.__mcp_tool_security__ = security  # type: ignore[attr-defined]
            mcp_tool_view.__mcp_original_function__ = wrapped  # type: ignore

            # Generate input schema for introspection
            if schema:
                input_schema = create_json_schema_from_marshmallow(schema)
            else:
                # Try to generate schema from function signature
                input_schema = _generate_schema_from_signature(wrapped)

            mcp_tool_view.__mcp_tool_input_schema__ = input_schema  # type: ignore

            # Register route with optional context factory
            if context_factory:
                config.add_route(route_name, route_path, factory=context_factory)
            else:
                config.add_route(route_name, route_path)

            # Register the view with Pyramid - let introspection discover it
            config.add_view(
                mcp_tool_view,
                route_name=route_name,
                renderer="json",
                request_method=["GET", "POST"],
                permission=permission,
            )

        # Attach venusian decorator for deferred registration
        self.venusian.attach(wrapped, callback, category="pyramid_mcp", depth=depth + 1)

        return wrapped


def _generate_schema_from_signature(func: Callable) -> Dict[str, Any]:
    """Generate JSON schema from function signature for standalone tool decorator."""
    import inspect
    from typing import get_type_hints

    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        param_type = type_hints.get(param_name, str)

        # Convert Python types to JSON Schema types
        if param_type == int:
            json_type = "integer"
        elif param_type == float:
            json_type = "number"
        elif param_type == bool:
            json_type = "boolean"
        else:
            json_type = "string"

        properties[param_name] = {"type": json_type}

        # Add to required if no default value
        if param.default == inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }
