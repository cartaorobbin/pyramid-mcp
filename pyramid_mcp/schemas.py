"""
Pyramid MCP Schemas Module

This module provides Marshmallow schemas for validating and structuring
HTTP request data in MCP tools. These schemas represent the proper structure
of HTTP requests with path parameters, query parameters, request body, and headers.
"""

from typing import Any, Dict

import marshmallow.fields as fields
from marshmallow import Schema, missing, pre_dump


class PathParameterSchema(Schema):
    """Schema for path parameters in HTTP requests."""

    name = fields.Str(required=True, metadata={"description": "Parameter name"})
    value = fields.Str(required=True, metadata={"description": "Parameter value"})
    type = fields.Str(load_default="string", metadata={"description": "Parameter type"})
    description = fields.Str(
        load_default="", metadata={"description": "Parameter description"}
    )
    default = fields.Raw(
        load_default=None, metadata={"description": "Default parameter value"}
    )


class QueryParameterSchema(Schema):
    """Schema for query parameters in HTTP requests."""

    name = fields.Str(required=True, metadata={"description": "Parameter name"})
    value = fields.Str(required=True, metadata={"description": "Parameter value"})
    type = fields.Str(load_default="string", metadata={"description": "Parameter type"})
    description = fields.Str(
        load_default="", metadata={"description": "Parameter description"}
    )
    default = fields.Raw(
        load_default=None, metadata={"description": "Default parameter value"}
    )
    required = fields.Bool(
        load_default=True, metadata={"description": "Is parameter required"}
    )


class BodySchema(Schema):
    """Schema for request body fields."""

    name = fields.Str(required=True, metadata={"description": "Field name"})
    value = fields.Str(required=True, metadata={"description": "Field value"})
    type = fields.Str(load_default="string", metadata={"description": "Field type"})
    description = fields.Str(
        load_default="", metadata={"description": "Field description"}
    )
    required = fields.Bool(
        load_default=True, metadata={"description": "Is field required"}
    )


class HTTPRequestSchema(Schema):
    """Schema for HTTP request structure with path, query, body, and headers."""

    path = fields.List(fields.Nested(PathParameterSchema), load_default=[])
    query = fields.List(fields.Nested(QueryParameterSchema), load_default=[])
    body = fields.List(fields.Nested(BodySchema), load_default=[])
    headers = fields.Dict(
        keys=fields.Str(),
        values=fields.Str(),
        load_default={},
        metadata={"description": "HTTP headers"},
    )
    content_type = fields.Str(
        load_default="application/json",
        metadata={"description": "Content type of request"},
    )
    authorization = fields.Str(
        load_default="",
        metadata={"description": "Authorization header value"},
    )


def convert_marshmallow_field_to_mcp_type(field: Any) -> Dict[str, Any]:
    """Convert a Marshmallow field to MCP parameter type information."""
    import marshmallow.fields as fields_module

    field_info: Dict[str, Any] = {}

    # Map Marshmallow field types to MCP types
    # Check more specific types first to avoid inheritance issues
    if isinstance(field, fields_module.Email):
        field_info["type"] = "string"
        field_info["format"] = "email"
    elif isinstance(field, fields_module.UUID):
        field_info["type"] = "string"
        field_info["format"] = "uuid"
    elif isinstance(field, fields_module.DateTime):
        field_info["type"] = "string"
        field_info["format"] = "date-time"
    elif isinstance(field, fields_module.Date):
        field_info["type"] = "string"
        field_info["format"] = "date"
    elif isinstance(field, fields_module.Time):
        field_info["type"] = "string"
        field_info["format"] = "time"
    elif isinstance(field, fields_module.Url):
        field_info["type"] = "string"
        field_info["format"] = "uri"
    elif isinstance(field, fields_module.Integer):
        field_info["type"] = "integer"
    elif isinstance(field, fields_module.Float):
        field_info["type"] = "number"
    elif isinstance(field, fields_module.Boolean):
        field_info["type"] = "boolean"
    elif isinstance(field, fields_module.List):
        field_info["type"] = "array"
        # Get inner field type
        if hasattr(field, "inner") and field.inner:
            inner_field_info = convert_marshmallow_field_to_mcp_type(field.inner)
            # Remove None values from inner field info
            if isinstance(inner_field_info, dict):
                inner_field_info = {
                    k: v for k, v in inner_field_info.items() if v is not None
                }
                field_info["items"] = inner_field_info
    elif isinstance(field, fields_module.Nested):
        field_info["type"] = "object"
        # For nested fields, try to extract nested schema info
        if hasattr(field, "schema") and field.schema:
            # Use MCPSchemaInfoSchema to extract nested schema info
            nested_schema_converter = MCPSchemaInfoSchema()
            nested_info = nested_schema_converter.extract_schema_info(field.schema)
            if nested_info and isinstance(nested_info, dict):
                field_info.update(nested_info)
    elif isinstance(field, fields_module.Dict):
        field_info["type"] = "object"
        field_info["additionalProperties"] = True
    elif isinstance(field, fields_module.String):
        field_info["type"] = "string"
    else:
        # Default to string for unknown field types
        field_info["type"] = "string"

    # Add description if available (from field metadata)
    if hasattr(field, "metadata") and field.metadata:
        description = field.metadata.get("description")
        if description:
            field_info["description"] = description

    # Add validation constraints
    _add_field_validation_constraints(field, field_info)

    return field_info


