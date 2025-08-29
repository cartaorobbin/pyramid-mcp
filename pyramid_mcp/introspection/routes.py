"""
Route Discovery Module

This module handles the discovery and analysis of Pyramid routes and views.
It extracts route metadata, view information, and permissions from the
Pyramid introspection system.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def discover_routes(
    configurator: Any, cornice_discovery_func: Any
) -> List[Dict[str, Any]]:
    """Discover routes from the Pyramid application.

    Args:
        configurator: Pyramid configurator instance
        cornice_discovery_func: Function to discover Cornice services

    Returns:
        List of route information dictionaries containing route metadata,
        view callables, and other relevant information for MCP tool generation.
        Enhanced with Cornice service information when available.
    """
    if not configurator:
        return []

    routes_info = []

    try:
        # Get the registry and introspector
        registry = configurator.registry
        introspector = registry.introspector

        # Get route mapper for additional route information
        route_mapper = configurator.get_routes_mapper()
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

        # Permissions are directly available in view introspectables
        # No need for complex extraction - Pyramid stores them directly

        # Discover Cornice services for enhanced metadata
        cornice_services = cornice_discovery_func(registry)

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
            from pyramid_mcp.introspection.cornice import find_cornice_service_for_route

            cornice_service = find_cornice_service_for_route(
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
                    # Get permission from introspectable or related permissions
                    permission = extract_permission(view_intr, configurator)

                    view_info = {
                        "callable": view_callable,
                        "name": view_intr.get("name", ""),
                        "request_methods": view_intr.get("request_methods", []),
                        "permission": permission,
                        "renderer": None,
                        "context": view_intr.get("context"),
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

                    # Store ALL custom predicates dynamically
                    # This allows any custom security parameter to be extracted
                    for key, value in view_intr.items():
                        if key not in view_info and key not in view_info["predicates"]:
                            view_info[key] = value

                    # Enhanced: Extract Cornice metadata for this view
                    if cornice_service:
                        from pyramid_mcp.introspection.cornice import (
                            extract_cornice_view_metadata,
                        )

                        cornice_metadata = extract_cornice_view_metadata(
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

    except Exception:
        # Silently handle errors to avoid interfering with JSON protocol
        pass

    return routes_info


def extract_permission(
    view_intr: Any, configurator: Any, introspector: Optional[Any] = None
) -> Optional[str]:
    """Extract permission from view introspectable or related introspectables.

    First tries to get permission directly from the view introspectable.
    If not found, searches related introspectables in the Pyramid introspection
    system. Pyramid stores permissions in a separate 'permissions' category, but
    links them to views via the 'related' field in the introspection items.

    Args:
        view_intr: The view introspectable
        configurator: Pyramid configurator instance
        introspector: Pyramid introspector instance (optional, will be obtained
                     from configurator.registry.introspector if None)

    Returns:
        Permission string if found, None otherwise
    """
    # First try to get permission directly from view introspectable
    permission = view_intr.get("permission")
    if permission:
        return str(permission)

    # Get introspector if not provided
    if introspector is None:
        introspector = configurator.registry.introspector

    # If not found directly, check related permissions introspectables
    try:
        # Get the view category to find the full introspection item (not just the
        # introspectable)
        view_category = introspector.get_category("views") or []

        # Find the introspection item that contains our view introspectable
        for view_item in view_category:
            item_introspectable = view_item.get("introspectable", {})

            # Match by checking if this is the same view introspectable
            # We can match by route_name and callable
            if item_introspectable.get("route_name") == view_intr.get(
                "route_name"
            ) and item_introspectable.get("callable") == view_intr.get("callable"):
                # Found our view item! Now check the related introspectables
                related_items = view_item.get("related", [])

                for related_introspectable in related_items:
                    # Check if this is a permissions introspectable
                    if (
                        hasattr(related_introspectable, "category_name")
                        and related_introspectable.category_name == "permissions"
                    ):
                        # The permission value is stored in the discriminator
                        return str(related_introspectable.discriminator)

                break  # Found our view, no need to continue searching

    except (AttributeError, KeyError, TypeError) as e:
        # Don't fail introspection if permission extraction fails
        logger.warning(
            f"Failed to extract permission from related introspectables: {e}"
        )

    return None
