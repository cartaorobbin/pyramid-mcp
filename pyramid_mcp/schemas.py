"""
Pyramid MCP Schemas Module

This module provides Marshmallow schemas for validating and structuring
HTTP request data in MCP tools. These schemas represent the proper structure
of HTTP requests with path parameters, query parameters, request body, and headers.
"""

from marshmallow import Schema, fields


class PathParameterSchema(Schema):
    """Schema for path parameters in HTTP requests."""

    name = fields.Str(required=True, metadata={"description": "Parameter name"})
    value = fields.Str(required=True, metadata={"description": "Parameter value"})
    type = fields.Str(load_default="string", metadata={"description": "Parameter type"})
    description = fields.Str(
        load_default="", metadata={"description": "Parameter description"}
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
        load_default=None,
        allow_none=True,
        metadata={"description": "Default parameter value"},
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
        load_default=False, metadata={"description": "Whether field is required"}
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
