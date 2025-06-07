# Integration with AI Platforms

This guide shows how to integrate your pyramid-mcp server with various AI platforms and SDKs, including Claude, OpenAI, and other MCP-compatible clients.

## Overview

pyramid-mcp exposes your Pyramid application's functionality as Model Context Protocol (MCP) tools, making them available to AI assistants and applications. Once your pyramid-mcp server is running, AI clients can discover and call your tools automatically.

## Basic Setup

First, ensure your pyramid-mcp server is running:

```python
# In your Pyramid app
from pyramid.config import Configurator
from pyramid_mcp import tool

settings = {
    'mcp.server_name': 'my-api',
    'mcp.server_version': '1.0.0',
    'mcp.mount_path': '/mcp',
    'mcp.route_discovery.enabled': 'true',
}

config = Configurator(settings=settings)
config.include('pyramid_mcp')

# Your tools are now available at http://localhost:8080/mcp
```

## Claude Desktop Integration

Claude Desktop supports MCP servers directly through configuration.

### 1. Configuration File

Create or edit `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pyramid-api": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "http://localhost:8080/mcp",
        "-H", "Content-Type: application/json",
        "-d", "@-"
      ],
      "env": {}
    }
  }
}
```

### 2. Alternative: Using MCP Client Library

For more robust integration, create a wrapper script:

```python
#!/usr/bin/env python3
"""Claude MCP client for pyramid-mcp server."""

import asyncio
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["-c", """
import asyncio
import httpx
import sys
import json

async def proxy_request():
    async with httpx.AsyncClient() as client:
        for line in sys.stdin:
            try:
                data = json.loads(line.strip())
                response = await client.post(
                    'http://localhost:8080/mcp',
                    json=data,
                    headers={'Content-Type': 'application/json'}
                )
                print(response.text)
                sys.stdout.flush()
            except Exception as e:
                print(json.dumps({"error": str(e)}))

asyncio.run(proxy_request())
        """]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools]}")

if __name__ == "__main__":
    asyncio.run(main())
```

## OpenAI SDK Integration

OpenAI's SDK can work with MCP tools through function calling.

### 1. Tool Schema Generation

pyramid-mcp automatically generates OpenAI-compatible function schemas:

```python
import httpx
import json
from openai import OpenAI

# Get tools from your pyramid-mcp server
async def get_mcp_tools():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8080/mcp',
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
        )
        return response.json()['result']['tools']

# Convert MCP tools to OpenAI function format
def mcp_to_openai_functions(mcp_tools):
    functions = []
    for tool in mcp_tools:
        function = {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool.get("inputSchema", {"type": "object", "properties": {}})
        }
        functions.append(function)
    return functions
```

### 2. Function Calling with Tool Execution

```python
import asyncio
import httpx
from openai import OpenAI

class PyramidMCPClient:
    def __init__(self, mcp_url="http://localhost:8080/mcp"):
        self.mcp_url = mcp_url
        self.client = OpenAI()  # Uses OPENAI_API_KEY env var
        
    async def call_mcp_tool(self, name: str, arguments: dict):
        """Call a tool on the pyramid-mcp server."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": arguments
                    }
                }
            )
            return response.json()
    
    async def chat_with_tools(self, message: str):
        """Chat with OpenAI using pyramid-mcp tools."""
        # Get available tools
        tools_response = await self.get_tools()
        functions = mcp_to_openai_functions(tools_response['tools'])
        
        # Initial chat completion
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": message}],
            functions=functions,
            function_call="auto"
        )
        
        message = response.choices[0].message
        
        # If function call requested, execute it
        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            # Call the pyramid-mcp tool
            tool_result = await self.call_mcp_tool(function_name, function_args)
            
            # Send result back to OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": None, "function_call": message.function_call},
                    {"role": "function", "name": function_name, "content": str(tool_result)}
                ]
            )
            
        return response.choices[0].message.content

# Usage
async def main():
    client = PyramidMCPClient()
    result = await client.chat_with_tools("Calculate 15 + 27 using the calculator")
    print(result)

asyncio.run(main())
```

## LangChain Integration

LangChain can integrate with MCP servers through custom tools:

