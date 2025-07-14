#!/usr/bin/env python3
"""
Cornice + Bearer Authentication + MCP Integration Example

This example demonstrates:
- Cornice REST services with Bearer token authentication
- Marshmallow schema validation
- MCP integration with bearer security
- Proper Bearer token validation
- Different security levels (public, authenticated, admin)

Run this example:
    python examples/cornice-bearer/cornice_bearer_app.py

Then connect with an MCP client on http://localhost:8080/mcp
"""

from typing import Any, Dict, Optional
from wsgiref.simple_server import make_server

from marshmallow import Schema, fields
from pyramid.config import Configurator
from pyramid.request import Request

# Bearer Token Storage (In production, use a proper database/cache)
VALID_TOKENS = {
    "user-token-123": {
        "user_id": 1,
        "username": "alice",
        "role": "user",
        "permissions": ["read", "write"],
    },
    "admin-token-456": {
        "user_id": 2,
        "username": "bob",
        "role": "admin",
        "permissions": ["read", "write", "admin", "delete"],
    },
    "service-token-789": {
        "user_id": 3,
        "username": "service",
        "role": "service",
        "permissions": ["read", "write", "admin", "service"],
    },
}


# Marshmallow Schemas for Validation
class CreateUserSchema(Schema):
    """Schema for creating a new user."""

    username = fields.Str(required=True, validate=lambda x: len(x) >= 3)
    email = fields.Email(required=True)
    role = fields.Str(required=True, validate=lambda x: x in ["user", "admin"])
    full_name = fields.Str(required=False)


class UpdateUserSchema(Schema):
    """Schema for updating a user."""

    email = fields.Email(required=False)
    role = fields.Str(required=False, validate=lambda x: x in ["user", "admin"])
    full_name = fields.Str(required=False)


class CreatePostSchema(Schema):
    """Schema for creating a blog post."""

    title = fields.Str(required=True, validate=lambda x: len(x) >= 5)
    content = fields.Str(required=True, validate=lambda x: len(x) >= 10)
    category = fields.Str(
        required=False, validate=lambda x: x in ["tech", "business", "personal"]
    )
    published = fields.Bool(required=False, default=False)


class AdminActionSchema(Schema):
    """Schema for admin actions."""

    action = fields.Str(
        required=True,
        validate=lambda x: x in ["backup", "cleanup", "reset", "maintenance"],
    )
    target = fields.Str(required=False)
    force = fields.Bool(required=False, default=False)


# Bearer Token Validation Function
def validate_bearer_token(request: Request) -> Optional[Dict[str, Any]]:
    """
    Validate Bearer token from Authorization header.

    Returns:
        User info dict if valid, None if invalid
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]  # Remove 'Bearer ' prefix

    return VALID_TOKENS.get(token)


# Bearer Token Permission Checker
def check_permission(user_info: Dict[str, Any], required_permission: str) -> bool:
    """Check if user has required permission."""
    if not user_info:
        return False

    user_permissions = user_info.get("permissions", [])
    return required_permission in user_permissions


# Cornice Services are now defined in services.py and imported after pyramid-mcp setup


def create_app() -> Any:
    """Create and configure the Pyramid application with Cornice and MCP support."""

    # Configure MCP settings
    settings = {
        "mcp.server_name": "cornice-bearer-auth-app",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
        # Enable route discovery for Cornice services
        "mcp.route_discovery.enabled": "true",
        "mcp.route_discovery.include_patterns": "api/*",
        "mcp.security_parameter": "pcm_security",
    }

    # Create Pyramid configurator
    config = Configurator(settings=settings)

    # Include Cornice
    config.include("cornice")

    # Include pyramid-mcp plugin
    config.include("pyramid_mcp")

    # Scan for services (this will find and import the services module)
    config.scan("examples.cornice_bearer.services")

    return config.make_wsgi_app()


def main() -> None:
    """Run the example application."""
    print("🔐 Cornice + Bearer Auth + MCP Example")
    print("=" * 50)

    # Create the app
    app = create_app()

    # Start the server
    server = make_server("localhost", 8080, app)

    print("🌍 Server running at: http://localhost:8080")
    print("🔌 MCP endpoint at: http://localhost:8080/mcp")
    print()
    print("📚 Available endpoints:")
    print("  • GET  /api/public/info (public)")
    print("  • GET  /api/users (requires Bearer token)")
    print("  • POST /api/users (requires Bearer token + write permission)")
    print("  • GET  /api/posts (requires Bearer token)")
    print("  • POST /api/posts (requires Bearer token + write permission)")
    print("  • POST /api/admin/actions (requires Bearer token + admin permission)")
    print()
    print("🔑 Valid Bearer Tokens:")
    print("  • user-token-123 (user permissions: read, write)")
    print("  • admin-token-456 (admin permissions: read, write, admin, delete)")
    print("  • service-token-789 (service permissions: read, write, admin, service)")
    print()
    print("🛠️  MCP Tools (Bearer auth integrated):")
    print("  • get_api_public_info - Public server info (no auth)")
    print("  • list_api_users - List users (Bearer required)")
    print("  • create_api_users - Create user (Bearer + write required)")
    print("  • list_api_posts - List posts (Bearer required)")
    print("  • create_api_posts - Create post (Bearer + write required)")
    print("  • perform_api_admin_actions - Admin actions (Bearer + admin required)")
    print()
    print("🧪 Test with curl:")
    print(
        "curl -H 'Authorization: Bearer user-token-123' http://localhost:8080/api/users"
    )
    print("curl -H 'Authorization: Bearer admin-token-456' \\")
    print("     -H 'Content-Type: application/json' \\")
    print('     -d \'{"action": "backup"}\' \\')
    print("     http://localhost:8080/api/admin/actions")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped!")


if __name__ == "__main__":
    main()
