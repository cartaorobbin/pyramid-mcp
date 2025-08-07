"""
Pytest configuration and fixtures for Cornice-specific tests.

This file provides fixtures for testing Cornice integration with pyramid_mcp.
The fixtures follow the same patterns as the main conftest.py but are specialized
for Cornice services.
"""

import pytest


class SimpleSecurityPolicy:
    """Simple security policy for testing Bearer authentication."""

    def identity(self, request):
        """Check if auth_token was provided via MCP arguments."""
        # pyramid-mcp stores auth headers in request.mcp_auth_headers
        auth_headers = getattr(request, "mcp_auth_headers", {})

        if "Authorization" in auth_headers:
            auth_header = auth_headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
                # For testing, any non-empty token creates a valid identity
                if token:
                    return {
                        "user_id": "test_user",
                        "username": "testuser",
                        "token": token,
                    }

        return None

    def authenticated_userid(self, request):
        """Get the authenticated user ID."""
        identity = self.identity(request)
        return identity.get("user_id") if identity else None

    def permits(self, request, context, permission):
        """Check if current user has the given permission."""
        if permission == "authenticated":
            # Any valid auth_token grants authenticated permission
            return self.identity(request) is not None
        return True

    def effective_principals(self, request):
        """Get all effective principals for the current request."""
        identity = self.identity(request)
        if not identity:
            return ["system.Everyone"]

        principals = ["system.Everyone", "system.Authenticated"]
        if "user_id" in identity:
            principals.append(f"userid:{identity['user_id']}")
        return principals


@pytest.fixture
def pyramid_app_with_services():
    """
    Create a Pyramid app with Cornice services.

    services is a list of Cornice service objects to add to the configuration.
    """

    def _create_app(services, settings=None):
        from pyramid.config import Configurator
        from webtest import TestApp

        # Use provided settings or default

        actual_settings = {
            "mcp.route_discovery.enabled": "true",
            "mcp.server_name": "test-server",
            "mcp.server_version": "1.0.0",
        }

        if settings is not None:
            actual_settings.update(settings)

        config = Configurator(settings=actual_settings)

        # Set up simple security policy for testing
        config.set_security_policy(SimpleSecurityPolicy())

        # Include Cornice first, then pyramid_mcp
        config.include("cornice")
        config.include("pyramid_mcp")

        # Add Cornice services
        for service in services:
            config.add_cornice_service(service)

        return TestApp(config.make_wsgi_app())

    return _create_app
