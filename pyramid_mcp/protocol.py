"""
MCP Protocol Implementation

This module implements the Model Context Protocol (MCP) using JSON-RPC 2.0
messages. It provides the core protocol functionality for communication
between MCP clients and servers.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Union

from marshmallow import Schema, fields


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
        result = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result


@dataclass
class MCPResponse:
    """Represents an MCP JSON-RPC response."""

    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[MCPError] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            result["id"] = self.id
        if self.error:
            result["error"] = self.error.to_dict()
        elif self.result is not None:
            result["result"] = self.result
        return result


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool format."""
        result = {"name": self.name}
        if self.description:
            result["description"] = self.description
        if self.input_schema:
            result["inputSchema"] = self.input_schema
        return result


class MCPProtocolHandler:
    """Handles MCP protocol messages and routing."""

    def __init__(self, server_name: str, server_version: str):
        """Initialize the MCP protocol handler.

        Args:
            server_name: Name of the MCP server
            server_version: Version of the MCP server
        """
        self.server_name = server_name
        self.server_version = server_version
        self.tools: Dict[str, MCPTool] = {}
        self.capabilities: Dict[str, Any] = {"tools": {}, "resources": {}, "prompts": {}}

    def register_tool(self, tool: MCPTool) -> None:
        """Register an MCP tool.

        Args:
            tool: The MCPTool to register
        """
        self.tools[tool.name] = tool
        # Update capabilities to indicate we have tools
        self.capabilities["tools"] = {}

    def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP message.

        Args:
            message_data: The parsed JSON message

        Returns:
            The response message as a dictionary
        """
        try:
            request = MCPRequest.from_dict(message_data)

            # Route to appropriate handler
            if request.method == "initialize":
                return self._handle_initialize(request)
            elif request.method == "tools/list":
                return self._handle_list_tools(request)
            elif request.method == "tools/call":
                return self._handle_call_tool(request)
            else:
                error = MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND.value,
                    message=f"Method '{request.method}' not found",
                )
                response = MCPResponse(id=request.id, error=error)
                return response.to_dict()

        except Exception as e:
            error = MCPError(code=MCPErrorCode.INTERNAL_ERROR.value, message=str(e))
            response = MCPResponse(error=error)
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

    def _handle_call_tool(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle MCP tools/call request."""
        params = request.params or {}
        tool_name = params.get("name")

        if not tool_name:
            error = MCPError(
                code=MCPErrorCode.INVALID_PARAMS.value,
                message="Missing required parameter 'name'",
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        tool = self.tools.get(tool_name)
        if not tool:
            error = MCPError(
                code=MCPErrorCode.METHOD_NOT_FOUND.value,
                message=f"Tool '{tool_name}' not found",
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        if not tool.handler:
            error = MCPError(
                code=MCPErrorCode.INTERNAL_ERROR.value,
                message=f"Tool '{tool_name}' has no handler",
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()

        try:
            # Call the tool handler with arguments
            tool_args = params.get("arguments", {})
            result = tool.handler(**tool_args)

            # Wrap result in MCP format
            mcp_result = {"content": [{"type": "text", "text": str(result)}]}

            response = MCPResponse(id=request.id, result=mcp_result)
            return response.to_dict()

        except Exception as e:
            error = MCPError(
                code=MCPErrorCode.INTERNAL_ERROR.value,
                message=f"Tool execution failed: {str(e)}",
            )
            response = MCPResponse(id=request.id, error=error)
            return response.to_dict()


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
    json_schema = {"type": "object", "properties": {}, "required": []}

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
