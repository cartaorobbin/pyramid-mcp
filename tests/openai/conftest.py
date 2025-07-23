"""Simple fixtures for OpenAI MCP integration tests."""

import threading
import time
from wsgiref.simple_server import make_server

import pytest
from pyramid.config import Configurator


@pytest.fixture
def pyramid_mcp_app():
    """Create a pyramid app with MCP configured, start server, and provide URL."""
    config = Configurator()
    config.include("pyramid_mcp")

    # Add test tools directly
    from pyramid_mcp import tool

    @tool("add")
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    @tool("echo")
    def echo_text(text: str) -> str:
        """Echo text back."""
        return f"Echo: {text}"

    app = config.make_wsgi_app()

    # Start server in thread
    server = make_server("localhost", 8000, app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Give server time to start
    time.sleep(0.1)

    # Return info about the running server
    server_info = {
        "app": app,
        "server_url": "http://localhost:8000",
        "mcp_url": "http://localhost:8000/mcp/sse",  # SSE endpoint for OpenAI Agents
        "server": server,
    }

    yield server_info

    # Cleanup
    server.shutdown()
    server.server_close()
