"""
Tests for MCP security authentication parameters with Pyramid views.

This module tests the integration between:
- Pyramid views using @view_config
- MCP tools using @tool decorator with security parameters
- Authentication parameter handling in real HTTP requests
- End-to-end authentication flow with Bearer and Basic auth

Testing ensures that:
1. Views with @tool(security=...) properly receive authentication parameters
2. Authentication headers are correctly generated and accessible
3. Tool parameters are properly validated and cleaned
4. Real HTTP requests through WebTest work correctly
"""

import json
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid.response import Response
from webtest import TestApp
import pytest

from pyramid_mcp import tool
# Security schemas will be created automatically from strings


# =============================================================================
# 🔐 PYRAMID VIEW + MCP SECURITY INTEGRATION TESTS
# =============================================================================


def test_pyramid_view_with_bearer_auth_integration():
    """Test complete integration of Pyramid view with Bearer authentication."""
    config = Configurator()
    
    # IMPORTANT: Enable route discovery BEFORE including pyramid_mcp
    config.registry.settings.update({  # type: ignore
        'mcp.route_discovery.enabled': 'true'
    })
    
    config.include("pyramid_mcp")

    # Create a real Pyramid view that uses the mcp_security parameter in @view_config
    @view_config(
        route_name="secure_api_endpoint", 
        renderer="json",
        mcp_security="bearer"
    )
    def secure_api_view(request) -> dict:
        """Normal Pyramid view that checks for auth headers."""
        # Get data from request parameters
        try:
            if request.content_type == 'application/json':
                data = request.json_body.get('data', 'default')
            else:
                data = request.params.get('data', 'default')
        except:
            data = 'default'
        
        # Check for Authorization header (set by MCP framework from auth_token parameter)
        auth_header = request.headers.get('Authorization', '')
        
        return {
            "data": data,
            "auth_header_received": bool(auth_header),
            "authorization_header": auth_header,
            "request_method": request.method,
            "view_type": "pyramid_view_with_security"
        }

    # Add the route
    config.add_route("secure_api_endpoint", "/api/secure")
    config.add_view(secure_api_view)
    
    config.scan()

    # Create test app
    app = TestApp(config.make_wsgi_app())

    # Test 1: Initialize MCP
    init_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1,
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
    })
    assert init_response.status_code == 200

    # Test 2: List tools to verify our secure tool is available
    list_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    })
    assert list_response.status_code == 200
    tools = list_response.json["result"]["tools"]
    
    # Find our secure tool (auto-generated name based on route)
    secure_tool_name = "get_secure_api_endpoint"  # Auto-generated from route name + method
    secure_tool = next((t for t in tools if secure_tool_name in t["name"]), None)
    assert secure_tool is not None, f"Tool with '{secure_tool_name}' not found in tools: {[t['name'] for t in tools]}"
    
    # Verify the tool schema includes auth_token parameter
    tool_schema = secure_tool["inputSchema"]
    assert "auth_token" in tool_schema["properties"]
    assert "auth_token" in tool_schema["required"]
    assert tool_schema["properties"]["auth_token"]["type"] == "string"

    # Test 3: Call the tool with authentication
    call_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
            "name": secure_tool["name"],  # Use the actual tool name
            "arguments": {
                "data": "test_data",
                "auth_token": "bearer_token_123"
            }
        }
    })
    assert call_response.status_code == 200
    
    # Verify the response
    result = call_response.json
    assert "result" in result
    assert "content" in result["result"]
    
    # Parse the content (should be JSON from the view)
    content_text = result["result"]["content"][0]["text"]
    response_data = json.loads(content_text)
    
    # Verify the response data
    assert response_data["data"] == "test_data"
    assert response_data["auth_header_received"] is True
    assert response_data["authorization_header"] == "Bearer bearer_token_123"
    assert response_data["view_type"] == "pyramid_view_with_security"

    # Test 4: Verify that missing auth_token causes validation error
    error_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 4,
        "params": {
            "name": secure_tool["name"],  # Use the actual tool name
            "arguments": {
                "data": "test_data"
                # Missing auth_token
            }
        }
    })
    assert error_response.status_code == 200
    assert "error" in error_response.json
    assert "missing_credentials" in error_response.json["error"]["message"]


