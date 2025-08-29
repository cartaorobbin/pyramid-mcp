"""
Security Processing Module

This module handles security schema conversion and authentication processing.
"""

import logging
from typing import Any, Optional

from pyramid_mcp.security import BasicAuthSchema, BearerAuthSchema

logger = logging.getLogger(__name__)


def convert_security_type_to_schema(security_type: str) -> Optional[Any]:
    """Convert string security type to appropriate schema object.

    Args:
        security_type: String security type ("bearer", "basic", "BearerAuth", etc.)

    Returns:
        Appropriate security schema object or None if unknown
    """
    security_type_lower = security_type.lower()

    # Handle various forms of Bearer authentication
    if security_type_lower in ["bearer", "bearerauth", "bearer_auth", "jwt"]:
        return BearerAuthSchema()
    # Handle various forms of Basic authentication
    elif security_type_lower in ["basic", "basicauth", "basic_auth"]:
        return BasicAuthSchema()
    else:
        # Unknown security type, return None
        return None
