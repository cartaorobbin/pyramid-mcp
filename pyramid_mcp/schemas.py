"""
Pyramid MCP Schemas Module

This module provides Marshmallow schemas for validating and structuring
HTTP request data in MCP tools. These schemas represent the proper structure
of HTTP requests with path parameters, query parameters, request body, and headers.
"""

from typing import Any, Dict, Optional

import marshmallow.fields as fields
from marshmallow import Schema, missing, pre_dump, validate


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
        # CRITICAL ISOLATION: Get nested schema class WITHOUT triggering instances
        nested_schema_class = _get_nested_schema_class_safely(field)
        if nested_schema_class:
            # Use completely isolated introspection that never creates instances
            nested_info = _safe_nested_schema_introspection(nested_schema_class)
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


def _get_nested_schema_class_safely(nested_field: Any) -> Optional[type]:
    """Get the schema class from a Nested field WITHOUT triggering instances.

    This function avoids accessing field.schema which triggers automatic instance
    creation in Marshmallow. Instead, it inspects the field's internal attributes
    to extract the schema class directly.
    """
    import marshmallow

    # CRITICAL: The 'nested' attribute contains the schema class without instances
    if hasattr(nested_field, "nested"):
        schema_attr = nested_field.nested
        if isinstance(schema_attr, type) and issubclass(
            schema_attr, marshmallow.Schema
        ):
            return schema_attr

    # Fallback: Check other possible attribute names
    for attr_name in ["_schema", "schema_class", "_schema_class", "_nested"]:
        if hasattr(nested_field, attr_name):
            attr_value = getattr(nested_field, attr_name)
            if isinstance(attr_value, type) and issubclass(
                attr_value, marshmallow.Schema
            ):
                return attr_value

    # If we can't find the schema class safely, return None
    # This is better than risking instance creation
    return None


def _safe_nested_schema_introspection(schema_or_class: Any) -> Dict[str, Any]:
    """Safely introspect nested schema without global state pollution.

    This function ensures complete isolation by:
    1. Never accessing .fields property of instances
    2. Never creating new schema instances
    3. Always working with schema classes and _declared_fields
    4. Never modifying existing instances or global state
    """
    import marshmallow

    # SAFETY: Always get the schema CLASS, never work with instances
    schema_class = None
    if isinstance(schema_or_class, type) and issubclass(
        schema_or_class, marshmallow.Schema
    ):
        # Already a schema class
        schema_class = schema_or_class
    elif isinstance(schema_or_class, marshmallow.Schema):
        # Schema instance - get its class WITHOUT touching the instance
        schema_class = schema_or_class.__class__
    else:
        # Not a Marshmallow schema
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

    # SAFETY: Use _declared_fields - no instantiation or .fields access
    if not hasattr(schema_class, "_declared_fields"):
        return {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

    fields_dict = schema_class._declared_fields
    properties = {}
    required = []

    # SAFETY: Recursively process fields with isolation
    for field_name, field_obj in fields_dict.items():
        field_info = convert_marshmallow_field_to_mcp_type(field_obj)

        # Use data_key if available, otherwise use field name
        key_name = getattr(field_obj, "data_key", None) or field_name
        properties[key_name] = field_info

        # Check if field is required
        if getattr(field_obj, "required", False):
            required.append(key_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


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

    properties = fields.Dict(load_default=dict)
    required = fields.List(fields.Str(), load_default=list)
    type = fields.Str(load_default="object")
    additionalProperties = fields.Bool(load_default=False)

    @pre_dump
    def extract_schema_info(self, schema: Any, **kwargs: Any) -> Dict[str, Any]:
        """Extract field information from a Marshmallow schema with complete isolation.

        CRITICAL: This method MUST provide complete isolation to prevent global
        state pollution that could affect Cornice or other schema usage.
        """
        # Use the completely isolated introspection function
        return _safe_nested_schema_introspection(schema)


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


class MCPContentItemSchema(Schema):
    """Schema for individual MCP content items."""

    type = fields.Str(
        required=True,
        metadata={"description": "Content type (e.g., 'text', 'image', 'resource')"},
    )
    text = fields.Str(
        allow_none=True,
        metadata={"description": "Text content for type=text"},
    )
    data = fields.Raw(
        allow_none=True,
        metadata={"description": "Raw data content for other types"},
    )
    mimeType = fields.Str(
        allow_none=True,
        metadata={"description": "MIME type for binary content"},
    )

    @pre_dump
    def transform_content_item(self, obj: Any, **kwargs: Any) -> Dict[str, Any]:
        """Transform raw content into proper MCP content item format."""
        # Handle case where obj is already a proper content item
        if isinstance(obj, dict) and "type" in obj:
            return obj

        # Transform raw content into content item
        if isinstance(obj, dict):
            # For dict content, provide both text representation and raw data
            return {
                "type": "text",
                "text": str(obj),
                "data": obj,
            }
        else:
            # For simple content, just text
            return {
                "type": "text",
                "text": str(obj),
            }


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

    # OpenAI compatibility: Add simple content field at top level
    content = fields.List(
        fields.Nested(MCPContentItemSchema),
        required=True,
        metadata={"description": "List of content items (OpenAI compatibility)"},
    )

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

            # Check for custom llm_context_hint from view predicate
            custom_llm_hint = view_info.get("llm_context_hint") if view_info else None
            default_llm_hint = "This is a response from a Pyramid API"

            # Trust the predicate, but handle edge cases for direct testing
            # In normal operation, the predicate handles normalization
            # In direct tests, we need basic fallback for truly empty values
            if custom_llm_hint is not None and str(custom_llm_hint).strip():
                llm_context_hint = str(custom_llm_hint).strip()
            else:
                llm_context_hint = default_llm_hint

            ret = {
                "content": [
                    content
                ],  # Schema will transform content via MCPContentItemSchema
                "type": "mcp/context",
                "version": "1.0",
                "tags": ["api_response"],
                "llm_context_hint": llm_context_hint,
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
                "content": [
                    content
                ],  # Schema will transform content via MCPContentItemSchema
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


class MCPRequestSchema(Schema):
    """Schema for MCP JSON-RPC request validation and serialization."""

    jsonrpc = fields.Str(validate=validate.Equal("2.0"), load_default="2.0")
    method = fields.Str(required=True)
    params = fields.Dict(allow_none=True, load_default=None)
    id = fields.Raw(allow_none=True, load_default=None)


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
