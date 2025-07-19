"""
MCP Protocol Implementation

This module implements the Model Context Protocol (MCP) using JSON-RPC 2.0
messages. It provides the core protocol functionality for communication
between MCP clients and servers.
"""

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set, Union

from marshmallow import Schema, fields
from pyramid.interfaces import ISecurityPolicy
from pyramid.request import Request

from pyramid_mcp.security import (
    MCPSecurityType,
    create_auth_headers,
    extract_auth_credentials,
    merge_auth_into_schema,
    remove_auth_from_tool_args,
    validate_auth_credentials,
)

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
class MCPError:
    """Represents an MCP protocol error."""

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"code": self.code, "message": self.message}
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class MCPRequest:
    """Represents an MCP JSON-RPC request."""

    jsonrpc: str = "2.0"
    method: str = ""
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create MCPRequest from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        response_dict: Dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            response_dict["params"] = self.params
        if self.id is not None:
            response_dict["id"] = self.id
        return response_dict


@dataclass
class MCPResponse:
    """Represents an MCP JSON-RPC response."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        response_dict: Dict[str, Any] = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            response_dict["id"] = self.id
        if self.error:
            response_dict["error"] = self.error.to_dict()
        elif self.result is not None:
            response_dict["result"] = self.result
        return response_dict


# MCP Tool-related schemas
class MCPToolInputSchema(Schema):
    """Schema for MCP tool input parameter."""

    type = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    properties = fields.Dict(allow_none=True)
    required = fields.List(fields.Str(), allow_none=True)


class MCPToolSchema(Schema):
    """Schema for MCP tool definition."""

    name = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    inputSchema = fields.Nested(MCPToolInputSchema, allow_none=True)


class MCPCapabilitiesSchema(Schema):
    """Schema for MCP server capabilities."""

    tools = fields.Dict(allow_none=True)
    resources = fields.Dict(allow_none=True)
    prompts = fields.Dict(allow_none=True)


class MCPServerInfoSchema(Schema):
    """Schema for MCP server information."""

    name = fields.Str(required=True)
    version = fields.Str(required=True)


class MCPInitializeResultSchema(Schema):
    """Schema for MCP initialize response."""

    protocolVersion = fields.Str(required=True)
    capabilities = fields.Nested(MCPCapabilitiesSchema, required=True)
    serverInfo = fields.Nested(MCPServerInfoSchema, required=True)


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
        tool_dict["inputSchema"] = merge_auth_into_schema(base_schema, self.security)

        return tool_dict


class MCPProtocolHandler:
    """Handles MCP protocol messages and routing."""

    # Special sentinel value to indicate no response should be sent
    NO_RESPONSE = object()

    def __init__(self, server_name: str, server_version: str):
        """Initialize the MCP protocol handler.

        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
        """
        self.server_name = server_name
        self.server_version = server_version
        self.tools: Dict[str, MCPTool] = {}
        self.capabilities: Dict[str, Any] = {
            "tools": {"listChanged": True},
            "resources": {"subscribe": False, "listChanged": True},
            "prompts": {"listChanged": True},
        }
        # Track used tool names to prevent collisions
        self._used_tool_names: Set[str] = set()

    def register_tool(self, tool: MCPTool) -> None:
        """Register an MCP tool.

        Args:
            tool: The MCPTool to register
        """
        original_name = tool.name

        # Sanitize the tool name to ensure Claude Desktop compatibility
        sanitized_name = sanitize_tool_name(tool.name, self._used_tool_names)

        # Update the tool with the sanitized name
        if sanitized_name != original_name:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"Tool name '{original_name}' sanitized to '{sanitized_name}' "
                f"for Claude Desktop compatibility"
            )
            tool.name = sanitized_name

        # Register the tool
        self.tools[sanitized_name] = tool
        self._used_tool_names.add(sanitized_name)

        # Update capabilities to indicate we have tools
        self.capabilities["tools"] = {}

    def handle_message(
        self,
        message_data: Dict[str, Any],
        pyramid_request: Request,
    ) -> Union[Dict[str, Any], object]:
        """Handle an incoming MCP message.

        Args:
            message_data: The parsed JSON message
            pyramid_request: The pyramid request

        Returns:
            The response message as a dictionary, or NO_RESPONSE for notifications
        """
        try:
            request = MCPRequest.from_dict(message_data)

            # Route to appropriate handler
            if request.method == "initialize":
                return self._handle_initialize(request)
            elif request.method == "tools/list":
                return self._handle_list_tools(request)
            elif request.method == "tools/call":
                return self._handle_call_tool(request, pyramid_request)
            elif request.method == "resources/list":
                return self._handle_list_resources(request)
            elif request.method == "prompts/list":
                return self._handle_list_prompts(request)
            elif request.method == "notifications/initialized":
                # Notifications don't expect responses according to JSON-RPC 2.0 spec
                self._handle_notifications_initialized(request)
                return self.NO_RESPONSE
            else:
                error = MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND.value,
                    message=f"Method '{request.method}' not found",
                )
                response = MCPResponse(id=request.id, error=error)
                return response.to_dict()

        except Exception as e:
            # Try to extract request ID if possible
            request_id = None
            try:
                if message_data and "id" in message_data:
                    request_id = message_data["id"]
            except Exception:
                pass

            error = MCPError(code=MCPErrorCode.INTERNAL_ERROR.value, message=str(e))
            response = MCPResponse(id=request_id, error=error)
            return response.to_dict()

    def _handle_initialize(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": self.capabilities,
            "serverInfo": {"name": self.server_name, "version": self.server_version},
        }
        response = MCPResponse(id=request.id, result=result)
        return response.to_dict()

    def _handle_list_tools(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP tools/list request."""
        tools_list = [tool.to_dict() for tool in self.tools.values()]
        result = {"tools": tools_list}
        response = MCPResponse(id=request.id, result=result)
        return response.to_dict()

    def _handle_call_tool(
        self, request: MCPRequest, pyramid_request: Request
    ) -> Dict[str, Any]:
        """Handle tools/call requests."""
        import logging

        logger = logging.getLogger(__name__)

        if not request.params:
            error = MCPError(
                code=MCPErrorCode.INVALID_PARAMS.value, message="Missing parameters"
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        tool_name = request.params.get("name")
        tool_args = request.params.get("arguments", {})

        # 🐛 DEBUG: Log MCP tool call details
        logger.info(f"📞 MCP Tool Call: {tool_name}")
        logger.debug(f"📞 Tool arguments: {tool_args}")
        logger.debug(f"📞 Available tools: {list(self.tools.keys())}")

        if not tool_name:
            error = MCPError(
                code=MCPErrorCode.INVALID_PARAMS.value, message="Tool name is required"
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        if tool_name not in self.tools:
            logger.error(f"❌ Tool not found: {tool_name}")
            logger.error(f"❌ Available tools: {list(self.tools.keys())}")
            error = MCPError(
                code=MCPErrorCode.METHOD_NOT_FOUND.value,
                message=f"Tool '{tool_name}' not found",
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        tool = self.tools[tool_name]
        logger.debug(f"📞 Found tool: {tool.name}")
        logger.debug(f"📞 Tool description: {tool.description}")
        logger.debug(f"📞 Tool has security: {tool.security is not None}")

        # Check if tool has a handler
        if not tool.handler:
            logger.error(f"❌ Tool '{tool_name}' has no handler")
            error = MCPError(
                code=MCPErrorCode.INTERNAL_ERROR.value,
                message=f"Tool '{tool_name}' has no handler",
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        # Check if tool has security requirements and permissions
        # For route-based tools, permissions are checked via Pyramid's security system
        # For manual tools, permissions are checked here

        # NOTE: Permission checking is delegated to the tool handler
        # Route-based tools use Pyramid's built-in security system
        # Manual tools can implement their own permission checks

        # Tools without permissions are accessible to everyone
        # Tools with permissions need to be checked based on their type
        has_permission = True
        if tool.permission:
            # Determine if this is a route-based tool or manual tool
            # Route-based tools have handlers created by PyramidIntrospector
            # Manual tools have their original function as the handler
            is_route_based_tool = (
                hasattr(tool.handler, "__name__")
                and tool.handler.__name__ == "handler"
                and hasattr(tool.handler, "__qualname__")
                and "PyramidIntrospector._create_route_handler"
                in tool.handler.__qualname__
            )

            if is_route_based_tool:
                # For route-based tools, let the Pyramid view handle permission checking
                has_permission = True
                logger.debug(
                    f"📞 Route-based tool - permission '{tool.permission}' will be checked by view"
                )
            else:
                # For manual tools, check permission here using Pyramid's security system
                try:
                    security_policy = pyramid_request.registry.queryUtility(
                        ISecurityPolicy
                    )
                    if security_policy:
                        # Check if user has the required permission
                        has_permission = security_policy.permits(
                            pyramid_request, None, tool.permission
                        )
                        logger.debug(
                            f"📞 Manual tool permission check: '{tool.permission}' -> {has_permission}"
                        )
                    else:
                        # No security policy configured - deny access to protected tools
                        has_permission = False
                        logger.debug(
                            f"📞 No security policy configured - denying access to protected tool"
                        )
                except Exception as e:
                    logger.error(f"❌ Error checking permission: {str(e)}")
                    has_permission = False
        else:
            logger.debug(f"📞 Tool has no permission requirement - allowing access")

        if has_permission:
            # Process authentication parameters if tool has security schema
            if tool.security:
                logger.debug(
                    f"📞 Processing authentication for tool with security schema"
                )

                # Validate authentication credentials first
                auth_validation_error = validate_auth_credentials(
                    tool_args, tool.security
                )
                if auth_validation_error:
                    logger.error(
                        f"❌ Authentication validation failed: {auth_validation_error['message']}"
                    )
                    error = MCPError(
                        code=MCPErrorCode.INVALID_PARAMS.value,
                        message=auth_validation_error["message"],
                        data={
                            "authentication_error_type": auth_validation_error["type"],
                            "tool_name": tool_name,
                            "details": auth_validation_error.get("details", {}),
                        },
                    )
                    response = MCPResponse(id=request.id, error=error)
                    return response.to_dict()

                # Extract authentication credentials from tool arguments
                try:
                    auth_credentials = extract_auth_credentials(
                        tool_args, tool.security
                    )
                    logger.debug(
                        f"🔐 Extracted auth credentials: {list(auth_credentials.keys())}"
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to extract auth credentials: {str(e)}")
                    error = MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR.value,
                        message=(
                            "Failed to extract authentication parameters: " f"{str(e)}"
                        ),
                        data={
                            "authentication_error_type": (
                                "credential_extraction_error"
                            ),
                            "tool_name": tool_name,
                        },
                    )
                    response = MCPResponse(id=request.id, error=error)
                    return response.to_dict()

                # Remove authentication parameters from tool arguments
                # This ensures credentials are not passed to the handler function
                try:
                    tool_args = remove_auth_from_tool_args(tool_args, tool.security)
                    logger.debug(
                        f"🔐 Removed auth params from tool args: {list(tool_args.keys())}"
                    )
                except Exception as e:
                    logger.error(f"❌ Failed to remove auth parameters: {str(e)}")
                    error = MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR.value,
                        message=(
                            "Failed to process authentication parameters: " f"{str(e)}"
                        ),
                        data={
                            "authentication_error_type": ("parameter_processing_error"),
                            "tool_name": tool_name,
                        },
                    )
                    response = MCPResponse(id=request.id, error=error)
                    return response.to_dict()

                # Create HTTP headers from authentication credentials
                try:
                    auth_headers = create_auth_headers(auth_credentials, tool.security)
                    logger.debug(f"🔐 Created auth headers: {list(auth_headers.keys())}")
                except Exception as e:
                    logger.error(f"❌ Failed to create auth headers: {str(e)}")
                    error = MCPError(
                        code=MCPErrorCode.INTERNAL_ERROR.value,
                        message=(f"Failed to create authentication headers: {str(e)}"),
                        data={
                            "authentication_error_type": "header_creation_error",
                            "tool_name": tool_name,
                        },
                    )
                    response = MCPResponse(id=request.id, error=error)
                    return response.to_dict()

                # Store auth headers in pyramid_request for handler access
                # Handlers can access these via pyramid_request.mcp_auth_headers
                pyramid_request.mcp_auth_headers = auth_headers
                logger.debug(f"🔐 Stored auth headers in pyramid_request")
            else:
                # No authentication required - set empty headers for consistency
                pyramid_request.mcp_auth_headers = {}
                logger.debug(f"🔐 No auth required - set empty headers")

            # Check if this is a route-based tool that needs pyramid_request
            # (route-based tools have a signature that accepts pyramid_request)
            import inspect

            try:
                sig = inspect.signature(tool.handler)
                # If handler has pyramid_request parameter, pass it
                if "pyramid_request" in sig.parameters:
                    logger.debug(
                        f"🚀 Calling route-based tool handler with pyramid_request"
                    )
                    result = tool.handler(pyramid_request, **tool_args)
                else:
                    logger.debug(
                        f"🚀 Calling manual tool handler without pyramid_request"
                    )
                    result = tool.handler(**tool_args)
            except (ValueError, TypeError):
                # Fallback for handlers without introspectable signature
                logger.debug(f"🚀 Calling tool handler (fallback mode)")
                result = tool.handler(**tool_args)

            # 🐛 DEBUG: Log tool execution result
            logger.debug(f"✅ Tool execution completed")
            logger.debug(f"✅ Result type: {type(result)}")
            logger.debug(
                f"✅ Result preview: {str(result)[:200]}{'...' if len(str(result)) > 200 else ''}"
            )

            # Handle different result formats
            if isinstance(result, dict) and "content" in result:
                # Result is already in MCP format
                mcp_result = result
                logger.debug(f"✅ Result already in MCP format")
            else:
                # Wrap result in MCP format
                mcp_result = {"content": [{"type": "text", "text": str(result)}]}
                logger.debug(f"✅ Wrapped result in MCP format")

            response = MCPResponse(id=request.id, result=mcp_result)
            return response.to_dict()

        error_msg = f"Access denied for tool '{tool_name}'"
        logger.error(f"❌ {error_msg}")
        error = MCPError(
            code=MCPErrorCode.INVALID_PARAMS.value,
            message=error_msg,
        )
        response = MCPResponse(id=request.id, error=error)
        return response.to_dict()

    def _handle_list_resources(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP resources/list request."""
        # For now, return empty resources list
        # This can be extended to support MCP resources in the future
        result: Dict[str, Any] = {"resources": []}
        response = MCPResponse(id=request.id, result=result)
        return response.to_dict()

    def _handle_list_prompts(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP prompts/list request."""
        # For now, return empty prompts list
        # This can be extended to support MCP prompts in the future
        result: Dict[str, Any] = {"prompts": []}
        response = MCPResponse(id=request.id, result=result)
        return response.to_dict()

    def _handle_notifications_initialized(
        self, request: MCPRequest
    ) -> Optional[Dict[str, Any]]:
        """Handle MCP notifications/initialized request."""
        # This is a notification - no response should be sent for notifications
        # But since our current architecture expects a response, we'll return None
        # and handle this special case in the main handler
        return None


def create_json_schema_from_marshmallow(schema_class: type) -> Dict[str, Any]:
    """Convert a Marshmallow schema to JSON Schema format.

    Args:
        schema_class: A Marshmallow Schema class

    Returns:
        A dictionary representing the JSON Schema
    """
    # This is a simplified conversion - a more complete implementation
    # would handle all Marshmallow field types and options
    schema_instance = schema_class()
    json_schema: Dict[str, Any] = {"type": "object", "properties": {}, "required": []}

    for field_name, field_obj in schema_instance.fields.items():
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

        json_schema["properties"][field_name] = field_schema

        if field_obj.required:
            json_schema["required"].append(field_name)

    return json_schema
