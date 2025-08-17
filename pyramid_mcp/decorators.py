"""
Tool decorator for creating MCP tools as Cornice services.

This module provides the @tool decorator that creates Cornice services for MCP tools
with automatic schema generation from function signatures. This replaces the old
approach of creating Pyramid views with metadata.
"""

import inspect
from typing import Any, Callable, Optional, get_type_hints

import venusian  # type: ignore[import-untyped]
from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields

from pyramid_mcp.security import MCPSecurityType


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
        if param_name == "self":
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

            @service.post(**service_kwargs)  # type: ignore[misc]
            def tool_endpoint(request: Any) -> Any:
                """Tool endpoint function."""
                try:
                    # Extract validated arguments from request
                    validated_data = request.validated

                    # Call the original function with validated arguments
                    result = wrapped(**validated_data)

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
