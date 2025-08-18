# Pyramid MCP

[![PyPI version](https://badge.fury.io/py/pyramid-mcp.svg)](https://badge.fury.io/py/pyramid-mcp)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/your-org/pyramid-mcp/workflows/tests/badge.svg)](https://github.com/your-org/pyramid-mcp/actions)
[![Coverage](https://codecov.io/gh/your-org/pyramid-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/pyramid-mcp)

## ⚠️ Development Status

**🚧 This project is currently under active development and is not yet ready for production use.**

- 🧪 **Experimental**: APIs and features may change without notice
- 🔄 **Breaking Changes**: Expect breaking changes between releases
- 📋 **Not Production Ready**: Use at your own risk in production environments
- 🐛 **Known Issues**: Some features may be incomplete or have bugs

**For Production Use**: Please wait for the 1.0.0 stable release or use the project for experimentation and development only.

---

Pyramid MCP is a library that exposes Pyramid web application endpoints as Model Context Protocol (MCP) tools. It's inspired by fastapi_mcp but designed specifically for the Pyramid web framework.

## Features

- 🔌 **Pyramid Plugin**: Easy integration with `config.include('pyramid_mcp')`
- 🛠️ **Tool Registration**: Simple `@tool` decorator for registering MCP tools
- 🔐 **Authentication Parameters**: Support for Bearer token and Basic auth as tool parameters (uses `mcp_security` parameter by default, configurable)
- 🛡️ **Security Filtering**: Automatic filtering of tools based on user permissions and ACL contexts (enabled by default)
- ⚙️ **Settings-based Configuration**: Configure via Pyramid settings
- 🔍 **Route Discovery**: Automatic discovery of Pyramid routes (configurable)
- 📡 **Multiple Protocols**: Support for HTTP and SSE (Server-Sent Events)
- 🎛️ **Enable/Disable Control**: Easily enable or disable MCP endpoints via configuration (perfect for staging → production workflows)
- 🧪 **Well Tested**: Comprehensive test suite with pytest
- 📚 **Type Hints**: Full type annotations for better IDE support
- 🚀 **Easy to Use**: Minimal setup required

## Installation

### From PyPI (Recommended)

```bash
pip install pyramid-mcp
```

### From Source

```bash
git clone https://github.com/your-org/pyramid-mcp
cd pyramid-mcp
pip install -e .
```

### Requirements

- Python 3.9+
- Pyramid 2.0+
- Marshmallow 3.22+ (for schema validation)

## Quick Start

### Basic Usage

```python
from pyramid.config import Configurator
from pyramid.view import view_config
from pyramid_mcp import tool

# Include pyramid_mcp in your Pyramid application
def create_app():
    config = Configurator(settings={
        'mcp.server_name': 'my-api',
        'mcp.mount_path': '/mcp'
    })
    
    # Include the pyramid_mcp plugin
    config.include('pyramid_mcp')
    
    # Add your regular Pyramid routes
    config.add_route('home', '/')
    config.scan()
    
    return config.make_wsgi_app()

# Register MCP tools using the decorator
@tool(name="calculate", description="Perform basic math operations")
def calculate(operation: str, a: float, b: float) -> float:
    """Perform basic math operations."""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    else:
        raise ValueError(f"Unknown operation: {operation}")

@view_config(route_name='home', renderer='json')
def home_view(request):
    return {"message": "Hello World", "mcp_available": True}
```

### Run Your Application

```python
if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    
    app = create_app()
    server = make_server('0.0.0.0', 8080, app)
    print("Server started at http://localhost:8080")
    print("MCP endpoint available at http://localhost:8080/mcp")
    server.serve_forever()
```

### Test Your MCP Integration

```bash
# Initialize MCP connection
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "id": 1}'

# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}'

# Call the calculate tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call", 
    "id": 3,
    "params": {
      "name": "calculate",
      "arguments": {"operation": "add", "a": 5, "b": 3}
    }
  }'
```

## Security Parameter Name

**Key Concept**: The security parameter name is **`mcp_security`** by default, but can be configured to any name you prefer.

This allows you to:
- Use existing security parameters from your application (e.g., `pcm_security`, `api_security`)
- Avoid duplicating security configuration
- Maintain consistency across your application

```python
# Default: uses 'mcp_security' parameter
@view_config(route_name='secure', renderer='json', mcp_security='bearer')

# Configured: uses your existing parameter name
settings = {'mcp.security_parameter': 'pcm_security'}
# Now use: pcm_security='BearerAuth'
@view_config(route_name='secure', renderer='json', pcm_security='BearerAuth')
```

**See the [Configurable Security Parameter](#configurable-security-parameter) section for complete details.**

### Configuration

Configure pyramid_mcp using Pyramid settings:

```python
settings = {
    # MCP Server Configuration
    'mcp.server_name': 'my-api',           # Server name
    'mcp.server_version': '1.0.0',        # Server version
    'mcp.mount_path': '/mcp',              # Mount path for MCP endpoints
    
    # Protocol Configuration  
    'mcp.enable_sse': 'true',              # Enable Server-Sent Events
    'mcp.enable_http': 'true',             # Enable HTTP protocol
    
    # Route Discovery Configuration
    'mcp.route_discovery.enabled': 'false',           # Enable automatic route discovery
    'mcp.route_discovery.include_patterns': 'api/*',  # Routes to include as tools
    'mcp.route_discovery.exclude_patterns': 'internal/*',  # Routes to exclude from tools
}

config = Configurator(settings=settings)
config.include('pyramid_mcp')
```

### Accessing MCP in Views

```python
@view_config(route_name='mcp_info', renderer='json')
def mcp_info_view(request):
    # Access MCP instance through request
    mcp = request.mcp
    
    # Get available tools
    tools = list(mcp.protocol_handler.tools.keys())
    
    return {
        'server_name': mcp.config.server_name,
        'available_tools': tools,
        'mount_path': mcp.config.mount_path
    }
```

## API Reference

### Plugin Integration

```python
# Basic inclusion
config.include('pyramid_mcp')

# Access MCP instance
mcp = config.get_mcp()           # From configurator
mcp = request.mcp                # From request (in views)
```

### Tool Registration

```python
from pyramid_mcp import tool

@tool(name="my_tool", description="Tool description")
def my_tool(param1: str, param2: int) -> str:
    """Tool implementation."""
    return f"Result: {param1} * {param2}"

# With schema validation (optional)
from marshmallow import Schema, fields

class MyToolSchema(Schema):
    param1 = fields.Str(required=True)
    param2 = fields.Int(required=True)

@tool(name="validated_tool", schema=MyToolSchema)
def validated_tool(param1: str, param2: int) -> str:
    return f"Validated: {param1} + {param2}"

# With authentication parameters
from pyramid_mcp.security import BearerAuthSchema

@tool(
    name="secure_tool", 
    description="Tool that requires authentication",
    security=BearerAuthSchema()
)
def secure_tool(pyramid_request, data: str, auth_token: str) -> dict:
    """Tool with Bearer token authentication."""
    # Access authentication headers from the standard request headers
    auth_header = pyramid_request.headers.get("Authorization", "")
    return {"data": data, "authenticated": bool(auth_header)}
```

### Manual Usage (Advanced)

```python
from pyramid_mcp import PyramidMCP, MCPConfiguration
from pyramid_mcp.security import BearerAuthSchema

# Manual configuration
config = Configurator()
mcp_config = MCPConfiguration(
    server_name="my-server",
    mount_path="/mcp"
)

pyramid_mcp = PyramidMCP(config, config=mcp_config)

# Register tools manually
@pyramid_mcp.tool("manual_tool")
def manual_tool(x: int) -> int:
    return x * 2

# Register tool with authentication
@pyramid_mcp.tool(
    name="secure_manual_tool",
    description="Secure tool with authentication",
    security=BearerAuthSchema()
)
def secure_manual_tool(pyramid_request, data: str, auth_token: str) -> dict:
    auth_header = pyramid_request.headers.get("Authorization", "")
    return {"data": data, "authenticated": bool(auth_header)}

# Mount manually (with auto_commit=False for more control)
pyramid_mcp.mount(auto_commit=False)
config.commit()
```

## MCP Protocol

Once configured, your Pyramid application will expose MCP endpoints:

- **HTTP**: `POST /mcp` (or your configured mount path)
- **SSE**: `GET /mcp/sse` (if enabled)

### Example MCP Requests

```bash
# Initialize MCP connection
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "initialize", "id": 1}'

# List available tools
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 2}'

# Call a tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call", 
    "id": 3,
    "params": {
      "name": "calculate",
      "arguments": {"operation": "add", "a": 5, "b": 3}
    }
  }'
```

## Troubleshooting

### Common Issues

#### "Module not found" error
```bash
ModuleNotFoundError: No module named 'pyramid_mcp'
```
**Solution**: Make sure pyramid-mcp is installed in your active Python environment:
```bash
pip list | grep pyramid-mcp
pip install pyramid-mcp
```

#### MCP endpoints not accessible
**Problem**: Getting 404 when accessing `/mcp` endpoint.

**Solutions**:
1. Ensure you've included the plugin: `config.include('pyramid_mcp')`
2. Check your mount path setting: `'mcp.mount_path': '/mcp'`
3. Verify the configurator is properly committed if using manual setup

#### Tools not showing up in `/tools/list`
**Problem**: Registered tools don't appear in MCP tools list.

**Solutions**:
1. Ensure tools are registered before mounting: `pyramid_mcp.mount()`
2. Check that `config.scan()` is called to discover `@tool` decorators
3. Verify the tool registration syntax

#### Type validation errors
**Problem**: Getting validation errors when calling tools.

**Solutions**:
1. Check parameter types match the function signature
2. Use Marshmallow schemas for complex validation
3. Review the MCP request format

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In your Pyramid settings
settings = {
    'mcp.server_name': 'my-api',
    'mcp.mount_path': '/mcp',
    # Add debug settings if needed
}
```

### Getting Help

- 📖 [Documentation](https://your-org.github.io/pyramid-mcp)
- 🐛 [Report Issues](https://github.com/your-org/pyramid-mcp/issues)
- 💬 [Discussions](https://github.com/your-org/pyramid-mcp/discussions)
- 📧 [Contact the maintainers](https://github.com/your-org/pyramid-mcp/discussions)

## Examples

### Complete Examples

See the `examples/` directory for complete example applications:

- **[Basic Integration](examples/pyramid_app_example.py)**: Complete Pyramid application with MCP integration
- **Advanced Usage**: Multiple tools, schema validation, and SSE support

### Tool Examples

```python
# Simple tool
@tool(name="greet", description="Greet a user")
def greet(name: str) -> str:
    return f"Hello, {name}!"

# Tool with schema validation
from marshmallow import Schema, fields

class UserSchema(Schema):
    name = fields.Str(required=True, validate=lambda x: len(x) > 0)
    age = fields.Int(required=True, validate=lambda x: x > 0)

@tool(name="create_user", description="Create a new user", schema=UserSchema)
def create_user(name: str, age: int) -> dict:
    return {"id": 123, "name": name, "age": age, "created": True}

# Tool with Bearer token authentication
from pyramid_mcp.security import BearerAuthSchema

@tool(
    name="secure_api_request",
    description="Make authenticated API request",
    security=BearerAuthSchema()
)
def secure_api_request(pyramid_request, endpoint: str, auth_token: str) -> dict:
    # Auth headers are automatically created and available in request headers
    auth_header = pyramid_request.headers.get("Authorization", "")
    # auth_header = "Bearer <token>"
    return {"endpoint": endpoint, "status": "authenticated"}

# Tool with Basic authentication
from pyramid_mcp.security import BasicAuthSchema

@tool(
    name="database_query",
    description="Query database with credentials",
    security=BasicAuthSchema()
)
def database_query(pyramid_request, query: str, username: str, password: str) -> dict:
    # Auth headers are automatically created and available in request headers
    auth_header = pyramid_request.headers.get("Authorization", "")
    # auth_header = "Basic <base64_encoded_credentials>"
    return {"query": query, "status": "executed"}

# Async tool (if using async views)
@tool(name="async_tool", description="Async operation")
async def async_tool(data: str) -> str:
    # Simulate async work
    await asyncio.sleep(0.1)
    return f"Processed: {data}"
```

## Configuration

### All Configuration Options

```python
settings = {
    # MCP Server Configuration
    'mcp.server_name': 'my-api',           # Server name (default: 'pyramid-mcp')
    'mcp.server_version': '1.0.0',        # Server version (default: '1.0.0')
    'mcp.mount_path': '/mcp',              # Mount path for MCP endpoints (default: '/mcp')
    'mcp.enable': 'true',                  # Enable MCP endpoints (default: True)
    
    # Security Configuration
    'mcp.security_parameter': 'mcp_security',  # Name of security parameter in views (default: 'mcp_security')
    'mcp.add_security_predicate': 'true',     # Register security view predicate (default: True)
    'mcp.expose_auth_as_params': 'true',      # Expose auth credentials as tool parameters (default: True)
    
    # Protocol Configuration  
    'mcp.enable_sse': 'true',              # Enable Server-Sent Events (default: True)
    'mcp.enable_http': 'true',             # Enable HTTP protocol (default: True)
    
    # Route Discovery Configuration
    'mcp.route_discovery.enabled': 'false',           # Enable automatic route discovery (default: False)
    'mcp.route_discovery.include_patterns': 'api/*',  # Routes to include as tools
    'mcp.route_discovery.exclude_patterns': 'internal/*',  # Routes to exclude from tools
}
```

### Enable/Disable MCP Endpoints

The `mcp.enable` configuration allows you to control whether MCP endpoints are created when including the pyramid_mcp plugin. This is particularly useful for staging → production workflows.

#### Basic Usage

```python
# Enable MCP endpoints (default behavior)
settings = {
    'mcp.enable': 'true'  # or True, 'yes', 'on', '1'
}

# Disable MCP endpoints 
settings = {
    'mcp.enable': 'false'  # or False, 'no', 'off', '0'
}
```

#### When `mcp.enable=true` (default)

- ✅ **Full MCP functionality**: HTTP endpoints, tool registration, route discovery
- ✅ **Production ready**: All features available for client connections
- ✅ **Backward compatible**: Default behavior, existing code continues to work

#### When `mcp.enable=false`

- ✅ **View predicates only**: `mcp_description`, `llm_context_hint`, `mcp_security` predicates still registered
- ❌ **No HTTP endpoints**: `/mcp` endpoints are not created
- ❌ **No tool registration**: `@tool` decorators are not processed
- ❌ **No route discovery**: Automatic route discovery is skipped

#### Staging → Production Workflow

This configuration enables a clean staging → production deployment pattern:

```python
# staging.ini - Test views with predicates, no MCP endpoints exposed
[app:main]
mcp.enable = false
mcp.server_name = staging-api

# production.ini - Full MCP functionality
[app:main] 
mcp.enable = true
mcp.server_name = production-api
```

**Staging Benefits:**
- Test that views work with MCP predicates (`mcp_description`, `llm_context_hint`, etc.)
- No accidental exposure of MCP endpoints in staging
- Validate configuration without enabling external access

**Production Benefits:**
- Clean activation of MCP functionality
- Same codebase, different configuration
- Zero downtime deployment when enabling MCP

### Authentication Parameters Feature

Pyramid MCP supports tools that require authentication credentials to be passed as parameters rather than HTTP headers. This is particularly useful for Claude AI clients that cannot pass HTTP headers.

#### Controlling Authentication Parameter Exposure

You can control whether authentication parameters are exposed in tool schemas using the `mcp.expose_auth_as_params` configuration:

```python
# Expose auth credentials as tool parameters (default)
settings = {
    'mcp.expose_auth_as_params': 'true'
}

# Don't expose auth credentials as parameters (use HTTP headers instead)
settings = {
    'mcp.expose_auth_as_params': 'false'
}
```

**When `expose_auth_as_params=true` (default):**
- Authentication parameters appear in the tool's input schema
- Clients (like Claude) can see and provide auth credentials as regular parameters
- Useful for clients that cannot send HTTP headers

**When `expose_auth_as_params=false`:**
- Authentication parameters are NOT included in the tool's input schema
- Tools rely on traditional HTTP header authentication
- Useful when you want to use standard HTTP authentication patterns

#### Bearer Token Authentication

```python
from pyramid_mcp import tool
from pyramid_mcp.security import BearerAuthSchema

@tool(
    name="secure_api_call",
    description="Call a secure API endpoint",
    security=BearerAuthSchema()
)
def secure_api_call(pyramid_request, data: str, auth_token: str) -> dict:
    """Call a secure API with Bearer token authentication."""
    # Authentication headers are automatically available in request headers
    auth_header = pyramid_request.headers.get("Authorization", "")
    # auth_header = "Bearer <token>"
    
    # Make API call with authentication
    return {"success": True, "data": data}
```

#### HTTP Basic Authentication

```python
from pyramid_mcp import tool
from pyramid_mcp.security import BasicAuthSchema

@tool(
    name="secure_ftp_access",
    description="Access FTP server with credentials",
    security=BasicAuthSchema()
)
def secure_ftp_access(pyramid_request, path: str, username: str, password: str) -> dict:
    """Access FTP server with basic authentication."""
    # Authentication headers are automatically available in request headers
    auth_header = pyramid_request.headers.get("Authorization", "")
    # auth_header = "Basic <base64_encoded_credentials>"
    
    # Use credentials for FTP access
    return {"path": path, "status": "connected"}
```

#### How It Works

1. **Schema Integration**: Authentication parameters are automatically merged into the tool's JSON schema
2. **Parameter Extraction**: Credentials are extracted from tool arguments during execution
3. **Header Generation**: Authentication headers are created and added to the subrequest headers
4. **Parameter Cleanup**: Authentication parameters are removed from the arguments passed to your handler function
5. **Validation**: Credentials are validated before tool execution

#### Example MCP Call with Authentication

```bash
# Call a tool with Bearer token authentication
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call", 
    "id": 1,
    "params": {
      "name": "secure_api_call",
      "arguments": {
        "data": "hello world",
        "auth_token": "your-bearer-token-here"
      }
    }
  }'

# Call a tool with Basic authentication
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "method": "tools/call", 
    "id": 2,
    "params": {
      "name": "secure_ftp_access",
      "arguments": {
        "path": "/home/user",
        "username": "myuser",
        "password": "mypassword"
      }
    }
  }'
```

#### Security Considerations

- **Credentials are passed as parameters**: Authentication data is sent in the request body, not HTTP headers
- **No credential logging**: Authentication parameters are removed from handler arguments before execution
- **Validation**: Credentials are validated before tool execution
- **Standard HTTP headers**: Credentials are converted to standard HTTP Authorization headers for your use

### Configurable Security Parameter

**Parameter Name**: The security parameter name is **`mcp_security`** by default, but can be configured to any name you prefer.

By default, pyramid-mcp looks for the `mcp_security` parameter in your view configurations to determine what authentication parameters to add to MCP tools. However, you can configure this to use any existing security parameter from your application, avoiding the need to duplicate security configuration.

```python
# Default usage with 'mcp_security' parameter
@view_config(route_name='secure', renderer='json', mcp_security='bearer')
def secure_view(request):
    return {"data": "secure"}

# Or configure to use your existing parameter name
settings = {
    'mcp.security_parameter': 'pcm_security',  # Use existing parameter name
}
config = Configurator(settings=settings)
config.include('pyramid_mcp')

# Now use your existing parameter name
@view_config(route_name='secure', renderer='json', pcm_security='BearerAuth')
def secure_view(request):
    return {"data": "secure"}
```

#### Using Existing Security Parameters

If your application already uses security parameters like `pcm_security`, `api_security`, or any other custom parameter name, you can configure pyramid-mcp to use them:

```python
# Configure pyramid-mcp to use your existing security parameter
settings = {
    'mcp.security_parameter': 'pcm_security',  # Use existing parameter name
    'mcp.server_name': 'my-api',
    'mcp.mount_path': '/mcp'
}

config = Configurator(settings=settings)
config.include('pyramid_mcp')
```

#### Example with Custom Security Parameter

```python
from pyramid.view import view_config
from pyramid.config import Configurator

# Configure to use 'api_auth' as the security parameter
settings = {
    'mcp.security_parameter': 'api_auth',
    'mcp.server_name': 'my-enterprise-api'
}

config = Configurator(settings=settings)
config.include('pyramid_mcp')

# Your existing views with custom security parameter
@view_config(
    route_name='secure_endpoint',
    renderer='json',
    api_auth='bearer'  # Uses your existing parameter name
)
def secure_endpoint_view(request):
    return {"message": "secure data"}

@view_config(
    route_name='admin_endpoint', 
    renderer='json',
    api_auth='basic'  # Uses your existing parameter name
)
def admin_endpoint_view(request):
    return {"admin": "data"}
```

#### Benefits of Configurable Security Parameter

1. **No Duplication**: Reuse existing security configuration instead of adding new `mcp_security` parameters
2. **Consistency**: Use the same security parameter names across your entire application
3. **Integration**: Seamlessly integrate with existing security systems and middleware
4. **Flexibility**: Change security parameter names without modifying view code

#### Backward Compatibility

The default behavior remains unchanged. If you don't configure `mcp.security_parameter`, pyramid-mcp will continue to use `mcp_security` as the parameter name:

```python
# Default behavior (no configuration needed)
@view_config(route_name='secure', renderer='json', mcp_security='bearer')
def secure_view(request):
    return {"data": "secure"}
```

#### Advanced Security Integration

You can integrate with complex security systems by using descriptive parameter names:

```python
# Configure for enterprise security system
settings = {
    'mcp.security_parameter': 'enterprise_auth_level',
    'mcp.server_name': 'enterprise-api'
}

@view_config(
    route_name='financial_data',
    renderer='json', 
    enterprise_auth_level='bearer'  # Integrates with existing system
)
def financial_data_view(request):
    return {"financial": "data"}
```

#### Disabling Security Predicate Registration

**Parameter**: `mcp.add_security_predicate`  
**Type**: Boolean  
**Default**: `true`

In some cases, you may want to disable pyramid-mcp's automatic registration of the security view predicate. This is useful when:

1. **Library Conflicts**: Another library (like pycornmarsh) already registers the same predicate name
2. **Manual Registration**: You want to register the predicate manually with custom behavior
3. **Testing**: You need to control predicate registration timing for testing

```python
# Disable automatic predicate registration
settings = {
    'mcp.security_parameter': 'pcm_security',
    'mcp.add_security_predicate': 'false',  # Disable automatic registration
}

config = Configurator(settings=settings)
config.include('pyramid_mcp')

# The 'pcm_security' predicate won't be registered by pyramid-mcp
# Your application or another library must register it
```

**Use Cases**:
- **Cornice Integration**: When using Cornice with existing security predicates
- **Custom Predicates**: When you need predicates with custom validation logic
- **Conflict Resolution**: When multiple libraries try to register the same predicate

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-org/pyramid-mcp
cd pyramid-mcp

# Install with development dependencies
make install

# Or manually with poetry
poetry install
poetry shell
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test types
make test-unit         # Unit tests only
make test-integration  # Integration tests only

# Run tests with pytest directly
poetry run pytest -v
poetry run pytest --cov=pyramid_mcp --cov-report=html
```

### Code Quality

```bash
# Run all quality checks
make check

# Individual commands
make format    # Format code with black
make lint      # Lint with ruff
make type      # Type check with mypy
```

### Making Changes

1. Create a new branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Add tests for new functionality
4. Run the test suite: `make test`
5. Check code quality: `make check`
6. Commit your changes: `git commit -m "Add your feature"`
7. Push and create a pull request

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Ways to Contribute

- 🐛 **Report bugs** by creating issues
- 💡 **Suggest features** through discussions
- 📖 **Improve documentation** 
- 🧪 **Write tests** to improve coverage
- 🔧 **Fix bugs** and implement features
- 📝 **Write examples** and tutorials

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Related Projects

- 🔗 [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk) - The official MCP Python SDK
- 🚀 [FastAPI MCP](https://github.com/your-org/fastapi-mcp) - Similar integration for FastAPI
- 🏗️ [Pyramid](https://trypyramid.com/) - The Pyramid web framework

## Acknowledgments

- Thanks to the [Pyramid](https://trypyramid.com/) team for the excellent web framework
- Inspired by [FastAPI MCP](https://github.com/your-org/fastapi-mcp)
- Built with the [Model Context Protocol](https://github.com/modelcontextprotocol/python-sdk)

---

**⭐ If you find this project useful, please consider giving it a star on GitHub! ⭐**