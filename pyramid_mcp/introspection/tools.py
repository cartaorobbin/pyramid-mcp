"""
Tool Generation Module

This module handles the conversion of routes to MCP tools,
including tool naming, description generation, and input schema creation.
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from pyramid_mcp.protocol import MCPTool
from pyramid_mcp.schemas import BodySchema, PathParameterSchema

logger = logging.getLogger(__name__)

# HTTP methods that should not be exposed as MCP tools
EXCLUDED_HTTP_METHODS = {"OPTIONS", "HEAD"}


def convert_route_to_tools(
    route_info: Dict[str, Any],
    config: Any,
    permission_extractor: Callable,
    route_handler_creator: Callable,
    security_converter: Callable,
    schema_extractor: Callable,
    schema_location_determiner: Callable,
    location_from_structure_determiner: Callable,
) -> List[MCPTool]:
    """Convert a route to one or more MCP tools.

    Args:
        route_info: Route information dictionary
        config: MCP configuration
        permission_extractor: Function to extract permissions from views
        route_handler_creator: Function to create route handlers
        security_converter: Function to convert security types to schemas
        schema_extractor: Function to extract Marshmallow schema info
        schema_location_determiner: Function to determine parameter location
        location_from_structure_determiner: Function to determine location from schema

    Returns:
        List of MCP tools for this route
    """
    tools: List[MCPTool] = []
    route_name = route_info.get("name", "")
    route_pattern = route_info.get("pattern", "")
    views = route_info.get("views", [])

    # If no views, skip this route
    if not views:
        return tools

    # Group views by HTTP method
    views_by_method: Dict[str, List[Dict[str, Any]]] = {}
    for view in views:
        # Use view's request methods, or fall back to route's request methods
        methods = view.get("request_methods")
        if not methods:
            # For Cornice services, check if we have explicit method definitions
            cornice_service = route_info.get("cornice_service")
            if cornice_service:
                # Extract defined methods from Cornice service
                defined_methods = cornice_service.get("defined_methods", [])
                if defined_methods:
                    methods = defined_methods
                else:
                    # Extract methods from service definitions
                    definitions = cornice_service.get("definitions", [])
                    methods = list(set(method for method, _, _ in definitions))

            # Fall back to route's request methods only if not a Cornice service
            if not methods:
                route_methods = route_info.get("request_methods")
                if route_methods:
                    methods = list(route_methods)
                else:
                    methods = ["GET"]  # Final fallback only for non-Cornice routes
        elif isinstance(methods, str):
            # If methods is a string, convert to list
            methods = [methods]
        elif not isinstance(methods, list):
            # If methods is some other iterable, convert to list
            methods = list(methods)

        for method in methods:
            if method not in views_by_method:
                views_by_method[method] = []
            views_by_method[method].append(view)

    # Create MCP tool for each HTTP method
    for method, method_views in views_by_method.items():
        # Skip OPTIONS and HEAD methods - they are not meaningful as MCP tools
        if method.upper() in EXCLUDED_HTTP_METHODS:
            continue

        # 🐛 FIX: Find the view that matches this specific route pattern
        # Instead of just using the first view, find the one that belongs
        # to this route
        view = None
        for candidate_view in method_views:
            # Check if this view belongs to the current route by comparing
            # route names
            candidate_route_name = candidate_view.get("route_name", "")
            if candidate_route_name == route_name:
                view = candidate_view
                break

        # Fallback to first view if no exact match found (backward compatibility)
        if view is None:
            view = method_views[0]

        view_callable = view.get("callable")

        if not view_callable:
            continue

        # Generate tool name for regular Pyramid views and Cornice services
        tool_name = generate_tool_name(route_name, method, route_pattern)

        # Generate tool description
        description = generate_tool_description(
            route_name, method, route_pattern, view_callable, view
        )

        # Generate input schema from route pattern and view signature
        input_schema = generate_input_schema(
            route_pattern,
            view_callable,
            method,
            view,
            schema_extractor,
            schema_location_determiner,
            location_from_structure_determiner,
        )

        # Extract security configuration from view info using
        # configurable parameter
        security_type = view.get(config.security_parameter)
        security = None
        if security_type:
            security = security_converter(security_type)

        # Extract permission using the proper method that handles all cases
        permission = permission_extractor(view)

        # Extract llm_context_hint from view info
        llm_context_hint = view.get("llm_context_hint")

        # Create MCP tool
        tool = MCPTool(
            name=tool_name,
            description=description,
            input_schema=input_schema,
            handler=route_handler_creator(route_info, view, method),
            permission=permission,
            security=security,
            llm_context_hint=llm_context_hint,
            config=config,
        )

        # Store original route pattern and method for route-based tools
        route_pattern = route_info.get("pattern", "")
        if route_pattern:
            tool._internal_route_path = route_pattern
            tool._internal_route_method = method.upper()

        tools.append(tool)

    return tools


def generate_tool_name(route_name: str, method: str, pattern: str) -> str:
    """Generate a descriptive tool name from route information.

    Args:
        route_name: Pyramid route name
        method: HTTP method
        pattern: Route pattern

    Returns:
        Generated tool name
    """
    # Special handling for tool decorator routes
    if route_name and route_name.startswith("tool_"):
        # For tool decorator routes, use the tool name without prefixes
        return route_name[5:]  # Remove "tool_" prefix

    # Start with route name, make it more descriptive
    if route_name:
        base_name = route_name
    else:
        # Generate from pattern
        base_name = pattern.replace("/", "_").replace("{", "").replace("}", "")
        base_name = re.sub(r"[^a-zA-Z0-9_]", "", base_name)

    # Add HTTP method context
    method_lower = method.lower()
    if method_lower == "get":
        if "list" in base_name or base_name.endswith("s"):
            prefix = "list"
        else:
            prefix = "get"
    elif method_lower == "post":
        prefix = "create"
    elif method_lower == "put":
        prefix = "update"
    elif method_lower == "patch":
        prefix = "modify"
    elif method_lower == "delete":
        prefix = "delete"
    else:
        prefix = method_lower

    # Combine prefix with base name intelligently
    if base_name.startswith(prefix):
        return base_name
    elif base_name.endswith("_" + prefix):
        return base_name
    else:
        return f"{prefix}_{base_name}"


def generate_tool_description(
    route_name: str,
    method: str,
    pattern: str,
    view_callable: Callable,
    view_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate a descriptive tool description.

    Args:
        route_name: Pyramid route name
        method: HTTP method
        pattern: Route pattern
        view_callable: View callable function
        view_info: View introspectable information (optional)

    Returns:
        Generated description with priority order:
        1. mcp_description from view_config parameter
        2. View function docstring
        3. Auto-generated description from route info
    """
    # 1. First check for explicit MCP description from view_config parameter
    mcp_desc = view_info.get("mcp_description") if view_info else None
    if mcp_desc and isinstance(mcp_desc, str) and mcp_desc.strip():
        return str(mcp_desc.strip())

    # 2. Fallback to function attribute (for backward compatibility)
    if view_callable is not None and hasattr(view_callable, "mcp_description"):
        mcp_desc = getattr(view_callable, "mcp_description")
        if isinstance(mcp_desc, str) and mcp_desc.strip():
            return mcp_desc.strip()

    # 2. Try to get description from view docstring (existing behavior)
    if (
        view_callable is not None
        and hasattr(view_callable, "__doc__")
        and view_callable.__doc__
    ):
        doc = view_callable.__doc__.strip()
        if doc:
            return doc

    # 3. Generate description from route information (existing behavior)
    action_map = {
        "GET": "Retrieve",
        "POST": "Create",
        "PUT": "Update",
        "PATCH": "Modify",
        "DELETE": "Delete",
    }

    action = action_map.get(method.upper(), method.upper())
    resource = route_name.replace("_", " ").title()

    return f"{action} {resource} via {method} {pattern}"


