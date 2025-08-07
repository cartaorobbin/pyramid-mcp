"""
Test for Cornice query string validation.

This test explores how Cornice implements validation of query string parameters
using Marshmallow schemas with the marshmallow_querystring_validator.
"""
import pytest
from cornice import Service
from cornice.validators import marshmallow_validator
from marshmallow import EXCLUDE, Schema, fields, pre_load
from pyramid.response import Response


class SubSchema(Schema):
    path = fields.Str(required=True)

    @pre_load
    def pre_load(self, data, **kwargs):
        data["path"] = self.context["request"].path
        return data


class ResponseSchema(Schema):
    path = fields.Str(required=True)
    method = fields.Str(required=True)
    sub = fields.Nested(SubSchema, required=False)

    @pre_load
    def pre_load(self, data, **kwargs):
        data["path"] = self.context["request"].path
        data["sub"] = {"path": "sub"}
        return data


class ParentSchema(Schema):
    """Schema for pagination query parameters."""

    # child = fields.Nested(ChildSchema, required=True)
    name = fields.Str(required=True)
    response = fields.Nested(ResponseSchema, required=False)


class RequestSchema(Schema):
    """Schema for pagination query parameters."""

    class Meta:
        unknown = EXCLUDE

    body = fields.Nested(ParentSchema, required=False)


@pytest.mark.parametrize(
    "settings",
    [{"mcp.route_discovery.enabled": "true"}, {"mcp.route_discovery.enabled": "false"}],
)
def test_cornice_post(settings, pyramid_app_with_services, logs):
    """Test that Cornice validates query string parameters using Marshmallow schema."""

    # Create a Cornice service with querystring validation
    users_service = Service(
        name="users",
        path="/api/v1/users",
        description="List users with pagination query parameters",
    )

    @users_service.post(schema=RequestSchema, validators=(marshmallow_validator,))
    def create_users(request):
        """List users with validated pagination parameters."""
        # Return validated parameters directly
        return Response(json=request.validated)

    # Create test app with the service
    app = pyramid_app_with_services([users_service], settings=settings)

    app.post_json("/api/v1/users", {"name": "John Doe", "response": {"method": "POST"}})
