"""
Test for path parameter resolution in Cornice services.

This test reproduces the issue where path parameters like {uuid_or_tax_id:.*}
are not being properly resolved in subrequests.
"""

import pytest
from cornice import Service
from cornice.validators import marshmallow_path_validator, marshmallow_validator
from marshmallow import EXCLUDE, Schema, fields
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


class PathSchema(Schema):
    """Schema for pagination query parameters."""

    uuid = fields.UUID(
        required=True,
        metadata={"description": "UUID"},
    )


@pytest.mark.parametrize("uuid", ["059d1c3a-7cff-4d84-88ae-6b610c69a442"])
def test_path_parameter_resolution_from_schema(uuid, pyramid_app_with_services, logs):
    """Test that path parameters are properly resolved in subrequests."""

    # Create a simple Cornice service with path parameter
    person_service = Service(
        name="get_person",
        path="/api/v1/persons/{uuid:.*}",
        description="Get person by UUID or tax ID",
    )

    @person_service.get(
        schema=PathSchema,
        validators=(marshmallow_path_validator,),
    )
    def get_person_handler(request):
        """Get person by UUID or tax ID."""
        uuid = request.validated["uuid"]
        return Response(
            json={
                "person_id": str(uuid),  # Convert UUID to string for JSON serialization
                "name": f"Person {uuid}",
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
            "arguments": {"uuid": uuid},
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
        "person_id": uuid,
        "name": f"Person {uuid}",
        "status": "found",
    }
    assert actual_content == expected_content

    # Verify the URL was properly constructed using logassert
    # The final URL should have the resolved parameter
    assert f"FINAL URL: /api/v1/persons/{uuid}" in logs.debug
    # The subrequest should also have the resolved URL
    assert (
        f"Created subrequest: GET http://localhost/api/v1/persons/{uuid}" in logs.info
    )


class PathRequestSchema(Schema):
    """Schema for pagination query parameters."""

    class Meta:
        unknown = EXCLUDE

    path = fields.Nested(PathSchema())


@pytest.mark.parametrize("uuid", ["059d1c3a-7cff-4d84-88ae-6b610c69a442"])
def test_path_parameter_resolution_from_schema_marshmallow_validator(
    uuid, pyramid_app_with_services, logs
):
    """Test that path parameters are properly resolved in subrequests."""

    # Create a simple Cornice service with path parameter
    person_service = Service(
        name="get_person",
        path="/api/v1/persons/{uuid:.*}",
        description="Get person by UUID or tax ID",
    )

    @person_service.get(
        schema=PathRequestSchema,
        validators=(marshmallow_validator,),
    )
    def get_person_handler(request):
        """Get person by UUID or tax ID."""
        uuid = request.validated["path"]["uuid"]
        return Response(
            json={
                "person_id": str(uuid),  # Convert UUID to string for JSON serialization
                "name": f"Person {uuid}",
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
            "arguments": {"uuid": uuid},
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
        "person_id": uuid,  # This will be the string UUID from the parameter
        "name": f"Person {uuid}",
        "status": "found",
    }

    assert actual_content == expected_content

    # Verify the URL was properly constructed using logassert
    # The final URL should have the resolved parameter
    assert f"FINAL URL: /api/v1/persons/{uuid}" in logs.debug
    # The subrequest should also have the resolved URL
    assert (
        f"Created subrequest: GET http://localhost/api/v1/persons/{uuid}" in logs.info
    )
