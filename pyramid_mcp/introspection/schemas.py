"""
Schema Processing Module

This module handles Marshmallow schema introspection, JSON schema generation,
parameter location determination, and field validation constraints.
"""

import logging
from typing import Any, Dict, List, Optional

from cornice.validators import (
    marshmallow_body_validator,
    marshmallow_path_validator,
    marshmallow_querystring_validator,
    marshmallow_validator,
)

from pyramid_mcp.schemas import extract_marshmallow_schema_info

logger = logging.getLogger(__name__)


# All schema introspection functions have been moved to pyramid_mcp.schemas
# This module now only contains introspection-specific parameter location logic


def determine_parameter_location_from_validators(
    validators: List[Any], method_info: Optional[Dict[str, Any]] = None
) -> str:
    """Determine where parameters should be placed based on Cornice validators.

    This examines the actual validators used in the Cornice service to determine
    the correct parameter location, rather than guessing based on HTTP methods.

    Args:
        validators: List of Cornice validators
        method_info: Additional method information (unused for now)

    Returns:
        Parameter location: 'querystring', 'body', or 'path'
    """
    # Check each validator against the imported functions
    for validator in validators:
        # Direct function comparison - much more reliable than string matching
        if validator is marshmallow_body_validator:
            return "body"
        elif validator is marshmallow_querystring_validator:
            return "querystring"
        elif validator is marshmallow_path_validator:
            return "path"
        elif validator is marshmallow_validator:
            # Generic validator - need to examine the schema structure
            # to determine the appropriate parameter location
            # This should be handled by the calling code that has access
            # to the schema structure - we can't determine it from the
            # validator alone
            return "schema_dependent"
    return ""


def determine_location_from_schema_structure(
    schema: Any, method_info: Optional[Dict[str, Any]] = None
) -> str:
    """Determine parameter location by examining the schema structure.

    This method examines the actual schema to determine where parameters
    should be placed when using the generic marshmallow_validator.

    Args:
        schema: Marshmallow schema instance or class
        method_info: Additional method information

    Returns:
        Parameter location: 'querystring', 'body', or 'path'
    """
    if not schema:
        # No schema - default to querystring
        return "querystring"

    try:
        # Extract schema information to examine its structure
        schema_info = extract_marshmallow_schema_info(schema)
        schema_properties = schema_info.get("properties", {})

        # If schema has explicit structure fields, it's handled elsewhere
        # This method is for schemas without explicit structure
        if any(field in schema_properties for field in ["path", "querystring", "body"]):
            # This should be handled by the explicit structure code path
            return "querystring"  # Safe default

        # For schemas without explicit structure, examine the field types
        # and characteristics to make an intelligent decision

        # Check if schema has fields that suggest it's for request body
        # (complex objects, nested fields, file uploads, etc.)
        has_complex_fields = False
        has_file_fields = False

        for field_name, field_info in schema_properties.items():
            field_type = field_info.get("type", "string")
            if field_type in ["object", "array"]:
                has_complex_fields = True
            elif field_info.get("format") == "binary":
                has_file_fields = True

        # Decision logic based on schema characteristics
        if has_file_fields:
            # File uploads typically go in request body
            return "body"
        elif has_complex_fields:
            # Complex nested structures typically go in request body
            return "body"
        elif len(schema_properties) > 5:
            # Many fields often indicate a form/body payload
            return "body"
        else:
            # Simple schemas with few fields typically use querystring
            return "querystring"

    except Exception as e:
        logger.warning(
            f"Error examining schema structure: {e}, defaulting to querystring"
        )
        return "querystring"