def _add_field_validation_constraints(field: Any, field_info: Dict[str, Any]) -> None:
    """Add validation constraints from field to field_info dict."""
    import marshmallow.validate as validate

    # Handle string length constraints
    if hasattr(field, "validate"):
        validators = (
            field.validate if isinstance(field.validate, list) else [field.validate]
        )

        for validator in validators:
            if isinstance(validator, validate.Length):
                if validator.min is not None:
                    if field_info.get("type") == "string":
                        field_info["minLength"] = validator.min
                    elif field_info.get("type") == "array":
                        field_info["minItems"] = validator.min

                if validator.max is not None:
                    if field_info.get("type") == "string":
                        field_info["maxLength"] = validator.max
                    elif field_info.get("type") == "array":
                        field_info["maxItems"] = validator.max

            elif isinstance(validator, validate.Range):
                if validator.min is not None:
                    field_info["minimum"] = validator.min
                if validator.max is not None:
                    field_info["maximum"] = validator.max

            elif isinstance(validator, validate.OneOf):
                field_info["enum"] = list(validator.choices)

    # Handle default values
    if hasattr(field, "load_default") and field.load_default is not None:
        # Convert marshmallow missing sentinel to None
        if field.load_default != missing:
            field_info["default"] = field.load_default

    # Also check dump_default and the older default field
    if hasattr(field, "dump_default") and field.dump_default is not None:
        if field.dump_default != missing:
            field_info["default"] = field.dump_default
    elif hasattr(field, "default") and field.default is not None:
        if field.default != missing:
            field_info["default"] = field.default


class MCPSchemaInfoSchema(Schema):
    """Schema for MCP schema information structure."""

    properties = fields.Dict(missing=dict)
    required = fields.List(fields.Str(), missing=list)
    type = fields.Str(missing="object")
    additionalProperties = fields.Bool(missing=False)

    @pre_dump
    def extract_schema_info(self, schema: Any, **kwargs: Any) -> Dict[str, Any]:
        """Extract field information from a Marshmallow schema."""
        import marshmallow

        # Handle schema class vs instance
        if isinstance(schema, type):
            # If it's a class, instantiate it
            try:
                schema_instance = schema()
            except Exception:
                # If instantiation fails, return empty info
                return {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                }
        else:
            schema_instance = schema

        # Check if it's actually a Marshmallow schema
        if not isinstance(schema_instance, marshmallow.Schema):
            return {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            }

        # Start with basic schema structure
        schema_data: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

        # Convert each field to MCP format
        for field_name, field_obj in schema_instance.fields.items():
            field_info = convert_marshmallow_field_to_mcp_type(field_obj)
            # Remove None values from field info
            if isinstance(field_info, dict):
                field_info = {k: v for k, v in field_info.items() if v is not None}
                schema_data["properties"][field_name] = field_info

            # Check if field is required
            if field_obj.required:
                schema_data["required"].append(field_name)

        return schema_data


# =============================================================================
# 🔧 MCP CONTEXT SCHEMAS
# =============================================================================
# Schemas for the new MCP context format that replaces the old content array format


class MCPSourceSchema(Schema):
    """Schema for MCP context source information."""

    kind = fields.Str(
        required=True,
        metadata={"description": "Source kind (e.g., 'rest_api', 'database', 'file')"},
    )
    name = fields.Str(
        required=True, metadata={"description": "Human-readable source name"}
    )
    url = fields.Str(
        allow_none=True, metadata={"description": "Source URL if applicable"}
    )
    fetched_at = fields.DateTime(
        format="iso",
        required=True,
        metadata={"description": "When the data was fetched"},
    )
    additional_info = fields.Dict(
        allow_none=True,
        metadata={"description": "Additional source-specific information"},
    )


class MCPRepresentationSchema(Schema):
    """Schema for MCP context representation."""

    format = fields.Str(
        required=True,
        metadata={"description": "Data format (e.g., 'raw_json', 'text', 'xml')"},
    )
    content = fields.Raw(
        required=True, metadata={"description": "The actual data content"}
    )
    encoding = fields.Str(
        allow_none=True, metadata={"description": "Content encoding if applicable"}
    )