def test_pyramid_view_with_basic_auth_integration():
    """Test complete integration of Pyramid view with Basic authentication."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Create a real Pyramid view that uses Basic auth
    @view_config(
        route_name="secure_ftp_endpoint", 
        renderer="json",
        mcp_security="basic"
    )
    def secure_ftp_view(pyramid_request, path: str, username: str, password: str) -> dict:
        """Pyramid view that requires Basic authentication."""
        auth_headers = getattr(pyramid_request, 'mcp_auth_headers', {})
        
        return {
            "path": path,
            "auth_headers_available": bool(auth_headers),
            "authorization_header": auth_headers.get("Authorization", ""),
            "auth_type": "basic",
            "view_type": "pyramid_view_with_basic_auth"
        }

    # Add the route
    config.add_route("secure_ftp_endpoint", "/ftp/secure")
    config.add_view(secure_ftp_view)
    
    # Enable route discovery
    config.registry.settings.update({  # type: ignore
        'mcp.route_discovery.enabled': 'true'
    })
    
    config.scan()

    # Create test app
    app = TestApp(config.make_wsgi_app())

    # Initialize MCP
    init_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1
    })
    assert init_response.status_code == 200

    # Get the tool name (auto-generated)
    list_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    })
    tools = list_response.json["result"]["tools"]
    ftp_tool = next((t for t in tools if "ftp" in t["name"].lower()), None)
    assert ftp_tool is not None

    # Call the tool with Basic auth
    call_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
            "name": ftp_tool["name"],
            "arguments": {
                "path": "/home/user",
                "username": "testuser",
                "password": "testpass"
            }
        }
    })
    assert call_response.status_code == 200
    
    # Verify the response
    result = call_response.json
    content_text = result["result"]["content"][0]["text"]
    response_data = json.loads(content_text)
    
    # Verify Basic auth header was created correctly
    assert response_data["path"] == "/home/user"
    assert response_data["auth_headers_available"] is True
    assert response_data["authorization_header"].startswith("Basic ")
    assert response_data["auth_type"] == "basic"

    # Verify the Basic auth encoding is correct
    import base64
    expected_auth = base64.b64encode(b"testuser:testpass").decode('ascii')
    assert response_data["authorization_header"] == f"Basic {expected_auth}"


def test_pyramid_view_security_parameter_validation():
    """Test that security parameters are properly validated in Pyramid views."""
    config = Configurator()
    config.include("pyramid_mcp")

    @view_config(
        route_name="validation_endpoint", 
        renderer="json",
        mcp_security="bearer"
    )
    def validation_view(pyramid_request, message: str, auth_token: str) -> dict:
        """View for testing parameter validation."""
        return {"message": message, "authenticated": True}

    config.add_route("validation_endpoint", "/api/validate")
    config.add_view(validation_view)
    
    config.registry.settings.update({  # type: ignore
        'mcp.route_discovery.enabled': 'true'
    })
    
    config.scan()
    app = TestApp(config.make_wsgi_app())

    # Initialize MCP
    init_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1
    })
    assert init_response.status_code == 200

    # Get tool
    list_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    })
    tools = list_response.json["result"]["tools"]
    validation_tool = next((t for t in tools if "validation" in t["name"]), None)
    assert validation_tool is not None

    # Test 1: Valid parameters
    call_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
            "name": validation_tool["name"],
            "arguments": {
                "message": "test",
                "auth_token": "valid_token"
            }
        }
    })
    assert call_response.status_code == 200

    # Test 2: Missing auth_token should fail
    error_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 4,
        "params": {
            "name": validation_tool["name"],
            "arguments": {
                "message": "test"
                # Missing auth_token
            }
        }
    })
    assert error_response.status_code == 200
    assert "error" in error_response.json

    # Test 3: Empty auth_token should fail
    error_response2 = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 5,
        "params": {
            "name": validation_tool["name"],
            "arguments": {
                "message": "test",
                "auth_token": ""  # Empty token
            }
        }
    })
    assert error_response2.status_code == 200
    assert "error" in error_response2.json
    assert "missing_credentials" in error_response2.json["error"]["message"]


def test_pyramid_view_without_security_still_works():
    """Test that Pyramid views without security parameters still work correctly."""
    config = Configurator()
    config.include("pyramid_mcp")

    @view_config(route_name="normal_endpoint", renderer="json")
    def normal_view(pyramid_request, data: str) -> dict:
        """Normal view without any security requirements."""
        return {"data": data, "secure": False}

    config.add_route("normal_endpoint", "/api/normal")
    config.add_view(normal_view)
    
    config.registry.settings.update({  # type: ignore
        'mcp.route_discovery.enabled': 'true'
    })
    
    config.scan()
    app = TestApp(config.make_wsgi_app())

    # Initialize MCP
    init_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1
    })
    assert init_response.status_code == 200

    # Get tool
    list_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    })
    tools = list_response.json["result"]["tools"]
    normal_tool = next((t for t in tools if "normal" in t["name"]), None)
    assert normal_tool is not None

    # Verify tool does NOT have auth parameters
    tool_schema = normal_tool["inputSchema"]
    assert "auth_token" not in tool_schema["properties"]
    assert "username" not in tool_schema["properties"]
    assert "password" not in tool_schema["properties"]

    # Call tool without auth
    call_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
            "name": normal_tool["name"],
            "arguments": {
                "data": "test_data"
            }
        }
    })
    assert call_response.status_code == 200
    
    result = call_response.json
    content_text = result["result"]["content"][0]["text"]
    response_data = json.loads(content_text)
    
    assert response_data["data"] == "test_data"
    assert response_data["secure"] is False


def test_mixed_secure_and_normal_tools():
    """Test that secure and normal tools can coexist in the same app."""
    config = Configurator()
    config.include("pyramid_mcp")

    @view_config(
        route_name="secure_endpoint", 
        renderer="json",
        mcp_security="bearer"
    )
    def secure_view(pyramid_request, data: str, auth_token: str) -> dict:
        """Secure view requiring Bearer token."""
        return {"data": data, "secure": True, "token_received": bool(auth_token)}

    @view_config(route_name="normal_endpoint", renderer="json")
    def normal_view(pyramid_request, data: str) -> dict:
        """Normal view without security."""
        return {"data": data, "secure": False}

    config.add_route("secure_endpoint", "/api/secure")
    config.add_route("normal_endpoint", "/api/normal")
    config.add_view(secure_view)
    config.add_view(normal_view)
    
    config.registry.settings.update({  # type: ignore
        'mcp.route_discovery.enabled': 'true'
    })
    
    config.scan()
    app = TestApp(config.make_wsgi_app())

    # Initialize MCP
    init_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1
    })
    assert init_response.status_code == 200

    # Get tools
    list_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    })
    tools = list_response.json["result"]["tools"]
    
    secure_tool = next((t for t in tools if "secure" in t["name"]), None)
    normal_tool = next((t for t in tools if "normal" in t["name"]), None)
    
    assert secure_tool is not None
    assert normal_tool is not None

    # Verify secure tool has auth parameters
    secure_schema = secure_tool["inputSchema"]
    assert "auth_token" in secure_schema["properties"]
    
    # Verify normal tool does NOT have auth parameters  
    normal_schema = normal_tool["inputSchema"]
    assert "auth_token" not in normal_schema["properties"]

    # Test 1: Call secure tool with auth
    secure_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 3,
        "params": {
            "name": secure_tool["name"],
            "arguments": {
                "data": "secure_data",
                "auth_token": "test_token"
            }
        }
    })
    assert secure_response.status_code == 200
    
    # Test 2: Call normal tool without auth
    normal_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 4,
        "params": {
            "name": normal_tool["name"],
            "arguments": {
                "data": "normal_data"
            }
        }
    })
    assert normal_response.status_code == 200

    # Verify responses
    secure_result = json.loads(secure_response.json["result"]["content"][0]["text"])
    normal_result = json.loads(normal_response.json["result"]["content"][0]["text"])
    
    assert secure_result["secure"] is True
    assert secure_result["token_received"] is True
    
    assert normal_result["secure"] is False


def test_pyramid_view_security_schema_in_tool_list():
    """Test that tools with security properly include auth parameters in their schemas."""
    config = Configurator()
    config.include("pyramid_mcp")

    @view_config(
        route_name="bearer_endpoint", 
        renderer="json",
        mcp_security="bearer"
    )
    def bearer_view(pyramid_request, data: str, auth_token: str) -> dict:
        """Bearer auth view."""
        return {"data": data, "auth_type": "bearer"}

    @view_config(
        route_name="basic_endpoint", 
        renderer="json",
        mcp_security="basic"
    )
    def basic_view(pyramid_request, data: str, username: str, password: str) -> dict:
        """Basic auth view."""
        return {"data": data, "auth_type": "basic"}

    config.add_route("bearer_endpoint", "/api/bearer")
    config.add_route("basic_endpoint", "/api/basic")
    config.add_view(bearer_view)
    config.add_view(basic_view)
    
    config.registry.settings.update({  # type: ignore
        'mcp.route_discovery.enabled': 'true'
    })
    
    config.scan()
    app = TestApp(config.make_wsgi_app())

    # Initialize MCP
    init_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "initialize",
        "id": 1
    })
    assert init_response.status_code == 200

    # Get tools
    list_response = app.post_json("/mcp", {  # type: ignore
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 2
    })
    tools = list_response.json["result"]["tools"]
    
    bearer_tool = next((t for t in tools if "bearer" in t["name"]), None)
    basic_tool = next((t for t in tools if "basic" in t["name"]), None)
    
    assert bearer_tool is not None
    assert basic_tool is not None

    # Verify Bearer tool schema
    bearer_schema = bearer_tool["inputSchema"]
    assert "data" in bearer_schema["properties"]
    assert "auth_token" in bearer_schema["properties"]
    assert "auth_token" in bearer_schema["required"]
    assert bearer_schema["properties"]["auth_token"]["type"] == "string"

    # Verify Basic tool schema
    basic_schema = basic_tool["inputSchema"]
    assert "data" in basic_schema["properties"]
    assert "username" in basic_schema["properties"]
    assert "password" in basic_schema["properties"]
    assert "username" in basic_schema["required"]
    assert "password" in basic_schema["required"]
    assert basic_schema["properties"]["username"]["type"] == "string"
    assert basic_schema["properties"]["password"]["type"] == "string" 