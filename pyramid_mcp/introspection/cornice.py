"""
Cornice Integration Module

This module handles the integration with Cornice REST framework,
extracting service metadata and method-specific configurations.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from cornice.service import get_services

logger = logging.getLogger(__name__)


def discover_cornice_services(registry: Any) -> List[Dict[str, Any]]:
    """Discover Cornice services from the Pyramid registry.

    Args:
        registry: Pyramid registry

    Returns:
        List of Cornice service information dictionaries
    """
    cornice_services = []

    try:
        # Get Cornice services

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
                "default_content_type": getattr(service, "default_content_type", None),
                "default_accept": getattr(service, "default_accept", None),
            }
            cornice_services.append(service_info)

    except ImportError:
        # Cornice is not installed, return empty list
        pass
    except Exception:
        # Silently handle errors to avoid interfering with JSON protocol
        pass

    return cornice_services


def find_cornice_service_for_route(
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
    # 🐛 FIX: Sort services by name length (descending) to prefer more
    # specific matches
    # This prevents "buggy_service" from matching "buggy_service_detail"
    sorted_services = sorted(
        cornice_services, key=lambda s: len(s.get("name", "")), reverse=True
    )

    for service_info in sorted_services:
        # Match by service name (Cornice often uses service name as route name)
        if service_info["name"] == route_name:
            return service_info

        # Match by path pattern
        if service_info["path"] == route_pattern:
            return service_info

    # Second pass: Check prefix matching only if no exact matches found
    for service_info in sorted_services:
        # Check if route name contains service name (common pattern)
        # But only if it's not a substring of a longer service name we
        # already checked
        if (
            service_info["name"]
            and route_name.startswith(service_info["name"])
            and service_info["name"] != route_name
        ):  # Avoid duplicate exact matches
            return service_info

    return None


def extract_cornice_view_metadata(
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
                method_matches = method.upper() in [m.upper() for m in request_methods]
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
            # 🔍 DEEP DEBUG: Special logging for workspace parts path
            service_path = cornice_service.get("path", "")
            if (
                "/api/v1/workspaces/parts" in service_path
                or "workspace" in service_path.lower()
            ):
                logger.info(f"🔍 WORKSPACE PARTS DEBUG - Service path: {service_path}")
                logger.info(f"   Service name: {cornice_service.get('name', 'N/A')}")
                logger.info(f"   Method: {method}")
                logger.info(f"   View callable: {view}")
                logger.info(
                    f"   View callable name: {getattr(view, '__name__', 'N/A')}"
                )
                logger.info(f"   Method matches: {method_matches}")
                logger.info(f"   View matches: {view_matches}")
                logger.info(f"   Args keys: {list(args.keys())}")
                logger.info(f"   Schema in args: {args.get('schema')}")
                logger.info(f"   Schema type: {type(args.get('schema'))}")
                logger.info(f"   Validators in args: {args.get('validators', [])}")
                logger.info(f"   Full args: {args}")

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
                k: v for k, v in method_metadata.items() if v is not None and v != []
            }

            metadata["method_specific"][method.upper()] = method_metadata

    return metadata


def extract_service_level_metadata(service: Any) -> Dict[str, Any]:
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
