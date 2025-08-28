import pytest
from cornice import Service
from cornice.validators import marshmallow_validator
from marshmallow import EXCLUDE, Schema, fields
from pyramid.response import Response


class PathSchema(Schema):
    """Schema for pagination query parameters."""

    uuid = fields.UUID(
        required=True,
        metadata={"description": "UUID"},
    )


class PathRequestSchema(Schema):
    """Schema for pagination query parameters."""

    class Meta:
        unknown = EXCLUDE

    path = fields.Nested(PathSchema())


@pytest.fixture
def person_services():
    """Fixture that creates the person services used across tests."""

    # Service for getting all persons (no parameters)
    persons_service = Service(
        name="persons_service",
        path="/api/v1/persons",
        description="Get person by UUID or tax ID",
    )

    @persons_service.get()
    def get_persons_handler(request):
        """Get person by UUID or tax ID."""
        return Response(
            json=[
                {
                    "person_id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Person 1",
                    "status": "active",
                },
                {
                    "person_id": "987fcdeb-51a2-43d1-9f12-345678901234",
                    "name": "Person 2",
                    "status": "active",
                },
            ]
        )

    # Service for getting a specific person (with path parameter)
    person_service = Service(
        name="person_service",
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
                "person_id": str(uuid),
                "name": f"Person {uuid}",
                "status": "found",
            }
        )

    return [person_service, persons_service]


@pytest.mark.parametrize("uuid", ["059d1c3a-7cff-4d84-88ae-6b610c69a442"])
def test_path_parameter_resolution_from_schema_marshmallow_validator(
    uuid, pyramid_app_with_services, person_services, logs
):
    """Test that path parameters are properly resolved in subrequests."""

    # Create test app with the services from fixture
    app = pyramid_app_with_services(person_services)

    tools_response = app.post_json(
        "/mcp", {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
    )

    assert tools_response.json == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "tools": [
                {
                    "name": "get_person_service",
                    "description": "Get person by UUID or tax ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "object",
                                "properties": {
                                    "uuid": {
                                        "type": "string",
                                        "format": "uuid",
                                        "description": "UUID",
                                    }
                                },
                                "required": ["uuid"],
                                "additionalProperties": False,
                            }
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                },
                {
                    "name": "get_persons_service",
                    "description": "Get person by UUID or tax ID.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                        "additionalProperties": False,
                    },
                },
            ]
        },
    }


def test_get_person_service_call_with_path_parameter(
    pyramid_app_with_services, person_services
):
    """Test calling get_person_service with proper path parameter."""

    # Create test app with the services from fixture
    app = pyramid_app_with_services(person_services)

    # Call the get_person_service tool with structured path parameter
    test_uuid = "059d1c3a-7cff-4d84-88ae-6b610c69a442"
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "get_person_service",
                "arguments": {"path": {"uuid": test_uuid}},
            },
        },
    )

    # Get the actual response and extract the dynamic timestamp
    actual_response = call_response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    # Assert the complete response structure
    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": {
                        "person_id": test_uuid,
                        "name": f"Person {test_uuid}",
                        "status": "found",
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": f"http://localhost/api/v1/persons/{test_uuid}",
                "fetched_at": fetched_at,  # Use the actual dynamic timestamp
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


def test_get_person_service_call_with_invalid_uuid(
    pyramid_app_with_services, person_services
):
    """Test calling get_person_service with an invalid UUID format."""

    # Create test app with the services from fixture
    app = pyramid_app_with_services(person_services)

    # Call the get_person_service tool with invalid UUID
    invalid_uuid = "not-a-valid-uuid"
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {
                "name": "get_person_service",
                "arguments": {"path": {"uuid": invalid_uuid}},
            },
        },
    )

    # Get the actual response and extract the dynamic timestamp
    actual_response = call_response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    # Assert the complete error response structure
    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": {
                        "status": "error",
                        "errors": [
                            {
                                "location": "path",
                                "name": "uuid",
                                "description": ["Not a valid UUID."],
                            }
                        ],
                    },
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": f"http://localhost/api/v1/persons/{invalid_uuid}",
                "fetched_at": fetched_at,
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }


def test_get_persons_service_call_without_parameters(
    pyramid_app_with_services, person_services
):
    """Test calling get_persons_service without parameters."""

    # Create test app with the services from fixture
    app = pyramid_app_with_services(person_services)

    # Call the get_persons_service tool without parameters
    call_response = app.post_json(
        "/mcp",
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
            "params": {"name": "get_persons_service", "arguments": {}},
        },
    )

    # Get the actual response and extract the dynamic timestamp
    actual_response = call_response.json
    fetched_at = actual_response["result"]["source"]["fetched_at"]

    # Assert the complete response structure
    assert actual_response == {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": "IMPORTANT: All that is at data key.",
                    "data": [
                        {
                            "person_id": "123e4567-e89b-12d3-a456-426614174000",
                            "name": "Person 1",
                            "status": "active",
                        },
                        {
                            "person_id": "987fcdeb-51a2-43d1-9f12-345678901234",
                            "name": "Person 2",
                            "status": "active",
                        },
                    ],
                }
            ],
            "type": "mcp/context",
            "version": "1.0",
            "source": {
                "kind": "rest_api",
                "name": "PyramidAPI",
                "url": "http://localhost/api/v1/persons",
                "fetched_at": fetched_at,  # Use the actual dynamic timestamp
            },
            "tags": ["api_response"],
            "llm_context_hint": "This is a response from a Pyramid API",
        },
    }
