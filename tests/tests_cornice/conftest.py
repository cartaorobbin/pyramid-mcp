"""
Pytest configuration and fixtures for Cornice-specific tests.

This file provides fixtures for testing Cornice integration with pyramid_mcp.
The fixtures follow the same patterns as the main conftest.py but are specialized
for Cornice services.
"""

import pytest


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
        if settings is None:
            settings = {
                "mcp.route_discovery.enabled": "true",
                "mcp.server_name": "test-server",
                "mcp.server_version": "1.0.0",
            }

        config = Configurator(settings=settings)

        # Include Cornice first, then pyramid_mcp
        config.include("cornice")
        config.include("pyramid_mcp")

        # Add Cornice services
        for service in services:
            config.add_cornice_service(service)

        return TestApp(config.make_wsgi_app())

    return _create_app
