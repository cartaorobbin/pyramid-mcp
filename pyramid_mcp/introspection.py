"""
Pyramid Introspection Module

This module provides functionality to discover and analyze Pyramid routes
and convert them into MCP tools.
"""

import inspect
import re
from typing import Any, Dict, List, Optional, Callable, Union

from pyramid_mcp.protocol import MCPTool


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
            route_category = introspector.get_category('routes') or []
            route_introspectables = [item['introspectable'] for item in route_category]
            
            # Get all view introspectables for cross-referencing
            view_category = introspector.get_category('views') or []
            view_introspectables = [item['introspectable'] for item in view_category]
            view_by_route = {}
            for view_intr in view_introspectables:
                route_name = view_intr.get('route_name')
                if route_name:
                    if route_name not in view_by_route:
                        view_by_route[route_name] = []
                    view_by_route[route_name].append(view_intr)
            
            # Process each route
            for route_intr in route_introspectables:
                route_name = route_intr.get('name')
                if not route_name:
                    continue
                    
                # Get route object for additional metadata
                route_obj = route_objects.get(route_name)
                
                # Get associated views
                views = view_by_route.get(route_name, [])
                
                # Build comprehensive route information
                route_info = {
                    'name': route_name,
                    'pattern': route_intr.get('pattern', ''),
                    'request_methods': route_intr.get('request_methods', []),
                    'factory': route_intr.get('factory'),
                    'predicates': {
                        'xhr': route_intr.get('xhr'),
                        'request_method': route_intr.get('request_method'),
                        'path_info': route_intr.get('path_info'),
                        'request_param': route_intr.get('request_param'),
                        'header': route_intr.get('header'),
                        'accept': route_intr.get('accept'),
                        'custom_predicates': route_intr.get('custom_predicates', []),
                    },
                    'route_object': route_obj,
                    'views': []
                }
                
                # Process associated views
                for view_intr in views:
                    view_callable = view_intr.get('callable')
                    if view_callable:
                        view_info = {
                            'callable': view_callable,
                            'name': view_intr.get('name', ''),
                            'request_methods': view_intr.get('request_methods', []),
                            'permission': None,  # Will be populated from permissions introspectables
                            'renderer': None,
                            'context': view_intr.get('context'),
                            'predicates': {
                                'xhr': view_intr.get('xhr'),
                                'accept': view_intr.get('accept'),
                                'header': view_intr.get('header'),
                                'request_param': view_intr.get('request_param'),
                                'match_param': view_intr.get('match_param'),
                                'csrf_token': view_intr.get('csrf_token'),
                            }
                        }
                        
                        # Try to get renderer information from templates
                        template_category = introspector.get_category('templates') or []
                        template_introspectables = [item['introspectable'] for item in template_category]
                        for template_intr in template_introspectables:
                            # Match templates to views - this is a heuristic approach
                            # since templates don't directly reference view callables
                            if (template_intr.get('name') and 
                                hasattr(view_callable, '__name__') and 
                                view_callable.__name__ in str(template_intr.get('name', ''))):
                                view_info['renderer'] = {
                                    'name': template_intr.get('name'),
                                    'type': template_intr.get('type')
                                }
                                break
                        
                        route_info['views'].append(view_info)
                
                routes_info.append(route_info)
                
        except Exception as e:
            # Log the error but don't fail completely
            print(f"Error discovering routes: {e}")
            
        return routes_info

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
            introspector: Pyramid introspector instance (legacy parameter, we use self.configurator now)
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
        route_name = route_info.get('name', '')
        route_pattern = route_info.get('pattern', '')
        
        # Exclude MCP routes themselves
        if route_name.startswith('mcp_'):
            return True
            
        # Exclude static routes and assets
        if 'static' in route_name.lower() or route_pattern.startswith('/static'):
            return True
            
        # Check include patterns
        include_patterns = getattr(config, 'include_patterns', None)
        if include_patterns:
            if not any(self._pattern_matches(pattern, route_pattern, route_name) 
                      for pattern in include_patterns):
                return True
        
        # Check exclude patterns
        exclude_patterns = getattr(config, 'exclude_patterns', None)
        if exclude_patterns:
            if any(self._pattern_matches(pattern, route_pattern, route_name) 
                  for pattern in exclude_patterns):
                return True
        
        return False

    def _pattern_matches(self, pattern: str, route_pattern: str, route_name: str) -> bool:
        """Check if a pattern matches a route pattern or name.

        Args:
            pattern: Pattern to match (supports wildcards like 'api/*')
            route_pattern: Route URL pattern (e.g., '/api/users/{id}')
            route_name: Route name

        Returns:
            True if pattern matches, False otherwise
        """
        # Normalize route pattern for matching
        normalized_route = route_pattern.lstrip('/')
        
        # Handle wildcard patterns
        if '*' in pattern or '?' in pattern:
            # Pattern with wildcards - convert to regex
            pattern_regex = pattern.replace('*', '.*').replace('?', '.')
            pattern_regex = f'^{pattern_regex}$'
            
            # Check against both route pattern and name
            return bool(re.match(pattern_regex, normalized_route) or 
                       re.match(pattern_regex, route_name))
        else:
            # Exact pattern - should match as prefix for routes and exact/prefix for names
            route_match = (normalized_route == pattern or 
                          normalized_route.startswith(pattern + '/'))
            name_match = route_name.startswith(pattern)
            
            return route_match or name_match

    def _convert_route_to_tools(self, route_info: Dict[str, Any], config: Any) -> List[MCPTool]:
        """Convert a route to one or more MCP tools.

        Args:
            route_info: Route information dictionary
            config: MCP configuration

        Returns:
            List of MCP tools for this route
        """
        tools = []
        route_name = route_info.get('name', '')
        route_pattern = route_info.get('pattern', '')
        views = route_info.get('views', [])
        
        # If no views, skip this route
        if not views:
            return tools
            
        # Group views by HTTP method
        views_by_method = {}
        for view in views:
            methods = view.get('request_methods') or ['GET']
            for method in methods:
                if method not in views_by_method:
                    views_by_method[method] = []
                views_by_method[method].append(view)
        
        # Create MCP tool for each HTTP method
        for method, method_views in views_by_method.items():
            # Use the first view for this method (most specific)
            view = method_views[0]
            view_callable = view.get('callable')
            
            if not view_callable:
                continue
                
            # Generate tool name
            tool_name = self._generate_tool_name(route_name, method, route_pattern)
            
            # Generate tool description
            description = self._generate_tool_description(
                route_name, method, route_pattern, view_callable
            )
            
            # Generate input schema from route pattern and view signature
            input_schema = self._generate_input_schema(
                route_pattern, view_callable, method
            )
            
            # Create MCP tool
            tool = MCPTool(
                name=tool_name,
                description=description,
                input_schema=input_schema,
                handler=self._create_route_handler(route_info, view, method)
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
            base_name = pattern.replace('/', '_').replace('{', '').replace('}', '')
            base_name = re.sub(r'[^a-zA-Z0-9_]', '', base_name)
        
        # Add HTTP method context
        method_lower = method.lower()
        if method_lower == 'get':
            if 'list' in base_name or base_name.endswith('s'):
                prefix = 'list'
            else:
                prefix = 'get'
        elif method_lower == 'post':
            prefix = 'create'
        elif method_lower == 'put':
            prefix = 'update'
        elif method_lower == 'patch':
            prefix = 'modify'
        elif method_lower == 'delete':
            prefix = 'delete'
        else:
            prefix = method_lower
        
        # Combine prefix with base name intelligently
        if base_name.startswith(prefix):
            return base_name
        elif base_name.endswith('_' + prefix):
            return base_name
        else:
            return f"{prefix}_{base_name}"

    def _generate_tool_description(
        self, route_name: str, method: str, pattern: str, view_callable: Callable
    ) -> str:
        """Generate a descriptive tool description.

        Args:
            route_name: Pyramid route name
            method: HTTP method
            pattern: Route pattern
            view_callable: View callable function

        Returns:
            Generated description
        """
        # Try to get description from view docstring
        if view_callable and hasattr(view_callable, '__doc__') and view_callable.__doc__:
            doc = view_callable.__doc__.strip()
            if doc:
                return doc
        
        # Generate description from route information
        action_map = {
            'GET': 'Retrieve',
            'POST': 'Create',
            'PUT': 'Update',
            'PATCH': 'Modify',
            'DELETE': 'Delete'
        }
        
        action = action_map.get(method.upper(), method.upper())
        resource = route_name.replace('_', ' ').title()
        
        return f"{action} {resource} via {method} {pattern}"

    def _generate_input_schema(
        self, pattern: str, view_callable: Callable, method: str
    ) -> Optional[Dict[str, Any]]:
        """Generate JSON schema for tool input from route pattern and view signature.

        Args:
            pattern: Route pattern (e.g., '/users/{id}')
            view_callable: View callable function
            method: HTTP method

        Returns:
            JSON schema dictionary or None
        """
        properties = {}
        required = []
        
        # Extract path parameters from route pattern
        path_params = re.findall(r'\{([^}]+)\}', pattern)
        for param in path_params:
            # Remove any regex constraints (e.g., {id:\d+} -> id)
            clean_param = param.split(':')[0]
            properties[clean_param] = {
                "type": "string",
                "description": f"Path parameter: {clean_param}"
            }
            required.append(clean_param)
        
        # Try to extract parameters from view function signature
        if view_callable:
            try:
                sig = inspect.signature(view_callable)
                for param_name, param in sig.parameters.items():
                    # Skip 'request' parameter
                    if param_name == 'request':
                        continue
                        
                    # Skip path parameters (already handled)
                    if param_name in [p.split(':')[0] for p in path_params]:
                        continue
                    
                    param_schema = {"type": "string"}
                    
                    # Try to infer type from annotation
                    if param.annotation != inspect.Parameter.empty:
                        if param.annotation == int:
                            param_schema["type"] = "integer"
                        elif param.annotation == float:
                            param_schema["type"] = "number"
                        elif param.annotation == bool:
                            param_schema["type"] = "boolean"
                        elif param.annotation == list:
                            param_schema["type"] = "array"
                        elif param.annotation == dict:
                            param_schema["type"] = "object"
                    
                    # Add description based on context
                    if method.upper() in ['POST', 'PUT', 'PATCH']:
                        param_schema["description"] = f"Request body parameter: {param_name}"
                    else:
                        param_schema["description"] = f"Query parameter: {param_name}"
                    
                    properties[param_name] = param_schema
                    
                    # Required if no default value
                    if param.default == inspect.Parameter.empty:
                        required.append(param_name)
                        
            except Exception:
                # If signature inspection fails, continue with path params only
                pass
        
        # Return schema if we have properties
        if properties:
            schema = {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False
            }
            return schema
        
        return None

    def _create_route_handler(
        self, route_info: Dict[str, Any], view_info: Dict[str, Any], method: str
    ) -> Callable:
        """Create a handler function that calls the original Pyramid view.

        Args:
            route_info: Route information
            view_info: View information
            method: HTTP method

        Returns:
            Handler function for MCP tool
        """
        view_callable = view_info.get('callable')
        route_pattern = route_info.get('pattern', '')
        
        def handler(**kwargs):
            """MCP tool handler that delegates to Pyramid view.
            
            This is a placeholder implementation. In a real implementation,
            you would need to:
            1. Create a proper Pyramid request object
            2. Set up the request context and matchdict
            3. Call the view callable
            4. Handle the response appropriately
            
            For now, this returns a description of what would be called.
            """
            return {
                "action": f"Would call {view_callable.__name__ if view_callable else 'unknown'} "
                         f"for {method} {route_pattern}",
                "parameters": kwargs,
                "route": route_info.get('name'),
                "method": method
            }
        
        return handler
