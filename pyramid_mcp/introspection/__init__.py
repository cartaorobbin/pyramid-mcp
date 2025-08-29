"""
Pyramid Introspection Package

This package provides functionality to discover and analyze Pyramid routes
and convert them into MCP tools. Includes support for Cornice REST framework
to extract enhanced metadata and validation information.

The package is organized into focused modules:
- core: Main PyramidIntrospector class and coordination
- routes: Route discovery and view introspection
- cornice: Cornice service integration
- schemas: Marshmallow schema processing
- requests: Subrequest creation and response handling
- tools: MCP tool generation and naming
- security: Security schema conversion
"""

from pyramid_mcp.introspection.core import PyramidIntrospector

# Main exports - this is what external code should import
__all__ = ["PyramidIntrospector"]
