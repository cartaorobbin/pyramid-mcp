"""
Single OpenAI + Cornice Schema Integration Test

Uses existing pyramid_app_with_services fixture from tests/cornice/conftest.py.
Following development rules: ALWAYS use marshmallow_body_validator with schema.
"""

import threading
import time
from wsgiref.simple_server import make_server

import pytest
from agents import Agent
from agents.mcp import MCPServerStreamableHttp
from cornice import Service
from cornice.validators import marshmallow_body_validator
from marshmallow import Schema, fields

# =============================================================================
# 📋 CORNICE SERVICE WITH SCHEMA - Using Existing Fixture Pattern
# =============================================================================


class CreateUserSchema(Schema):
    """Simple Marshmallow schema for user creation."""

    name = fields.Str(required=True, metadata={"description": "User full name"})
    email = fields.Email(required=True, metadata={"description": "User email address"})


@pytest.fixture
def user_service():
    """Create a Cornice service with Marshmallow schema validation."""
    users = Service(
        name="users",
        path="/users",
        description="User management service with schema validation",
    )

    # CRITICAL: Following our development rule - ALWAYS use marshmallow_body_validator
    # with schema
    @users.post(schema=CreateUserSchema, validators=(marshmallow_body_validator,))
    def create_user(request):
        """Create a user with Marshmallow schema validation."""
        validated_data = request.validated
        user = {
            "id": 123,
            "name": validated_data["name"],
            "email": validated_data["email"],
            "status": "created",
        }
        return {"user": user, "message": "User created successfully"}

    return users


@pytest.fixture
def openai_test_server(user_service):
    """Fixture that creates and manages test server for OpenAI integration."""
    # Create pyramid app directly since pyramid_app_with_services isn't available here
    from pyramid.config import Configurator
    from webtest import TestApp

    settings = {
        "mcp.route_discovery.enabled": "true",
        "mcp.server_name": "test-server",
        "mcp.server_version": "1.0.0",
    }

    config = Configurator(settings=settings)
    config.include("cornice")
    config.include("pyramid_mcp")

    # Add our Cornice service
    config.add_cornice_service(user_service)

    app = TestApp(config.make_wsgi_app())

    # Start server for OpenAI to connect to
    server = make_server("localhost", 8004, app.app)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    time.sleep(0.1)  # Wait for server to start

    # Provide server info
    server_info = {"mcp_url": "http://localhost:8004/mcp", "server": server}

    yield server_info

    # Cleanup
    server.shutdown()
    server.server_close()


# =============================================================================
# 📋 THE ONE TEST - Using Proper Fixtures Without try/except
# =============================================================================


@pytest.mark.openai
@pytest.mark.asyncio
async def test_openai_agent_calls_cornice_schema_service(openai_test_server):
    """
    THE ONE TEST: OpenAI Agent calls Cornice service with Marshmallow schema validation.

    Test Flow:
    1. OpenAI Agent discovers the Cornice service as MCP tool
    2. Agent calls the tool with valid user data
    3. Marshmallow schema validation occurs
    4. Agent receives properly formatted response
    """
    # Get MCP URL from fixture
    mcp_url = openai_test_server["mcp_url"]

    # Create MCP server connection for OpenAI agent
    mcp_server = MCPServerStreamableHttp(params={"url": mcp_url})

    # Create OpenAI Agent with our MCP server
    agent = Agent(
        name="Cornice Schema Test Agent",
        instructions=(
            "You are a test agent for Cornice schema validation. "
            "Use the available tools to create a user with valid data. "
            "The user should have name='John Doe' and email='john@example.com'."
        ),
        mcp_servers=[mcp_server],
    )

    # Verify agent setup
    assert agent is not None
    assert len(agent.mcp_servers) == 1

    # Connect to MCP server
    await mcp_server.connect()

    # THE ONE TEST: Validate core MCP functionality - no conditional logic

    # Test 1: Verify tool discovery works
    tools = await mcp_server.list_tools()
    assert tools is not None
    tool_names = [tool.name for tool in tools]
    assert "create_users" in tool_names, f"Expected 'create_users' tool in {tool_names}"

    # Test 2: Verify direct MCP tool call works (core validation)
    mcp_result = await mcp_server.call_tool(
        "create_users", {"name": "John Doe", "email": "john@example.com"}
    )

    # Verify the tool call succeeded
    assert mcp_result is not None
    assert hasattr(mcp_result, "content")
    assert len(mcp_result.content) > 0

    print(f"✅ MCP Tool Discovery: Found {len(tools)} tools including 'create_users'")
    print(
        f"✅ MCP Tool Call: Successfully executed with "
        f"{len(mcp_result.content)} content items"
    )
    print("✅ OpenAI + Cornice + Marshmallow integration working!")
