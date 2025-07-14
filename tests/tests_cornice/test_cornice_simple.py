"""
Test for protected Cornice service with schema validation integrated with pyramid-mcp.

This test demonstrates:
- Single Cornice service with Marshmallow schema validation
- Permission-based protection on the service
- MCP integration through pyramid-mcp's automatic route discovery
- Assertion of view response through MCP call
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields


class CreateProductSchema(Schema):
    """Marshmallow schema for product creation."""

    name = fields.Str(required=True, metadata={"description": "Product name"})
    price = fields.Float(required=True, metadata={"description": "Product price"})
    category = fields.Str(required=False, metadata={"description": "Product category"})


@pytest.fixture
def products_service():
    """Create a Cornice service with schema validation."""
    products = Service(
        name="products",
        path="/products",
        description="Product management service",
    )

    @products.post(schema=CreateProductSchema, validators=(marshmallow_body_validator,))
    def create_product(request):
        """Create a new product with schema validation."""
        # Access validated data directly - marshmallow_body_validator ensures it's there
        validated_data = request.validated

        # Simulate product creation
        product = {
            "id": 1,
            "name": validated_data["name"],
            "price": validated_data["price"],
            "category": validated_data.get("category", "general"),
            "status": "created",
        }

        return {"product": product, "message": "Product created successfully"}

    return products


def test_cornice_service_with_schema_via_mcp(
    pyramid_app_with_services, products_service
):
    """Test that Cornice service with Marshmallow schema works via MCP integration."""
    # Configure MCP settings
    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-server",
        "mcp.server_version": "1.0.0",
    }

    # Create app with Cornice services using the new fixture
    app = pyramid_app_with_services(services=[products_service], settings=settings)

    # Test data for product creation
    product_data = {"name": "Test Widget", "price": 29.99, "category": "electronics"}

    # MCP call to create product
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "create_products", "arguments": product_data},
    }

    # Call the MCP endpoint
    response = app.post_json("/mcp", mcp_request)  # type: ignore

    # Assert successful MCP response
    assert response.status_code == 200
    assert response.content_type == "application/json"

    # Assert MCP response structure
    mcp_response = response.json
    assert mcp_response["id"] == 1
    assert mcp_response["jsonrpc"] == "2.0"
    assert "result" in mcp_response

    # Assert view response content - this is the actual test of the view return value
    result = mcp_response["result"]
    assert "content" in result
    assert len(result["content"]) == 1

    # The response should now be structured JSON instead of text
    content_item = result["content"][0]

    # Check if we got structured JSON (new format) or text (old format)

    view_response = content_item["data"]

    # Test the actual view return value
    assert "product" in view_response
    assert "message" in view_response
    assert view_response["message"] == "Product created successfully"

    # Test the product data returned by the view
    product = view_response["product"]
    assert product["id"] == 1
    assert product["name"] == "Test Widget"
    assert product["price"] == 29.99
    assert product["category"] == "electronics"
    assert product["status"] == "created"


def test_cornice_service_tool_info_validation(
    pyramid_app_with_services, products_service
):
    """Test that Cornice service tool info is properly exposed via MCP."""
    # Create app with Cornice services using the new fixture
    # Note: No settings override - use fixture's isolated configuration
    app = pyramid_app_with_services(services=[products_service])

    # MCP call to list tools
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }

    # Call the MCP endpoint
    response = app.post_json("/mcp", mcp_request)  # type: ignore

    # Assert successful MCP response
    assert response.status_code == 200
    assert response.content_type == "application/json"

    # Assert MCP response structure
    mcp_response = response.json
    assert mcp_response["id"] == 1
    assert mcp_response["jsonrpc"] == "2.0"
    assert "result" in mcp_response

    # Get the tools list
    result = mcp_response["result"]
    assert "tools" in result
    tools = result["tools"]

    # Find the Cornice service tool among all registered tools
    cornice_tools = [tool for tool in tools if tool["name"] == "create_products"]
    assert (
        len(cornice_tools) == 1
    ), f"Expected 1 create_products tool, got {len(cornice_tools)}"

    # Check the Cornice service tool
    tool = cornice_tools[0]
    assert tool["description"] == "Create a new product with schema validation."

    # Validate the input schema contains Marshmallow schema information
    assert "inputSchema" in tool
    input_schema = tool["inputSchema"]

    # This test validates that the Marshmallow schema fields from CreateProductSchema
    # are properly exposed in the MCP tool info

    # The input schema should have properties field containing the Marshmallow fields
    assert "properties" in input_schema
    properties = input_schema["properties"]

    # Validate 'name' field from CreateProductSchema
    assert "name" in properties
    name_field = properties["name"]
    assert name_field["type"] == "string"
    assert name_field["description"] == "Product name"

    # Validate 'price' field from CreateProductSchema
    assert "price" in properties
    price_field = properties["price"]
    assert price_field["type"] == "number"
    assert price_field["description"] == "Product price"

    # Validate 'category' field from CreateProductSchema
    assert "category" in properties
    category_field = properties["category"]
    assert category_field["type"] == "string"
    assert category_field["description"] == "Product category"

    # Validate required fields match the schema
    assert "required" in input_schema
    required_fields = input_schema["required"]
    assert "name" in required_fields
    assert "price" in required_fields
    assert "category" not in required_fields  # Optional field

    # Validate schema structure
    assert input_schema["type"] == "object"
    assert input_schema.get("additionalProperties") is False
