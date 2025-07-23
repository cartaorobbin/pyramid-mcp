"""
WSGI Module for MCP Server

This module provides a WSGI application that serves the MCP protocol.
"""

import json
from typing import Any, Callable, Dict, Iterable

from pyramid.request import Request

from pyramid_mcp.protocol import MCPProtocolHandler


class MCPWSGIApp:
    """WSGI application that serves MCP protocol over HTTP."""

    def __init__(self, protocol_handler: MCPProtocolHandler, config: Any):
        """Initialize the MCP WSGI application.

        Args:
            protocol_handler: The MCP protocol handler
            config: MCP configuration
        """
        self.protocol_handler = protocol_handler
        self.config = config

    def __call__(
        self, environ: Dict[str, Any], start_response: Callable
    ) -> Iterable[bytes]:
        """WSGI application callable.

        Args:
            environ: WSGI environment
            start_response: WSGI start_response callable

        Returns:
            Response iterable
        """
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")

        # Handle MCP HTTP requests
        if method == "POST" and path == "/":
            return self._handle_mcp_request(environ, start_response)

        # Handle SSE requests
        elif path == "/sse":
            return self._handle_sse_request(environ, start_response)

        # Default response
        else:
            start_response("404 Not Found", [("Content-Type", "text/plain")])
            return [b"Not Found"]

    def _handle_mcp_request(
        self, environ: Dict[str, Any], start_response: Callable
    ) -> Iterable[bytes]:
        """Handle MCP JSON-RPC requests.

        Args:
            environ: WSGI environment
            start_response: WSGI start_response callable

        Returns:
            Response iterable
        """
        try:
            # Read request body
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            request_body = environ["wsgi.input"].read(content_length)

            # Parse JSON
            request_data = json.loads(request_body.decode("utf-8"))

            # Handle through protocol handler
            # Create a dummy request for WSGI context (no Pyramid request available)
            dummy_request = Request.blank("/")
            response_data = self.protocol_handler.handle_message(
                request_data, dummy_request
            )

            # Return JSON response
            response_json = json.dumps(response_data)
            response_bytes = response_json.encode("utf-8")

            start_response(
                "200 OK",
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_bytes))),
                ],
            )

            return [response_bytes]

        except Exception as e:
            # Try to extract request ID if possible
            request_id = None
            try:
                if request_data and "id" in request_data:
                    request_id = request_data["id"]
            except (TypeError, KeyError, AttributeError):
                pass

            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }
            response_json = json.dumps(error_response)
            response_bytes = response_json.encode("utf-8")

            start_response(
                "500 Internal Server Error",
                [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_bytes))),
                ],
            )

            return [response_bytes]

    def _handle_sse_request(
        self, environ: Dict[str, Any], start_response: Callable
    ) -> Iterable[bytes]:
        """Handle SSE requests.

        Args:
            environ: WSGI environment
            start_response: WSGI start_response callable

        Returns:
            Response iterable
        """
        # Simple SSE implementation
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/event-stream"),
                ("Cache-Control", "no-cache"),
                ("Access-Control-Allow-Origin", "*"),
            ],
        )

        # Send initial message
        welcome_msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
        sse_data = f"data: {json.dumps(welcome_msg)}\n\n"

        return [sse_data.encode("utf-8")]