class MCPContextResultSchema(Schema):
    """Schema for the new MCP context result format."""

    type = fields.Str(
        required=True,
        dump_default="mcp/context",
        metadata={"description": "MCP result type"},
    )
    version = fields.Str(
        required=True,
        dump_default="1.0",
        metadata={"description": "MCP context version"},
    )
    source = fields.Nested(
        MCPSourceSchema,
        required=True,
        metadata={"description": "Information about the data source"},
    )
    representation = fields.Nested(
        MCPRepresentationSchema,
        required=True,
        metadata={"description": "The data representation"},
    )
    tags = fields.List(
        fields.Str(),
        allow_none=True,
        metadata={"description": "Tags for categorizing the context"},
    )
    llm_context_hint = fields.Str(
        allow_none=True,
        metadata={"description": "Hint for the LLM about how to use this context"},
    )
    confidence = fields.Float(
        allow_none=True,
        metadata={"description": "Confidence score for the data (0.0-1.0)"},
    )
    expires_at = fields.DateTime(
        format="iso",
        allow_none=True,
        metadata={"description": "When this context expires"},
    )

    @pre_dump
    def transform_to_mcp_context(self, obj: Any, **kwargs: Any) -> Dict[str, Any]:
        """Transform input data to MCP context format before dumping.

        This handles both:
        1. Pyramid HTTP responses (with response + view_info)
        2. Simple tool results (with content + metadata)
        """
        from datetime import datetime, timezone

        fetched_at = datetime.now(timezone.utc)

        # Case 1: Pyramid HTTP response format
        response = obj.get("response")
        view_info = obj.get("view_info")

        if response is not None and view_info is not None:
            # Handle Pyramid HTTP response objects
            if (
                hasattr(response, "headers")
                and response.headers.get("Content-Type") == "application/json"
            ):
                content_format = "raw_json"
                content = response.json
            else:
                content_format = "text"
                content = response.text if hasattr(response, "text") else str(response)

            ret = {
                "type": "mcp/context",
                "version": "1.0",
                "tags": ["api_response"],
                "llm_context_hint": "This is a response from a Pyramid API",
                "source": {
                    "kind": "rest_api",
                    "name": "PyramidAPI",
                    "fetched_at": fetched_at,
                    "url": view_info.get("url")
                    or "https://legal-entity-rest.io.geru.com.br",
                },
                "representation": {"format": content_format, "content": content},
            }
        else:
            # Case 2: Simple tool result format
            content = obj.get("content")
            source_kind = obj.get("source_kind", "mcp_tool")
            source_name = obj.get("source_name", "MCP Tool")
            tags = obj.get("tags", ["tool_response"])
            llm_hint = obj.get("llm_context_hint", "Result from an MCP tool")

            # Determine content format based on type
            if isinstance(content, dict):
                content_format = "raw_json"
            else:
                content_format = "text"

            ret = {
                "type": "mcp/context",
                "version": "1.0",
                "tags": tags,
                "llm_context_hint": llm_hint,
                "source": {
                    "kind": source_kind,
                    "name": source_name,
                    "fetched_at": fetched_at,
                },
                "representation": {"format": content_format, "content": content},
            }

        return ret


# =============================================================================
# 🔧 MCP PROTOCOL SCHEMAS
# =============================================================================
# Core MCP protocol schemas for JSON-RPC messages


class MCPErrorSchema(Schema):
    """Marshmallow schema for MCP protocol error."""

    code = fields.Int(required=True, metadata={"description": "Error code"})
    message = fields.Str(required=True, metadata={"description": "Error message"})
    data = fields.Dict(
        allow_none=True, metadata={"description": "Additional error data"}
    )


class MCPResponseSchema(Schema):
    """Marshmallow schema for MCP JSON-RPC response."""

    jsonrpc = fields.Str(
        required=True, dump_default="2.0", metadata={"description": "JSON-RPC version"}
    )
    id = fields.Raw(allow_none=True, metadata={"description": "Request ID"})
    result = fields.Raw(allow_none=True, metadata={"description": "Response result"})
    error = fields.Nested(
        MCPErrorSchema, allow_none=True, metadata={"description": "Response error"}
    )

    @pre_dump
    def format_mcp_response(self, obj: Any, **kwargs: Any) -> Dict[str, Any]:
        """Format MCP response, handling both success and error cases."""
        if isinstance(obj, dict):
            data = obj.copy()
        else:
            # Convert object attributes to dict
            data = {}
            for field_name in self.fields:
                if hasattr(obj, field_name):
                    data[field_name] = getattr(obj, field_name)

        # Ensure jsonrpc version is set
        if "jsonrpc" not in data:
            data["jsonrpc"] = "2.0"

        # Handle error construction from separate error fields
        if "error_code" in data or "error_message" in data:
            error_data: Dict[str, Any] = {}

            if "error_code" in data:
                error_data["code"] = data.pop("error_code")
            if "error_message" in data:
                error_data["message"] = data.pop("error_message")
            if "error_data" in data:
                error_data["data"] = data.pop("error_data")

            # Only create error if we have required fields
            if "code" in error_data and "message" in error_data:
                data["error"] = error_data
                # Remove result if we have an error
                data.pop("result", None)

        return data
