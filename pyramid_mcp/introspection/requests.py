"""
Request Handling Module

This module handles subrequest creation, parameter processing,
response conversion, and transaction configuration.
"""

import json
import logging
import re
import traceback
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlencode

from pyramid.request import Request

from pyramid_mcp.schemas import MCPContextResultSchema

logger = logging.getLogger(__name__)


def create_route_handler(
    route_info: Dict[str, Any],
    view_info: Dict[str, Any],
    method: str,
    security_parameter: str,
    security_conversion_func: Callable,
) -> Callable:
    """Create a handler function that calls the Pyramid view via subrequest.

    Args:
        route_info: Route information
        view_info: View information
        method: HTTP method
        security_parameter: Name of the security parameter
        security_conversion_func: Function to convert security type to schema

    Returns:
        Handler function for MCP tool
    """

    route_pattern = route_info.get("pattern", "")
    route_name = route_info.get("name", "")

    # Get security configuration from view_info using configurable parameter
    security_type = view_info.get(security_parameter)
    security = None
    if security_type:
        security = security_conversion_func(security_type)

    def handler(pyramid_request: Any, **kwargs: Any) -> Dict[str, Any]:
        """MCP tool handler that delegates to Pyramid view via subrequest."""
        # Log tool execution start
        logger.debug(
            f"🚀 Executing MCP tool for route: {route_name} "
            f"({method} {route_pattern})"
        )
        logger.debug(f"🚀 Tool arguments: {kwargs}")
        try:
            # Create subrequest to call the actual route
            logger.debug(f"🔧 Creating subrequest for {route_name}...")
            subrequest = create_subrequest(
                pyramid_request, kwargs, route_pattern, method, security
            )

            # Log subrequest execution
            logger.debug(
                f"🔧 Executing subrequest: {subrequest.method} {subrequest.url}"
            )

            # Execute the subrequest
            response = pyramid_request.invoke_subrequest(subrequest)

            # Convert response to MCP format
            logger.debug("✅ Subrequest completed successfully")
            mcp_result = convert_response_to_mcp(response, view_info)

            return mcp_result

        except Exception as e:
            # Log detailed error information
            logger.error(f"❌ Error executing MCP tool for {route_name}: {str(e)}")
            logger.debug(f"❌ Error type: {type(e).__name__}")
            logger.debug(f"❌ Route: {route_name} ({method} {route_pattern})")
            logger.debug(f"❌ Arguments: {kwargs}")

            # Log additional error context if available
            if hasattr(e, "response"):
                response_obj = getattr(e, "response", None)
                if response_obj:
                    logger.error(
                        f"❌ HTTP Response Status: "
                        f"{getattr(response_obj, 'status_code', 'Unknown')}"
                    )
                    logger.error(
                        f"❌ HTTP Response Text: "
                        f"{getattr(response_obj, 'text', 'N/A')}"
                    )

            # Check if this looks like a content type error
            error_message = str(e).lower()
            if any(
                phrase in error_message
                for phrase in [
                    "unsupported content type",
                    "content-type",
                    "application/json",
                    "form data",
                    "urlencoded",
                ]
            ):
                logger.error("🚨 CONTENT TYPE ERROR DETECTED!")
                logger.error(
                    "🚨 This appears to be related to the hardcoded "
                    "'application/json' content type"
                )
                logger.error(
                    "🚨 Target API may require "
                    "'application/x-www-form-urlencoded' or other content type"
                )

            # Log stack trace for debugging
            logger.debug(f"❌ Full traceback: {traceback.format_exc()}")

            # Return error in MCP format
            return {
                "error": f"Error calling view: {str(e)}",
                "route": route_name,
                "method": method,
                "parameters": kwargs,
            }

    return handler


