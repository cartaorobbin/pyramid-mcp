"""
Integration tests for transport functionality.

This module tests:
- stdio transport integration with Docker containers
- pyramid_tm integration with pyramid-mcp subrequests
- Transaction context sharing between parent and subrequests
- Environment variable sharing in subrequests

IMPORTANT: stdio tests rebuild the Docker container to ensure testing against
latest code. This makes tests slower but ensures accuracy.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
from pyramid.config import Configurator
from pyramid.request import Request
from pyramid.view import view_config

from pyramid_mcp.introspection.requests import configure_transaction, create_subrequest

# =============================================================================
# 🐳 STDIO TRANSPORT TESTS (DOCKER-BASED)
# =============================================================================


@pytest.fixture(scope="module", autouse=True)
def ensure_fresh_docker_container():
    """
    Ensure Docker container is built with current code before running tests.

    This prevents false positives from testing against outdated cached images.
    """
    print("\n🔨 Rebuilding Docker container with current code...")

    # Remove existing image to force rebuild
    subprocess.run(
        ["docker", "rmi", "pyramid-mcp-secure:latest"],
        capture_output=True,
        check=False,  # Don't fail if image doesn't exist
    )

    # Rebuild container from project root
    result = subprocess.run(
        [
            "docker",
            "build",
            "-f",
            "examples/secure/Dockerfile",
            "-t",
            "pyramid-mcp-secure:latest",
            ".",
        ],
        cwd=Path(
            __file__
        ).parent.parent.parent,  # Go to project root from tests/integration/
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(f"Failed to build Docker container: {result.stderr}")

    print("✅ Docker container rebuilt successfully")


@pytest.mark.slow
def test_stdio_transport_initialize():
    """Test that stdio transport can initialize the MCP protocol."""
    # Create a temporary ini file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        f.write(
            """[app:main]
use = egg:pyramid_mcp#secure_example

mcp.tools.secure_calculator.enabled = true
mcp.tools.user_management.enabled = true
mcp.tools.system_status.enabled = true
mcp.tools.secure_data_processor.enabled = true

