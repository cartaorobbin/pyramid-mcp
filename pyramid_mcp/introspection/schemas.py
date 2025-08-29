"""
Schema Processing Module

This module handles Marshmallow schema introspection, JSON schema generation,
parameter location determination, and field validation constraints.
"""

import logging
from typing import Any, Dict, List, Optional

import marshmallow
import marshmallow.fields as fields
import marshmallow.validate as validate
from cornice.validators import (
    marshmallow_body_validator,
    marshmallow_querystring_validator,
    marshmallow_validator,
)

from pyramid_mcp.schemas import _safe_nested_schema_introspection

logger = logging.getLogger(__name__)


def extract_marshmallow_schema_info(schema: Any) -> Dict[str, Any]:
    """Extract field information from a Marshmallow schema with complete isolation.

    Args:
        schema: Marshmallow schema instance or class

    Returns:
        Dictionary containing schema field information for MCP
    """
    # Use completely isolated introspection to prevent global state
    # pollution
    try:
        result = _safe_nested_schema_introspection(schema)
        return result
    except Exception as e:
        logger.error(f"   ❌ Exception in extract_marshmallow_schema_info: {e}")
        import traceback

        logger.error(f"   Traceback: {traceback.format_exc()}")
        return {}


def get_nested_schema_class_safely(nested_field: Any) -> Optional[type]:
    """Get the schema class from a Nested field WITHOUT triggering instances.

    This function avoids accessing field.schema which triggers automatic instance
    creation in Marshmallow. Instead, it inspects the field's internal attributes
    to extract the schema class directly.
    """
    # CRITICAL: The 'nested' attribute contains the schema class without instances
    if hasattr(nested_field, "nested"):
        schema_attr = nested_field.nested
        if isinstance(schema_attr, type) and issubclass(
            schema_attr, marshmallow.Schema
        ):
            return schema_attr

    # Fallback: Check other possible attribute names
    for attr_name in ["_schema", "schema_class", "_schema_class", "_nested"]:
        if hasattr(nested_field, attr_name):
            attr_value = getattr(nested_field, attr_name)
            if isinstance(attr_value, type) and issubclass(
                attr_value, marshmallow.Schema
            ):
                return attr_value

    # If we can't find the schema class safely, return None
    # This is better than risking instance creation
    return None


def marshmallow_field_to_mcp_type(field: Any) -> Dict[str, Any]:
    """Convert a Marshmallow field to MCP parameter type.

    Args:
        field: Marshmallow field instance

    Returns:
        Dictionary containing MCP parameter type information
    """
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
            inner_field_info = marshmallow_field_to_mcp_type(field.inner)
            field_info["items"] = inner_field_info
    elif isinstance(field, fields.Nested):
        field_info["type"] = "object"
        # CRITICAL ISOLATION: Get nested schema class WITHOUT triggering instances
        nested_schema_class = get_nested_schema_class_safely(field)
        if nested_schema_class:
            nested_info = extract_marshmallow_schema_info(nested_schema_class)
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
        add_validation_constraints(field, field_info)

    # Add default value if available
    # Check for dump_default first (new marshmallow), then default (old marshmallow)
    if hasattr(field, "dump_default") and field.dump_default is not None:
        if field.dump_default is not marshmallow.missing:
            field_info["default"] = field.dump_default
    elif hasattr(field, "default") and field.default is not None:
        if field.default is not marshmallow.missing:
            field_info["default"] = field.default

    return field_info


def add_validation_constraints(field: Any, field_info: Dict[str, Any]) -> None:
    """Add validation constraints from Marshmallow field to MCP field info.

    Args:
        field: Marshmallow field instance
        field_info: MCP field info dictionary to update
    """
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
        elif validator is marshmallow_validator:
            # Generic validator - need to examine the schema structure
            # to determine the appropriate parameter location
            # This should be handled by the calling code that has access
            # to the schema structure - we can't determine it from the
            # validator alone
            return "schema_dependent"
        # Note: marshmallow_path_validator is less common, add if needed
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
