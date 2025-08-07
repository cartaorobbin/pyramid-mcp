"""
Test for path parameter resolution in Cornice services.

This test reproduces the issue where path parameters like {uuid_or_tax_id:.*}
are not being properly resolved in subrequests.
"""

from cornice import Service
from pyramid.response import Response


def test_path_parameter_resolution(pyramid_app_with_services, logs):
    """Test that path parameters are properly resolved in subrequests."""

    # Create a simple Cornice service with path parameter
    person_service = Service(
        name="get_person",
        path="/api/v1/persons/{uuid_or_tax_id:.*}",
        description="Get person by UUID or tax ID",
    )

    @person_service.get()
    def get_person_handler(request):
        """Get person by UUID or tax ID."""
        uuid_or_tax_id = request.matchdict["uuid_or_tax_id"]
        return Response(
            json={
                "person_id": uuid_or_tax_id,
                "name": f"Person {uuid_or_tax_id}",
                "status": "found",
            }
        )

    # Create test app with the service
    app = pyramid_app_with_services([person_service])

    # Test MCP tool call with path parameter
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_person",
            "arguments": {"uuid_or_tax_id": "17143981885"},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed and return the person data
    assert response.status_code == 200
    result = response.json
    assert result["id"] == 1
    assert "result" in result

    # The actual person data should be in the MCP context format
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"

    # Extract the actual response content
    actual_content = mcp_result["representation"]["content"]
    expected_content = {
        "person_id": "17143981885",
        "name": "Person 17143981885",
        "status": "found",
    }
    assert actual_content == expected_content

    # Verify the URL was properly constructed using logassert
    # The final URL should have the resolved parameter
    assert "FINAL URL: /api/v1/persons/17143981885" in logs.debug
    # The subrequest should also have the resolved URL
    assert (
        "Created subrequest: GET http://localhost/api/v1/persons/17143981885"
        in logs.info
    )


def test_multiple_path_parameters_resolution(pyramid_app_with_services, logs):
    """Test that multiple path parameters are properly resolved in subrequests."""

    # Create a Cornice service with two path parameters
    user_posts_service = Service(
        name="get_user_post",
        path="/api/v1/users/{user_id}/posts/{post_id:.*}",
        description="Get a specific post by a specific user",
    )

    @user_posts_service.get()
    def get_user_post_handler(request):
        """Get a specific post by a specific user."""
        user_id = request.matchdict["user_id"]
        post_id = request.matchdict["post_id"]
        return Response(
            json={
                "user_id": user_id,
                "post_id": post_id,
                "title": f"Post {post_id} by User {user_id}",
                "status": "published",
            }
        )

    # Create test app with the service
    app = pyramid_app_with_services([user_posts_service])

    # Test MCP tool call with two path parameters
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_user_post",
            "arguments": {"user_id": "123", "post_id": "abc-def-456"},
        },
    }

    response = app.post_json("/mcp", mcp_request)

    # Should succeed and return the post data
    assert response.status_code == 200
    result = response.json
    assert result["id"] == 2
    assert "result" in result

    # The actual post data should be in the MCP context format
    mcp_result = result["result"]
    assert mcp_result["type"] == "mcp/context"

    # Extract the actual response content
    actual_content = mcp_result["representation"]["content"]
    expected_content = {
        "user_id": "123",
        "post_id": "abc-def-456",
        "title": "Post abc-def-456 by User 123",
        "status": "published",
    }
    assert actual_content == expected_content

    # Verify both path parameters were properly resolved
    assert "FINAL URL: /api/v1/users/123/posts/abc-def-456" in logs.debug
    assert (
        "Created subrequest: GET http://localhost/api/v1/users/123/posts/abc-def-456"
        in logs.info
    )