def generate_input_schema(
    pattern: str,
    view_callable: Callable,
    method: str,
    view_info: Optional[Dict[str, Any]] = None,
    schema_extractor: Optional[Callable] = None,
    schema_location_determiner: Optional[Callable] = None,
    location_from_structure_determiner: Optional[Callable] = None,
) -> Optional[Dict[str, Any]]:
    """Generate JSON schema for tool input based on HTTP request structure.

    Creates a schema that properly represents HTTP requests with separate
    sections for path parameters, query parameters, request body, and headers.

    Args:
        pattern: Route pattern (e.g., '/users/{id}')
        view_callable: View callable function
        method: HTTP method
        view_info: View information including Cornice metadata
        schema_extractor: Function to extract Marshmallow schema info
        schema_location_determiner: Function to determine parameter location
        location_from_structure_determiner: Function to determine location from schema

    Returns:
        JSON schema dictionary using HTTPRequestSchema structure or None
    """
    # Initialize with empty HTTP request structure
    http_request: Dict[str, Any] = {
        "path": [],
        "query": [],
        "body": [],
        "headers": {},
    }

    # Check for Marshmallow schema in Cornice metadata first
    if view_info and "cornice_metadata" in view_info and schema_extractor:
        cornice_metadata = view_info["cornice_metadata"]

        method_specific = cornice_metadata.get("method_specific", {})

        # Look for schema in method-specific metadata
        if method.upper() in method_specific:
            method_info = method_specific[method.upper()]
            schema = method_info.get("schema")

            if schema:
                # Extract Marshmallow schema and structure it properly
                schema_info = schema_extractor(schema)
                if schema_info:
                    # Check if schema has explicit structure fields
                    schema_properties = schema_info.get("properties", {})
                    has_explicit_structure = any(
                        field in schema_properties
                        for field in ["path", "querystring", "body"]
                    )

                    if has_explicit_structure:
                        # Schema has explicit structure - use it directly
                        result: Dict[str, Any] = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                            "additionalProperties": False,
                        }

                        # Copy explicit structure fields to their proper places
                        for field_name in ["path", "querystring", "body"]:
                            if field_name in schema_properties:
                                result["properties"][field_name] = schema_properties[
                                    field_name
                                ]

                        return result

                    # Schema lacks explicit structure - apply defaults
                    # BUT ALWAYS include path parameters from route pattern
                    schema_result: Dict[str, Any] = {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    }

                    # Add path parameters from route pattern
                    path_params = re.findall(r"\{([^}]+)\}", pattern)
                    if path_params:
                        path_properties = {}
                        for param in path_params:
                            # Remove any regex constraints (e.g., {id:\d+} -> id)
                            clean_param = param.split(":")[0]
                            path_properties[clean_param] = {
                                "type": "string",
                                "description": f"Path parameter: {clean_param}",
                            }

                        schema_result["properties"]["path"] = {
                            "type": "object",
                            "properties": path_properties,
                            "required": list(path_properties.keys()),
                            "additionalProperties": False,
                            "description": "Path parameters for the request",
                        }

                    # Determine parameter placement based on Cornice validators,
                    # not HTTP method guessing
                    schema_properties = schema_info.get("properties", {})
                    if schema_properties and schema_location_determiner:
                        # Get validators to determine where parameters should go
                        validators = method_info.get("validators", [])

                        # Determine placement based on actual Cornice validators
                        parameter_location = schema_location_determiner(
                            validators, method_info
                        )

                        # Handle generic validator case by examining schema
                        # structure
                        if (
                            parameter_location == "schema_dependent"
                            and location_from_structure_determiner
                        ):
                            # For generic marshmallow_validator, examine the schema
                            # to determine appropriate parameter location
                            schema = method_info.get("schema")
                            parameter_location = location_from_structure_determiner(
                                schema, method_info
                            )

                        # Map parameter location to proper description format
                        description_map = {
                            "body": "Request body parameters",
                            "querystring": "Query parameters for the request",
                            "path": "Path parameters for the request",
                        }

                        # Use consistent schema processing for all parameter locations
                        schema_result["properties"][parameter_location] = {
                            "type": "object",
                            "properties": schema_properties,
                            "required": schema_info.get("required", []),
                            "additionalProperties": False,
                            "description": description_map.get(
                                parameter_location,
                                f"{parameter_location.title()} parameters "
                                "for the request",
                            ),
                        }

                    return schema_result
                else:
                    logger.warning(
                        f"Schema extraction returned empty result for "
                        f"{method} {pattern}"
                    )
            else:
                logger.debug(f"No schema found in method info for {method} {pattern}")
        else:
            logger.debug(
                f"Method {method.upper()} not found in method_specific "
                f"for {pattern}"
            )

    # Extract path parameters from route pattern
    path_params = re.findall(r"\{([^}]+)\}", pattern)
    for param in path_params:
        # Remove any regex constraints (e.g., {id:\d+} -> id)
        clean_param = param.split(":")[0]

        # Use PathParameterSchema to create proper path parameter
        path_param_schema = PathParameterSchema()
        path_param_data = path_param_schema.load(
            {
                "name": clean_param,
                "value": "",  # Will be filled by the tool caller
                "type": "string",
                "description": f"Path parameter: {clean_param}",
            }
        )
        http_request["path"].append(path_param_data)

    # Add request body fields for methods that typically have body data
    if method.upper() in ["POST", "PUT", "PATCH"]:
        # Use BodySchema to create proper body field
        body_schema = BodySchema()
        body_field_data = body_schema.load(
            {
                "name": "data",
                "value": "",
                "type": "string",
                "description": "Request body data",
                "required": True,
            }
        )
        http_request["body"].append(body_field_data)

    # Convert to proper JSON schema format maintaining HTTP structure
    if http_request["path"] or http_request["query"] or http_request["body"]:
        # Create proper JSON schema structure that maintains HTTP semantics
        json_schema: Dict[str, Any] = {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        }

        # Add all parameter types using the same structure
        add_parameter_object_to_schema(
            json_schema,
            http_request["path"],
            "path",
            "Path parameters for the request",
        )
        add_parameter_object_to_schema(
            json_schema,
            http_request["query"],
            "querystring",
            "Query parameters for the request",
        )
        add_parameter_object_to_schema(
            json_schema, http_request["body"], "body", "Request body parameters"
        )

        return json_schema

    return None


def add_parameter_object_to_schema(
    json_schema: Dict[str, Any],
    param_list: List[Dict[str, Any]],
    object_name: str,
    description: str,
) -> None:
    """Add a parameter object (path, query, or body) to the JSON schema.

    Args:
        json_schema: The main JSON schema to modify
        param_list: List of parameters to add
        object_name: Name of the object (path, querystring, body)
        description: Description for the parameter object
    """
    if param_list:
        properties: Dict[str, Any] = {}
        required: List[str] = []

        for param in param_list:
            param_name = param["name"]
            param_schema = {
                "type": param.get("type", "string"),
                "description": param.get("description", f"{description}: {param_name}"),
            }

            # Add default value if present
            if "default" in param:
                param_schema["default"] = param["default"]

            properties[param_name] = param_schema

            # Add to required if no default value and required is True
            if "default" not in param and param.get("required", False):
                required.append(param_name)

        # Create nested object
        json_schema["properties"][object_name] = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
            "description": description,
        }
