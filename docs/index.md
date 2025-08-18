# pyramid-mcp

[![Release](https://img.shields.io/github/v/release/tomas_correa/pyramid-mcp)](https://img.shields.io/github/v/release/tomas_correa/pyramid-mcp)
[![Build status](https://img.shields.io/github/actions/workflow/status/tomas_correa/pyramid-mcp/main.yml?branch=main)](https://github.com/tomas_correa/pyramid-mcp/actions/workflows/main.yml?query=branch%3Amain)
[![Commit activity](https://img.shields.io/github/commit-activity/m/tomas_correa/pyramid-mcp)](https://img.shields.io/github/commit-activity/m/tomas_correa/pyramid-mcp)
[![License](https://img.shields.io/github/license/tomas_correa/pyramid-mcp)](https://img.shields.io/github/license/tomas_correa/pyramid-mcp)

**pyramid-mcp** is a Pyramid plugin that exposes your web application's functionality as [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools, making them available to AI assistants like Claude, OpenAI GPT models, and other MCP-compatible clients.

## Key Features

- 🔌 **Easy Integration**: Simple `config.include('pyramid_mcp')` setup
- 🛠️ **Manual Tools**: Register custom tools with the `@tool` decorator
- 🔍 **Route Discovery**: Automatically convert API endpoints to MCP tools
- ⚙️ **Flexible Configuration**: Comprehensive settings via Pyramid configuration
- 🚀 **Production Ready**: Built for scalability with authentication and security features
- 📋 **Full MCP Support**: Implements the complete MCP specification

## Quick Start

### Installation

```bash
pip install pyramid-mcp
```

### Basic Usage

```python
from pyramid.config import Configurator
from pyramid_mcp import tool

# Configure your Pyramid app
settings = {
    'mcp.server_name': 'my-api',
    'mcp.mount_path': '/mcp',
    'mcp.route_discovery.enabled': 'true',
}

config = Configurator(settings=settings)

# Register a custom tool
@tool(name="greet", description="Greet someone")
def greet(name: str) -> str:
    return f"Hello, {name}!"

# Include pyramid-mcp plugin
config.include('pyramid_mcp')

# Your MCP tools are now available at /mcp
```

## Documentation

- **[Integration Guide](integration.md)** - Connect with Claude, OpenAI, and other AI platforms
- **[Publishing Guide](publishing.md)** - How to publish releases to PyPI with GitHub Actions
- **[API Reference](modules.md)** - Complete API documentation
- **[Examples](../examples/)** - Working examples and tutorials

## Use Cases

### API Tool Integration
Convert your existing REST APIs into tools that AI assistants can call:

```python
@view_config(route_name='users', renderer='json')
def list_users(request):
    return {"users": get_all_users()}

# Automatically becomes available as an MCP tool
```

### Custom Business Logic
Expose complex business operations as simple tools:

```python
@tool(name="process_order", description="Process a customer order")
def process_order(order_id: int, action: str) -> dict:
    # Your business logic here
    return {"order_id": order_id, "status": "processed"}
```

### Data Analysis Tools
Create tools for data queries and analysis:

```python
@tool(name="sales_report", description="Generate sales reports")
def generate_sales_report(start_date: str, end_date: str) -> dict:
    # Generate report logic
    return {"report": "sales_data.pdf", "total": 15000}
```

## Architecture

pyramid-mcp implements the Model Context Protocol specification, providing:

- **JSON-RPC 2.0** endpoints for MCP communication
- **Tool Registration** via decorators and route discovery
- **Schema Generation** from Python type hints
- **Error Handling** with proper MCP error responses
- **Streaming Support** via Server-Sent Events (SSE)

## Configuration Options

```python
settings = {
    # Server identification
    'mcp.server_name': 'my-server',
    'mcp.server_version': '1.0.0',
    
    # Endpoint configuration
    'mcp.mount_path': '/mcp',
    'mcp.enable_sse': 'true',
    'mcp.enable_http': 'true',
    
    # Route discovery
    'mcp.route_discovery.enabled': 'true',
    'mcp.route_discovery.include_patterns': 'api/*,admin/*',
    'mcp.route_discovery.exclude_patterns': 'internal/*',
    
    # Security and filtering
    'mcp.filter_forbidden_tools': 'true',  # Filter tools based on permissions (default: true)
}
```

## Contributing

We welcome contributions! Please see our [development rules](../README.md#development) for guidelines on:

- Code quality standards
- Testing requirements
- Documentation expectations
- Pull request process

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- 📖 **Documentation**: This site and inline code documentation
- 🐛 **Issues**: [GitHub Issues](https://github.com/tomas_correa/pyramid-mcp/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/tomas_correa/pyramid-mcp/discussions)
- 📧 **Email**: For private inquiries