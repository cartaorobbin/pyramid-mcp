"""
Pytest configuration and fixtures for Cornice-specific tests.

This file provides fixtures for testing Cornice integration with pyramid_mcp.
The fixtures follow the same patterns as the main conftest.py but are specialized
for Cornice services.
"""

import pytest

# Import the unified TestSecurityPolicy from main conftest
from tests.conftest import TestSecurityPolicy


@pytest.fixture
def pyramid_app_with_services():
    """
    Create a Pyramid app with Cornice services.

    Special Cornice fixture that follows the unified pattern but handles
    Cornice services. This is the ONLY exception to the unified pyramid_app
    fixture.

    Args:
        services (list): List of Cornice service objects to add
        settings (dict, optional): Pyramid settings to merge with defaults
        scan_path (str, optional): Package path to scan for @tool decorators
            (default: None)

    Returns:
        TestApp: Configured WebTest TestApp instance with Cornice services
    """

    def _create_app(services, settings=None, scan_path=None):
        from pyramid.config import Configurator
        from webtest import TestApp

        # Merge settings with defaults (consistent with main fixture)
        default_settings = {
            "mcp.route_discovery.enabled": "true",
            "mcp.server_name": "test-server",
            "mcp.server_version": "1.0.0",
            "mcp.mount_path": "/mcp",
        }
        if settings:
            default_settings.update(settings)
        final_settings = default_settings

        config = Configurator(settings=final_settings)

        # Set up unified security policy for testing (consistent with main fixture)
        config.set_security_policy(TestSecurityPolicy())

        # Include Cornice first, then pyramid_mcp
        config.include("cornice")
        config.include("pyramid_mcp")

        # Add Cornice services
        for service in services:
            config.add_cornice_service(service)

        # Scan for @tool decorators if requested (consistent with main fixture)
        if scan_path:
            config.scan(scan_path, categories=["pyramid_mcp"])

        return TestApp(config.make_wsgi_app())

    return _create_app
