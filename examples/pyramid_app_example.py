"""
Example Pyramid application using pyramid_mcp as a plugin.

This example shows how to:
1. Include pyramid_mcp in your Pyramid application
2. Configure MCP settings
3. Register tools using the @tool decorator
4. Create a complete Pyramid application with MCP support
"""

from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from wsgiref.simple_server import make_server

from pyramid_mcp import tool


# Example API views
@view_config(route_name='home', renderer='json')
def home_view(request):
    """Home page view."""
    return {"message": "Welcome to the API", "version": "1.0.0"}


@view_config(route_name='users', renderer='json')
def list_users_view(request):
    """List all users."""
    # Mock users data
    users = [
        {"id": 1, "name": "John Doe", "email": "john@example.com"},
        {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
    ]
    return {"users": users}


# MCP Tools - these will be automatically registered with the MCP server
@tool(name="calculate", description="Perform basic math operations")
def calculate(operation: str, a: float, b: float) -> float:
    """Perform basic math operations.
    
    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number
        
    Returns:
        Result of the operation
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")


@tool(name="echo", description="Echo a message back")
def echo_message(message: str) -> str:
    """Echo a message back to the caller.
    
    Args:
        message: The message to echo
        
    Returns:
        The echoed message
    """
    return f"Echo: {message}"


@tool(name="get_user_count", description="Get the total number of users")
def get_user_count() -> int:
    """Get the total number of users in the system.
    
    Returns:
        Total number of users
    """
    # In a real application, this would query the database
    return 2


def create_app(settings=None):
    """Create and configure the Pyramid application."""
    if settings is None:
        settings = {
            # MCP Configuration
            'mcp.server_name': 'example-api',
            'mcp.server_version': '1.0.0',
            'mcp.mount_path': '/mcp',
            'mcp.enable_sse': 'true',
            'mcp.enable_http': 'true',
        }
    
    # Create Pyramid configurator
    config = Configurator(settings=settings)
    
    # Add regular Pyramid routes
    config.add_route('home', '/')
    config.add_route('users', '/users')
    
    # Include pyramid_mcp plugin - this will:
    # 1. Parse MCP settings from Pyramid settings
    # 2. Create and configure the MCP server
    # 3. Register any @tool decorated functions
    # 4. Mount MCP endpoints at the configured path
    config.include('pyramid_mcp')
    
    # Scan for view configurations
    config.scan()
    
    return config.make_wsgi_app()


def main():
    """Run the example application."""
    # Create the application
    app = create_app()
    
    # Start the server
    server = make_server('localhost', 8080, app)
    print("Server started at http://localhost:8080")
    print("MCP endpoints available at http://localhost:8080/mcp")
    print("API endpoints:")
    print("  - http://localhost:8080/ (home)")
    print("  - http://localhost:8080/users (users list)")
    print("\nMCP Tools registered:")
    print("  - calculate: Perform basic math operations")
    print("  - echo: Echo a message back")
    print("  - get_user_count: Get total number of users")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == '__main__':
    main() 