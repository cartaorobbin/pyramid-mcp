"""
MCP Protocol Implementation

This module implements the Model Context Protocol (MCP) using JSON-RPC 2.0
messages. It provides the core protocol functionality for communication
between MCP clients and servers.
"""

import hashlib
import inspect
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union, cast
from urllib.parse import urlencode

from marshmallow import ValidationError, fields
from pyramid.interfaces import (
    IDefaultRootFactory,
    IRootFactory,
    IRoutesMapper,
    ISecurityPolicy,
)
from pyramid.request import Request

from pyramid_mcp.schemas import (
    MCPContextResultSchema,
    MCPRequestSchema,
    MCPResponseSchema,
)
from pyramid_mcp.security import MCPSecurityType, merge_auth_into_schema

# Module-level logger
logger = logging.getLogger(__name__)

# Claude Desktop client validation pattern for tool names
CLAUDE_TOOL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def validate_tool_name(name: str) -> bool:
    """
    Validate if a tool name matches Claude Desktop's requirements.

    Args:
        name: Tool name to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(CLAUDE_TOOL_NAME_PATTERN.match(name))


def sanitize_tool_name(name: str, used_names: Optional[Set[str]] = None) -> str:
    """
    Sanitize a tool name to meet Claude Desktop requirements.

    This function ensures the name matches the pattern ^[a-zA-Z0-9_-]{1,64}$
    and handles collisions by appending a hash-based suffix.

    Args:
        name: Original tool name
        used_names: Set of already used names to avoid collisions

    Returns:
        Sanitized tool name that's guaranteed to be valid

    Raises:
        ValueError: If the name cannot be sanitized (e.g., empty after cleaning)
    """
    if used_names is None:
        used_names = set()

    # Step 1: Clean the name - remove invalid characters
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    # Step 2: Ensure it's not empty
    if not cleaned:
        cleaned = "tool"

    # Step 3: Ensure it doesn't start with a number (good practice)
    if cleaned[0].isdigit():
        cleaned = "tool_" + cleaned

    # Step 4: Handle length - if too long, truncate intelligently
    if len(cleaned) > 64:
        # Reserve 8 characters for collision hash (underscore + 7 chars)
        max_base_length = 64 - 8
        cleaned = cleaned[:max_base_length]

    # Step 5: Check for collision
    if cleaned not in used_names:
        return cleaned

    # Step 6: Handle collision with hash-based suffix
    # Create a hash of the original name for uniqueness
    name_hash = hashlib.md5(name.encode("utf-8")).hexdigest()[:7]

    # Calculate max length for base to fit hash suffix
    max_base_length = 64 - 8  # 8 chars for "_" + 7-char hash
    base_name = cleaned[:max_base_length]

    # Try variations with the hash
    for i in range(1000):  # Safety limit
        if i == 0:
            candidate = f"{base_name}_{name_hash}"
        else:
            # If even the hash collides, add a counter
            counter_suffix = f"{i:03d}"
            # Adjust base name to fit hash + counter
            available_length = (
                64 - len(name_hash) - len(counter_suffix) - 2
            )  # 2 underscores
            adjusted_base = base_name[:available_length]
            candidate = f"{adjusted_base}_{name_hash}_{counter_suffix}"

        if candidate not in used_names:
            return candidate

    # This should never happen in practice
    raise ValueError(f"Could not generate unique name for '{name}' after 1000 attempts")


class MCPErrorCode(Enum):
    """Standard MCP error codes based on JSON-RPC 2.0."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


