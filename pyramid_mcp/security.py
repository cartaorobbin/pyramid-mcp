"""
MCP Security Authentication Parameters

This module provides authentication parameter specifications for MCP tools
that need to receive authentication credentials as tool parameters rather
than through HTTP headers. This is particularly useful for Claude AI
clients that cannot pass HTTP headers.

Uses Marshmallow schemas for consistency with the rest of the pyramid-mcp
codebase.
"""

import base64
from typing import Any, Dict, Optional, Union

from marshmallow import Schema, fields, validate


class BearerAuthSchema(Schema):
    """Schema for Bearer token authentication parameters.

    This schema defines the structure for tools that need Bearer token authentication
    passed as a parameter rather than through HTTP headers.

    Example:
        @tool(
            name="secure_api",
            description="Call secure API",
            mcp_security=BearerAuthSchema()
        )
        def call_secure_api(data: str, auth_token: str) -> dict:
            # Use auth_token for authentication
            headers = {"Authorization": f"Bearer {auth_token}"}
            # ... make API call
    """

    auth_token = fields.Str(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Bearer authentication token"},
    )


class BasicAuthSchema(Schema):
    """Schema for HTTP Basic authentication parameters.

    This schema defines the structure for tools that need Basic authentication
    credentials passed as parameters rather than through HTTP headers.

    Example:
        @tool(
            name="secure_ftp",
            description="Access FTP server",
            mcp_security=BasicAuthSchema()
        )
        def access_ftp(path: str, username: str, password: str) -> dict:
            # Use username and password for authentication
            # ... make FTP connection
    """

    username = fields.Str(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Username for basic authentication"},
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1),
        metadata={"description": "Password for basic authentication"},
    )


# Union type for all supported authentication types
MCPSecurityType = Union[BearerAuthSchema, BasicAuthSchema]


def merge_auth_into_schema(
    base_schema: Optional[Dict[str, Any]],
    security: Optional[MCPSecurityType],
    expose_auth_as_params: bool = True,
) -> Dict[str, Any]:
    """Merge authentication parameters into a tool's input schema.

    This function takes a base JSON schema and adds authentication parameter
    fields based on the authentication specification.

    Args:
        base_schema: Base JSON schema for the tool or None
        security: Authentication specification (BearerAuthSchema or BasicAuthSchema)
        expose_auth_as_params: Whether to expose authentication parameters in the schema

    Returns:
        Updated JSON schema with authentication parameters
        (if expose_auth_as_params=True)

    Example:
        base = {
            "type": "object",
            "properties": {"data": {"type": "string"}},
            "required": ["data"]
        }

        auth = BearerAuthSchema()
        result = merge_auth_into_schema(base, auth)
        # result["properties"]["auth_token"] = {"type": "string", "description": "..."}
        # result["required"] = ["data", "auth_token"]
    """
    # Import here to avoid circular imports
    from pyramid_mcp.protocol import create_json_schema_from_marshmallow

    # Start with base schema or create new one
    merged_schema = (
        base_schema.copy()
        if base_schema
        else {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }
    )

    # Ensure properties exist
    if "properties" not in merged_schema:
        merged_schema["properties"] = {}

    # Ensure required list exists
    if "required" not in merged_schema:
        merged_schema["required"] = []

    # Add authentication parameters if specified and enabled
    if security and expose_auth_as_params:
        # Generate JSON schema from the auth schema
        auth_json_schema = create_json_schema_from_marshmallow(security.__class__)

        # Merge authentication properties into the base schema
        if "properties" in auth_json_schema:
            merged_schema["properties"].update(auth_json_schema["properties"])

        # Merge required fields
        if "required" in auth_json_schema:
            for field in auth_json_schema["required"]:
                if field not in merged_schema["required"]:
                    merged_schema["required"].append(field)

    return merged_schema


def extract_auth_credentials(
    tool_args: Dict[str, Any], security: Optional[MCPSecurityType]
) -> Dict[str, Any]:
    """Extract authentication credentials from tool arguments.

    This function extracts authentication credentials from the tool arguments
    and returns them in a standardized format for use in HTTP headers or
    other authentication mechanisms.

    Args:
        tool_args: Dictionary of tool arguments passed by the client
        mcp_security: Authentication specification used by the tool

    Returns:
        Dictionary with extracted authentication credentials

    Example:
        args = {"data": "hello", "auth_token": "abc123"}
        auth = BearerAuthSchema()
        result = extract_auth_credentials(args, auth)
        # result = {"bearer_token": "abc123"}
    """
    if not security:
        return {}

    credentials = {}

    if isinstance(security, BearerAuthSchema):
        token = tool_args.get("auth_token")
        if token:
            credentials["bearer_token"] = token

    elif isinstance(security, BasicAuthSchema):
        username = tool_args.get("username")
        password = tool_args.get("password")
        if username and password:
            credentials["username"] = username
            credentials["password"] = password

    return credentials


