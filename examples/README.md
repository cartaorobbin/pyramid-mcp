# pyramid-mcp Examples

This directory contains examples showing how to use pyramid-mcp in your applications.

## Simple App Example

**File**: `simple_app.py`

A minimal example demonstrating:
- Basic pyramid-mcp setup with `config.include('pyramid_mcp')`
- Manual tool registration using the `@tool` decorator
- Automatic route discovery for API endpoints
- Complete runnable server

### Running the Example

```bash
# From the project root
python examples/simple_app.py
```

The server will start on `http://localhost:8080` with:
- Regular API endpoints at `/api/*`
- MCP JSON-RPC endpoint at `/mcp`

### What's Included

**Manual MCP Tools:**
- `calculator` - Perform basic math operations
- `text_processor` - Process text in various ways

**Auto-discovered Tools:**
- `api_hello` - From the `/api/hello` endpoint
- `api_users` - From the `/api/users` endpoint

### Testing the Example

You can test the MCP endpoint using curl:

```bash
# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'

# Call the calculator tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
      "name": "calculator",
      "arguments": {"operation": "add", "a": 5, "b": 3}
    }
  }'
```

## Integration with AI Platforms

For detailed instructions on integrating with Claude, OpenAI, and other AI platforms, see the [Integration Documentation](../docs/integration.md). 