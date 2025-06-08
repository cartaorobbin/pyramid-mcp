# Simple Pyramid MCP Example

This is a simple example demonstrating pyramid-mcp integration with basic MCP tools and API endpoint discovery.

## Features

- ✅ Basic MCP tools (`calculator`, `text_processor`)
- ✅ Permission-based tools (`user_profile`, `admin_users`)
- ✅ Auto-discovery of API endpoints as MCP tools
- ✅ Simple setup with minimal configuration
- ✅ Docker support for easy deployment

## Available MCP Tools

### Public Tools (No Authentication Required)
- **calculator**: Perform basic math operations (add, subtract, multiply, divide)
- **text_processor**: Process text with various operations (upper, lower, reverse, title)

### Protected Tools (Authentication Required)
- **user_profile**: Get user profile information (requires `authenticated` permission)
- **admin_users**: Administrative user operations (requires `admin` permission)

### Auto-Discovered API Tools
- **api_hello**: Say hello endpoint from `/api/hello`
- **api_users**: List users endpoint from `/api/users`

## Running Locally

### Direct Python Execution
```bash
cd examples/simple
python simple_app.py
```

### Using Poetry
```bash
cd examples/simple
poetry install
poetry run python simple_app.py
```

The server will start on `http://localhost:8080` with MCP endpoint at `http://localhost:8080/mcp`.

## Docker Support

### Build and Run for Claude Desktop (stdio transport)
```bash
cd examples/simple
docker build -t pyramid-mcp-simple .
```

The container is designed to run with stdio transport for Claude Desktop integration.

### Test MCP Connection (HTTP mode for manual testing)
```bash
# Run in HTTP mode for testing
docker run -p 8080:8080 pyramid-mcp-simple python simple_app.py

# In another terminal, test MCP endpoint
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Test calculator tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"calculator","arguments":{"operation":"add","a":5,"b":3}}}'

# Test text processor tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"text_processor","arguments":{"text":"hello world","operation":"title"}}}'
```

## Claude Desktop Integration

Add this to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pyramid-mcp-simple": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "pyramid-mcp-simple"
      ]
    }
  }
}
```

This configuration uses stdio transport, which is the proper MCP approach.

## Configuration

The app uses these MCP settings:
- **Server Name**: `simple-pyramid-app`
- **Version**: `1.0.0`
- **Mount Path**: `/mcp`
- **Route Discovery**: Enabled for `api/*` patterns

## API Endpoints

### Standard HTTP Endpoints
- `GET /api/hello?name=YourName` - Hello endpoint
- `GET /api/users` - List users

### MCP JSON-RPC Endpoint
- `POST /mcp` - MCP protocol endpoint

## Example MCP Client Usage

```python
import requests

# List available tools
response = requests.post('http://localhost:8080/mcp', json={
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
})

# Call calculator tool
response = requests.post('http://localhost:8080/mcp', json={
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "calculator",
        "arguments": {
            "operation": "add",
            "a": 10,
            "b": 5
        }
    }
})
```

## Development

To extend this example:

1. Add new `@tool` decorated functions for MCP tools
2. Add new `@view_config` decorated functions for API endpoints
3. Configure route discovery patterns in settings
4. Update Docker build if needed

This simple example is perfect for getting started with pyramid-mcp integration! 