def create_auth_headers(
    credentials: Dict[str, Any], security: Optional[MCPSecurityType]
) -> Dict[str, str]:
    """Create HTTP headers from authentication credentials.

    This function converts extracted authentication credentials into HTTP headers
    that can be used for API calls or other HTTP requests.

    Args:
        credentials: Authentication credentials from extract_auth_credentials()
        mcp_security: Authentication specification

    Returns:
        Dictionary of HTTP headers for authentication

    Example:
        credentials = {"bearer_token": "abc123"}
        auth_spec = BearerAuthSchema()
        headers = create_auth_headers(credentials, auth_spec)
        # headers = {"Authorization": "Bearer abc123"}
    """
    if not security or not credentials:
        return {}

    headers = {}

    if isinstance(security, BearerAuthSchema):
        token = credentials.get("bearer_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"

    elif isinstance(security, BasicAuthSchema):
        username = credentials.get("username")
        password = credentials.get("password")
        if username and password:
            credentials_str = f"{username}:{password}"
            encoded = base64.b64encode(credentials_str.encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

    return headers


def validate_auth_credentials(
    tool_args: Dict[str, Any], security: Optional[MCPSecurityType]
) -> Optional[Dict[str, Any]]:
    """Validate authentication credentials using the schema.

    This function validates the authentication parameters in the tool arguments
    using the Marshmallow schema validation.

    Args:
        tool_args: Dictionary of tool arguments passed by the client
        security: Authentication specification used by the tool

    Returns:
        Error dict with 'type', 'message', and 'details' if validation fails,
        None if validation succeeds

    Example:
        args = {"data": "hello", "auth_token": "abc123"}
        auth = BearerAuthSchema()
        error = validate_auth_credentials(args, auth)
        # error is None if valid, dict with error info if invalid
    """
    if not security:
        return None

    try:
        # Extract only the auth-related parameters
        auth_data = {}
        missing_fields = []
        empty_fields = []

        if isinstance(security, BearerAuthSchema):
            token = tool_args.get("auth_token")
            if token is None:
                missing_fields.append("auth_token")
            elif not token or (isinstance(token, str) and not token.strip()):
                empty_fields.append("auth_token")
            else:
                auth_data["auth_token"] = token

        elif isinstance(security, BasicAuthSchema):
            username = tool_args.get("username")
            password = tool_args.get("password")

            if username is None:
                missing_fields.append("username")
            elif not username or (isinstance(username, str) and not username.strip()):
                empty_fields.append("username")
            else:
                auth_data["username"] = username

            if password is None:
                missing_fields.append("password")
            elif not password or (isinstance(password, str) and not password.strip()):
                empty_fields.append("password")
            else:
                auth_data["password"] = password

        # Handle missing required fields
        if missing_fields:
            return {
                "type": "missing_credentials",
                "message": "Required authentication parameters are missing",
                "details": {"missing_fields": missing_fields},
            }

        # Handle empty required fields
        if empty_fields:
            return {
                "type": "empty_credentials",
                "message": "Required authentication parameters cannot be empty",
                "details": {"empty_fields": empty_fields},
            }

        # Validate using the schema
        security.load(auth_data)
        return None

    except Exception as e:
        # Handle Marshmallow validation errors
        from marshmallow import ValidationError

        if isinstance(e, ValidationError):
            return {
                "type": "validation_error",
                "message": "Authentication parameters are invalid",
                "details": {"validation_errors": e.messages},
            }

        # Handle other unexpected errors
        return {
            "type": "authentication_error",
            "message": "Authentication validation failed",
            "details": {"error": "Unexpected validation error"},
        }


def remove_auth_from_tool_args(
    tool_args: Dict[str, Any], security: Optional[MCPSecurityType]
) -> Dict[str, Any]:
    """Remove authentication parameters from tool arguments.

    This ensures that authentication credentials are not passed to the actual
    tool handler function, keeping them separate from business logic.

    Args:
        tool_args: Original tool arguments dictionary
        mcp_security: Authentication specification used by the tool

    Returns:
        New dictionary with authentication parameters removed

    Example:
        args = {"data": "hello", "auth_token": "abc123"}
        auth = BearerAuthSchema()
        clean_args = remove_auth_from_tool_args(args, auth)
        # clean_args = {"data": "hello"}
    """
    if not security:
        return tool_args

    # Create a copy and remove auth parameters
    clean_args = tool_args.copy()

    if isinstance(security, BearerAuthSchema):
        clean_args.pop("auth_token", None)

    elif isinstance(security, BasicAuthSchema):
        clean_args.pop("username", None)
        clean_args.pop("password", None)

    return clean_args
