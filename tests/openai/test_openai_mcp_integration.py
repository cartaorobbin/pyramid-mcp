"""
Test OpenAI Agent using pyramid-mcp server via MCP.
"""

import os

import pytest
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY environment variable not set",
)
@pytest.mark.asyncio
async def test_agent_with_pyramid_mcp_server(pyramid_mcp_app):
    """Test creating an OpenAI Agent that uses pyramid MCP server configuration."""

    # Get HTTP MCP URL from running server (not SSE)
    server_url = pyramid_mcp_app["server_url"]
    mcp_url = f"{server_url}/mcp"  # Use HTTP endpoint, not SSE

    # Create MCP server connection configuration using HTTP transport
    mcp_server = MCPServerStreamableHttp(
        params={
            "url": mcp_url,
        }
    )

    # Create Agent with MCP server
    agent = Agent(
        name="Test Agent",
        instructions="You are a helpful assistant that can use tools to help users.",
        mcp_servers=[mcp_server],
    )

    # Verify agent is created with MCP server
    assert agent is not None
    assert len(agent.mcp_servers) == 1
    assert agent.mcp_servers[0] == mcp_server

    # Connect to MCP server for communication
    await mcp_server.connect()

    # Ask the agent a math question to test MCP tool usage
    result = await Runner.run(starting_agent=agent, input="What is 5 + 3?")

    # Verify we got a result
    assert result is not None
    assert result.final_output is not None

    # Validate the actual answer - should contain "8" since 5 + 3 = 8
    final_output = str(result.final_output).lower()
    assert "8" in final_output, (
        f"Expected answer '8' not found in response: {result.final_output}"
    )

    print(f"✅ Agent response: {result.final_output}")
    print("✅ OpenAI Agent successfully communicated with pyramid-mcp server!")
    print("✅ Correct answer validated: 5 + 3 = 8")
