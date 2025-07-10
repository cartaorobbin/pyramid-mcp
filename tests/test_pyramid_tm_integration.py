"""
Test pyramid_tm integration with pyramid-mcp subrequests.

This test verifies that subrequests share the same transaction context
as the parent request when pyramid_tm is active.
"""

import pytest
from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.view import view_config

from pyramid_mcp.introspection import PyramidIntrospector


@pytest.fixture
def pyramid_tm_config():
    """Set up Pyramid application with pyramid_tm."""
    config = Configurator()
    config.include("pyramid_tm")

    # Add a simple test route
    config.add_route("test_route", "/test")

    @view_config(route_name="test_route", renderer="json")
    def test_view(request):
        return {"message": "test response", "has_tm": hasattr(request, "tm")}

    config.add_view(test_view)
    config.scan()

    return config


def test_pyramid_tm_transaction_sharing(pyramid_tm_config):
    """Test that subrequests share transaction context with parent request."""
    # Create pyramid_mcp introspector
    introspector = PyramidIntrospector(pyramid_tm_config)

    # Create a parent request that would have pyramid_tm active
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    # Set up transaction manager on parent request (simulating pyramid_tm)
    import transaction

    parent_request.tm = transaction.TransactionManager()

    # Create subrequest using our introspector
    subrequest = introspector._create_subrequest(parent_request, {}, "/test", "GET")

    # Verify transaction sharing
    assert hasattr(subrequest, "tm")
    assert subrequest.tm is parent_request.tm
    assert subrequest.registry is parent_request.registry


def test_configure_transaction_method(pyramid_tm_config):
    """Test the configure_transaction method directly."""
    # Create pyramid_mcp introspector
    introspector = PyramidIntrospector(pyramid_tm_config)

    # Create a parent request with transaction manager
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    import transaction

    parent_request.tm = transaction.TransactionManager()

    # Create a subrequest without transaction manager
    subrequest = Request.blank("/test")

    # Call configure_transaction directly
    introspector.configure_transaction(parent_request, subrequest)

    # Verify transaction was configured
    assert hasattr(subrequest, "tm")
    assert subrequest.tm is parent_request.tm
    assert subrequest.registry is parent_request.registry


def test_subrequest_environ_sharing(pyramid_tm_config):
    """Test that subrequest inherits environ from parent request."""
    # Create pyramid_mcp introspector
    introspector = PyramidIntrospector(pyramid_tm_config)

    # Create a parent request with custom environ data
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    # Add some custom environ data to parent request
    parent_request.environ["CUSTOM_VAR"] = "test_value"
    parent_request.environ["SERVER_NAME"] = "localhost"
    parent_request.environ["HTTP_X_FORWARDED_FOR"] = "192.168.1.1"
    parent_request.environ["wsgi.version"] = (1, 0)

    # Create subrequest using our introspector
    subrequest = introspector._create_subrequest(parent_request, {}, "/test", "GET")

    # Verify environ sharing
    assert subrequest.environ["CUSTOM_VAR"] == "test_value"
    assert subrequest.environ["SERVER_NAME"] == "localhost"
    assert subrequest.environ["HTTP_X_FORWARDED_FOR"] == "192.168.1.1"
    assert subrequest.environ["wsgi.version"] == (1, 0)

    # Verify subrequest-specific values are preserved
    assert subrequest.environ["REQUEST_METHOD"] == "GET"
    assert subrequest.environ["PATH_INFO"] == "/test"
    assert "REQUEST_METHOD" in subrequest.environ
    assert "PATH_INFO" in subrequest.environ
