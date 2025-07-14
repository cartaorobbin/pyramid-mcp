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
