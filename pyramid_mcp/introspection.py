"""
Pyramid Introspection Module

This module provides functionality to discover and analyze Pyramid routes
and convert them into MCP tools. Includes support for Cornice REST framework
to extract enhanced metadata and validation information.
"""

import inspect
import re
from typing import Any, Callable, Dict, List, Optional, Union

from pyramid_mcp.protocol import MCPTool
from pyramid_mcp.security import BearerAuthSchema, BasicAuthSchema


class PyramidIntrospector:
    """Handles introspection of Pyramid applications to discover routes and views."""

    def __init__(self, configurator: Optional[Any] = None):
        """Initialize the introspector.

        Args:
            configurator: Pyramid configurator instance
        """
        self.configurator = configurator

    def discover_routes(self) -> List[Dict[str, Any]]:
        """Discover routes from the Pyramid application.

        Returns:
            List of route information dictionaries containing route metadata,
            view callables, and other relevant information for MCP tool generation.
            Enhanced with Cornice service information when available.
        """
        if not self.configurator:
            return []

        routes_info = []

        try:
            # Get the registry and introspector
            registry = self.configurator.registry
            introspector = registry.introspector

            # Get route mapper for additional route information
            route_mapper = self.configurator.get_routes_mapper()
            route_objects = {route.name: route for route in route_mapper.get_routes()}

            # Get all route introspectables
            route_category = introspector.get_category("routes") or []
            route_introspectables = [item["introspectable"] for item in route_category]

            # Get all view introspectables for cross-referencing
            view_category = introspector.get_category("views") or []
            view_introspectables = [item["introspectable"] for item in view_category]
            view_by_route: Dict[str, List[Any]] = {}
            for view_intr in view_introspectables:
                route_name = view_intr.get("route_name")
                if route_name:
                    if route_name not in view_by_route:
                        view_by_route[route_name] = []
                    view_by_route[route_name].append(view_intr)

            # Discover Cornice services for enhanced metadata
            cornice_services = self._discover_cornice_services(registry)

            # Process each route
            for route_intr in route_introspectables:
                route_name = route_intr.get("name")
                if not route_name:
                    continue

                # Get route object for additional metadata
                route_obj = route_objects.get(route_name)

                # Get associated views
                views = view_by_route.get(route_name, [])

                # Check if this route is managed by a Cornice service
                cornice_service = self._find_cornice_service_for_route(
                    route_name, route_intr.get("pattern", ""), cornice_services
                )

                # Build comprehensive route information
                route_info = {
                    "name": route_name,
                    "pattern": route_intr.get("pattern", ""),
                    "request_methods": route_intr.get("request_methods", []),
                    "factory": route_intr.get("factory"),
                    "predicates": {
                        "xhr": route_intr.get("xhr"),
                        "request_method": route_intr.get("request_method"),
                        "path_info": route_intr.get("path_info"),
                        "request_param": route_intr.get("request_param"),
                        "header": route_intr.get("header"),
                        "accept": route_intr.get("accept"),
                        "custom_predicates": route_intr.get("custom_predicates", []),
                    },
                    "route_object": route_obj,
                    "views": [],
                    "cornice_service": cornice_service,  # Enhanced with Cornice info
                }

                # Process associated views with Cornice enhancement
                for view_intr in views:
                    view_callable = view_intr.get("callable")
                    if view_callable:
                        view_info = {
                            "callable": view_callable,
                            "name": view_intr.get("name", ""),
                            "request_methods": view_intr.get("request_methods", []),
                            "permission": None,  # Populated from permissions
                            "renderer": None,
                            "context": view_intr.get("context"),
                            "mcp_description": view_intr.get("mcp_description"),
                            "mcp_security": view_intr.get("mcp_security"),
                            "predicates": {
                                "xhr": view_intr.get("xhr"),
                                "accept": view_intr.get("accept"),
                                "header": view_intr.get("header"),
                                "request_param": view_intr.get("request_param"),
                                "match_param": view_intr.get("match_param"),
                                "csrf_token": view_intr.get("csrf_token"),
                            },
                            "cornice_metadata": {},  # Enhanced with Cornice data
                        }

                        # Enhanced: Extract Cornice metadata for this view
                        if cornice_service:
                            cornice_metadata = self._extract_cornice_view_metadata(
                                cornice_service,
                                view_callable,
                                view_intr.get("request_methods", []),
                            )
                            view_info["cornice_metadata"] = cornice_metadata

                        # Try to get renderer information from templates
                        template_category = introspector.get_category("templates") or []
                        template_introspectables = [
                            item["introspectable"] for item in template_category
                        ]
                        for template_intr in template_introspectables:
                            # Match templates to views - this is a heuristic approach
                            # since templates don't directly reference view callables
                            if (
                                template_intr.get("name")
                                and hasattr(view_callable, "__name__")
                                and view_callable.__name__
                                in str(template_intr.get("name", ""))
                            ):
                                view_info["renderer"] = {
                                    "name": template_intr.get("name"),
                                    "type": template_intr.get("type"),
                                }
                                break

                        route_info["views"].append(view_info)

                routes_info.append(route_info)

        except Exception as e:
            # Log the error but don't fail completely
            print(f"Error discovering routes: {e}")

        return routes_info

    def _discover_cornice_services(self, registry: Any) -> List[Dict[str, Any]]:
        """Discover Cornice services from the Pyramid registry.

        Args:
            registry: Pyramid registry

        Returns:
            List of Cornice service information dictionaries
        """
        cornice_services = []

        try:
            # Try to import cornice to check if it's available
            import cornice  # noqa: F401
            from cornice.service import get_services

            # Get all registered Cornice services
            services = get_services()

            for service in services:
                service_info = {
                    "service": service,
                    "name": getattr(service, "name", ""),
                    "path": getattr(service, "path", ""),
                    "description": getattr(service, "description", ""),
                    "defined_methods": getattr(service, "defined_methods", []),
                    "definitions": getattr(service, "definitions", []),
                    "cors_origins": getattr(service, "cors_origins", None),
                    "cors_credentials": getattr(service, "cors_credentials", None),
                    "factory": getattr(service, "factory", None),
                    "acl": getattr(service, "acl", None),
                    "default_validators": getattr(service, "default_validators", []),
                    "default_filters": getattr(service, "default_filters", []),
                    "default_content_type": getattr(
                        service, "default_content_type", None
                    ),
                    "default_accept": getattr(service, "default_accept", None),
                }
                cornice_services.append(service_info)

        except ImportError:
            # Cornice is not installed, return empty list
            pass
        except Exception as e:
            print(f"Error discovering Cornice services: {e}")

        return cornice_services

    def _find_cornice_service_for_route(
        self,
        route_name: str,
        route_pattern: str,
        cornice_services: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Find the Cornice service that manages a specific route.

        Args:
            route_name: Name of the route
            route_pattern: Pattern of the route
            cornice_services: List of discovered Cornice services

        Returns:
            Cornice service info if found, None otherwise
        """
        for service_info in cornice_services:
            # Match by service name (Cornice often uses service name as route name)
            if service_info["name"] == route_name:
                return service_info

            # Match by path pattern
            if service_info["path"] == route_pattern:
                return service_info

            # Check if route name contains service name (common pattern)
            if service_info["name"] and route_name.startswith(service_info["name"]):
                return service_info

        return None

    def _extract_cornice_view_metadata(
        self,
        cornice_service: Dict[str, Any],
        view_callable: Callable,
        request_methods: Union[str, List[str]],
    ) -> Dict[str, Any]:
        """Extract Cornice-specific metadata for a view.

        Args:
            cornice_service: Cornice service information
            view_callable: View callable function
            request_methods: HTTP methods for this view

        Returns:
            Dictionary containing Cornice metadata
        """
        metadata = {
            "service_name": cornice_service.get("name", ""),
            "service_description": cornice_service.get("description", ""),
            "validators": [],
            "filters": [],
            "content_type": None,
            "accept": None,
            "cors_enabled": False,
            "method_specific": {},
        }

        # Extract service-level defaults
        metadata["validators"] = cornice_service.get("default_validators", [])
        metadata["filters"] = cornice_service.get("default_filters", [])
        metadata["content_type"] = cornice_service.get("default_content_type")
        metadata["accept"] = cornice_service.get("default_accept")

        # Check for CORS configuration
        metadata["cors_enabled"] = (
            cornice_service.get("cors_origins") is not None
            or cornice_service.get("cors_credentials") is not None
        )

        # Extract method-specific configurations from service definitions
        definitions = cornice_service.get("definitions", [])
        for method, view, args in definitions:
            # Match by method first, then by view callable name as fallback
            method_matches = False
            if request_methods:
                if isinstance(request_methods, str):
                    # Single method as string
                    method_matches = method.upper() == request_methods.upper()
                elif isinstance(request_methods, list):
                    # Multiple methods as list
                    method_matches = method.upper() in [
                        m.upper() for m in request_methods
                    ]
            view_matches = False

            if view == view_callable:
                view_matches = True
            elif hasattr(view, "__name__") and hasattr(view_callable, "__name__"):
                view_name = view.__name__
                callable_name = view_callable.__name__
                # Check exact match or if callable is a method-decorated version
                view_matches = (
                    view_name == callable_name
                    or callable_name.startswith(f"{view_name}__")
                    or view_name.startswith(f"{callable_name}__")
                )

            if method_matches or view_matches:
                method_metadata = {
                    "method": method,
                    "validators": args.get("validators", []),
                    "filters": args.get("filters", []),
                    "content_type": args.get("content_type"),
                    "accept": args.get("accept"),
                    "permission": args.get("permission"),
                    "renderer": args.get("renderer"),
                    "cors_origins": args.get("cors_origins"),
                    "cors_credentials": args.get("cors_credentials"),
                    "error_handler": args.get("error_handler"),
                    "schema": args.get("schema"),
                    "colander_schema": args.get("colander_schema"),
                    "deserializer": args.get("deserializer"),
                    "serializer": args.get("serializer"),
                }

                # Clean up None values
                method_metadata = {
                    k: v
                    for k, v in method_metadata.items()
                    if v is not None and v != []
                }

                metadata["method_specific"][method.upper()] = method_metadata

        return metadata

    def discover_tools(self, config: Any) -> List[MCPTool]:
        """Discover routes and convert them to MCP tools.

        Args:
            config: Configuration object with include/exclude patterns

        Returns:
            List of MCPTool objects
        """
        # Use the existing comprehensive method
        return self.discover_tools_from_pyramid(None, config)

    def discover_tools_from_pyramid(
        self, introspector: Any, config: Any
    ) -> List[MCPTool]:
        """Discover MCP tools from Pyramid routes.

        Args:
            introspector: Pyramid introspector instance (legacy parameter,
                         we use self.configurator now)
            config: MCP configuration

        Returns:
            List of discovered MCP tools
        """
        tools: List[MCPTool] = []

        # Discover routes using our comprehensive discovery method
        routes_info = self.discover_routes()

        for route_info in routes_info:
            # Skip routes that should be excluded
            if self._should_exclude_route(route_info, config):
                continue

            # Convert route to MCP tools (one per HTTP method)
            route_tools = self._convert_route_to_tools(route_info, config)
            tools.extend(route_tools)
        return tools

    def _should_exclude_route(self, route_info: Dict[str, Any], config: Any) -> bool:
        """Check if a route should be excluded from MCP tool generation.

        Args:
            route_info: Route information dictionary
            config: MCP configuration

        Returns:
            True if route should be excluded, False otherwise
        """
        route_name = route_info.get("name", "")
        route_pattern = route_info.get("pattern", "")

        # Exclude MCP routes themselves
        if route_name.startswith("mcp_"):
            return True

        # Exclude static routes and assets
        if "static" in route_name.lower() or route_pattern.startswith("/static"):
            return True

        # Check include patterns
        include_patterns = getattr(config, "include_patterns", None)
        if include_patterns:
            if not any(
                self._pattern_matches(pattern, route_pattern, route_name)
                for pattern in include_patterns
            ):
                return True

        # Check exclude patterns
        exclude_patterns = getattr(config, "exclude_patterns", None)
        if exclude_patterns:
            if any(
                self._pattern_matches(pattern, route_pattern, route_name)
                for pattern in exclude_patterns
            ):
                return True

        return False

    def _pattern_matches(
        self, pattern: str, route_pattern: str, route_name: str
    ) -> bool:
        """Check if a pattern matches a route pattern or name.

        Args:
            pattern: Pattern to match (supports wildcards like 'api/*')
            route_pattern: Route URL pattern (e.g., '/api/users/{id}')
            route_name: Route name

        Returns:
            True if pattern matches, False otherwise
        """
        # Normalize route pattern for matching
        normalized_route = route_pattern.lstrip("/")

        # Handle wildcard patterns
        if "*" in pattern or "?" in pattern:
            # Pattern with wildcards - convert to regex
            pattern_regex = pattern.replace("*", ".*").replace("?", ".")
            pattern_regex = f"^{pattern_regex}$"

            # Check against both route pattern and name
            return bool(
                re.match(pattern_regex, normalized_route)
                or re.match(pattern_regex, route_name)
            )
        else:
            # Exact pattern - should match as prefix for routes and
            # exact/prefix for names
            route_match = normalized_route == pattern or normalized_route.startswith(
                pattern + "/"
            )
            name_match = route_name.startswith(pattern)

            return route_match or name_match

    def _convert_route_to_tools(
        self, route_info: Dict[str, Any], config: Any
    ) -> List[MCPTool]:
        """Convert a route to one or more MCP tools.

        Args:
            route_info: Route information dictionary
            config: MCP configuration

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
                # Fall back to route's request methods
                route_methods = route_info.get("request_methods")
                if route_methods:
                    methods = list(route_methods)
                else:
                    methods = ["GET"]  # Final fallback
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
            # Use the first view for this method (most specific)
            view = method_views[0]
            view_callable = view.get("callable")

            if not view_callable:
                continue

            # Generate tool name
            tool_name = self._generate_tool_name(route_name, method, route_pattern)

            # Generate tool description
            description = self._generate_tool_description(
                route_name, method, route_pattern, view_callable, view
            )

            # Generate input schema from route pattern and view signature
            input_schema = self._generate_input_schema(
                route_pattern, view_callable, method, view
            )

            # Extract security configuration from view info
            security_type = view.get("mcp_security")
            security = None
            if security_type:
                security = self._convert_security_type_to_schema(security_type)

            # Create MCP tool
            tool = MCPTool(
                name=tool_name,
                description=description,
                input_schema=input_schema,
                handler=self._create_route_handler(route_info, view, method),
                security=security,
            )

            tools.append(tool)

        return tools

    def _generate_tool_name(self, route_name: str, method: str, pattern: str) -> str:
        """Generate a descriptive tool name from route information.

        Args:
            route_name: Pyramid route name
            method: HTTP method
            pattern: Route pattern

        Returns:
            Generated tool name
        """
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

    def _generate_tool_description(
        self,
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

    def _generate_input_schema(
        self,
        pattern: str,
        view_callable: Callable,
        method: str,
        view_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generate JSON schema for tool input from route pattern and view signature.

        Args:
            pattern: Route pattern (e.g., '/users/{id}')
            view_callable: View callable function
            method: HTTP method
            view_info: View information including Cornice metadata

        Returns:
            JSON schema dictionary or None
        """
        properties: Dict[str, Any] = {}
        required: List[str] = []

        # Check for Marshmallow schema in Cornice metadata first
        if view_info and "cornice_metadata" in view_info:
            cornice_metadata = view_info["cornice_metadata"]
            method_specific = cornice_metadata.get("method_specific", {})

            # Look for schema in method-specific metadata
            if method.upper() in method_specific:
                method_info = method_specific[method.upper()]
                schema = method_info.get("schema")

                if schema:
                    # Extract schema information using Marshmallow
                    schema_info = self._extract_marshmallow_schema_info(schema)
                    if schema_info and "properties" in schema_info:
                        # Use schema properties as base
                        properties.update(schema_info["properties"])
                        required.extend(schema_info.get("required", []))

        # Extract path parameters from route pattern
        path_params = re.findall(r"\{([^}]+)\}", pattern)
        for param in path_params:
            # Remove any regex constraints (e.g., {id:\d+} -> id)
            clean_param = param.split(":")[0]
            properties[clean_param] = {
                "type": "string",
                "description": f"Path parameter: {clean_param}",
            }
            required.append(clean_param)

        # Add common query parameters for known patterns
        if method.upper() == "GET":
            # For GET endpoints, add common parameters based on docstring analysis
            if (
                view_callable is not None
                and hasattr(view_callable, "__doc__")
                and view_callable.__doc__
            ):
                doc = view_callable.__doc__.lower()

                # Check for name parameter in hello endpoints
                if "hello" in doc or "name" in doc:
                    properties["name"] = {
                        "type": "string",
                        "description": "Name to greet",
                        "default": "World",
                    }

                # For user endpoints, look for common parameters
                if "user" in doc:
                    if "id" not in properties:  # Don't override path params
                        properties["limit"] = {
                            "type": "integer",
                            "description": "Maximum number of items to return",
                            "default": 10,
                        }
                        properties["offset"] = {
                            "type": "integer",
                            "description": "Number of items to skip",
                            "default": 0,
                        }

        # Add a generic 'data' parameter for request body/query data
        # (since Pyramid views only take 'request' parameter, we can't extract params from signature)
        if "data" not in properties:
            properties["data"] = {
                "type": "string",
                "description": "Request data parameter",
            }
            # Make it required for POST/PUT/PATCH methods
            if method.upper() in ["POST", "PUT", "PATCH"]:
                required.append("data")

        # Return schema if we have properties
        if properties:
            schema = {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            }
            return schema

        return None

    def _create_route_handler(
        self, route_info: Dict[str, Any], view_info: Dict[str, Any], method: str
    ) -> Callable:
        """Create a handler function that calls the Pyramid view via subrequest.

        Args:
            route_info: Route information
            view_info: View information
            method: HTTP method

        Returns:
            Handler function for MCP tool
        """
        route_pattern = route_info.get("pattern", "")
        route_name = route_info.get("name", "")
        
        # Get security configuration from view_info
        security_type = view_info.get("mcp_security")
        security = None
        if security_type:
            security = self._convert_security_type_to_schema(security_type)

        def handler(pyramid_request: Any, **kwargs: Any) -> Dict[str, Any]:
            """MCP tool handler that delegates to Pyramid view via subrequest."""
            try:
                # Create subrequest to call the actual route
                subrequest = self._create_subrequest(
                    pyramid_request, kwargs, route_pattern, method, security
                )

                # Execute the subrequest
                response = pyramid_request.invoke_subrequest(subrequest)

                # Convert response to MCP format
                return self._convert_response_to_mcp(response, view_info)

            except Exception as e:
                # Return error in MCP format
                return {
                    "error": f"Error calling view: {str(e)}",
                    "route": route_name,
                    "method": method,
                    "parameters": kwargs,
                }

        return handler

    def _create_subrequest(
        self,
        pyramid_request: Any,
        kwargs: Dict[str, Any],
        route_pattern: str,
        method: str,
        security: Optional[Any] = None,
    ) -> Any:
        """Create a subrequest to call the actual Pyramid view.

        Args:
            pyramid_request: Original pyramid request
            kwargs: MCP tool arguments
            route_pattern: Route pattern (e.g., '/api/hello')
            method: HTTP method
            security: Security schema for auth parameter conversion

        Returns:
            Subrequest object ready for execution
        """
        import json
        import re

        from pyramid.request import Request

        # Get authentication headers from pyramid_request if they were processed by MCP protocol handler
        auth_headers = {}
        if hasattr(pyramid_request, 'mcp_auth_headers') and pyramid_request.mcp_auth_headers:
            auth_headers = pyramid_request.mcp_auth_headers
            print(f"🔐 AUTH DEBUG: Using MCP auth headers: {auth_headers}")
        else:
            print("🔐 AUTH DEBUG: No MCP auth headers found")
        
        # kwargs should already have auth parameters removed by MCP protocol handler
        filtered_kwargs = kwargs
        print(f"🔐 AUTH DEBUG: kwargs after MCP processing: {filtered_kwargs}")

        # Extract path parameters from route pattern
        path_params = re.findall(r"\{([^}]+)\}", route_pattern)
        path_param_names = [param.split(":")[0] for param in path_params]

        # Separate path parameters from other parameters (using filtered kwargs)
        path_values = {}
        query_params = {}
        json_body = {}

        for key, value in filtered_kwargs.items():
            if key in path_param_names:
                path_values[key] = value
            else:
                if method.upper() in ["POST", "PUT", "PATCH"]:
                    json_body[key] = value
                else:
                    query_params[key] = value

        # Build the actual URL by replacing path parameters in the pattern
        url = route_pattern
        for param_name, param_value in path_values.items():
            # Replace {param} and {param:regex} patterns with actual values
            url = re.sub(rf"\{{{param_name}(?::[^}}]+)?\}}", str(param_value), url)

        # Add query parameters to URL
        if query_params:
            from urllib.parse import urlencode

            query_string = urlencode(query_params)
            url = f"{url}?{query_string}"

        # Create the subrequest
        subrequest = Request.blank(url)
        subrequest.method = method.upper()

        # 🌍 ENVIRON SHARING SUPPORT
        # Copy parent request environ to subrequest for better context preservation
        self._copy_request_environ(pyramid_request, subrequest)

        # Set request body for POST/PUT/PATCH requests
        if method.upper() in ["POST", "PUT", "PATCH"] and json_body:
            subrequest.body = json.dumps(json_body).encode("utf-8")
            subrequest.content_type = "application/json"

        # Copy important headers from original request
        if hasattr(pyramid_request, "headers"):
            # Copy relevant headers (like Authorization, User-Agent, etc.)
            for header_name in ["Authorization", "User-Agent", "Accept"]:
                if header_name in pyramid_request.headers:
                    subrequest.headers[header_name] = pyramid_request.headers[
                        header_name
                    ]

        # Add authentication headers from MCP security parameters
        for header_name, header_value in auth_headers.items():
            subrequest.headers[header_name] = header_value

        # 🔄 PYRAMID_TM TRANSACTION SHARING SUPPORT
        # Ensure subrequest shares the same transaction context as the parent request
        self.configure_transaction(pyramid_request, subrequest)

        return subrequest

    def configure_transaction(self, pyramid_request: Any, subrequest: Any) -> None:
        """Configure transaction sharing between parent request and subrequest.

        When pyramid_tm is active on the parent request, we need to ensure that
        subrequests share the same transaction context rather than creating
        separate transactions.

        Args:
            pyramid_request: The original pyramid request
            subrequest: The subrequest to configure
        """
        # Share transaction manager from parent request if it exists
        # This works both with pyramid_tm and manual transaction management
        if hasattr(pyramid_request, "tm") and pyramid_request.tm is not None:
            # Set the same transaction manager on the subrequest
            subrequest.tm = pyramid_request.tm

            # Also copy the registry reference to ensure proper integration
            if hasattr(pyramid_request, "registry"):
                subrequest.registry = pyramid_request.registry

    def _copy_request_environ(self, pyramid_request: Any, subrequest: Any) -> None:
        """Copy parent request environ to subrequest for better context preservation.

        This ensures that subrequests inherit important context from the parent request
        including environment variables, WSGI environ data, and middleware-added
        context.

        Args:
            pyramid_request: The original pyramid request
            subrequest: The subrequest to configure
        """
        # Request-specific environ variables that should NOT be copied
        # These should remain specific to the subrequest
        request_specific_keys = {
            "PATH_INFO",
            "SCRIPT_NAME",
            "REQUEST_METHOD",
            "QUERY_STRING",
            "CONTENT_TYPE",
            "CONTENT_LENGTH",
            "REQUEST_URI",
            "RAW_URI",
            "wsgi.input",
            "wsgi.errors",
            "pyramid.request",
            "pyramid.route",
            "pyramid.matched_route",
            "pyramid.matchdict",
            "pyramid.request.method",
            "pyramid.request.path",
            "pyramid.request.path_info",
            "pyramid.request.script_name",
            "pyramid.request.query_string",
        }

        # Copy all parent environ except request-specific variables
        for key, value in pyramid_request.environ.items():
            if key not in request_specific_keys:
                subrequest.environ[key] = value

    def _create_request_for_view(
        self, kwargs: Dict[str, Any], route_pattern: str, method: str
    ) -> Any:
        """DEPRECATED: Use _create_subrequest instead.

        This method is kept for backward compatibility but should not be used
        for new code. Use subrequest mechanism instead.
        """
        # This method is deprecated and should not be used
        # Keeping it for backward compatibility only
        raise NotImplementedError(
            "This method is deprecated. Use subrequest mechanism instead."
        )

    def _convert_response_to_mcp(
        self, response: Any, view_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Convert Pyramid view response to MCP tool response format.

        Args:
            response: Pyramid view response (dict, string, or Response object)
            view_info: Optional view information for content type detection

        Returns:
            MCP-compatible response
        """
        import json

        from pyramid.response import Response

        # Helper function to check if we should return structured JSON
        def should_return_structured_json(
            response_data: Any, content_type: Optional[str] = None
        ) -> bool:
            """Determine if response should be returned as structured JSON."""
            # Check if response is a dictionary (likely JSON)
            if isinstance(response_data, dict):
                return True

            # Check if content type indicates JSON
            if content_type and "application/json" in content_type.lower():
                return True

            # Check view info for JSON renderer or content type
            if view_info and isinstance(view_info, dict):
                # Check cornice metadata for JSON content type
                cornice_metadata = view_info.get("cornice_metadata", {})
                if cornice_metadata.get("content_type") == "application/json":
                    return True

                # Check method-specific metadata
                method_specific = cornice_metadata.get("method_specific", {})
                for method_data in method_specific.values():
                    if method_data.get("content_type") == "application/json":
                        return True
                    if method_data.get("renderer") == "json":
                        return True

                # Check renderer information
                renderer = view_info.get("renderer", {})
                if isinstance(renderer, dict) and renderer.get("type") == "json":
                    return True

            return False

        # Handle different response types
        if isinstance(response, dict):
            # Direct dictionary response (most common for JSON APIs)
            if should_return_structured_json(response):
                return {"content": [{"type": "application/json", "data": response}]}
            else:
                return {
                    "content": [
                        {"type": "text", "text": json.dumps(response, indent=2)}
                    ]
                }
        elif isinstance(response, str):
            # String response
            return {"content": [{"type": "text", "text": response}]}
        elif isinstance(response, Response):
            # Pyramid Response object
            try:
                # Get the content type from the response
                content_type = (
                    response.content_type if hasattr(response, "content_type") else None
                )

                # Get the body content
                if hasattr(response, "text"):
                    content = response.text
                elif hasattr(response, "body"):
                    body = response.body
                    if isinstance(body, bytes):
                        content = body.decode("utf-8")
                    else:
                        content = str(body)
                else:
                    content = str(response)

                # Try to parse as JSON
                try:
                    parsed = json.loads(content)
                    # Check if we should return structured JSON
                    if should_return_structured_json(parsed, content_type):
                        return {
                            "content": [{"type": "application/json", "data": parsed}]
                        }
                    else:
                        return {
                            "content": [
                                {"type": "text", "text": json.dumps(parsed, indent=2)}
                            ]
                        }
                except json.JSONDecodeError:
                    return {"content": [{"type": "text", "text": str(content)}]}

            except Exception:
                return {"content": [{"type": "text", "text": str(response)}]}
        elif hasattr(response, "json") and callable(response.json):
            # Response object with json() method
            try:
                parsed_json = response.json()
                # Check if we should return structured JSON
                if should_return_structured_json(parsed_json):
                    return {
                        "content": [{"type": "application/json", "data": parsed_json}]
                    }
                else:
                    json_data = json.dumps(parsed_json, indent=2)
                    return {"content": [{"type": "text", "text": json_data}]}
            except Exception:
                return {"content": [{"type": "text", "text": str(response)}]}
        elif hasattr(response, "text"):
            # Response object with text attribute
            return {"content": [{"type": "text", "text": str(response.text)}]}
        elif hasattr(response, "body"):
            # Response object with body attribute
            try:
                body = response.body
                if isinstance(body, bytes):
                    body = body.decode("utf-8")
                # Try to parse as JSON for content type detection
                try:
                    parsed = json.loads(body)
                    # Check if we should return structured JSON
                    if should_return_structured_json(parsed):
                        return {
                            "content": [{"type": "application/json", "data": parsed}]
                        }
                    else:
                        json_data = json.dumps(parsed, indent=2)
                        return {"content": [{"type": "text", "text": json_data}]}
                except json.JSONDecodeError:
                    return {"content": [{"type": "text", "text": str(body)}]}
            except Exception:
                return {"content": [{"type": "text", "text": str(response)}]}
        else:
            # Fallback to string representation
            return {"content": [{"type": "text", "text": str(response)}]}

    def _normalize_path_pattern(self, pattern: str) -> str:
        """Normalize path pattern for matching.

        Args:
            pattern: Route pattern to normalize

        Returns:
            Normalized pattern
        """
        # Remove regex constraints from path parameters
        # e.g., {id:\d+} -> {id}, {filename:.+} -> {filename}
        import re

        normalized = re.sub(r"\{([^}:]+):[^}]+\}", r"{\1}", pattern)
        return normalized

    def _extract_service_level_metadata(self, service: Any) -> Dict[str, Any]:
        """Extract service-level metadata from a Cornice service object.

        Args:
            service: Cornice service object

        Returns:
            Dictionary containing service-level metadata
        """
        metadata = {}

        # Extract basic attributes with defaults
        metadata["name"] = getattr(service, "name", "")
        metadata["description"] = getattr(service, "description", "")
        metadata["path"] = getattr(service, "path", "")
        metadata["validators"] = getattr(service, "default_validators", [])
        metadata["filters"] = getattr(service, "default_filters", [])
        metadata["content_type"] = getattr(
            service, "default_content_type", "application/json"
        )
        metadata["accept"] = getattr(service, "default_accept", "application/json")
        metadata["cors_origins"] = getattr(service, "cors_origins", None)
        metadata["cors_credentials"] = getattr(service, "cors_credentials", False)

        return metadata

    def _extract_marshmallow_schema_info(self, schema: Any) -> Dict[str, Any]:
        """Extract field information from a Marshmallow schema.

        Args:
            schema: Marshmallow schema instance or class

        Returns:
            Dictionary containing schema field information for MCP
        """
        try:
            # Try to import marshmallow
            import marshmallow
        except ImportError:
            # If marshmallow is not available, return empty schema info
            return {}

        # Handle schema class vs instance
        if isinstance(schema, type):
            # If it's a class, instantiate it
            try:
                schema_instance = schema()
            except Exception:
                # If instantiation fails, return empty info
                return {}
        else:
            # It's already an instance
            schema_instance = schema

        # Check if it's actually a Marshmallow schema
        if not isinstance(schema_instance, marshmallow.Schema):
            return {}

        schema_info: Dict[str, Any] = {
            "properties": {},
            "required": [],
            "type": "object",
            "additionalProperties": False,
        }

        # Extract field information
        for field_name, field_obj in schema_instance.fields.items():
            field_info = self._marshmallow_field_to_mcp_type(field_obj)
            schema_info["properties"][field_name] = field_info

            # Check if field is required
            if field_obj.required:
                schema_info["required"].append(field_name)

        return schema_info

    def _marshmallow_field_to_mcp_type(self, field: Any) -> Dict[str, Any]:
        """Convert a Marshmallow field to MCP parameter type.

        Args:
            field: Marshmallow field instance

        Returns:
            Dictionary containing MCP parameter type information
        """
        try:
            # Try to import marshmallow fields
            import marshmallow.fields as fields
        except ImportError:
            # If marshmallow is not available, return generic string type
            return {"type": "string", "description": "Unknown field type"}

        field_info: Dict[str, Any] = {}

        # Map Marshmallow field types to MCP types
        # Check more specific types first to avoid inheritance issues
        if isinstance(field, fields.Email):
            field_info["type"] = "string"
            field_info["format"] = "email"
        elif isinstance(field, fields.Url):
            field_info["type"] = "string"
            field_info["format"] = "uri"
        elif isinstance(field, fields.UUID):
            field_info["type"] = "string"
            field_info["format"] = "uuid"
        elif isinstance(field, fields.Date):
            field_info["type"] = "string"
            field_info["format"] = "date"
        elif isinstance(field, fields.Time):
            field_info["type"] = "string"
            field_info["format"] = "time"
        elif isinstance(field, fields.DateTime):
            field_info["type"] = "string"
            field_info["format"] = "date-time"
        elif isinstance(field, fields.Integer):
            field_info["type"] = "integer"
        elif isinstance(field, fields.Float):
            field_info["type"] = "number"
        elif isinstance(field, fields.Boolean):
            field_info["type"] = "boolean"
        elif isinstance(field, fields.List):
            field_info["type"] = "array"
            # If the list has a container field, get its type
            if hasattr(field, "inner") and field.inner:
                inner_field_info = self._marshmallow_field_to_mcp_type(field.inner)
                field_info["items"] = inner_field_info
        elif isinstance(field, fields.Nested):
            field_info["type"] = "object"
            # For nested fields, try to extract nested schema info
            if hasattr(field, "schema") and field.schema:
                nested_info = self._extract_marshmallow_schema_info(field.schema)
                if nested_info:
                    field_info.update(nested_info)
        elif isinstance(field, fields.Dict):
            field_info["type"] = "object"
            field_info["additionalProperties"] = True
        elif isinstance(field, fields.String):
            field_info["type"] = "string"
        else:
            # Default to string for unknown field types
            field_info["type"] = "string"

        # Add description if available (from field metadata)
        if hasattr(field, "metadata") and field.metadata:
            if "description" in field.metadata:
                field_info["description"] = field.metadata["description"]
            elif "doc" in field.metadata:
                field_info["description"] = field.metadata["doc"]

        # Add validation constraints
        if hasattr(field, "validate") and field.validate:
            self._add_validation_constraints(field, field_info)

        # Add default value if available
        if hasattr(field, "default") and field.default is not None:
            # Handle marshmallow.missing
            try:
                import marshmallow

                if field.default is not marshmallow.missing:
                    field_info["default"] = field.default
            except ImportError:
                pass

        return field_info

    def _add_validation_constraints(
        self, field: Any, field_info: Dict[str, Any]
    ) -> None:
        """Add validation constraints from Marshmallow field to MCP field info.

        Args:
            field: Marshmallow field instance
            field_info: MCP field info dictionary to update
        """
        try:
            import marshmallow.validate as validate
        except ImportError:
            return

        validators = field.validate
        if not validators:
            return

        # Handle single validator or list of validators
        if not isinstance(validators, list):
            validators = [validators]

        for validator in validators:
            # Length validator
            if isinstance(validator, validate.Length):
                if hasattr(validator, "min") and validator.min is not None:
                    if field_info.get("type") == "string":
                        field_info["minLength"] = validator.min
                    elif field_info.get("type") == "array":
                        field_info["minItems"] = validator.min
                if hasattr(validator, "max") and validator.max is not None:
                    if field_info.get("type") == "string":
                        field_info["maxLength"] = validator.max
                    elif field_info.get("type") == "array":
                        field_info["maxItems"] = validator.max

            # Range validator
            elif isinstance(validator, validate.Range):
                if hasattr(validator, "min") and validator.min is not None:
                    field_info["minimum"] = validator.min
                if hasattr(validator, "max") and validator.max is not None:
                    field_info["maximum"] = validator.max

            # OneOf validator (enum)
            elif isinstance(validator, validate.OneOf):
                if hasattr(validator, "choices") and validator.choices:
                    field_info["enum"] = list(validator.choices)

            # Regexp validator
            elif isinstance(validator, validate.Regexp):
                if hasattr(validator, "regex") and validator.regex:
                    pattern = (
                        validator.regex.pattern
                        if hasattr(validator.regex, "pattern")
                        else str(validator.regex)
                    )
                    field_info["pattern"] = pattern

    def _convert_security_type_to_schema(self, security_type: str) -> Optional[Any]:
        """Convert string security type to appropriate schema object.

        Args:
            security_type: String security type ("bearer", "basic", etc.)

        Returns:
            Appropriate security schema object or None if unknown
        """
        security_type_lower = security_type.lower()
        
        if security_type_lower == "bearer":
            return BearerAuthSchema()
        elif security_type_lower == "basic":
            return BasicAuthSchema()
        else:
            # Unknown security type, return None
            return None
