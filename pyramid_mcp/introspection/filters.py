"""
Filtering Module

This module handles filtering logic for routes and tools,
including pattern matching, exclusion rules, and include/exclude patterns.
"""

import re
from typing import Any, Dict

from pyramid_mcp.protocol import MCPTool


def should_exclude_route(route_info: Dict[str, Any], config: Any) -> bool:
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
            pattern_matches_route(pattern, route_pattern, route_name)
            for pattern in include_patterns
        ):
            return True

    # Check exclude patterns
    exclude_patterns = getattr(config, "exclude_patterns", None)
    if exclude_patterns:
        if any(
            pattern_matches_route(pattern, route_pattern, route_name)
            for pattern in exclude_patterns
        ):
            return True

    return False


def should_exclude_tool(tool: MCPTool, config: Any) -> bool:
    """Check if a tool should be excluded based on its name.

    Args:
        tool: MCPTool instance to check
        config: MCP configuration

    Returns:
        True if tool should be excluded, False otherwise
    """
    tool_name = tool.name

    # Check exclude patterns against tool name
    exclude_patterns = getattr(config, "exclude_patterns", None)
    if exclude_patterns:
        if any(
            tool_pattern_matches(pattern, tool_name) for pattern in exclude_patterns
        ):
            return True

    return False


def tool_pattern_matches(pattern: str, tool_name: str) -> bool:
    """Check if a pattern matches a tool name.

    Args:
        pattern: Pattern to match (supports wildcards like 'admin*')
        tool_name: Tool name to check

    Returns:
        True if pattern matches, False otherwise
    """
    # Handle wildcard patterns
    if "*" in pattern or "?" in pattern:
        # Pattern with wildcards - convert to regex
        pattern_regex = pattern.replace("*", ".*").replace("?", ".")
        pattern_regex = f"^{pattern_regex}$"
        return bool(re.match(pattern_regex, tool_name))
    else:
        # Exact pattern - should match as prefix or exact match
        return tool_name == pattern or tool_name.startswith(pattern + "_")


def pattern_matches_route(pattern: str, route_pattern: str, route_name: str) -> bool:
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