```python
from langchain.tools import BaseTool
from langchain.agents import initialize_agent, AgentType
from langchain.llms import OpenAI
import httpx
import asyncio
from typing import Any

class PyramidMCPTool(BaseTool):
    name: str
    description: str
    mcp_url: str = "http://localhost:8080/mcp"
    
    def _run(self, **kwargs: Any) -> str:
        """Execute the tool synchronously."""
        return asyncio.run(self._arun(**kwargs))
    
    async def _arun(self, **kwargs: Any) -> str:
        """Execute the tool asynchronously."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.mcp_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": self.name,
                        "arguments": kwargs
                    }
                }
            )
            result = response.json()
            if 'result' in result:
                return str(result['result']['content'][0]['text'])
            else:
                return f"Error: {result.get('error', 'Unknown error')}"

# Create tools from pyramid-mcp server
async def create_langchain_tools():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://localhost:8080/mcp',
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }
        )
        
        tools = []
        for tool_info in response.json()['result']['tools']:
            tool = PyramidMCPTool(
                name=tool_info['name'],
                description=tool_info['description']
            )
            tools.append(tool)
        
        return tools

# Usage with LangChain agent
async def main():
    tools = await create_langchain_tools()
    llm = OpenAI(temperature=0)
    
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )
    
    result = agent.run("Calculate 25 * 4 and then convert the result to uppercase text")
    print(result)

asyncio.run(main())
```

## Custom MCP Client

For full control, you can create a custom MCP client:

```python
import asyncio
import httpx
import json
from typing import Dict, List, Any

class PyramidMCPClient:
    def __init__(self, base_url: str = "http://localhost:8080/mcp"):
        self.base_url = base_url
        self.request_id = 0
    
    def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id
    
    async def _make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a JSON-RPC request to the MCP server."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                json=request,
                headers={"Content-Type": "application/json"}
            )
            return response.json()
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize the MCP connection."""
        return await self._make_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        })
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools."""
        response = await self._make_request("tools/list")
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Call a specific tool."""
        response = await self._make_request("tools/call", {
            "name": name,
            "arguments": arguments
        })
        
        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")
        
        result = response.get("result", {})
        content = result.get("content", [])
        if content:
            return content[0].get("text", content[0])
        return result

# Usage example
async def main():
    client = PyramidMCPClient()
    
    # Initialize connection
    await client.initialize()
    
    # List available tools
    tools = await client.list_tools()
    print("Available tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
    
    # Call a tool
    result = await client.call_tool("calculator", {
        "operation": "multiply",
        "a": 6,
        "b": 7
    })
    print(f"Calculation result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Production Deployment

### Security Considerations

1. **Authentication**: Add authentication to your MCP endpoints:

```python
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

def includeme(config):
    # Add authentication
    config.set_authentication_policy(AuthTktAuthenticationPolicy('secret'))
    config.set_authorization_policy(ACLAuthorizationPolicy())
    
    # Protect MCP endpoints
    config.add_route('mcp', '/mcp', factory='myapp.security.MCPContextFactory')
```

2. **HTTPS**: Always use HTTPS in production:

```python
# Configure your WSGI server (e.g., Gunicorn) with SSL
# gunicorn --certfile=cert.pem --keyfile=key.pem -b 0.0.0.0:443 myapp:app
```

3. **Rate Limiting**: Add rate limiting to prevent abuse:

```python
from pyramid_ratelimit import RateLimitPredicate

config.add_route('mcp', '/mcp', 
                predicate=RateLimitPredicate(per_second=10))
```

### Scaling

For high-traffic scenarios:

1. **Load Balancing**: Use multiple pyramid-mcp instances behind a load balancer
2. **Caching**: Cache tool results when appropriate
3. **Async Tools**: Use async functions for I/O-bound tools
4. **Resource Limits**: Set appropriate timeouts and resource limits

### Monitoring

Monitor your MCP server with standard Pyramid monitoring tools:

```python
# Add logging and metrics
import logging
from pyramid.events import NewRequest

def log_mcp_requests(event):
    if event.request.path.startswith('/mcp'):
        logging.info(f"MCP request: {event.request.method} {event.request.path}")

config.add_subscriber(log_mcp_requests, NewRequest)
```

## Troubleshooting

### Common Issues

1. **Tools not appearing**: Check that routes are registered before `config.include('pyramid_mcp')`
2. **JSON-RPC errors**: Verify request format matches MCP specification
3. **Tool execution errors**: Check tool function signatures and error handling
4. **Connection issues**: Ensure server is accessible and CORS is configured if needed

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In your Pyramid settings
settings['mcp.debug'] = 'true'
```

For more help, see the [pyramid-mcp documentation](https://github.com/your-org/pyramid-mcp) or open an issue. 