@dataclass
class MCPTool:
    """Represents an MCP tool that can be called by clients."""

    name: str
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    handler: Optional[Callable] = None
    permission: Optional[str] = None  # Pyramid permission requirement
    context: Optional[Any] = None  # Context for permission checking
    security: Optional[MCPSecurityType] = None  # Authentication parameter specification
    llm_context_hint: Optional[str] = None  # Custom context hint for LLM responses
    config: Optional[Any] = None  # MCP configuration object
    # Internal fields for unified security architecture
    _internal_route_name: Optional[str] = None  # Route name for manual tools
    _internal_route_path: Optional[str] = None  # Route path for manual tools
    _internal_route_method: Optional[str] = None  # HTTP method for route-based tools

    def __post_init__(self) -> None:
        """Ensure config is always available with defaults."""
        if self.config is None:
            from pyramid_mcp.core import MCPConfiguration

            self.config = MCPConfiguration()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool format."""
        tool_dict: Dict[str, Any] = {"name": self.name}
        if self.description:
            tool_dict["description"] = self.description

        # Start with base inputSchema or create default
        base_schema = self.input_schema or {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

        # Merge authentication parameters into inputSchema
        # Note: config is guaranteed to exist due to __post_init__
        expose_auth = self.config.expose_auth_as_params if self.config else True
        tool_dict["inputSchema"] = merge_auth_into_schema(
            base_schema, self.security, expose_auth
        )

        return tool_dict


class MCPProtocolHandler:
    """Handles MCP protocol messages and routing."""

    # Special sentinel value to indicate no response should be sent
    NO_RESPONSE = object()

    def __init__(
        self, server_name: str, server_version: str, config: Optional[Any] = None
    ):
        """Initialize the MCP protocol handler.

        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
            config: MCP configuration object containing expose_auth_as_params setting
        """
        self.server_name = server_name
        self.server_version = server_version
        self.config = config
        self.tools: Dict[str, MCPTool] = {}
        self.capabilities: Dict[str, Any] = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": False, "listChanged": True},
            "prompts": {"listChanged": True},
        }
        # Track used tool names to prevent collisions
        self._used_tool_names: Set[str] = set()

    def register_tool(self, tool: MCPTool, config: Optional[Any] = None) -> None:
        """Register an MCP tool.

        Args:
            tool: The MCPTool to register
            config: Pyramid configurator (for creating views for manual tools)
        """
        original_name = tool.name

        # Sanitize the tool name to ensure Claude Desktop compatibility
        sanitized_name = sanitize_tool_name(tool.name, self._used_tool_names)

        # Update the tool with the sanitized name
        if sanitized_name != original_name:
            logger.warning(
                f"Tool name '{original_name}' sanitized to '{sanitized_name}' "
                f"for Claude Desktop compatibility"
            )
            tool.name = sanitized_name

        # For manual tools, create a Pyramid view at setup time
        if config and tool.handler and not self._is_route_based_tool(tool):
            self._create_manual_tool_view(config, tool)

        # Register the tool
        self.tools[sanitized_name] = tool
        self._used_tool_names.add(sanitized_name)

        # Update capabilities to indicate we have tools
        self.capabilities["tools"] = {}

    def _is_route_based_tool(self, tool: MCPTool) -> bool:
        """Check if a tool is route-based."""
        return (
            tool.handler is not None
            and hasattr(tool.handler, "__name__")
            and tool.handler.__name__ == "handler"
            and hasattr(tool.handler, "__qualname__")
            and "PyramidIntrospector._create_route_handler" in tool.handler.__qualname__
        )

    def _create_manual_tool_view(self, config: Any, tool: MCPTool) -> None:
        """Create a Pyramid view for a manual tool."""

        route_name = f"mcp_tool_{tool.name}"
        route_path = f"/mcp/tools/{tool.name}"

        # Store route info in tool for subrequest
        tool._internal_route_name = route_name
        tool._internal_route_path = route_path

        # Create the view function
        def tool_view(request: Request) -> Dict[str, Any]:
            """Pyramid view for manual tool execution."""
            try:
                # Extract args from request
                if (
                    request.method == "POST"
                    and request.content_type == "application/json"
                ):
                    args_data = request.json_body or {}
                else:
                    args_data = dict(request.params)

                # Call the tool handler
                handler = tool.handler
                if not handler:
                    return {"error": "Tool handler not found", "tool_name": tool.name}

                sig = inspect.signature(handler)
                if "pyramid_request" in sig.parameters:
                    result = handler(request, **args_data)
                else:
                    result = handler(**args_data)

                # Return result for schema processing
                return {"mcp_result": result, "tool_name": tool.name}

            except Exception as e:
                return {
                    "error": f"Tool execution failed: {str(e)}",
                    "tool_name": tool.name,
                }

        # Add route and view to Pyramid
        config.add_route(route_name, route_path)
        config.add_view(
            tool_view,
            route_name=route_name,
            request_method="POST",
            renderer="json",
            permission=tool.permission,
            context=tool.context,
        )

    def handle_message(
        self,
        message_data: Dict[str, Any],
        request: Request,
    ) -> Union[Dict[str, Any], object]:
        """Handle an incoming MCP message.

        Args:
            message_data: The parsed JSON message
            request: The pyramid request

        Returns:
            The response message as a dictionary, or NO_RESPONSE for notifications
        """
        try:
            # Parse and validate the request using schema
            schema = MCPRequestSchema()
            mcp_request = cast(Dict[str, Any], schema.load(message_data))
        except ValidationError as validation_error:
            # Handle Marshmallow validation errors
            # For malformed requests (missing required fields), JSON-RPC spec
            # suggests INVALID_REQUEST. However, current tests expect
            # METHOD_NOT_FOUND for backward compatibility
            request_id = None
            try:
                if message_data and "id" in message_data:
                    request_id = message_data["id"]
            except Exception:
                pass

            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {
                        "id": request_id,
                        # For backward compatibility
                        "error_code": MCPErrorCode.METHOD_NOT_FOUND.value,
                        "error_message": f"Invalid request: {str(validation_error)}",
                    }
                ),
            )

        try:
            # Route to appropriate handler
            if mcp_request["method"] == "initialize":
                return self._handle_initialize(mcp_request)
            elif mcp_request["method"] == "tools/list":
                return self._handle_list_tools(mcp_request, request)
            elif mcp_request["method"] == "tools/call":
                return self._handle_call_tool(mcp_request, request)
            elif mcp_request["method"] == "resources/list":
                return self._handle_list_resources(mcp_request)
            elif mcp_request["method"] == "prompts/list":
                return self._handle_list_prompts(mcp_request)
            elif mcp_request["method"] == "notifications/initialized":
                # Notifications don't expect responses according to JSON-RPC 2.0 spec
                self._handle_notifications_initialized(mcp_request)
                return self.NO_RESPONSE
            else:
                return cast(
                    Dict[str, Any],
                    MCPResponseSchema().dump(
                        {
                            "id": mcp_request.get("id"),
                            "error_code": MCPErrorCode.METHOD_NOT_FOUND.value,
                            "error_message": (
                                f"Method '{mcp_request['method']}' not found"
                            ),
                        }
                    ),
                )

        except Exception as e:
            # Try to extract request ID if possible
            request_id = None
            try:
                if message_data and "id" in message_data:
                    request_id = message_data["id"]
            except Exception:
                pass

            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {
                        "id": request_id,
                        "error_code": MCPErrorCode.INTERNAL_ERROR.value,
                        "error_message": str(e),
                    }
                ),
            )

    def _handle_initialize(self, mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": {"name": self.server_name, "version": self.server_version},
        }
        return cast(
            Dict[str, Any],
            MCPResponseSchema().dump({"id": mcp_request.get("id"), "result": result}),
        )

    def _handle_list_tools(
        self, mcp_request: Dict[str, Any], request: Optional[Request] = None
    ) -> Dict[str, Any]:
        """Handle MCP tools/list request."""
        # Get all tools
        all_tools = list(self.tools.values())

        # Filter tools based on permissions if configured
        if self.config and self.config.filter_forbidden_tools and request:
            tools_list = self._filter_accessible_tools(all_tools, request)
        else:
            tools_list = [tool.to_dict() for tool in all_tools]

        result = {"tools": tools_list}
        return cast(
            Dict[str, Any],
            MCPResponseSchema().dump({"id": mcp_request.get("id"), "result": result}),
        )

    def _filter_accessible_tools(
        self, tools: List[MCPTool], request: Request
    ) -> List[Dict[str, Any]]:
        """Filter tools based on user permissions.

        Args:
            tools: List of all available tools
            request: Current pyramid request for permission checking

        Returns:
            List of tool dictionaries for accessible tools only
        """
        accessible_tools = []

        # Get security policy
        policy = request.registry.queryUtility(ISecurityPolicy)
        if not policy:
            # No security policy configured, return all tools
            logger.debug("No security policy found, returning all tools")
            return [tool.to_dict() for tool in tools]

        logger.debug(f"Filtering {len(tools)} tools based on permissions")

        for tool in tools:
            # Check if tool is accessible
            is_accessible = self._check_tool_permission(tool, request, policy)

            if is_accessible:
                accessible_tools.append(tool.to_dict())

        logger.debug(
            f"Filtered tools: {len(accessible_tools)}/{len(tools)} tools accessible"
        )
        return accessible_tools

    def _check_tool_permission(
        self, tool: MCPTool, request: Request, policy: Any
    ) -> bool:
        """Check if current user has permission to access a specific tool.

        Args:
            tool: Tool to check
            request: Current pyramid request
            policy: Security policy instance

        Returns:
            True if user has permission, False otherwise
        """
        # Check if tool has permission requirement
        if not tool.permission:
            # No permission required, tool is accessible
            logger.debug(
                f"Tool '{tool.name}' has no permission requirement, accessible"
            )
            return True

        try:
            # Use the existing subrequest creation logic - it handles everything!
            subrequest = self._create_unified_tool_subrequest(request, tool, {})

            # Check permission using security policy
            has_permission = policy.permits(
                subrequest, subrequest.context, tool.permission
            )

            logger.debug(
                f"Permission check for tool '{tool.name}': "
                f"permission='{tool.permission}', result={has_permission}"
            )

            return bool(has_permission)

        except (AttributeError, TypeError, ValueError) as e:
            # If there's any error in permission checking, deny access for security
            logger.warning(f"Error in permission check for tool '{tool.name}': {e}")
            return False

    def _handle_call_tool(
        self, mcp_request: Dict[str, Any], request: Request
    ) -> Dict[str, Any]:
        """Handle tools/call requests using unified subrequest approach."""

        # Validate basic parameters
        if not mcp_request.get("params"):
            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {
                        "id": mcp_request.get("id"),
                        "error_code": MCPErrorCode.INVALID_PARAMS.value,
                        "error_message": "Missing parameters",
                    }
                ),
            )

        params = mcp_request.get("params", {})
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})

        if not tool_name:
            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {
                        "id": mcp_request.get("id"),
                        "error_code": MCPErrorCode.INVALID_PARAMS.value,
                        "error_message": "Tool name is required",
                    }
                ),
            )

        if tool_name not in self.tools:
            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {
                        "id": mcp_request.get("id"),
                        "error_code": MCPErrorCode.METHOD_NOT_FOUND.value,
                        "error_message": f"Tool '{tool_name}' not found",
                    }
                ),
            )

        tool = self.tools[tool_name]
        logger.info(f"📞 MCP Tool Call: {tool_name} with arguments: {tool_args}")
        logger.debug(f"📞 Tool arguments: {tool_args}")

        try:
            # Extract auth credentials from request body
            # (only for tools with security schemas)
            auth_token = None
            if "auth_token" in tool_args and tool.security:
                # Only remove auth_token if tool has security schema
                auth_token = tool_args.pop("auth_token")
            elif "auth_token" in tool_args and not tool.security:
                # For tools without security schema, peek at the token
                # but don't remove it
                auth_token = tool_args.get("auth_token")

            # Create unified subrequest for both route-based and manual tools
            subrequest = self._create_unified_tool_subrequest(request, tool, tool_args)

            # Add auth headers to subrequest
            if auth_token:
                auth_header = f"Bearer {auth_token}"
                subrequest.headers["Authorization"] = auth_header
            elif (
                self.config
                and not self.config.expose_auth_as_params
                and "Authorization" in request.headers
            ):
                # When expose_auth_as_params=false, use HTTP header auth directly
                auth_header = request.headers["Authorization"]
                subrequest.headers["Authorization"] = auth_header

            # Execute subrequest - Pyramid handles auth, permissions, and execution
            response = request.invoke_subrequest(subrequest)

            # Transform response to MCP context format using schema
            schema = MCPContextResultSchema()

            # Prepare data for schema transformation
            view_info = {
                "tool_name": tool_name,
                "url": f"/_internal/mcp-tool/{tool_name}",
            }

            # Include llm_context_hint if the tool has one
            if tool.llm_context_hint:
                view_info["llm_context_hint"] = tool.llm_context_hint

            schema_data = {
                "response": response,
                "view_info": view_info,
            }

            # Transform and return directly using schema
            mcp_result = schema.dump(schema_data)
            logger.debug("✅ Transformed response to MCP context format")
            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {"id": mcp_request.get("id"), "result": mcp_result}
                ),
            )

        except Exception as e:
            logger.error(f"❌ Error executing tool '{tool_name}': {str(e)}")

            return cast(
                Dict[str, Any],
                MCPResponseSchema().dump(
                    {
                        "id": mcp_request.get("id"),
                        "error_code": MCPErrorCode.INTERNAL_ERROR.value,
                        "error_message": f"Tool execution failed: {str(e)}",
                    }
                ),
            )

    def _create_unified_tool_subrequest(
        self, request: Request, tool: MCPTool, tool_args: Dict[str, Any]
    ) -> Request:
        """Create a subrequest for tool execution.

        This method properly handles path parameter substitution for route-based tools
        and creates appropriate subrequests for both manual and route-based tools.

        Args:
            request: Original pyramid request
            tool: Tool to execute
            tool_args: Tool arguments

        Returns:
            Subrequest configured for tool execution
        """

        # Get the tool's URL pattern (either route-based or manual tool view)
        if hasattr(tool, "_internal_route_path") and tool._internal_route_path:
            route_pattern = tool._internal_route_path
        else:
            # Fallback for route-based tools without stored path
            route_pattern = f"/mcp/tools/{tool.name}"

        # Get the HTTP method
        method = "POST"  # Default for manual tools
        if hasattr(tool, "_internal_route_method") and tool._internal_route_method:
            method = tool._internal_route_method

        # Extract path parameters from route pattern
        path_params = re.findall(r"\{([^}]+)\}", route_pattern)
        path_param_names = [param.split(":")[0] for param in path_params]

        # Separate path parameters from other parameters
        path_values = {}
        remaining_args = {}

        # Handle special querystring parameter first
        args_copy = tool_args.copy()
        if "querystring" in args_copy:
            querystring_value = args_copy.pop("querystring")
            if isinstance(querystring_value, dict):
                remaining_args.update(querystring_value)

        # Separate path parameters from remaining args
        for key, value in args_copy.items():
            if key in path_param_names:
                path_values[key] = value
            else:
                remaining_args[key] = value

        # Build the actual URL by replacing path parameters in the pattern
        tool_url = route_pattern
        logger.debug(f"🔧 DEBUG: Original route pattern: {route_pattern}")
        logger.debug(f"🔧 DEBUG: Path values to substitute: {path_values}")

        for param_name, param_value in path_values.items():
            # Replace {param} and {param:regex} patterns with actual values
            old_url = tool_url
            tool_url = re.sub(
                rf"\{{{param_name}(?::[^}}]+)?\}}", str(param_value), tool_url
            )
            logger.debug(f"🔧 DEBUG: Replaced {param_name}: '{old_url}' -> '{tool_url}'")

        # Handle remaining parameters based on HTTP method
        if method.upper() in ["POST", "PUT", "PATCH"]:
            # For POST/PUT/PATCH, put remaining args in body
            body_data = remaining_args
            query_params: Dict[str, str] = {}
        else:
            # For GET/DELETE, use remaining args as query parameters
            body_data = {}
            query_params = {}
            for key, value in remaining_args.items():
                if isinstance(value, (str, int, float, bool)):
                    query_params[key] = str(value)

        # Add query parameters to URL if any
        if query_params:
            query_string = urlencode(query_params)
            if "?" in tool_url:
                tool_url += f"&{query_string}"
            else:
                tool_url += f"?{query_string}"
            logger.debug(f"Added query params: {query_string}")

        # Log the final URL being constructed
        logger.debug(f"FINAL URL: {tool_url}")

        # Create subrequest with resolved URL using Pyramid's routing
        subrequest = Request.blank(tool_url)
        subrequest.method = method.upper()

        # Copy environment and context from parent request
        self._copy_request_context(request, subrequest)

        logger.info(f"Created subrequest: {subrequest.method} {subrequest.url}")
        logger.debug(f"Subrequest context: {type(subrequest.context).__name__}")

        # Set up request body for POST/PUT/PATCH requests
        if method.upper() in ["POST", "PUT", "PATCH"] and body_data:
            subrequest.content_type = "application/json"
            body_json = json.dumps(body_data).encode("utf-8")
            subrequest.body = body_json

        return subrequest

    def _copy_request_context(self, request: Request, subrequest: Request) -> None:
        """Copy security and context information from parent request to subrequest.

        Args:
            request: Original pyramid request
            subrequest: Subrequest to configure
        """
        # Copy registry for access to security policy and other utilities
        if hasattr(request, "registry"):
            subrequest.registry = request.registry

        # Copy registry and security policy (let security policy compute the rest)
        subrequest.registry = request.registry

        # Copy transaction manager if available (for pyramid_tm integration)
        if hasattr(request, "tm"):
            subrequest.tm = request.tm

        # Copy important environ variables (but not request-specific ones)
        request_specific_keys = {
            "PATH_INFO",
            "SCRIPT_NAME",
            "REQUEST_METHOD",
            "QUERY_STRING",
            "CONTENT_TYPE",
            "CONTENT_LENGTH",
            "REQUEST_URI",
            "RAW_URI",
        }

        for key, value in request.environ.items():
            if key not in request_specific_keys:
                subrequest.environ[key] = value

        # CRITICAL: Resolve the route to get proper context and matchdict
        # This ensures context factories are applied and ACLs work for ALL tools
        mapper = request.registry.getUtility(IRoutesMapper)
        route_info = mapper(subrequest)

        # Get route and set matchdict
        route = route_info["route"]
        subrequest.matchdict = route_info["match"]

        # Get context factory from route or use fallback factories
        context_factory = getattr(route, "factory", None)
        if context_factory is None:
            # Try IDefaultRootFactory first
            context_factory = request.registry.queryUtility(IDefaultRootFactory)
        if context_factory is None:
            # Try IRootFactory as second fallback
            context_factory = request.registry.queryUtility(IRootFactory)
        if context_factory is None:
            # Final fallback: create a simple context dict
            subrequest.context = {}
        else:
            # Create the context using the factory
            subrequest.context = context_factory(subrequest)

    def _handle_list_resources(self, mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP resources/list request."""
        # For now, return empty resources list
        # This can be extended to support MCP resources in the future
        result: Dict[str, Any] = {"resources": []}
        return cast(
            Dict[str, Any],
            MCPResponseSchema().dump({"id": mcp_request.get("id"), "result": result}),
        )

    def _handle_list_prompts(self, mcp_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP prompts/list request."""
        # For now, return empty prompts list
        # This can be extended to support MCP prompts in the future
        result: Dict[str, Any] = {"prompts": []}
        return cast(
            Dict[str, Any],
            MCPResponseSchema().dump({"id": mcp_request.get("id"), "result": result}),
        )

    def _handle_notifications_initialized(
        self, mcp_request: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle MCP notifications/initialized request."""
        # This is a notification - no response should be sent for notifications
        # But since our current architecture expects a response, we'll return None
        # and handle this special case in the main handler
        return None


def create_json_schema_from_marshmallow(schema_class: type) -> Dict[str, Any]:
    """Convert a Marshmallow schema to JSON Schema format without instantiation.

    Args:
        schema_class: A Marshmallow Schema class

    Returns:
        A dictionary representing the JSON Schema
    """
    # Use _declared_fields to avoid instantiation and registry pollution
    json_schema: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    # Get fields without instantiation
    if hasattr(schema_class, "_declared_fields"):
        fields_dict = schema_class._declared_fields
    else:
        # Not a Marshmallow schema class
        return json_schema

    for field_name, field_obj in fields_dict.items():
        field_schema = {"type": "string"}  # Default to string

        if isinstance(field_obj, fields.Integer):
            field_schema["type"] = "integer"
        elif isinstance(field_obj, fields.Float):
            field_schema["type"] = "number"
        elif isinstance(field_obj, fields.Boolean):
            field_schema["type"] = "boolean"
        elif isinstance(field_obj, fields.List):
            field_schema["type"] = "array"
        elif isinstance(field_obj, fields.Dict):
            field_schema["type"] = "object"

        if hasattr(field_obj, "metadata") and "description" in field_obj.metadata:
            field_schema["description"] = field_obj.metadata["description"]

        # Use data_key if available, otherwise use field_name
        schema_field_name = getattr(field_obj, "data_key", None) or field_name
        json_schema["properties"][schema_field_name] = field_schema

        if field_obj.required:
            json_schema["required"].append(schema_field_name)

    return json_schema