def create_subrequest(
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

    # 🐛 DEBUG: Log incoming parameters
    logger.debug(f"🔧 Creating subrequest - Route: {route_pattern}, Method: {method}")

    # kwargs should already have auth parameters removed by MCP protocol handler
    filtered_kwargs = kwargs
    # Filtered kwargs logged only if different from original
    if len(filtered_kwargs) != len(kwargs):
        logger.debug(f"🔧 Filtered kwargs (after auth removal): {filtered_kwargs}")

    # Extract path parameters from route pattern
    path_params = re.findall(r"\{([^}]+)\}", route_pattern)
    path_param_names = [param.split(":")[0] for param in path_params]
    logger.debug(f"🔧 Path parameter names: {path_param_names}")

    # Separate path parameters from other parameters (using filtered kwargs)
    path_values = {}
    query_params = {}
    json_body = {}

    # 🔧 SPECIAL HANDLING FOR QUERYSTRING PARAMETER
    # MCP clients (like Claude) send querystring parameters as a nested dict
    # e.g., {"querystring": {"page": 3, "limit": 50}}
    # Extract them as actual query params regardless of HTTP method
    # This is because querystring parameters are meant to be URL query parameters
    if "querystring" in filtered_kwargs:
        querystring_value = filtered_kwargs.pop("querystring")
        logger.debug(f"🔧 Found querystring parameter: {querystring_value}")
        if isinstance(querystring_value, dict):
            # Extract nested parameters and add them to query_params
            # This handles both empty dict {} and dict with values
            query_params.update(querystring_value)
            logger.debug(f"🔧 Extracted query params from querystring: {query_params}")
        # If querystring_value is None or not a dict, we ignore it gracefully
        else:
            logger.debug(f"🔧 Ignoring non-dict querystring value: {querystring_value}")

    # Handle structured parameter groups
    if "path" in filtered_kwargs:
        path_group = filtered_kwargs.pop("path")
        if isinstance(path_group, dict):
            path_values.update(path_group)
            logger.debug(f"🔧 Path parameter group: {path_group}")

    if "body" in filtered_kwargs:
        body_group = filtered_kwargs.pop("body")
        if isinstance(body_group, dict):
            json_body.update(body_group)
            logger.debug(f"🔧 Body parameter group: {body_group}")

    # Process remaining individual parameters
    for key, value in filtered_kwargs.items():
        if key in path_param_names:
            path_values[key] = value
        else:
            if method.upper() in ["POST", "PUT", "PATCH"]:
                json_body[key] = value
            else:
                query_params[key] = value

    # Log parameter distribution summary
    if path_values or query_params or json_body:
        logger.debug(
            f"🔧 Parameters: {len(path_values)} path, "
            f"{len(query_params)} query, {len(json_body)} body"
        )

    # Build the actual URL by replacing path parameters in the pattern
    url = route_pattern
    for param_name, param_value in path_values.items():
        # Replace {param} and {param:regex} patterns with actual values
        url = re.sub(rf"\{{{param_name}(?::[^}}]+)?\}}", str(param_value), url)

    # Add query parameters to URL
    if query_params:
        query_string = urlencode(query_params)
        url = f"{url}?{query_string}"
        logger.debug(f"🔧 Added query string: {query_string}")

    # Create the subrequest
    subrequest = Request.blank(url)
    subrequest.method = method.upper()
    logger.debug(f"🔧 Created subrequest: {method.upper()} {url}")

    # 🌍 ENVIRON SHARING SUPPORT
    # Copy parent request environ to subrequest for better context preservation
    copy_request_environ(pyramid_request, subrequest)

    # Set request body for POST/PUT/PATCH requests
    if method.upper() in ["POST", "PUT", "PATCH"] and json_body:
        # ⚠️ CRITICAL: This is where content type is hardcoded!
        body_json = json.dumps(json_body)
        subrequest.body = body_json.encode("utf-8")
        subrequest.content_type = "application/json"

        # 🐛 DEBUG: Log the critical content type setting
        logger.warning(
            "🚨 HARDCODED CONTENT TYPE: Setting Content-Type to " "'application/json'"
        )
        logger.warning(f"🚨 Request body size: {len(body_json)} characters")
        logger.warning(
            f"🚨 Request body preview: {body_json[:200]}"
            f"{'...' if len(body_json) > 200 else ''}"
        )
        logger.warning(
            "🚨 This may cause 'Unsupported content type' errors with "
            "APIs expecting form data!"
        )

    # Copy important headers from original request
    if hasattr(pyramid_request, "headers"):
        # Copy relevant headers (like Authorization, User-Agent, etc.)
        for header_name in ["Authorization", "User-Agent", "Accept"]:
            if header_name in pyramid_request.headers:
                subrequest.headers[header_name] = pyramid_request.headers[header_name]
                logger.debug(f"🔧 Copied header: {header_name}")

    # Note: Authentication headers are now handled directly by the MCP protocol handler
    # in _create_tool_subrequest() method, not here

    # 🐛 INFO: Log final subrequest details
    # Log final subrequest summary
    logger.debug(f"🔧 Subrequest: {subrequest.method} {subrequest.url}")

    # 🔄 PYRAMID_TM TRANSACTION SHARING SUPPORT
    # Ensure subrequest shares the same transaction context as the parent request
    configure_transaction(pyramid_request, subrequest)

    return subrequest


def configure_transaction(pyramid_request: Any, subrequest: Any) -> None:
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


def copy_request_environ(pyramid_request: Any, subrequest: Any) -> None:
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


def convert_response_to_mcp(
    response: Any, view_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convert Pyramid view response to MCP tool response format.

    Args:
        response: Pyramid view response (dict, string, or Response object)
        view_info: Optional view information for content type detection

    Returns:
        MCP-compatible response in new context format
    """
    # Create MCP context using the schema - all response parsing logic
    # is handled in the schema's @pre_dump method
    schema = MCPContextResultSchema()

    # If we have view_info, pass it along for better source naming
    data = {"response": response, "view_info": view_info}
    return schema.dump(data)  # type: ignore[no-any-return]


def normalize_path_pattern(pattern: str) -> str:
    """Normalize path pattern for matching.

    Args:
        pattern: Route pattern to normalize

    Returns:
        Normalized pattern
    """
    # Remove regex constraints from path parameters
    # e.g., {id:\d+} -> {id}, {filename:.+} -> {filename}
    normalized = re.sub(r"\{([^}:]+):[^}]+\}", r"{\1}", pattern)
    return normalized
