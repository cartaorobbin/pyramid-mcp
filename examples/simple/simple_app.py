#!/usr/bin/env python3
"""
Simple Pyramid application with MCP integration.

This example demonstrates:
- Basic pyramid-mcp setup using config.include()
- Manual tool registration with @tool decorator
- Automatic route discovery for API endpoints
- How to run the server and connect with MCP clients

Run this example:
    python examples/simple_app.py

Then connect with an MCP client on http://localhost:8080/mcp
"""

from pyramid.config import Configurator
from pyramid.view import view_config
from wsgiref.simple_server import make_server

from pyramid_mcp import tool


# Define some API endpoints that will be auto-discovered as MCP tools
@view_config(route_name="api_hello", renderer="json")
def hello_api(request):
    """Say hello to someone."""
    name = request.params.get("name", "World")
    return {"message": f"Hello, {name}!", "timestamp": "2024-12-28"}


@view_config(route_name="api_users", renderer="json")
def list_users(request):
    """Get a list of users."""
    return {
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
        ]
    }


# Define manual MCP tools using the @tool decorator
@tool(name="calculator", description="Perform basic math calculations")
def calculate(operation: str, a: float, b: float) -> float:
    """Perform basic math operations like add, subtract, multiply, divide.

    Args:
        operation: The math operation (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        The result of the calculation
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None,
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    result = operations[operation](a, b)
    if result is None:
        raise ValueError("Cannot divide by zero")

    return result


@tool(name="text_processor", description="Process text in various ways")
def process_text(text: str, operation: str = "upper") -> str:
    """Process text with various operations.

    Args:
        text: The text to process
        operation: How to process it (upper, lower, reverse, title)

    Returns:
        The processed text
    """
    operations = {
        "upper": str.upper,
        "lower": str.lower,
        "reverse": lambda x: x[::-1],
        "title": str.title,
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    return operations[operation](text)


# Example with permission requirements
@tool(
    name="admin_users", description="Administrative user operations", permission="admin"
)
def admin_user_operations(action: str, user_id: int = None) -> dict:
    """Perform administrative operations on users (requires admin permission).

    Args:
        action: The action to perform (list, create, delete, etc.)
        user_id: User ID for user-specific operations

    Returns:
        Result of the administrative operation
    """
    if action == "list":
        return {
            "users": [
                {"id": 1, "name": "Alice", "role": "user"},
                {"id": 2, "name": "Bob", "role": "admin"},
                {"id": 3, "name": "Charlie", "role": "user"},
            ],
            "total": 3,
        }
    elif action == "delete" and user_id:
        return {"message": f"User {user_id} deleted successfully", "action": "delete"}
    else:
        return {"error": "Invalid action or missing user_id"}


@tool(
    name="user_profile",
    description="Get user profile information",
    permission="authenticated",
)
def get_user_profile(user_id: int) -> dict:
    """Get detailed user profile information (requires authentication).

    Args:
        user_id: The ID of the user to get profile for

    Returns:
        User profile information
    """
    # This would typically fetch from a database
    profiles = {
        1: {
            "id": 1,
            "name": "Alice",
            "email": "alice@example.com",
            "role": "user",
            "last_login": "2024-12-28",
        },
        2: {
            "id": 2,
            "name": "Bob",
            "email": "bob@example.com",
            "role": "admin",
            "last_login": "2024-12-27",
        },
        3: {
            "id": 3,
            "name": "Charlie",
            "email": "charlie@example.com",
            "role": "user",
            "last_login": "2024-12-26",
        },
    }

    profile = profiles.get(user_id)
    if not profile:
        raise ValueError(f"User {user_id} not found")

    return profile


def create_app():
    """Create and configure the Pyramid application with MCP support."""

    # Configure MCP settings
    settings = {
        "mcp.server_name": "simple-pyramid-app",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
        # Enable route discovery for API endpoints
        "mcp.route_discovery.enabled": "true",
        "mcp.route_discovery.include_patterns": "api/*",
    }

    # Create Pyramid configurator
    config = Configurator(settings=settings)

    # Add API routes (these will be auto-discovered as MCP tools)
    config.add_route("api_hello", "/api/hello")
    config.add_route("api_users", "/api/users")

    # Include pyramid-mcp plugin (this registers tools and mounts MCP endpoints)
    config.include("pyramid_mcp")

    # Scan for view configurations
    config.scan()

    return config.make_wsgi_app()


def main():
    """Run the example application."""
    print("🚀 Starting Simple Pyramid + MCP Example")
    print("=" * 50)

    # Create the app
    app = create_app()

    # Start the server
    server = make_server("localhost", 8080, app)

    print("🌍 Server running at: http://localhost:8080")
    print("🔌 MCP endpoint at: http://localhost:8080/mcp")
    print()
    print("📚 Available endpoints:")
    print("  • http://localhost:8080/api/hello?name=YourName")
    print("  • http://localhost:8080/api/users")
    print("  • http://localhost:8080/mcp (MCP JSON-RPC endpoint)")
    print()
    print("🛠️  Available MCP tools:")
    print("  • calculator - Perform math operations (public)")
    print("  • text_processor - Process text (public)")
    print("  • user_profile - Get user profile (requires 'authenticated' permission)")
    print("  • admin_users - Admin operations (requires 'admin' permission)")
    print("  • api_hello - Auto-discovered from /api/hello")
    print("  • api_users - Auto-discovered from /api/users")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped!")


if __name__ == "__main__":
    main()