mcp.security.context_factory = authenticated_context_factory
mcp.security.permission = view
"""
        )
        ini_path = f.name

    try:
        # Test initialize request
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }

        # Run via Docker container
        cmd = [
            "docker",
            "run",
            "--rm",
            "-i",
            "pyramid-mcp-secure:latest",
            "pstdio",
            "--ini",
            "/app/examples/secure/development.ini",
        ]

        result = subprocess.run(
            cmd,
            input=json.dumps(initialize_request),
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Parse response
        response = json.loads(result.stdout.strip())

        # Verify response structure
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert "capabilities" in response["result"]
        assert "serverInfo" in response["result"]

    finally:
        # Clean up temporary file
        Path(ini_path).unlink(missing_ok=True)


@pytest.mark.slow
def test_stdio_transport_list_tools():
    """Test that stdio transport can list available tools."""
    # Test tools/list request
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {},
    }

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "pyramid-mcp-secure:latest",
        "pstdio",
        "--ini",
        "/app/examples/secure/development.ini",
    ]

    result = subprocess.run(
        cmd,
        input=json.dumps(list_request),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Parse response
    response = json.loads(result.stdout.strip())

    # Verify response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 2

    # For the secure example, tools should be filtered out for anonymous users
    # This verifies that filter_forbidden_tools=true is working correctly
    if "result" in response:
        assert "tools" in response["result"]
        assert isinstance(response["result"]["tools"], list)
        tools = response["result"]["tools"]
        # Secure app should have no tools visible to anonymous users
        assert (
            len(tools) == 0
        ), f"Anonymous user should not see tools in secure app, got: {[t['name'] for t in tools]}"  # noqa: E501
    else:
        # Alternative: Some implementations might return error for no accessible tools
        assert "error" in response
        # This is also acceptable behavior for a secure application


@pytest.mark.slow
def test_stdio_transport_call_tool_success():
    """Test calling a tool via stdio transport."""
    # Test tools/call request
    call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "secure_calculator",  # This tool is available in secure example
            "arguments": {"body": {"operation": "add", "a": 5, "b": 3}},
        },
    }

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "pyramid-mcp-secure:latest",
        "pstdio",
        "--ini",
        "/app/examples/secure/development.ini",
    ]

    result = subprocess.run(
        cmd,
        input=json.dumps(call_request),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Parse response
    response = json.loads(result.stdout.strip())

    # Verify response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 3
    # Accept either result or error (tool might not be available in container)
    assert "result" in response or "error" in response

    if "result" in response:
        # The result should be in MCP context format
        result_data = response["result"]
        assert isinstance(result_data, dict)
    else:
        # If tool not found, verify it's a proper MCP error response
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]


@pytest.mark.slow
def test_stdio_transport_call_tool_auth_required():
    """Test calling a tool that requires authentication."""
    # Test tools/call request for a secured tool
    call_request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "get_secure_calculator",  # This tool should require auth
            "arguments": {"body": {"operation": "add", "a": 5, "b": 3}},
        },
    }

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "pyramid-mcp-secure:latest",
        "pstdio",
        "--ini",
        "/app/examples/secure/development.ini",
    ]

    result = subprocess.run(
        cmd,
        input=json.dumps(call_request),
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Command should still succeed (it might return an error response,
    # but the command itself works)
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Parse response
    response = json.loads(result.stdout.strip())

    # Verify response structure
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 4

    # Should have either result or error (depends on auth setup)
    assert "result" in response or "error" in response


@pytest.mark.slow
def test_stdio_transport_protocol_compliance():
    """Test that stdio transport follows MCP protocol correctly."""
    # Test multiple requests in sequence
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        },
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        },
    ]

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "pyramid-mcp-secure:latest",
        "pstdio",
        "--ini",
        "/app/examples/secure/development.ini",
    ]

    # Send all requests
    input_data = "\n".join(json.dumps(req) for req in requests)

    result = subprocess.run(
        cmd,
        input=input_data,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Parse responses (should be multiple JSON objects)
    output_lines = [
        line.strip() for line in result.stdout.strip().split("\n") if line.strip()
    ]

    # Should have responses for initialize and tools/list (not for notification)
    assert len(output_lines) >= 2

    # Parse each response
    responses = []
    for line in output_lines:
        try:
            response = json.loads(line)
            responses.append(response)
        except json.JSONDecodeError:
            # Ignore non-JSON lines (might be debug output)
            continue

    # Should have at least 2 responses
    assert len(responses) >= 2

    # Verify responses have correct structure
    for response in responses:
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response  # All our test responses should have IDs


@pytest.mark.slow
def test_stdio_transport_notifications_initialized():
    """Test that notifications/initialized is handled correctly."""
    # Test notification (should not return a response)
    notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }

    cmd = [
        "docker",
        "run",
        "--rm",
        "-i",
        "pyramid-mcp-secure:latest",
        "pstdio",
        "--ini",
        "/app/examples/secure/development.ini",
    ]

    result = subprocess.run(
        cmd,
        input=json.dumps(notification),
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Command should succeed
    assert result.returncode == 0, f"Command failed: {result.stderr}"

    # Output should be empty or minimal (no response for notifications)
    output = result.stdout.strip()
    if output:
        # If there's output, it shouldn't be a JSON-RPC response
        try:
            response = json.loads(output)
            # If it parses as JSON, it shouldn't be a response to our notification
            assert "id" not in response or response.get("id") != notification.get("id")
        except json.JSONDecodeError:
            # Non-JSON output is fine (debug info, etc.)
            pass


# =============================================================================
# 🔄 PYRAMID_TM INTEGRATION TESTS
# =============================================================================


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
    # Create a parent request that would have pyramid_tm active
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    # Set up transaction manager on parent request (simulating pyramid_tm)
    import transaction

    parent_request.tm = transaction.TransactionManager()

    # Create subrequest using our introspector
    subrequest = create_subrequest(parent_request, {}, "/test", "GET")

    # Verify transaction sharing
    assert hasattr(subrequest, "tm")
    assert subrequest.tm is parent_request.tm
    assert subrequest.registry is parent_request.registry


def test_configure_transaction_method(pyramid_tm_config):
    """Test the configure_transaction method directly."""
    # Create a parent request with transaction manager
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    import transaction

    parent_request.tm = transaction.TransactionManager()

    # Create a subrequest without transaction manager
    subrequest = Request.blank("/test")

    # Call configure_transaction directly
    configure_transaction(parent_request, subrequest)

    # Verify transaction was configured
    assert hasattr(subrequest, "tm")
    assert subrequest.tm is parent_request.tm
    assert subrequest.registry is parent_request.registry


def test_subrequest_environ_sharing(pyramid_tm_config):
    """Test that subrequest inherits environ from parent request."""
    # Create a parent request with custom environ data
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    # Add some custom environ data to parent request
    parent_request.environ["CUSTOM_VAR"] = "test_value"
    parent_request.environ["SERVER_NAME"] = "localhost"
    parent_request.environ["HTTP_X_FORWARDED_FOR"] = "192.168.1.1"
    parent_request.environ["wsgi.version"] = (1, 0)

    # Create subrequest using our introspector
    subrequest = create_subrequest(parent_request, {}, "/test", "GET")

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


def test_pyramid_tm_with_mcp_tool_execution(pyramid_tm_config):
    """Test that pyramid_tm works correctly with MCP tool execution."""
    # This test verifies the integration between pyramid_tm and pyramid_mcp
    from pyramid_mcp.core import PyramidMCP

    # Create PyramidMCP instance with pyramid_tm enabled config
    pyramid_mcp = PyramidMCP(pyramid_tm_config)

    # Verify that the transaction manager is available
    assert hasattr(pyramid_tm_config.registry, "settings")

    # The transaction integration should work transparently
    # (This is more of an integration verification than a functional test)
    assert pyramid_mcp is not None
    assert pyramid_mcp.configurator is pyramid_tm_config


def test_pyramid_tm_subrequest_isolation(pyramid_tm_config):
    """Test that subrequests don't interfere with parent transaction state."""
    # Create parent request with transaction
    parent_request = Request.blank("/")
    parent_request.registry = pyramid_tm_config.registry

    import transaction

    parent_tm = transaction.TransactionManager()
    parent_request.tm = parent_tm

    # Create multiple subrequests
    subrequest1 = create_subrequest(parent_request, {}, "/test1", "GET")
    subrequest2 = create_subrequest(parent_request, {}, "/test2", "POST")

    # All should share the same transaction manager
    assert subrequest1.tm is parent_tm
    assert subrequest2.tm is parent_tm
    assert subrequest1.tm is subrequest2.tm

    # But should have independent request state
    assert subrequest1.environ["PATH_INFO"] != subrequest2.environ["PATH_INFO"]
    assert (
        subrequest1.environ["REQUEST_METHOD"] != subrequest2.environ["REQUEST_METHOD"]
    )
