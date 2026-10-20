"""
Tool decorator for creating MCP tools as Cornice services.

This module provides the @tool decorator that creates Cornice services for MCP tools
with automatic schema generation from function signatures. This replaces the old
approach of creating Pyramid views with metadata.
"""

import inspect
from typing import Any, Callable, Dict, Optional, get_type_hints

import venusian  # type: ignore[import-untyped]
from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields

from pyramid_mcp.result import MCPToolResult
from pyramid_mcp.security import MCPSecurityType

_INJECTED_PARAMETERS = {"self", "request", "pyramid_request"}


def _generate_marshmallow_schema_from_signature(func: Callable) -> type:
    """Generate Marshmallow schema class from function signature for Cornice validation.

    Args:
        func: Function to inspect

    Returns:
        Marshmallow schema class
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    schema_fields = {}

    for param_name, param in sig.parameters.items():
        if param_name in _INJECTED_PARAMETERS:
            continue

        param_type = type_hints.get(param_name, str)

        # Convert Python types to Marshmallow fields
        field: fields.Field
        if param_type == int:
            field = fields.Int()
        elif param_type == float:
            field = fields.Float()
        elif param_type == bool:
            field = fields.Bool()
        else:
            field = fields.Str()

        # Set required if no default value
        if param.default == inspect.Parameter.empty:
            field.required = True
        else:
            field.required = False

        schema_fields[param_name] = field

    # Create dynamic schema class
    schema_class = type(f"{func.__name__.title()}Schema", (Schema,), schema_fields)
    return schema_class


class tool:
    """A function decorator which creates MCP tools as Cornice services.

    This decorator follows the same pattern as Pyramid's @view_config decorator,
    using Venusian for deferred registration until config.scan() is called.

    Unlike the previous version, this creates Cornice services instead of Pyramid views,
    enabling automatic schema validation and unified discovery through introspection.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        permission: Pyramid permission requirement for this tool
        context: Context or context factory to use for permission checking
        security: Authentication parameter specification for this tool
        output_schema: Marshmallow schema advertised as outputSchema
        meta: Mapping advertised as the tool ``_meta`` (for example a UI URI)

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
            permission = settings.get("permission")
            context_factory = settings.get("context")
            security = settings.get("security")
            output_schema = settings.get("output_schema")
            meta = settings.get("meta")
            title = settings.get("title")
            annotations = settings.get("annotations")

            # Generate unique route name and path for this tool
            # NOTE: Don't use "mcp_" prefix as introspection excludes those routes
            route_name = f"tool_{tool_name}"
            route_path = f"/mcp/tools/{tool_name}"

            # Generate schema class from function signature
            schema_class = _generate_marshmallow_schema_from_signature(wrapped)

            # Create Cornice service with optional context factory
            service_init_kwargs = {
                "name": route_name,
                "path": route_path,
                "description": tool_description or f"MCP tool: {tool_name}",
            }

            # Add context factory if specified
            if context_factory:
                service_init_kwargs["factory"] = context_factory

            service = Service(**service_init_kwargs)

            # Create service method with validation, error handling, and permission
            service_kwargs = {
                "schema": schema_class,
                "validators": (marshmallow_body_validator,),
            }

            # Add permission if specified
            if permission:
                service_kwargs["permission"] = permission

            # Add security configuration for introspection using configurable parameter
            if security:
                # Get the security parameter name from settings
                security_param = config.registry.settings.get(
                    "mcp.security_parameter", "mcp_security"
                )
                # Convert security schema to string representation for introspection
                security_type_str = security.__class__.__name__.replace(
                    "Schema", ""
                )  # BearerAuthSchema -> BearerAuth
                service_kwargs[security_param] = security_type_str
            if output_schema is not None:
                service_kwargs["mcp_output_schema"] = output_schema
            if meta is not None:
                service_kwargs["mcp_meta"] = meta
            if title is not None:
                service_kwargs["mcp_title"] = title
            if annotations is not None:
                service_kwargs["mcp_annotations"] = annotations

            @service.post(**service_kwargs)  # type: ignore[misc]
            def tool_endpoint(request: Any) -> Any:
                """Tool endpoint function."""
                try:
                    # Extract validated arguments from request
                    validated_data = request.validated or {}
                    arguments = _call_arguments(wrapped, request, validated_data)

                    # Call the original function with validated arguments
                    result = wrapped(**arguments)
                    if isinstance(result, MCPToolResult):
                        return result.to_payload()

                    # Return just the result - protocol handler will wrap it
                    return result

                except Exception as e:
                    # Return error message directly - protocol handler will wrap it
                    return f"Error: {str(e)}"

            # Set the tool endpoint's docstring to match the original function
            if tool_description:
                tool_endpoint.__doc__ = tool_description

            # Register the service with config
            # Cornice services are registered and auto-discovered by introspection
            config.add_cornice_service(service)

        # Attach venusian decorator for deferred registration
        self.venusian.attach(wrapped, callback, category="pyramid_mcp", depth=depth + 1)

        return wrapped


def _call_arguments(func: Callable, request: Any, validated: Any) -> Dict[str, Any]:
    """Build the tool call, injecting the Pyramid request when asked for."""
    available = dict(validated)
    arguments: Dict[str, Any] = {}
    for name in inspect.signature(func).parameters:
        if name in ("request", "pyramid_request"):
            arguments[name] = request
        elif name in available:
            arguments[name] = available[name]
    return arguments


class resource:
    """Register a text resource served by ``resources/list`` and ``resources/read``.

    The handler receives the Pyramid request and returns a string, or a dict
    with ``text`` and an optional ``mimeType``. This decorator does not know
    what the text is.
    """

    venusian = venusian

    def __init__(
        self,
        uri: str,
        mime_type: str = "text/plain",
        description: Optional[str] = None,
        name: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store the resource identity. Registration happens at scan time."""
        self.uri = uri
        self.mime_type = mime_type
        self.description = description
        self.name = name
        self.meta = meta

    def __call__(self, wrapped: Callable) -> Callable:
        """Attach deferred registration of this resource."""
        uri = self.uri
        mime_type = self.mime_type
        description = self.description
        resource_name = self.name
        meta = self.meta

        def callback(context: Any, name: str, ob: Callable[..., Any]) -> None:
            """Register the resource once pyramid_mcp is included."""
            config = context.config
            pyramid_mcp = getattr(config.registry, "pyramid_mcp", None)
            if pyramid_mcp is None:
                return
            from pyramid_mcp.protocol import MCPResource

            pyramid_mcp.protocol_handler.register_resource(
                MCPResource(
                    uri=uri,
                    mime_type=mime_type,
                    handler=wrapped,
                    name=resource_name or wrapped.__name__,
                    description=description or wrapped.__doc__,
                    meta=meta,
                )
            )

        self.venusian.attach(wrapped, callback, category="pyramid_mcp", depth=1)
        return wrapped
