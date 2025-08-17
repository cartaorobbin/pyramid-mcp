"""
Integration test fixtures and configuration.

This module provides fixtures for integration tests that need specific
user endpoints and other setup.
"""

import pytest
from webtest import TestApp


@pytest.fixture
def integration_app(pyramid_config, users_db, user_id_counter):
    """
    Create a TestApp with MCP and user endpoints for integration testing.

    This fixture uses the modular pyramid_app fixture with user CRUD endpoints
    that are expected by the integration tests.
    """

    # Define user endpoint views
    def create_user(request):
        """Create a new user."""
        user_id_counter["value"] += 1
        user_id = user_id_counter["value"]

        user_data = request.json_body
        user_data["id"] = user_id
        users_db[user_id] = user_data

        return {"user": user_data}

    def list_users(request):
        """List all users."""
        return {"users": list(users_db.values())}

    def get_user(request):
        """Get a specific user."""
        user_id = int(request.matchdict["id"])
        if user_id not in users_db:
            request.response.status = 404
            return {"error": "User not found"}
        return {"user": users_db[user_id]}

    def update_user(request):
        """Update a specific user."""
        user_id = int(request.matchdict["id"])
        if user_id not in users_db:
            request.response.status = 404
            return {"error": "User not found"}

        update_data = request.json_body
        users_db[user_id].update(update_data)
        return {"user": users_db[user_id]}

    def delete_user(request):
        """Delete a specific user."""
        user_id = int(request.matchdict["id"])
        if user_id not in users_db:
            request.response.status = 404
            return {"error": "User not found"}

        deleted_user = users_db.pop(user_id)
        return {"message": "User deleted successfully", "user": deleted_user}

    # Use pyramid_config fixture to create configuration with custom patterns
    settings = {
        "mcp.route_discovery.enabled": True,
        "mcp.server_name": "pyramid-mcp",
        "mcp.server_version": "1.0.0",
        "mcp.mount_path": "/mcp",
    }

    ignore = ["tests.cornice_integration", "tests.openai"]

    # Create basic configuration
    config = pyramid_config(
        settings=settings, scan_path="tests", ignore=ignore, commit=False
    )

    # Add custom routes with specific patterns
    config.add_route("users_collection", "/users")
    config.add_route("user_item", "/users/{id}")

    # Add views to the routes
    config.add_view(
        create_user,
        route_name="users_collection",
        renderer="json",
        request_method="POST",
    )
    config.add_view(
        list_users, route_name="users_collection", renderer="json", request_method="GET"
    )
    config.add_view(
        get_user, route_name="user_item", renderer="json", request_method="GET"
    )
    config.add_view(
        update_user, route_name="user_item", renderer="json", request_method="PUT"
    )
    config.add_view(
        delete_user, route_name="user_item", renderer="json", request_method="DELETE"
    )

    # Commit and create TestApp
    config.commit()

    return TestApp(config.make_wsgi_app())
