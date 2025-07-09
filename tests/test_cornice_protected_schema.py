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
from pyramid.config import Configurator
from webtest import TestApp


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


@pytest.fixture
def pyramid_config_with_service(products_service):
    """Pyramid configuration with Cornice service."""
    config = Configurator()
    config.include("cornice")

    # Note: No authentication required - focusing on schema validation and view response

    # Add the service
    config.add_cornice_service(products_service)

    # Configure MCP settings to enable route discovery
    config.registry.settings.update(
        {  # type: ignore
            "mcp.route_discovery.enabled": "true",
            "mcp.server_name": "test-server",
            "mcp.server_version": "1.0.0",
        }
    )

    # Include pyramid-mcp for automatic route discovery
    config.include("pyramid_mcp")

    return config


def test_cornice_service_with_schema_via_mcp(pyramid_config_with_service):
    """Test that Cornice service with Marshmallow schema works via MCP integration."""
    config = pyramid_config_with_service
    app = TestApp(config.make_wsgi_app())

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

    # Parse the actual view response to test the business logic
    import json

    # Debug: Print what we actually got
    text_content = result["content"][0]["text"]
    print(f"Raw response text: {text_content}")

    view_response = json.loads(text_content)

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
